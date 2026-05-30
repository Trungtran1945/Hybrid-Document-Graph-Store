"""
Document Engine for the Hybrid Document-Graph Store.
Provides text indexing and search using Whoosh (BM25F scoring).
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
    """Whoosh schema definition for patient symptom documents."""

    @staticmethod
    def create_schema() -> Schema:
        return Schema(
            patient_id=ID(stored=True, unique=True),
            chief_complaint=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            symptoms=TEXT(stored=True, analyzer=StemmingAnalyzer()),
            medical_history=TEXT(stored=True, analyzer=StemmingAnalyzer()),
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
    Document Engine using Whoosh for full-text search.
    Implements BM25F scoring for relevance ranking.
    """

    def __init__(self, index_path: Optional[str] = None, recreate: bool = False):
        self.index_path = Path(index_path) if index_path else config.processed_dir / "documents_index"
        self.schema = DocumentSchema.create_schema()
        self.index = None
        self._init_index(recreate)

    def _init_index(self, recreate: bool = False) -> None:
        """Initialize or open the Whoosh index."""
        self.index_path.mkdir(parents=True, exist_ok=True)

        if recreate or not index.exists_in(self.index_path):
            if recreate and index.exists_in(self.index_path):
                # Clear existing index
                import shutil
                shutil.rmtree(self.index_path)
                self.index_path.mkdir(parents=True, exist_ok=True)

            self.index = index.create_in(self.index_path, self.schema)
            print(f"[DocumentEngine] Created new index at {self.index_path}")
        else:
            self.index = index.open_dir(self.index_path)
            print(f"[DocumentEngine] Opened existing index at {self.index_path}")

    def index_documents(self, patients: List[PatientSymptom]) -> int:
        """Index a list of patient symptom documents."""
        writer = self.index.writer()
        count = 0

        for patient in patients:
            doc = {
                "patient_id": patient.patient_id,
                "chief_complaint": patient.chief_complaint,
                "symptoms": patient.symptoms,
                "medical_history": patient.medical_history,
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
        """
        Search patient documents by text query.
        Returns list of (document_dict, score) tuples.
        """
        start_time = time.time()
        results = []

        with self.index.searcher(weighting=BM25F()) as searcher:
            # Build query parser on multiple fields
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

                # Apply filters
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
        """Search and return as DocumentResult objects."""
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
        """Retrieve a specific document by patient_id."""
        with self.index.searcher() as searcher:
            results = searcher.search(self.schema.patient_id == patient_id, limit=1)
            if results:
                return dict(results[0])
        return None

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed documents."""
        with self.index.searcher() as searcher:
            doc_count = searcher.doc_count_all()
            return {
                "document_count": doc_count,
                "index_path": str(self.index_path),
                "schema_fields": list(self.schema.names()),
            }

    def analyze_query(self, query_text: str) -> Dict[str, Any]:
        """Analyze a query and return token information."""
        from whoosh.analysis import StemmingAnalyzer
        analyzer = StemmingAnalyzer()
        tokens = [token.text for token in analyzer(query_text)]
        return {
            "original_query": query_text,
            "tokens": tokens,
            "token_count": len(tokens),
        }

    def rebuild_index(self, patients: List[PatientSymptom]) -> int:
        """Completely rebuild the index from scratch."""
        if self.index:
            self.index.close()
        self._init_index(recreate=True)
        return self.index_documents(patients)


# ============================================================
# Document Index Manager
# ============================================================

class DocumentIndexManager:
    """Manages multiple document indices for distributed processing."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or config.processed_dir / "indices"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.indices: Dict[int, DocumentEngine] = {}

    def create_partition_index(
        self,
        partition_id: int,
        patients: List[PatientSymptom]
    ) -> DocumentEngine:
        """Create a document index for a specific partition."""
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
        """Search within a specific partition."""
        if partition_id not in self.indices:
            raise ValueError(f"Partition {partition_id} not found")
        return self.indices[partition_id].search(query_text, **kwargs)

    def search_all_partitions(
        self,
        query_text: str,
        max_results: int = 20
    ) -> List[Tuple[Dict[str, Any], float, int]]:
        """Search across all partitions and merge results."""
        all_results = []
        for partition_id, engine in self.indices.items():
            hits = engine.search(query_text, max_results=max_results // len(self.indices) + 1)
            for doc, score in hits:
                all_results.append((doc, score, partition_id))

        # Sort by score and take top N
        all_results.sort(key=lambda x: x[1], reverse=True)
        return all_results[:max_results]
