"""
Bộ Máy Tài Liệu (Document Engine) cho Hệ Thống Lưu Trữ Tài Liệu–Đồ Thị Kết Hợp (Hybrid Document-Graph Store).
Cung cấp chức năng đánh chỉ mục (indexing) và tìm kiếm văn bản bằng Whoosh (tính điểm BM25F).
"""
import os
import time
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, KEYWORD
from whoosh.analysis import StemmingAnalyzer, StandardAnalyzer
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.scoring import BM25F
from whoosh.writing import BufferedWriter

from ..core.config import config
from ..core.models import PatientSymptom, DocumentResult


class DocumentSchema:
    """Định nghĩa Schema Whoosh cho documents triệu chứng bệnh nhân.
    
    Xác định các trường và kiểu dữ liệu cho full-text index:
    - TEXT: chief_complaint, symptoms, medical_history, initial_diagnosis
    - KEYWORD: department, gender (dùng để filter)
    - NUMERIC: severity, age
    - ID: patient_id (unique)
    """

    @staticmethod
    def create_schema() -> Schema:
        """Tạo schema mặc định với StemmingAnalyzer cho các trường text."""
        return Schema(
            patient_id=ID(stored=True, unique=True),
            chief_complaint=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            symptoms=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            medical_history=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            current_medications=TEXT(stored=True),
            initial_diagnosis=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            department=KEYWORD(stored=True, lowercase=True),
            severity=NUMERIC(stored=True),
            gender=KEYWORD(stored=True, lowercase=True),
            age=NUMERIC(stored=True),
            admission_date=ID(stored=True),
            full_text=TEXT(analyzer=StemmingAnalyzer()),
        )

    @staticmethod
    def create_schema_from_config() -> Schema:
        """Tạo schema động dựa trên cấu hình từ config.yaml.
        
        Đọc danh sách searchable/filterable fields từ config,
        tự động chọn kiểu TEXT, KEYWORD hoặc NUMERIC tương ứng.
        """
        cfg = config.document_engine
        searchable = cfg.get("fields", {}).get("searchable", [])
        filterable = cfg.get("fields", {}).get("filterable", [])

        schema_dict = {
            "patient_id": ID(stored=True, unique=True),
        }
        for field in searchable:
            schema_dict[field] = TEXT(stored=True, analyzer=StemmingAnalyzer())
        for field in filterable:
            if field in ["severity", "age"]:
                schema_dict[field] = NUMERIC(stored=True)
            else:
                schema_dict[field] = KEYWORD(stored=True, lowercase=True)

        schema_dict["full_text"] = TEXT(analyzer=StemmingAnalyzer())
        return Schema(**schema_dict)


class DocumentEngine:
    """
    Document Engine sử dụng Whoosh cho full-text search.
    Implement BM25F scoring để xếp hạng relevance.
    Đây là một trong hai engine chính của hệ thống hybrid.
    """

    def __init__(self, index_path: Optional[str] = None, recreate: bool = False):
        """Khởi tạo Document Engine với đường dẫn index.
        
        Nếu không có index_path, dùng mặc định từ config.processed_dir.
        Nếu recreate=True, tạo lại index từ đầu.
        """
        self.index_path = Path(index_path) if index_path else config.processed_dir / "documents_index"
        self.schema = DocumentSchema.create_schema()
        self.index = None
        self._init_index(recreate)

    def _init_index(self, recreate: bool = False) -> None:
        """Khởi tạo hoặc mở index Whoosh có sẵn.
        
        Luồng hoạt động:
        Bước 1: Tạo thư mục index nếu chưa tồn tại.
        Bước 2: Nếu recreate=True, xóa index cũ và tạo mới.
        Bước 3: Nếu index đã tồn tại, mở bằng open_dir().
        """
        self.index_path.mkdir(parents=True, exist_ok=True)

        if recreate or not index.exists_in(self.index_path):
            if recreate and index.exists_in(self.index_path):
                # Xóa index cũ
                import shutil
                shutil.rmtree(self.index_path)
                self.index_path.mkdir(parents=True, exist_ok=True)

            self.index = index.create_in(self.index_path, self.schema)
            print(f"[DocumentEngine] Created new index at {self.index_path}")
        else:
            self.index = index.open_dir(self.index_path)
            print(f"[DocumentEngine] Opened existing index at {self.index_path}")

    def index_documents(self, patients: List[PatientSymptom]) -> int:
        """Đánh index danh sách documents bệnh nhân vào Whoosh.
        
        Luồng hoạt động:
        Bước 1: Tạo writer từ index.
        Bước 2: Với mỗi PatientSymptom, chuyển thành dict và add_document.
        Bước 3: Commit writer để lưu index.
        
        Trả về số lượng documents đã index.
        """
        writer = self.index.writer()
        count = 0

        for patient in patients:
            doc = {
                "patient_id": patient.patient_id,
                "chief_complaint": patient.chief_complaint,
                "symptoms": patient.symptoms,
                "medical_history": patient.medical_history,
                "current_medications": patient.current_medications,
                "initial_diagnosis": patient.initial_diagnosis,
                "department": patient.department.lower(),
                "severity": patient.severity,
                "gender": patient.gender.lower(),
                "age": patient.age,
                "admission_date": patient.admission_date,
                "full_text": patient.to_searchable_text(),
            }
            writer.add_document(**doc)
            count += 1

        writer.commit()
        print(f"[DocumentEngine] Indexed {count} documents")
        return count

    def search(
        self,
        query_text: str,
        max_results: int = 20,
        department: Optional[str] = None,
        min_severity: Optional[int] = None,
        gender: Optional[str] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Tìm kiếm documents bệnh nhân theo văn bản truy vấn.

        Luồng hoạt động:
        Bước 1: Tạo MultifieldParser trên nhiều trường (chief_complaint, symptoms...).
        Bước 2: Parse query_text thành Whoosh query object.
        Bước 3: Thực hiện search với BM25F scoring, lấy gấp đôi max_results.
        Bước 4: Lọc kết quả theo department/severity/gender nếu có.
        Bước 5: Trả về danh sách (document_dict, score).
        """
        start_time = time.time()
        results = []

        with self.index.searcher(weighting=BM25F()) as searcher:
            # Xây query parser trên nhiều trường văn bản
            parser = MultifieldParser(
                ["chief_complaint", "symptoms", "medical_history", "initial_diagnosis", "full_text"],
                schema=self.schema,
                group=OrGroup,
            )

            try:
                query = parser.parse(query_text)
            except Exception as e:
                print(f"[DocumentEngine] Query parse error: {e}")
                return []

            hits = searcher.search(query, limit=max_results * 2)

            for hit in hits:
                doc = dict(hit)

                # Áp dụng filters
                if department and doc.get("department", "").lower() != department.lower():
                    continue
                if min_severity and doc.get("severity", 0) < min_severity:
                    continue
                if gender and doc.get("gender", "").lower() != gender.lower():
                    continue

                results.append((doc, hit.score))

                if len(results) >= max_results:
                    break

        elapsed = (time.time() - start_time) * 1000
        print(f"[DocumentEngine] Search '{query_text}' returned {len(results)} results in {elapsed:.2f}ms")
        return results

    def search_with_patient(
        self,
        query_text: str,
        patients_map: Dict[str, PatientSymptom],
        max_results: int = 20,
        department: Optional[str] = None,
        min_severity: Optional[int] = None,
    ) -> List[DocumentResult]:
        """Tìm kiếm và trả về kết quả dưới dạng DocumentResult objects.
        
        Gọi search() để lấy hits, sau đó map patient_id -> PatientSymptom object.
        Graph_importance mặc định là 0.0 (chưa kết hợp với graph).
        """
        hits = self.search(query_text, max_results, department, min_severity)
        results = []
        for doc, score in hits:
            patient_id = doc.get("patient_id")
            if patient_id in patients_map:
                patient = patients_map[patient_id]
                results.append(DocumentResult(
                    patient=patient,
                    text_score=score,
                    graph_importance=0.0,
                    combined_score=score,
                ))
        return results

    def get_document_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Truy xuất một document theo patient_id.
        
        Dùng searcher để tìm kiếm chính xác theo trường patient_id (ID field).
        Trả về dict của document hoặc None nếu không tìm thấy.
        """
        with self.index.searcher() as searcher:
            results = searcher.search(self.schema.patient_id == patient_id, limit=1)
            if results:
                return dict(results[0])
        return None

    def get_index_stats(self) -> Dict[str, Any]:
        """Lấy thống kê về index: số lượng document, đường dẫn, schema fields."""
        with self.index.searcher() as searcher:
            doc_count = searcher.doc_count_all()
            return {
                "document_count": doc_count,
                "index_path": str(self.index_path),
                "schema_fields": list(self.schema.names()),
            }

    def analyze_query(self, query_text: str) -> Dict[str, Any]:
        """Phân tích truy vấn và trả về thông tin token.
        
        Dùng StemmingAnalyzer để tokenize query_text.
        Trả về: original_query, danh sách tokens, số lượng token.
        Hữu ích cho debug query parsing.
        """
        from whoosh.analysis import StemmingAnalyzer
        analyzer = StemmingAnalyzer()
        tokens = [token.text for token in analyzer(query_text)]
        return {
            "original_query": query_text,
            "tokens": tokens,
            "token_count": len(tokens),
        }

    def rebuild_index(self, patients: List[PatientSymptom]) -> int:
        """Xây dựng lại index từ đầu (recreate).
        
        Đóng index cũ nếu đang mở, gọi _init_index(recreate=True),
        sau đó index_documents lại từ đầu.
        """
        if self.index:
            self.index.close()
        self._init_index(recreate=True)
        return self.index_documents(patients)


# ============================================================
# Bộ Quản Lý Chỉ Mục Tài Liệu (Document Index Manager)
# ============================================================

class DocumentIndexManager:
    """Quản lý nhiều Document indices cho xử lý phân tán.
    
    Tạo riêng một Whoosh index cho mỗi partition của đồ thị.
    Hỗ trợ tìm kiếm trên một partition hoặc toàn bộ partitions
    với merge kết quả theo BM25F score.
    """

    def __init__(self, base_path: Optional[Path] = None):
        """Khởi tạo manager với đường dẫn thư mục chứa indices.
        
        Mỗi partition sẽ có thư mục index riêng: partition_0, partition_1, ...
        """
        self.base_path = base_path or config.processed_dir / "indices"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.indices: Dict[int, DocumentEngine] = {}

    def create_partition_index(
        self,
        partition_id: int,
        patients: List[PatientSymptom]
    ) -> DocumentEngine:
        """Tạo document index riêng cho một partition cụ thể.
        
        Luồng hoạt động:
        Bước 1: Tạo DocumentEngine với đường dẫn partition_{partition_id}.
        Bước 2: Index documents của partition đó.
        Bước 3: Lưu vào self.indices[partition_id].
        """
        index_path = self.base_path / f"partition_{partition_id}"
        engine = DocumentEngine(index_path=str(index_path), recreate=True)
        engine.index_documents(patients)
        self.indices[partition_id] = engine
        return engine

    def search_partition(
        self,
        partition_id: int,
        query_text: str,
        **kwargs
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Tìm kiếm trong một partition cụ thể.
        
        Raises ValueError nếu partition_id chưa được tạo.
        """
        if partition_id not in self.indices:
            raise ValueError(f"Partition {partition_id} not found")
        return self.indices[partition_id].search(query_text, **kwargs)

    def search_all_partitions(
        self,
        query_text: str,
        max_results: int = 20
    ) -> List[Tuple[Dict[str, Any], float, int]]:
        """Tìm kiếm trên tất cả partitions và gộp kết quả.
        
        Luồng hoạt động:
        Bước 1: Với mỗi partition, search với max_results phân bổ đều.
        Bước 2: Gom tất cả kết quả kèm partition_id.
        Bước 3: Sắp xếp theo score giảm dần, lấy top N.
        """
        all_results = []
        for partition_id, engine in self.indices.items():
            hits = engine.search(query_text, max_results=max_results // len(self.indices) + 1)
            for doc, score in hits:
                all_results.append((doc, score, partition_id))

        # Sắp xếp theo score và lấy top N
        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:max_results]
