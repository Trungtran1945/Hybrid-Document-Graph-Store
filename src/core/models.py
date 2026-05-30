"""
Data models for the Hybrid Document-Graph Store.
Defines all entity types used across Document and Graph engines.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class NodeType(Enum):
    DISEASE = "disease"
    SYMPTOM = "symptom"
    MEDICAL_FIELD = "medical_field"
    DRUG = "drug"


class EdgeType(Enum):
    DISEASE_TO_SYMPTOM = "disease_to_symptom"
    DISEASE_TO_DISEASE = "disease_to_disease"
    SYMPTOM_TO_SYMPTOM = "symptom_to_symptom"
    DISEASE_TO_FIELD = "disease_to_field"
    DISEASE_TO_DRUG = "disease_to_drug"


class PartitionMethod(Enum):
    METIS = "metis"
    VERTEX_CUT = "vertex_cut"
    EDGE_CUT = "edge_cut"


class TraversalAlgorithm(Enum):
    BFS = "bfs"
    DFS = "dfs"
    SHORTEST_PATH = "shortest_path"


# ============================================================
# Document Store Models
# ============================================================

@dataclass
class PatientSymptom:
    """A document representing a patient symptom record."""
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
    patient_id_int: int = 0  # For graph ID mapping

    def to_dict(self) -> Dict[str, Any]:
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
        """Combine all text fields for full-text indexing."""
        return f"{self.chief_complaint} {self.symptoms} {self.medical_history} {self.initial_diagnosis}"

    @property
    def text_content(self) -> str:
        return self.to_searchable_text()


@dataclass
class DocumentResult:
    """A document search result with score."""
    patient: PatientSymptom
    text_score: float
    graph_importance: float
    combined_score: float
    graph_distance: Optional[int] = None
    distance_label: Optional[str] = None
    partition_id: Optional[int] = None


# ============================================================
# Graph Store Models
# ============================================================

@dataclass
class GraphNode:
    """A node in the disease correlation graph."""
    node_id: str
    node_type: NodeType
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    partition_id: Optional[int] = None
    degree: int = 0
    centrality: float = 0.0

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        if isinstance(other, GraphNode):
            return self.node_id == other.node_id
        return False


@dataclass
class GraphEdge:
    """An edge in the disease correlation graph."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash((self.source_id, self.target_id))


@dataclass
class GraphPartition:
    """Represents a graph partition for distributed processing."""
    partition_id: int
    node_ids: List[str]
    internal_edges: int
    cut_edges: int
    nodes: List[GraphNode] = field(default_factory=list)


@dataclass
class TraversalResult:
    """Result of a graph traversal operation."""
    visited_nodes: List[GraphNode]
    paths: Dict[str, List[str]]
    distances: Dict[str, int]
    depth_distribution: Dict[int, int]
    partition_coverage: Dict[int, int]


# ============================================================
# Hybrid Query Models
# ============================================================

@dataclass
class HybridQuery:
    """A hybrid query combining document search and graph traversal."""
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
    """Metrics tracking the cost of joining document and graph engines."""
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
        total = self.document_scan_cost + self.graph_traversal_cost + self.join_operation_cost
        if total < 100:
            return "LOW"
        elif total < 1000:
            return "MEDIUM"
        return "HIGH"

    @property
    def summary(self) -> str:
        return (
            f"Document scan: {self.document_scan_cost:.2f} ops | "
            f"Graph traversal: {self.graph_traversal_cost:.2f} ops | "
            f"Join ops: {self.join_operation_cost:.2f} | "
            f"Total: {self.total_latency_ms:.2f}ms"
        )


@dataclass
class HybridQueryResult:
    """Final result of a hybrid document-graph query."""
    query: HybridQuery
    results: List[DocumentResult]
    join_cost: JoinCostMetrics
    execution_time_ms: float
    partitions_accessed: List[int]
    graph_statistics: Dict[str, Any]
