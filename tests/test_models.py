import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.models import (
    NodeType, EdgeType, PartitionMethod, TraversalAlgorithm,
    PatientSymptom, DocumentResult, GraphNode, GraphEdge,
    GraphPartition, TraversalResult, HybridQuery, JoinCostMetrics,
    HybridQueryResult
)


class TestNodeType:
    """Kiểm tra enum NodeType — các loại node trong đồ thị bệnh."""

    def test_values(self):
        """Kiểm tra giá trị của từng NodeType enum."""
        assert NodeType.DISEASE.value == "disease"
        assert NodeType.SYMPTOM.value == "symptom"
        assert NodeType.MEDICAL_FIELD.value == "medical_field"
        assert NodeType.DRUG.value == "drug"


class TestEdgeType:
    """Kiểm tra enum EdgeType — các loại quan hệ trong đồ thị."""

    def test_values(self):
        """Kiểm tra giá trị của từng EdgeType enum."""
        assert EdgeType.DISEASE_TO_SYMPTOM.value == "disease_to_symptom"
        assert EdgeType.DISEASE_TO_DISEASE.value == "disease_to_disease"
        assert EdgeType.SYMPTOM_TO_SYMPTOM.value == "symptom_to_symptom"
        assert EdgeType.DISEASE_TO_FIELD.value == "disease_to_field"
        assert EdgeType.DISEASE_TO_DRUG.value == "disease_to_drug"


class TestPatientSymptom:
    """Kiểm tra dataclass PatientSymptom — hồ sơ triệu chứng bệnh nhân."""

    def test_create(self):
        """Kiểm tra tạo PatientSymptom với đầy đủ thông tin."""
        p = PatientSymptom(
            patient_id="P00001", age=45, gender="Male",
            chief_complaint="chest pain for 3 days",
            symptoms="chest pain (moderate); shortness of breath (mild)",
            medical_history="Past: Hypertension",
            current_medications="Lisinopril 10mg daily",
            initial_diagnosis="Hypertension", severity=3,
            department="Cardiology", admission_date="2025-01-15"
        )
        assert p.patient_id == "P00001"
        assert p.to_dict()["age"] == 45
        assert "chest pain" in p.to_searchable_text()
        assert "Hypertension" in p.text_content


class TestGraphNode:
    """Kiểm tra dataclass GraphNode — node trong đồ thị bệnh."""

    def test_create(self):
        """Kiểm tra tạo GraphNode với thuộc tính đầy đủ."""
        n = GraphNode(
            node_id="disease_Hypertension",
            node_type=NodeType.DISEASE,
            label="Hypertension",
            properties={"field": "Cardiology"},
            partition_id=1, degree=5, centrality=0.8
        )
        assert n.node_id == "disease_Hypertension"
        assert n.node_type == NodeType.DISEASE
        assert n.label == "Hypertension"
        assert n.degree == 5

    def test_hash(self):
        """Kiểm tra hash và so sánh bằng của GraphNode (dựa trên node_id)."""
        n1 = GraphNode(node_id="d1", node_type=NodeType.DISEASE, label="D1")
        n2 = GraphNode(node_id="d1", node_type=NodeType.DISEASE, label="D1")
        assert hash(n1) == hash(n2)
        assert n1 == n2


class TestGraphEdge:
    """Kiểm tra dataclass GraphEdge — cạnh trong đồ thị bệnh."""

    def test_create(self):
        """Kiểm tra tạo GraphEdge với source, target, type, weight."""
        e = GraphEdge(
            source_id="disease_Hypertension",
            target_id="symptom_headache",
            edge_type=EdgeType.DISEASE_TO_SYMPTOM,
            weight=0.8
        )
        assert e.source_id == "disease_Hypertension"
        assert e.edge_type == EdgeType.DISEASE_TO_SYMPTOM


class TestHybridQuery:
    """Kiểm tra dataclass HybridQuery — truy vấn kết hợp Document + Graph."""

    def test_defaults(self):
        """Kiểm tra giá trị mặc định của HybridQuery."""
        q = HybridQuery(query_text="chest pain", target_field="Cardiology")
        assert q.query_text == "chest pain"
        assert q.max_graph_distance == 3
        assert q.text_weight == 0.5
        assert q.graph_weight == 0.5
        assert q.traversal_algorithm == TraversalAlgorithm.BFS

    def test_custom(self):
        """Kiểm tra HybridQuery với tham số tùy chỉnh."""
        q = HybridQuery(
            query_text="fever", target_field="Infectious_Disease",
            max_graph_distance=2, text_weight=0.7, graph_weight=0.3,
            traversal_algorithm=TraversalAlgorithm.DFS, min_severity=3
        )
        assert q.max_graph_distance == 2
        assert q.text_weight == 0.7
        assert q.min_severity == 3


class TestJoinCostMetrics:
    """Kiểm tra dataclass JoinCostMetrics — theo dõi chi phí Join."""

    def test_cost_tier_low(self):
        """Kiểm tra cost_tier = LOW khi tổng chi phí < 100."""
        m = JoinCostMetrics(
            document_scan_count=5, document_scan_cost=10,
            graph_traversal_nodes=10, graph_traversal_cost=20,
            join_operations=50, join_operation_cost=5,
            network_transfer_cost=2, total_latency_ms=30,
            partition_access_count=2, edge_cut_ratio=0.3
        )
        assert m.cost_tier == "LOW"

    def test_cost_tier_high(self):
        """Kiểm tra cost_tier = HIGH khi tổng chi phí >= 1000."""
        m = JoinCostMetrics(
            document_scan_count=500, document_scan_cost=500,
            graph_traversal_nodes=200, graph_traversal_cost=600,
            join_operations=1000, join_operation_cost=50,
            network_transfer_cost=100, total_latency_ms=800,
            partition_access_count=4, edge_cut_ratio=0.5
        )
        assert m.cost_tier == "HIGH"

    def test_to_dict(self):
        """Kiểm tra to_dict() trả về đúng định dạng với cost_tier và cost_summary."""
        m = JoinCostMetrics(
            document_scan_count=10, document_scan_cost=5.0,
            graph_traversal_nodes=20, graph_traversal_cost=15.0,
            join_operations=30, join_operation_cost=3.0,
            network_transfer_cost=1.0, total_latency_ms=25.0,
            partition_access_count=3, edge_cut_ratio=0.2
        )
        d = m.to_dict()
        assert "cost_tier" in d
        assert d["document_scan_cost"] == 5.0


class TestDocumentResult:
    """Kiểm tra dataclass DocumentResult — kết quả tìm kiếm hybrid."""

    def test_create(self):
        """Kiểm tra tạo DocumentResult với patient, scores, distance."""
        p = PatientSymptom(
            patient_id="P00001", age=30, gender="Female",
            chief_complaint="fever", symptoms="fever (high)",
            medical_history="None", current_medications="None",
            initial_diagnosis="COVID_19", severity=4,
            department="Infectious_Disease", admission_date="2025-03-01"
        )
        r = DocumentResult(
            patient=p, text_score=15.0, graph_importance=0.8,
            combined_score=0.65, graph_distance=1,
            distance_label="Direct Connection", partition_id=2
        )
        assert r.patient.patient_id == "P00001"
        assert r.text_score == 15.0
        assert r.graph_distance == 1
