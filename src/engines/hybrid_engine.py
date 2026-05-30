"""
Hybrid Query Engine - Combines Document and Graph engines.
Implements the join between text-search relevance and graph-distance importance.
"""
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import networkx as nx

from ..core.config import config
from ..core.models import (
    PatientSymptom, DocumentResult,
    GraphNode, TraversalResult,
    HybridQuery, JoinCostMetrics, HybridQueryResult,
    NodeType, TraversalAlgorithm
)
from .document_engine import DocumentEngine
from .graph_engine import GraphEngine


class HybridQueryEngine:
    """
    Hybrid Query Engine that combines:
    1. Document Engine (BM25F text search)
    2. Graph Engine (METIS-partitioned, BFS/DFS traversal)
    With join cost analysis and combined scoring.
    """

    def __init__(
        self,
        document_engine: Optional[DocumentEngine] = None,
        graph_engine: Optional[GraphEngine] = None,
    ):
        self.doc_engine = document_engine or DocumentEngine()
        self.graph_engine = graph_engine or GraphEngine()
        self.patients_map: Dict[str, PatientSymptom] = {}
        self.disease_to_field: Dict[str, str] = {}
        self.graph_distance_weights = config.get(
            "graph_engine", "graph_distance", "importance_weights", default={}
        )
        if not self.graph_distance_weights:
            self.graph_distance_weights = {
                "direct": 1.0,
                "depth_1": 0.8,
                "depth_2": 0.5,
                "depth_3": 0.2,
            }

    def load_data(
        self,
        patients: List[PatientSymptom],
        nodes: List[GraphNode],
        edges: List[Any]
    ) -> None:
        """Load and initialize both engines with data."""
        # Build patient map
        self.patients_map = {p.patient_id: p for p in patients}

        # Build disease-to-field mapping
        from ..core.models import EdgeType
        self.disease_to_field = {}
        for node in nodes:
            if node.node_type == NodeType.DISEASE:
                field = node.properties.get("medical_field", "")
                self.disease_to_field[node.node_id] = field

        # Build graph
        from ..core.models import GraphEdge as GE
        graph_edges = [e if isinstance(e, GE) else None for e in edges]
        graph_edges = [e for e in edges if e is not None]
        self.graph_engine.build_graph(nodes, graph_edges)

        # METIS partitioning
        n_parts = config.get("graph_engine", "partitioning", "n_parts", default=4)
        self.graph_engine.partition_with_metis(n_parts=n_parts)

        # Index documents
        self.doc_engine.index_documents(patients)

    # ============================================================
    # Hybrid Query Execution
    # ============================================================

    def execute_query(self, query: HybridQuery) -> HybridQueryResult:
        """
        Execute a hybrid query combining text search and graph traversal.
        Returns results with combined scoring and join cost metrics.
        """
        start_time = time.time()

        # Step 1: Text search on Document Engine
        doc_start = time.time()
        doc_hits = self.doc_engine.search(
            query_text=query.query_text,
            max_results=query.max_results * 3,  # Get more, filter later
            department=query.department_filter,
            min_severity=query.min_severity,
        )
        doc_scan_time = (time.time() - doc_start) * 1000

        # Step 2: Graph traversal from medical field
        graph_start = time.time()
        traversal_result = self._traverse_graph(query)
        graph_traversal_time = (time.time() - graph_start) * 1000

        # Step 3: Join - compute graph distance for each document
        join_start = time.time()
        results = self._join_and_score(
            doc_hits=doc_hits,
            traversal_result=traversal_result,
            query=query,
        )
        join_time = (time.time() - join_start) * 1000

        # Step 4: Build join cost metrics
        total_time = (time.time() - start_time) * 1000
        join_cost = self._compute_join_cost(
            doc_hits_count=len(doc_hits),
            doc_scan_time=doc_scan_time,
            graph_traversal_time=graph_traversal_time,
            join_time=join_time,
            total_time=total_time,
            traversal_result=traversal_result,
            results_count=len(results),
        )

        # Get partitions accessed
        partitions_accessed = list(traversal_result.partition_coverage.keys())

        result = HybridQueryResult(
            query=query,
            results=results,
            join_cost=join_cost,
            execution_time_ms=total_time,
            partitions_accessed=partitions_accessed,
            graph_statistics=self._get_graph_stats_for_query(traversal_result),
        )

        print(f"[HybridEngine] Query executed: {len(results)} results in {total_time:.2f}ms")
        return result

    def _traverse_graph(self, query: HybridQuery) -> TraversalResult:
        """Perform graph traversal based on the query's algorithm."""
        field_node_id = f"field_{query.target_field}"

        # Find the field node
        if field_node_id not in self.graph_engine.graph:
            # Try label matching
            for node_id, node in self.graph_engine.nodes_metadata.items():
                if node.label == query.target_field and node.node_type == NodeType.MEDICAL_FIELD:
                    field_node_id = node_id
                    break

        if field_node_id not in self.graph_engine.graph:
            # Return empty result if field not found
            return TraversalResult(
                visited_nodes=[],
                paths={},
                distances={},
                depth_distribution={},
                partition_coverage={}
            )

        # Execute traversal based on algorithm
        if query.traversal_algorithm == TraversalAlgorithm.DFS:
            return self.graph_engine.traverse_dfs(
                start_node=field_node_id,
                max_depth=query.max_graph_distance,
            )
        elif query.traversal_algorithm == TraversalAlgorithm.SHORTEST_PATH:
            # For shortest path, get all paths from field to all diseases
            return self.graph_engine.traverse_bfs(
                start_node=field_node_id,
                max_depth=query.max_graph_distance,
            )
        else:  # BFS (default)
            return self.graph_engine.traverse_bfs(
                start_node=field_node_id,
                max_depth=query.max_graph_distance,
            )

    def _join_and_score(
        self,
        doc_hits: List[Tuple[Dict[str, Any], float]],
        traversal_result: TraversalResult,
        query: HybridQuery,
    ) -> List[DocumentResult]:
        """
        Join document results with graph distances and compute combined scores.
        This is the core join operation between Document and Graph engines.
        """
        if not doc_hits:
            return []

        # Build distance lookup from traversal result
        node_distances: Dict[str, int] = {}
        for node_id, distance in traversal_result.distances.items():
            if node_id in self.graph_engine.nodes_metadata:
                node = self.graph_engine.nodes_metadata[node_id]
                if node.node_type == NodeType.DISEASE:
                    node_distances[node.label] = distance
                elif node.node_type == NodeType.SYMPTOM:
                    # Map symptom to its connected diseases
                    for neighbor in self.graph_engine.graph.neighbors(node_id):
                        if neighbor in self.graph_engine.nodes_metadata:
                            neighbor_node = self.graph_engine.nodes_metadata[neighbor]
                            if neighbor_node.node_type == NodeType.DISEASE:
                                # Set distance to disease = symptom_distance + 1
                                disease_dist = distance + 1
                                if neighbor_node.label not in node_distances or \
                                   node_distances[neighbor_node.label] > disease_dist:
                                    node_distances[neighbor_node.label] = disease_dist

        # Score each document
        scored_results = []
        for doc, text_score in doc_hits:
            diagnosis = doc.get("initial_diagnosis", "")
            distance = node_distances.get(diagnosis, None)

            # Filter by max graph distance
            if distance is not None and distance > query.max_graph_distance:
                continue

            # Compute graph importance based on distance
            if distance is not None:
                graph_importance = self._distance_to_importance(distance)
            else:
                # If disease not found in graph, assign minimum importance
                graph_importance = 0.1

            # Compute distance label
            if distance is not None:
                if distance == 0:
                    distance_label = "Direct (Field Node)"
                elif distance == 1:
                    distance_label = "Direct Connection"
                elif distance == 2:
                    distance_label = "2 Hops"
                else:
                    distance_label = f"{distance} Hops"
            else:
                distance_label = "Not in Graph"

            # Combined score
            combined = (
                query.text_weight * self._normalize_text_score(text_score) +
                query.graph_weight * graph_importance
            )

            # Get patient object
            patient_id = doc.get("patient_id")
            patient = self.patients_map.get(patient_id)

            if patient:
                result = DocumentResult(
                    patient=patient,
                    text_score=text_score,
                    graph_importance=graph_importance,
                    combined_score=combined,
                    graph_distance=distance,
                    distance_label=distance_label,
                    partition_id=self.graph_engine.partition_map.get(
                        self._find_node_id_for_disease(diagnosis), 0
                    ) if diagnosis else None,
                )
                scored_results.append(result)

        # Sort by combined score
        scored_results.sort(key=lambda x: x.combined_score, reverse=True)

        return scored_results[:query.max_results]

    def _distance_to_importance(self, distance: int) -> float:
        """Convert graph distance to importance score."""
        weights = self.graph_distance_weights
        if distance == 0:
            return weights.get("direct", 1.0)
        elif distance == 1:
            return weights.get("depth_1", 0.8)
        elif distance == 2:
            return weights.get("depth_2", 0.5)
        elif distance == 3:
            return weights.get("depth_3", 0.2)
        return 0.1

    def _normalize_text_score(self, score: float) -> float:
        """Normalize text score to 0-1 range."""
        # BM25 scores are typically in range 0-100
        return min(score / 20.0, 1.0)

    def _find_node_id_for_disease(self, disease_name: str) -> Optional[str]:
        """Find the graph node ID for a disease name."""
        for node_id, node in self.graph_engine.nodes_metadata.items():
            if node.label == disease_name and node.node_type == NodeType.DISEASE:
                return node_id
        return None

    def _compute_join_cost(
        self,
        doc_hits_count: int,
        doc_scan_time: float,
        graph_traversal_time: float,
        join_time: float,
        total_time: float,
        traversal_result: TraversalResult,
        results_count: int,
    ) -> JoinCostMetrics:
        """Compute comprehensive join cost metrics."""

        # Document scan cost (approximate)
        # In distributed systems: full scan = O(n), index scan = O(log n + k)
        doc_scan_cost = doc_hits_count * 0.1 + 10 * 0.1  # Index lookup cost

        # Graph traversal cost
        # BFS/DFS: O(V + E) where V = visited nodes, E = traversed edges
        visited_nodes = len(traversal_result.visited_nodes)
        traversed_edges = sum(
            len(self.graph_engine.graph.neighbors(n.node_id))
            for n in traversal_result.visited_nodes
            if n.node_id in self.graph_engine.graph
        )
        graph_traversal_cost = visited_nodes * 1.0 + traversed_edges * 0.5

        # Join operation cost
        # Hash join: O(N) for building hash table + O(M) for probing
        join_operation_cost = doc_hits_count * 0.05 + visited_nodes * 0.05

        # Network transfer cost (simulated for partitioned access)
        partition_access = len(traversal_result.partition_coverage)
        edge_cut = self.graph_engine.compute_edge_cut_ratio()
        network_cost = partition_access * 50.0 * edge_cut  # Simulated

        return JoinCostMetrics(
            document_scan_count=doc_hits_count,
            document_scan_cost=doc_scan_cost,
            graph_traversal_nodes=visited_nodes,
            graph_traversal_cost=graph_traversal_cost,
            join_operations=doc_hits_count * visited_nodes,
            join_operation_cost=join_operation_cost,
            network_transfer_cost=network_cost,
            total_latency_ms=total_time,
            partition_access_count=partition_access,
            edge_cut_ratio=edge_cut,
        )

    def _get_graph_stats_for_query(self, traversal_result: TraversalResult) -> Dict[str, Any]:
        """Get graph statistics relevant to the current query."""
        return {
            "nodes_visited": len(traversal_result.visited_nodes),
            "depth_distribution": traversal_result.depth_distribution,
            "partition_coverage": traversal_result.partition_coverage,
            "edge_cut_ratio": round(self.graph_engine.compute_edge_cut_ratio(), 4),
        }

    # ============================================================
    # Join Strategy Comparison
    # ============================================================

    def evaluate_join_strategies(
        self,
        query: HybridQuery
    ) -> Dict[str, Any]:
        """
        Evaluate different join strategies and compare their costs.
        """
        strategies = {}

        # Strategy 1: Filter After Join (NLJ-like)
        start = time.time()
        result_filter_after = self._join_filter_after(query)
        strategies["filter_after_join"] = {
            "execution_time_ms": (time.time() - start) * 1000,
            "results_count": len(result_filter_after.results),
            "join_cost": result_filter_after.join_cost.to_dict(),
        }

        # Strategy 2: Index Nested Loop (for small graph results)
        start = time.time()
        result_inl = self._join_index_nested_loop(query)
        strategies["index_nested_loop"] = {
            "execution_time_ms": (time.time() - start) * 1000,
            "results_count": len(result_inl.results),
            "join_cost": result_inl.join_cost.to_dict(),
        }

        # Strategy 3: Hash Join (for large results)
        start = time.time()
        result_hash = self._join_hash_join(query)
        strategies["hash_join"] = {
            "execution_time_ms": (time.time() - start) * 1000,
            "results_count": len(result_hash.results),
            "join_cost": result_hash.join_cost.to_dict(),
        }

        return strategies

    def _join_filter_after(self, query: HybridQuery) -> HybridQueryResult:
        """Join strategy: Join first, then filter by graph distance."""
        return self.execute_query(query)

    def _join_index_nested_loop(self, query: HybridQuery) -> HybridQueryResult:
        """Join strategy: For each graph node, probe document index."""
        # Get traversal result
        traversal_result = self._traverse_graph(query)

        # For each visited disease, search documents
        all_results = []
        for node in traversal_result.visited_nodes:
            if node.node_type == NodeType.DISEASE:
                hits = self.doc_engine.search(
                    query_text=node.label,
                    max_results=10,
                    department=query.department_filter,
                    min_severity=query.min_severity,
                )
                for doc, score in hits:
                    distance = traversal_result.distances.get(node.node_id, 999)
                    graph_importance = self._distance_to_importance(distance)
                    combined = (
                        query.text_weight * self._normalize_text_score(score) +
                        query.graph_weight * graph_importance
                    )
                    patient = self.patients_map.get(doc.get("patient_id"))
                    if patient:
                        all_results.append(DocumentResult(
                            patient=patient,
                            text_score=score,
                            graph_importance=graph_importance,
                            combined_score=combined,
                            graph_distance=distance,
                            partition_id=node.partition_id,
                        ))

        all_results.sort(key=lambda x: x.combined_score, reverse=True)
        results = all_results[:query.max_results]

        return HybridQueryResult(
            query=query,
            results=results,
            join_cost=JoinCostMetrics(
                document_scan_count=len(all_results),
                document_scan_cost=len(all_results) * 0.1,
                graph_traversal_nodes=len(traversal_result.visited_nodes),
                graph_traversal_cost=len(traversal_result.visited_nodes) * 1.0,
                join_operations=len(traversal_result.visited_nodes) * 10,
                join_operation_cost=len(traversal_result.visited_nodes) * 10 * 0.05,
                network_transfer_cost=0,
                total_latency_ms=0,
                partition_access_count=len(traversal_result.partition_coverage),
                edge_cut_ratio=self.graph_engine.compute_edge_cut_ratio(),
            ),
            execution_time_ms=0,
            partitions_accessed=list(traversal_result.partition_coverage.keys()),
            graph_statistics={},
        )

    def _join_hash_join(self, query: HybridQuery) -> HybridQueryResult:
        """Join strategy: Hash join on disease name."""
        # Build hash table from documents
        doc_hits = self.doc_engine.search(
            query_text=query.query_text,
            max_results=query.max_results * 3,
            department=query.department_filter,
            min_severity=query.min_severity,
        )

        # Build hash on diagnosis
        diagnosis_hash: Dict[str, List[Tuple[Dict, float]]] = {}
        for doc, score in doc_hits:
            diagnosis = doc.get("initial_diagnosis", "")
            if diagnosis not in diagnosis_hash:
                diagnosis_hash[diagnosis] = []
            diagnosis_hash[diagnosis].append((doc, score))

        # Traverse graph and probe hash
        traversal_result = self._traverse_graph(query)
        all_results = []

        for node in traversal_result.visited_nodes:
            if node.node_type == NodeType.DISEASE and node.label in diagnosis_hash:
                distance = traversal_result.distances.get(node.node_id, 999)
                graph_importance = self._distance_to_importance(distance)

                for doc, score in diagnosis_hash[node.label]:
                    combined = (
                        query.text_weight * self._normalize_text_score(score) +
                        query.graph_weight * graph_importance
                    )
                    patient = self.patients_map.get(doc.get("patient_id"))
                    if patient:
                        all_results.append(DocumentResult(
                            patient=patient,
                            text_score=score,
                            graph_importance=graph_importance,
                            combined_score=combined,
                            graph_distance=distance,
                            partition_id=node.partition_id,
                        ))

        all_results.sort(key=lambda x: x.combined_score, reverse=True)
        results = all_results[:query.max_results]

        return HybridQueryResult(
            query=query,
            results=results,
            join_cost=JoinCostMetrics(
                document_scan_count=len(doc_hits),
                document_scan_cost=len(doc_hits) * 0.1,
                graph_traversal_nodes=len(traversal_result.visited_nodes),
                graph_traversal_cost=len(traversal_result.visited_nodes) * 1.0,
                join_operations=len(diagnosis_hash),
                join_operation_cost=len(diagnosis_hash) * 0.05,
                network_transfer_cost=0,
                total_latency_ms=0,
                partition_access_count=len(traversal_result.partition_coverage),
                edge_cut_ratio=self.graph_engine.compute_edge_cut_ratio(),
            ),
            execution_time_ms=0,
            partitions_accessed=list(traversal_result.partition_coverage.keys()),
            graph_statistics={},
        )

    # ============================================================
    # Analysis Queries
    # ============================================================

    def analyze_join_cost(self, query: HybridQuery) -> Dict[str, Any]:
        """Comprehensive join cost analysis for a query."""
        result = self.execute_query(query)
        strategies = self.evaluate_join_strategies(query)

        return {
            "query": {
                "text": query.query_text,
                "target_field": query.target_field,
                "max_distance": query.max_graph_distance,
                "text_weight": query.text_weight,
                "graph_weight": query.graph_weight,
            },
            "default_result": {
                "results_count": len(result.results),
                "execution_time_ms": result.execution_time_ms,
                "join_cost": result.join_cost.to_dict(),
                "partitions_accessed": result.partitions_accessed,
            },
            "strategy_comparison": strategies,
            "recommendation": self._recommend_strategy(strategies),
        }

    def _recommend_strategy(self, strategies: Dict[str, Any]) -> str:
        """Recommend the best join strategy based on cost analysis."""
        best = min(strategies.items(), key=lambda x: x[1]["execution_time_ms"])
        return f"Recommended: {best[0]} (fastest: {best[1]['execution_time_ms']:.2f}ms)"

    def get_field_coverage(self) -> Dict[str, Dict[str, Any]]:
        """Get coverage statistics for each medical field."""
        coverage = {}
        for field in [
            "Cardiology", "Neurology", "Oncology", "Pulmonology",
            "Gastroenterology", "Orthopedics", "Infectious_Disease",
            "Endocrinology", "Nephrology", "Rheumatology"
        ]:
            diseases = self.graph_engine.get_disease_nodes_in_field(field, max_distance=3)
            symptoms = []
            for node_id in self.graph_engine.graph.nodes():
                if node_id in self.graph_engine.nodes_metadata:
                    node = self.graph_engine.nodes_metadata[node_id]
                    if node.node_type == NodeType.SYMPTOM:
                        try:
                            dist = nx.shortest_path_length(
                                self.graph_engine.graph,
                                f"field_{field}",
                                node_id
                            )
                            if dist <= 3:
                                symptoms.append(node.label)
                        except:
                            pass

            # Count patients in this field
            patient_count = sum(
                1 for p in self.patients_map.values()
                if p.department == field
            )

            coverage[field] = {
                "disease_count": len(diseases),
                "symptom_count": len(symptoms),
                "patient_count": patient_count,
                "diseases": [d[0].label for d in diseases[:5]],
            }

        return coverage



