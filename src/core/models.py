"""
Các mô hình dữ liệu (data models) cho Hệ Thống Lưu Trữ Tài Liệu–Đồ Thị Kết Hợp (Hybrid Document-Graph Store).
Định nghĩa tất cả các loại thực thể (entity) được dùng trong Document Engine và Graph Engine.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class NodeType(Enum):
    """Kiểu node trong đồ thị bệnh.
    - DISEASE: bệnh (VD: Hypertension, Diabetes)
    - SYMPTOM: triệu chứng (VD: chest pain, fever)
    - MEDICAL_FIELD: chuyên khoa (VD: Cardiology, Neurology)
    - DRUG: thuốc điều trị (VD: Metformin, Lisinopril)
    """
    DISEASE = "disease"
    SYMPTOM = "symptom"
    MEDICAL_FIELD = "medical_field"
    DRUG = "drug"


class EdgeType(Enum):
    """Kiểu cạnh (quan hệ) trong đồ thị bệnh.
    - DISEASE_TO_SYMPTOM: bệnh có triệu chứng
    - DISEASE_TO_DISEASE: tương quan giữa hai bệnh
    - SYMPTOM_TO_SYMPTOM: triệu chứng liên quan
    - DISEASE_TO_FIELD: bệnh thuộc chuyên khoa
    - DISEASE_TO_DRUG: bệnh được điều trị bằng thuốc
    """
    DISEASE_TO_SYMPTOM = "disease_to_symptom"
    DISEASE_TO_DISEASE = "disease_to_disease"
    SYMPTOM_TO_SYMPTOM = "symptom_to_symptom"
    DISEASE_TO_FIELD = "disease_to_field"
    DISEASE_TO_DRUG = "disease_to_drug"


class PartitionMethod(Enum):
    """Phương pháp phân vùng đồ thị.
    - METIS: thuật toán recursive bisection
    - VERTEX_CUT: cắt đỉnh (dành cho hypergraph)
    - EDGE_CUT: cắt cạnh (mặc định)
    """
    METIS = "metis"
    VERTEX_CUT = "vertex_cut"
    EDGE_CUT = "edge_cut"


class TraversalAlgorithm(Enum):
    """Thuật toán duyệt đồ thị.
    - BFS: Breadth-First Search (tìm theo chiều rộng)
    - DFS: Depth-First Search (tìm theo chiều sâu)
    - SHORTEST_PATH: đường đi ngắn nhất (Dijkstra)
    """
    BFS = "bfs"
    DFS = "dfs"
    SHORTEST_PATH = "shortest_path"


# ============================================================
# Mô Hình Kho Tài Liệu (Document Store Models)
# ============================================================

@dataclass
class PatientSymptom:
    """Hồ sơ triệu chứng bệnh nhân — một document trong Document Store.
    
    Chứa đầy đủ thông tin nhân khẩu học, triệu chứng, tiền sử bệnh,
    chẩn đoán ban đầu và thông tin nhập viện.
    Đây là đơn vị dữ liệu chính cho Document Engine (Whoosh).
    """
    patient_id: str
    age: int
    gender: str
    chief_complaint: str
    symptoms: str
    medical_history: str
    current_medications: str
    initial_diagnosis: str
    severity: int
    department: str
    admission_date: str
    patient_id_int: int = 0  # Ánh xạ ID cho đồ thị

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi bệnh nhân thành dict để serialize JSON.
        
        Dùng cho API response và lưu file.
        """
        return {
            "patient_id": self.patient_id,
            "age": self.age,
            "gender": self.gender,
            "chief_complaint": self.chief_complaint,
            "symptoms": self.symptoms,
            "medical_history": self.medical_history,
            "current_medications": self.current_medications,
            "initial_diagnosis": self.initial_diagnosis,
            "severity": self.severity,
            "department": self.department,
            "admission_date": self.admission_date,
        }

    def to_searchable_text(self) -> str:
        """Gộp các trường văn bản để đánh chỉ mục full-text search.
        
        Kết hợp chief_complaint, symptoms, medical_history, initial_diagnosis
        thành một chuỗi duy nhất cho Whoosh indexing.
        """
        return f"{self.chief_complaint} {self.symptoms} {self.medical_history} {self.initial_diagnosis}"

    @property
    def text_content(self) -> str:
        """Alias của to_searchable_text() — dùng trong hybrid scoring."""
        return self.to_searchable_text()


@dataclass
class DocumentResult:
    """Kết quả tìm kiếm kết hợp Document + Graph.
    
    Mỗi kết quả bao gồm:
    - patient: thông tin bệnh nhân
    - text_score: điểm BM25F từ Document Engine
    - graph_importance: điểm quan trọng từ Graph Engine
    - combined_score: điểm kết hợp (text_score * text_weight + graph_importance * graph_weight)
    - graph_distance: khoảng cách đồ thị từ bệnh đến chuyên khoa
    """
    patient: PatientSymptom
    text_score: float
    graph_importance: float
    combined_score: float
    graph_distance: Optional[int] = None
    distance_label: Optional[str] = None
    partition_id: Optional[int] = None


# ============================================================
# Mô Hình Kho Đồ Thị (Graph Store Models)
# ============================================================

@dataclass
class GraphNode:
    """Node trong đồ thị tương quan bệnh tật.
    
    Có 4 loại (NodeType): DISEASE, SYMPTOM, MEDICAL_FIELD, DRUG.
    Mỗi node có partition_id để xác định partition trong distributed system.
    degree và centrality dùng cho phân tích đồ thị.
    """
    node_id: str
    node_type: NodeType
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    partition_id: Optional[int] = None
    degree: int = 0
    centrality: float = 0.0

    def __hash__(self):
        """Hash dựa trên node_id để dùng trong set/dict."""
        return hash(self.node_id)

    def __eq__(self, other):
        """So sánh hai node dựa trên node_id."""
        if isinstance(other, GraphNode):
            return self.node_id == other.node_id
        return False


@dataclass
class GraphEdge:
    """Cạnh (quan hệ) trong đồ thị tương quan bệnh.
    
    Mỗi cạnh có source_id, target_id, edge_type (VD: disease_to_symptom),
    và weight thể hiện độ mạnh của quan hệ.
    """
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        """Hash dựa trên cặp (source_id, target_id) không thứ tự."""
        return hash((self.source_id, self.target_id))


@dataclass
class GraphPartition:
    """Đại diện một phân vùng đồ thị cho xử lý phân tán.
    
    Mỗi partition có:
    - node_ids: danh sách node thuộc partition này
    - internal_edges: số cạnh nội bộ (cả hai đầu trong cùng partition)
    - cut_edges: số cạnh cắt (đi ra partition khác)
    """
    partition_id: int
    node_ids: List[str]
    internal_edges: int
    cut_edges: int
    nodes: List[GraphNode] = field(default_factory=list)


@dataclass
class TraversalResult:
    """Kết quả của một thao tác duyệt đồ thị (BFS/DFS).
    
    Bao gồm:
    - visited_nodes: các node đã thăm
    - paths: đường đi từ start node đến mỗi node
    - distances: khoảng cách từ start node
    - depth_distribution: phân bố số lượng node theo độ sâu
    - partition_coverage: số node thuộc mỗi partition đã thăm
    """
    visited_nodes: List[GraphNode]
    paths: Dict[str, List[str]]
    distances: Dict[str, int]
    depth_distribution: Dict[int, int]
    partition_coverage: Dict[int, int]


# ============================================================
# Mô Hình Truy Vấn Lai (Hybrid Query Models)
# ============================================================

@dataclass
class HybridQuery:
    """Truy vấn kết hợp Document + Graph.
    
    Tham số:
    - query_text: văn bản tìm kiếm triệu chứng
    - target_field: chuyên khoa mục tiêu (VD: Cardiology)
    - max_graph_distance: độ sâu tối đa duyệt đồ thị
    - text_weight / graph_weight: trọng số cho điểm kết hợp
    - traversal_algorithm: BFS, DFS hoặc SHORTEST_PATH
    """
    query_text: str
    target_field: str
    max_graph_distance: int = 3
    max_results: int = 20
    text_weight: float = 0.5
    graph_weight: float = 0.5
    traversal_algorithm: TraversalAlgorithm = TraversalAlgorithm.BFS
    min_severity: Optional[int] = None
    department_filter: Optional[str] = None


@dataclass
class JoinCostMetrics:
    """Theo dõi chi phí Join giữa Document Engine và Graph Engine.
    
    Mỗi metric mô phỏng chi phí trong distributed database:
    - document_scan_cost: chi phí quét/tìm kiếm index
    - graph_traversal_cost: chi phí duyệt đồ thị
    - join_operation_cost: chi phí thực hiện join
    - network_transfer_cost: chi phí truyền mạng giữa các partition
    """
    document_scan_count: int
    document_scan_cost: float
    graph_traversal_nodes: int
    graph_traversal_cost: float
    join_operations: int
    join_operation_cost: float
    network_transfer_cost: float
    total_latency_ms: float
    partition_access_count: int
    edge_cut_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển JoinCostMetrics thành dict cho JSON response.
        Làm tròn các giá trị float đến 4 chữ số thập phân.
        Kèm cost_tier và summary để dễ đọc.
        """
        return {
            "document_scan_count": self.document_scan_count,
            "document_scan_cost": round(self.document_scan_cost, 4),
            "graph_traversal_nodes": self.graph_traversal_nodes,
            "graph_traversal_cost": round(self.graph_traversal_cost, 4),
            "join_operations": self.join_operations,
            "join_operation_cost": round(self.join_operation_cost, 4),
            "network_transfer_cost": round(self.network_transfer_cost, 4),
            "total_latency_ms": round(self.total_latency_ms, 4),
            "partition_access_count": self.partition_access_count,
            "edge_cut_ratio": round(self.edge_cut_ratio, 4),
            "cost_tier": self.cost_tier,
            "cost_summary": self.summary,
        }

    @property
    def cost_tier(self) -> str:
        """Phân loại chi phí: LOW (< 100), MEDIUM (< 1000), HIGH (>= 1000).
        Dùng để đánh giá mức độ tốn kém của truy vấn.
        """
        total = self.document_scan_cost + self.graph_traversal_cost + self.join_operation_cost
        if total < 100:
            return "LOW"
        elif total < 1000:
            return "MEDIUM"
        return "HIGH"

    @property
    def summary(self) -> str:
        """Tổng hợp nhanh các chi phí dạng chuỗi."""
        return (
            f"Document scan: {self.document_scan_cost:.2f} ops | "
            f"Graph traversal: {self.graph_traversal_cost:.2f} ops | "
            f"Join ops: {self.join_operation_cost:.2f} | "
            f"Total: {self.total_latency_ms:.2f}ms"
        )


@dataclass
class HybridQueryResult:
    """Kết quả cuối cùng của truy vấn hybrid.
    
    Bao gồm:
    - query: truy vấn gốc
    - results: danh sách DocumentResult đã sắp xếp theo combined_score
    - join_cost: chi phí join giữa hai engine
    - execution_time_ms: thời gian thực thi tổng thể
    - partitions_accessed: các partition đã truy cập
    - graph_statistics: thống kê đồ thị liên quan đến truy vấn
    """
    query: HybridQuery
    results: List[DocumentResult]
    join_cost: JoinCostMetrics
    execution_time_ms: float
    partitions_accessed: List[int]
    graph_statistics: Dict[str, Any]
