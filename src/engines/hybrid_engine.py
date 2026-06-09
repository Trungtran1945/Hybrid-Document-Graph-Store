"""
Bộ Máy Truy Vấn Lai (Hybrid Query Engine) - Kết hợp Document Engine và Graph Engine.
Cài đặt phép kết nối (join) giữa điểm phù hợp tìm kiếm văn bản (text-search relevance) và tầm quan trọng khoảng cách đồ thị (graph-distance importance).
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
    Hybrid Query Engine — kết hợp Document Engine và Graph Engine.
    
    Các chức năng chính:
    1. Document Engine (BM25F text search) với Whoosh
    2. Graph Engine (METIS-partitioned, BFS/DFS traversal) với NetworkX
    3. Join cost analysis với 3 chiến lược: filter_after_join, index_nested_loop, hash_join
    4. Combined scoring: text_score * text_weight + graph_importance * graph_weight
    """

    def __init__(
        self,
        document_engine: Optional[DocumentEngine] = None,
        graph_engine: Optional[GraphEngine] = None,
    ):
        """Khởi tạo Hybrid Engine với DocumentEngine và GraphEngine.
        
        Nếu không truyền vào, tạo mới mặc định.
        Khởi tạo trọng số graph distance từ config.
        """
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
        """Tải và khởi tạo cả hai engine với dữ liệu.
        
        Luồng hoạt động:
        Bước 1: Xây patients_map (patient_id -> PatientSymptom).
        Bước 2: Xây disease_to_field mapping cho hybrid join.
        Bước 3: Xây dựng NetworkX graph từ nodes và edges.
        Bước 4: Phân vùng đồ thị bằng METIS.
        Bước 5: Index documents vào Whoosh.
        """
        # Xây patient map
        self.patients_map = {p.patient_id: p for p in patients}

        # Xây disease-to-field mapping
        from ..core.models import EdgeType
        self.disease_to_field = {}
        for node in nodes:
            if node.node_type == NodeType.DISEASE:
                field = node.properties.get("medical_field", "")
                self.disease_to_field[node.node_id] = field

        # Xây graph
        from ..core.models import GraphEdge as GE
        graph_edges = [e if isinstance(e, GE) else None for e in edges]
        graph_edges = [e for e in edges if e is not None]
        self.graph_engine.build_graph(nodes, graph_edges)

        # Phân vùng METIS
        n_parts = config.get("graph_engine", "partitioning", "n_parts", default=4)
        self.graph_engine.partition_with_metis(n_parts=n_parts)

        # Đánh chỉ mục (index) cho các tài liệu (documents)
        self.doc_engine.index_documents(patients)

    # ============================================================
    # Thực Thi Truy Vấn Lai (Hybrid Query Execution)
    # ============================================================

    def execute_query(self, query: HybridQuery) -> HybridQueryResult:
        """Thực thi truy vấn hybrid kết hợp text search và graph traversal.

        Luồng hoạt động:
        Bước 1 (Document Search): Tìm kiếm BM25F trên Whoosh index.
            - Lấy gấp 3 lần max_results để có dư cho lọc graph sau.
        Bước 2 (Graph Traversal): Duyệt đồ thị từ medical field target.
            - BFS/DFS từ field_node_id với max_graph_distance.
        Bước 3 (Join & Score): Kết hợp kết quả hai engine.
            - Với mỗi document hit, tính graph_distance và combined_score.
        Bước 4 (Cost Metrics): Tính join cost và thống kê.
        
        Trả về HybridQueryResult.
        """
        start_time = time.time()

        # Bước 1: Text search trên Document Engine
        doc_start = time.time()
        doc_hits = self.doc_engine.search(
            query_text=query.query_text,
            max_results=query.max_results * 3,  # Lấy nhiều hơn, lọc sau
            department=query.department_filter,
            min_severity=query.min_severity,
        )
        doc_scan_time = (time.time() - doc_start) * 1000

        # Bước 2: Graph traversal từ medical field
        graph_start = time.time()
        traversal_result = self._traverse_graph(query)
        graph_traversal_time = (time.time() - graph_start) * 1000

        # Bước 3: Join - tính graph distance cho mỗi document
        join_start = time.time()
        results = self._join_and_score(
            doc_hits=doc_hits,
            traversal_result=traversal_result,
            query=query,
        )
        join_time = (time.time() - join_start) * 1000

        # Bước 4: Xây join cost metrics
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

        # Lấy danh sách partitions đã truy cập
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
        """Thực hiện duyệt đồ thị dựa trên thuật toán của query.
        
        Xác định field_node_id từ query.target_field.
        Hỗ trợ 3 thuật toán: BFS (mặc định), DFS, SHORTEST_PATH.
        Nếu field không tồn tại, trả về TraversalResult rỗng.
        """
        field_node_id = f"field_{query.target_field}"

        # Tìm field node
        if field_node_id not in self.graph_engine.graph:
            # Thử matching theo label
            for node_id, node in self.graph_engine.nodes_metadata.items():
                if node.label == query.target_field and node.node_type == NodeType.MEDICAL_FIELD:
                    field_node_id = node_id
                    break

        if field_node_id not in self.graph_engine.graph:
            # Trả về rỗng nếu không tìm thấy field
            return TraversalResult(
                visited_nodes=[],
                paths={},
                distances={},
                depth_distribution={},
                partition_coverage={}
            )

        # Thực thi traversal theo thuật toán
        if query.traversal_algorithm == TraversalAlgorithm.DFS:
            return self.graph_engine.traverse_dfs(
                start_node=field_node_id,
                max_depth=query.max_graph_distance,
            )
        elif query.traversal_algorithm == TraversalAlgorithm.SHORTEST_PATH:
            # Với shortest path, lấy tất cả paths từ field đến diseases
            return self.graph_engine.traverse_bfs(
                start_node=field_node_id,
                max_depth=query.max_graph_distance,
            )
        else:  # BFS (mặc định)
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
        """Join kết quả documents với graph distances và tính combined score.
        
        Đây là core join operation giữa Document Engine và Graph Engine.
        
        Luồng hoạt động:
        Bước 1: Xây distance lookup từ traversal result.
            - Disease nodes: lấy distance trực tiếp.
            - Symptom nodes: map sang disease neighbors (distance + 1).
        Bước 2: Với mỗi document hit:
            - Tra diagnosis name trong node_distances.
            - Nếu distance > max_graph_distance -> skip (filter).
            - Tính graph_importance từ distance.
            - Tính combined_score = text_weight * norm(text_score) + graph_weight * graph_importance.
        Bước 3: Sắp xếp theo combined_score giảm dần, lấy top max_results.
        """
        if not doc_hits:
            return []

        # Xây distance lookup từ traversal result
        node_distances: Dict[str, int] = {}
        for node_id, distance in traversal_result.distances.items():
            if node_id in self.graph_engine.nodes_metadata:
                node = self.graph_engine.nodes_metadata[node_id]
                if node.node_type == NodeType.DISEASE:
                    node_distances[node.label] = distance
                elif node.node_type == NodeType.SYMPTOM:
                    # Map symptom sang diseases kết nối
                    for neighbor in self.graph_engine.graph.neighbors(node_id):
                        if neighbor in self.graph_engine.nodes_metadata:
                            neighbor_node = self.graph_engine.nodes_metadata[neighbor]
                            if neighbor_node.node_type == NodeType.DISEASE:
                                disease_dist = distance + 1
                                if neighbor_node.label not in node_distances or \
                                   node_distances[neighbor_node.label] > disease_dist:
                                    node_distances[neighbor_node.label] = disease_dist

        # Tính điểm cho mỗi document
        scored_results = []
        for doc, text_score in doc_hits:
            diagnosis = doc.get("initial_diagnosis", "")
            distance = node_distances.get(diagnosis, None)

            # Lọc theo max graph distance
            if distance is not None and distance > query.max_graph_distance:
                continue

            # Tính graph importance dựa trên distance
            if distance is not None:
                graph_importance = self._distance_to_importance(distance)
            else:
                # Nếu bệnh không có trong graph, gán importance tối thiểu
                graph_importance = 0.1

            # Tính distance label
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

            # Điểm kết hợp (combined score) giữa văn bản và đồ thị
            combined = (
                query.text_weight * self._normalize_text_score(text_score) +
                query.graph_weight * graph_importance
            )

            # Lấy patient object
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

        # Sắp xếp theo combined score
        scored_results.sort(key=lambda x: x.combined_score, reverse=True)

        return scored_results[:query.max_results]

    def _distance_to_importance(self, distance: int) -> float:
        """Chuyển đổi graph distance thành importance score (0-1).
        
        Quy tắc:
        - distance=0 (field node): 1.0
        - distance=1 (direct connection): 0.8
        - distance=2: 0.5
        - distance=3: 0.2
        - distance>3: 0.1 (minimum)
        """
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
        """Chuẩn hóa BM25 score về khoảng 0-1.
        
        BM25 scores thường trong khoảng 0-100,
        chia cho 20 để đưa về ~0-5, dùng min() để giới hạn ở 1.0.
        """
        return min(score / 20.0, 1.0)

    def _find_node_id_for_disease(self, disease_name: str) -> Optional[str]:
        """Tìm graph node ID từ tên bệnh.
        
        Duyệt nodes_metadata, match label và node_type == DISEASE.
        Trả về node_id hoặc None nếu không tìm thấy.
        """
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
        """Tính toán chi phí Join giữa Document và Graph engines.
        
        Mô phỏng chi phí trong distributed database:
        - Document scan cost: O(log n + k) với index lookup
        - Graph traversal cost: O(V + E) với BFS/DFS
        - Join operation cost: O(N + M) với hash join
        - Network transfer cost: dựa trên partition_access và edge_cut_ratio
        """
        # Chi phí quét tài liệu (document scan) - ước lượng
        # Trong hệ thống phân tán (distributed systems): quét toàn bộ (full scan) tốn O(n), quét chỉ mục (index scan) tốn O(log n + k)
        doc_scan_cost = doc_hits_count * 0.1 + 10 * 0.1  # Chi phí tra cứu chỉ mục (index lookup cost)

        # Chi phí duyệt đồ thị (graph traversal)
        # BFS/DFS: O(V + E) với V = số nút đã thăm (visited nodes), E = số cạnh đã duyệt (traversed edges)
        visited_nodes = len(traversal_result.visited_nodes)
        traversed_edges = sum(
            len(list(self.graph_engine.graph.neighbors(n.node_id)))
            for n in traversal_result.visited_nodes
            if n.node_id in self.graph_engine.graph
        )
        graph_traversal_cost = visited_nodes * 1.0 + traversed_edges * 0.5

        # Chi phí thao tác kết nối (join operation)
        # Kết nối bằng bảng băm (Hash join): O(N) xây bảng băm (hash table) + O(M) dò tìm (probing)
        join_operation_cost = doc_hits_count * 0.05 + visited_nodes * 0.05

        # Chi phí network transfer (mô phỏng cho partitioned access)
        partition_access = len(traversal_result.partition_coverage)
        edge_cut = self.graph_engine.compute_edge_cut_ratio()
        network_cost = partition_access * 50.0 * edge_cut  # Mô phỏng

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
        """Lấy thống kê đồ thị liên quan đến truy vấn hiện tại.
        
        Bao gồm: số nodes đã thăm, phân bố độ sâu, partition coverage, edge-cut ratio.
        """
        return {
            "nodes_visited": len(traversal_result.visited_nodes),
            "depth_distribution": traversal_result.depth_distribution,
            "partition_coverage": traversal_result.partition_coverage,
            "edge_cut_ratio": round(self.graph_engine.compute_edge_cut_ratio(), 4),
        }

    # ============================================================
    # So Sánh Chiến Lược Kết Nối (Join Strategy Comparison)
    # ============================================================

    def evaluate_join_strategies(
        self,
        query: HybridQuery
    ) -> Dict[str, Any]:
        """Đánh giá và so sánh 3 chiến lược Join khác nhau.
        
        Các chiến lược:
        1. filter_after_join: Join trước, lọc theo graph distance sau (giống Nested Loop Join).
        2. index_nested_loop: Với mỗi disease node, probe document index riêng.
        3. hash_join: Xây hash table trên diagnosis, probe từ traversal result.
        
        Trả về execution_time_ms, results_count, join_cost cho mỗi strategy.
        """
        strategies = {}

        # Strategy 1: Filter After Join (giống NLJ)
        start = time.time()
        result_filter_after = self._join_filter_after(query)
        strategies["filter_after_join"] = {
            "execution_time_ms": (time.time() - start) * 1000,
            "results_count": len(result_filter_after.results),
            "join_cost": result_filter_after.join_cost.to_dict(),
        }

        # Strategy 2: Index Nested Loop (cho graph results nhỏ)
        start = time.time()
        result_inl = self._join_index_nested_loop(query)
        strategies["index_nested_loop"] = {
            "execution_time_ms": (time.time() - start) * 1000,
            "results_count": len(result_inl.results),
            "join_cost": result_inl.join_cost.to_dict(),
        }

        # Strategy 3: Hash Join (cho results lớn)
        start = time.time()
        result_hash = self._join_hash_join(query)
        strategies["hash_join"] = {
            "execution_time_ms": (time.time() - start) * 1000,
            "results_count": len(result_hash.results),
            "join_cost": result_hash.join_cost.to_dict(),
        }

        return strategies

    def _join_filter_after(self, query: HybridQuery) -> HybridQueryResult:
        """Chiến lược Join: Join trước (tất cả documents), lọc theo graph distance sau.
        
        Tương tự Nested Loop Join trong relational databases.
        Đơn giản nhưng có thể tốn kém nếu có nhiều documents không liên quan.
        """
        return self.execute_query(query)

    def _join_index_nested_loop(self, query: HybridQuery) -> HybridQueryResult:
        """Chiến lược Join: Với mỗi graph node, probe document index riêng.
        
        Luồng hoạt động:
        Bước 1: Duyệt đồ thị để lấy visited disease nodes.
        Bước 2: Với mỗi disease node, search documents theo tên bệnh.
        Bước 3: Tính combined score và gộp kết quả.
        
        Hiệu quả khi traversal result nhỏ (ít disease nodes).
        """
        # Lấy traversal result
        traversal_result = self._traverse_graph(query)

        # Với mỗi disease visited, search documents
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
        """Chiến lược Join: Hash join trên disease name.
        
        Luồng hoạt động:
        Bước 1: Document search lấy tất cả hits.
        Bước 2: Xây hash table: diagnosis -> [(doc, score), ...].
        Bước 3: Duyệt đồ thị, probe hash table theo disease label.
        
        Hiệu quả khi có nhiều documents và graph traversal vừa phải.
        Hash join là O(N + M) với N = documents, M = graph nodes.
        """
        # Xây hash table từ documents
        doc_hits = self.doc_engine.search(
            query_text=query.query_text,
            max_results=query.max_results * 3,
            department=query.department_filter,
            min_severity=query.min_severity,
        )

        # Xây hash trên diagnosis
        diagnosis_hash: Dict[str, List[Tuple[Dict, float]]] = {}
        for doc, score in doc_hits:
            diagnosis = doc.get("initial_diagnosis", "")
            if diagnosis not in diagnosis_hash:
                diagnosis_hash[diagnosis] = []
            diagnosis_hash[diagnosis].append((doc, score))

        # Duyệt đồ thị và probe hash
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
    # Truy Vấn Phân Tích (Analysis Queries)
    # ============================================================

    def analyze_join_cost(self, query: HybridQuery) -> Dict[str, Any]:
        """Phân tích chi phí Join toàn diện cho một truy vấn.
        
        Luồng hoạt động:
        Bước 1: Thực thi query mặc định (filter_after_join).
        Bước 2: Đánh giá 3 chiến lược Join khác nhau.
        Bước 3: So sánh và khuyến nghị chiến lược tốt nhất.
        """
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
        """Khuyến nghị chiến lược Join tốt nhất dựa trên execution_time_ms.
        
        Chọn strategy có thời gian thực thi nhỏ nhất.
        """
        best = min(strategies.items(), key=lambda x: x[1]["execution_time_ms"])
        return f"Recommended: {best[0]} (fastest: {best[1]['execution_time_ms']:.2f}ms)"

    def get_field_coverage(self) -> Dict[str, Dict[str, Any]]:
        """Lấy thống kê coverage cho từng chuyên khoa y tế.
        
        Mỗi chuyên khoa trả về:
        - disease_count: số bệnh trong đồ thị
        - symptom_count: số triệu chứng trong đồ thị
        - patient_count: số bệnh nhân trong documents
        - diseases: tên 5 bệnh đầu tiên
        
        Dùng nx.shortest_path_length để xác định triệu chứng thuộc field nào.
        """
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

            # Đếm bệnh nhân trong field này
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



