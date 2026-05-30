"""
Graph Engine for the Hybrid Document-Graph Store.
Provides graph operations with NetworkX, METIS partitioning,
and distributed traversal algorithms (BFS, DFS, Shortest Path).
"""
import time
import random
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple, Callable
from collections import deque

import networkx as nx
import numpy as np

from ..core.config import config
from ..core.models import (
    GraphNode, GraphEdge, GraphPartition,
    TraversalResult, NodeType, EdgeType,
    TraversalAlgorithm
)


class GraphEngine:
    """
    Graph Engine using NetworkX with METIS partitioning support.
    Supports BFS, DFS, and Shortest Path traversal.
    """

    def __init__(self, graph_path: Optional[str] = None):
        self.graph_path = Path(graph_path) if graph_path else config.processed_dir / "graph_data.gpickle"
        self.graph: Optional[nx.Graph] = None
        self.nodes_metadata: Dict[str, GraphNode] = {}
        self.edges_metadata: Dict[Tuple[str, str], GraphEdge] = {}
        self.partition_map: Dict[str, int] = {}
        self.partitions: Dict[int, GraphPartition] = {}
        self.metis_partitions: Optional[Dict[str, int]] = None

    # ============================================================
    # Graph Loading & Building
    # ============================================================

    def build_graph(self, nodes: List[GraphNode], edges: List[GraphEdge]) -> nx.Graph:
        """Build NetworkX graph from node and edge lists."""
        self.graph = nx.Graph()
        self.nodes_metadata = {}
        self.edges_metadata = {}

        # Add nodes
        for node in nodes:
            self.graph.add_node(
                node.node_id,
                node_type=node.node_type.value,
                label=node.label,
                partition_id=0,
                **node.properties
            )
            self.nodes_metadata[node.node_id] = node

        # Add edges with weights
        for edge in edges:
            if self.graph.has_edge(edge.source_id, edge.target_id):
                # Update weight if edge exists
                existing = self.graph[edge.source_id][edge.target_id]
                existing["weight"] = max(existing.get("weight", 1.0), edge.weight)
            else:
                self.graph.add_edge(
                    edge.source_id,
                    edge.target_id,
                    edge_type=edge.edge_type.value,
                    weight=edge.weight
                )
            key = (min(edge.source_id, edge.target_id), max(edge.source_id, edge.target_id))
            self.edges_metadata[key] = edge

        # Set default partition to 0 for all nodes
        for node_id in self.graph.nodes():
            self.partition_map[node_id] = 0
            if node_id in self.nodes_metadata:
                self.nodes_metadata[node_id].partition_id = 0

        print(f"[GraphEngine] Built graph: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")
        return self.graph

    def save_graph(self) -> None:
        """Save graph to file for persistence."""
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "graph_data": nx.node_link_data(self.graph),
            "partition_map": self.partition_map,
            "nodes_metadata": {
                k: {
                    "node_id": v.node_id,
                    "node_type": v.node_type.value,
                    "label": v.label,
                    "properties": v.properties,
                    "partition_id": v.partition_id,
                    "degree": v.degree,
                    "centrality": v.centrality,
                }
                for k, v in self.nodes_metadata.items()
            }
        }
        with open(self.graph_path, "wb") as f:
            pickle.dump(data, f)
        print(f"[GraphEngine] Saved graph to {self.graph_path}")

    def load_graph(self) -> bool:
        """Load graph from file."""
        if not self.graph_path.exists():
            print(f"[GraphEngine] No saved graph found at {self.graph_path}")
            return False

        with open(self.graph_path, "rb") as f:
            data = pickle.load(f)

        self.graph = nx.node_link_graph(data["graph_data"])
        self.partition_map = data.get("partition_map", {})
        self.nodes_metadata = {}

        for node_id, meta in data.get("nodes_metadata", {}).items():
            self.nodes_metadata[node_id] = GraphNode(
                node_id=meta["node_id"],
                node_type=NodeType(meta["node_type"]),
                label=meta["label"],
                properties=meta.get("properties", {}),
                partition_id=meta.get("partition_id", 0),
                degree=meta.get("degree", 0),
                centrality=meta.get("centrality", 0.0),
            )

        # Update graph node attributes
        for node_id in self.graph.nodes():
            if node_id in self.nodes_metadata:
                self.graph.nodes[node_id]["partition_id"] = self.nodes_metadata[node_id].partition_id

        print(f"[GraphEngine] Loaded graph: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")
        return True

    # ============================================================
    # METIS Graph Partitioning
    # ============================================================

    def partition_with_metis(self, n_parts: int = 4) -> Dict[str, int]:
        """
        Partition the graph using METIS-style recursive bisection.
        Simulates METIS behavior using spectral/split-based partitioning.
        """
        if self.graph is None:
            raise ValueError("Graph not loaded or built")

        print(f"[GraphEngine] Performing METIS-style partitioning into {n_parts} parts...")

        # Convert to METIS format
        n = self.graph.number_of_nodes()
        node_list = list(self.graph.nodes())
        node_to_idx = {node: i for i, node in enumerate(node_list)}

        # Build adjacency for METIS
        adj_list = [[] for _ in range(n)]
        for u, v in self.graph.edges():
            adj_list[node_to_idx[u]].append(node_to_idx[v] + 1)
            adj_list[node_to_idx[v]].append(node_to_idx[u] + 1)

        try:
            import metis

            # Create METIS graph
            G = metis.Graph()
            for i, neighbors in enumerate(adj_list):
                G.add_vertex(i, neighbors)

            # Run METIS partitioning
            _, parts = metis.part_graph(G, n_parts)

            self.metis_partitions = {}
            for i, node_id in enumerate(node_list):
                partition_id = int(parts[i])
                self.metis_partitions[node_id] = partition_id
                self.partition_map[node_id] = partition_id
                if node_id in self.nodes_metadata:
                    self.nodes_metadata[node_id].partition_id = partition_id

            print(f"[GraphEngine] METIS partitioning complete: {n_parts} partitions")

            # Validate METIS output: check that nodes are actually distributed
            unique_parts = set(self.partition_map.values())
            if len(unique_parts) < 2:
                print(f"[GraphEngine] WARNING: METIS returned only {len(unique_parts)} partition(s), falling back...")
                self._partition_alternative(n_parts)
            elif len(unique_parts) != n_parts:
                print(f"[GraphEngine] WARNING: METIS returned {len(unique_parts)} partitions instead of {n_parts}, falling back...")
                self._partition_alternative(n_parts)

        except ImportError:
            print("[GraphEngine] METIS not available, using alternative partitioning...")
            self._partition_alternative(n_parts)
        except Exception as e:
            print(f"[GraphEngine] METIS failed ({e}), using alternative partitioning...")
            self._partition_alternative(n_parts)

        # Calculate partition statistics
        self._compute_partition_stats(n_parts)
        return self.metis_partitions or self.partition_map

    def _partition_alternative(self, n_parts: int) -> None:
        """Alternative partitioning using degree-based stratified approach."""
        nodes_by_type = {}
        for node_id, node in self.nodes_metadata.items():
            nt = node.node_type.value
            if nt not in nodes_by_type:
                nodes_by_type[nt] = []
            nodes_by_type[nt].append(node_id)

        all_nodes = list(self.graph.nodes())
        random.shuffle(all_nodes)

        # Balanced assignment
        for i, node_id in enumerate(all_nodes):
            partition_id = i % n_parts
            self.partition_map[node_id] = partition_id
            if node_id in self.nodes_metadata:
                self.nodes_metadata[node_id].partition_id = partition_id

        self.metis_partitions = self.partition_map.copy()

    def _compute_partition_stats(self, n_parts: int) -> None:
        """Compute statistics for each partition."""
        self.partitions = {}
        partition_nodes: Dict[int, List[str]] = {i: [] for i in range(n_parts)}
        partition_internal_edges: Dict[int, int] = {i: 0 for i in range(n_parts)}
        partition_cut_edges: Dict[int, int] = {i: 0 for i in range(n_parts)}

        for u, v in self.graph.edges():
            p_u = self.partition_map.get(u, 0)
            p_v = self.partition_map.get(v, 0)
            if p_u == p_v:
                partition_internal_edges[p_u] += 1
            else:
                partition_cut_edges[p_u] += 1
                partition_cut_edges[p_v] += 1
            partition_nodes[p_u].append(u)
            partition_nodes[p_v].append(v)

        for i in range(n_parts):
            unique_nodes = list(set(partition_nodes[i]))
            nodes = [self.nodes_metadata[n] for n in unique_nodes if n in self.nodes_metadata]
            self.partitions[i] = GraphPartition(
                partition_id=i,
                node_ids=unique_nodes,
                internal_edges=partition_internal_edges[i],
                cut_edges=partition_cut_edges[i],
                nodes=nodes
            )

    # ============================================================
    # Graph Traversal Algorithms
    # ============================================================

    def traverse_bfs(
        self,
        start_node: str,
        max_depth: int = 3,
        node_type_filter: Optional[NodeType] = None
    ) -> TraversalResult:
        """
        Breadth-First Search traversal from a starting node.
        Used to find all nodes within a certain distance from the start.
        """
        start_time = time.time()

        if self.graph is None or start_node not in self.graph:
            return TraversalResult(
                visited_nodes=[],
                paths={},
                distances={},
                depth_distribution={},
                partition_coverage={}
            )

        visited: Set[str] = set()
        distances: Dict[str, int] = {start_node: 0}
        parents: Dict[str, str] = {start_node: None}
        queue = deque([start_node])
        depth_distribution: Dict[int, int] = {0: 1}
        partition_coverage: Dict[int, int] = {}

        while queue:
            current = queue.popleft()
            if current not in visited:
                visited.add(current)

                current_dist = distances[current]
                if current_dist >= max_depth:
                    continue

                for neighbor in self.graph.neighbors(current):
                    if neighbor not in distances:
                        distances[neighbor] = current_dist + 1
                        parents[neighbor] = current
                        depth_distribution[current_dist + 1] = depth_distribution.get(current_dist + 1, 0) + 1

                        # Track partition coverage
                        p = self.partition_map.get(neighbor, 0)
                        partition_coverage[p] = partition_coverage.get(p, 0) + 1

                        if current_dist + 1 < max_depth:
                            queue.append(neighbor)

        # Build paths
        paths: Dict[str, List[str]] = {}
        for node_id in visited:
            path = []
            current = node_id
            while current is not None:
                path.append(current)
                current = parents.get(current)
            paths[node_id] = path[::-1]

        # Filter by node type if specified
        visited_nodes = [
            self.nodes_metadata.get(n, GraphNode(n, NodeType.DISEASE, n))
            for n in visited
            if node_type_filter is None or
               (n in self.nodes_metadata and self.nodes_metadata[n].node_type == node_type_filter)
        ]

        elapsed = (time.time() - start_time) * 1000
        print(f"[GraphEngine] BFS from '{start_node}': {len(visited_nodes)} nodes, {elapsed:.2f}ms")

        return TraversalResult(
            visited_nodes=visited_nodes,
            paths=paths,
            distances=distances,
            depth_distribution=depth_distribution,
            partition_coverage=partition_coverage
        )

    def traverse_dfs(
        self,
        start_node: str,
        max_depth: int = 3,
        node_type_filter: Optional[NodeType] = None
    ) -> TraversalResult:
        """
        Depth-First Search traversal from a starting node.
        Explores as deep as possible before backtracking.
        """
        start_time = time.time()

        if self.graph is None or start_node not in self.graph:
            return TraversalResult(
                visited_nodes=[],
                paths={},
                distances={},
                depth_distribution={},
                partition_coverage={}
            )

        visited: Set[str] = set()
        distances: Dict[str, int] = {}
        parents: Dict[str, str] = {}
        depth_distribution: Dict[int, int] = {}
        partition_coverage: Dict[int, int] = {}

        def dfs_recursive(node: str, depth: int, parent: Optional[str]):
            if depth > max_depth or node in visited:
                return

            visited.add(node)
            distances[node] = depth
            parents[node] = parent
            depth_distribution[depth] = depth_distribution.get(depth, 0) + 1

            p = self.partition_map.get(node, 0)
            partition_coverage[p] = partition_coverage.get(p, 0) + 1

            for neighbor in self.graph.neighbors(node):
                if neighbor not in visited:
                    dfs_recursive(neighbor, depth + 1, node)

        dfs_recursive(start_node, 0, None)

        # Build paths
        paths: Dict[str, List[str]] = {}
        for node_id in visited:
            path = []
            current = node_id
            while current is not None:
                path.append(current)
                current = parents.get(current)
            paths[node_id] = path[::-1]

        visited_nodes = [
            self.nodes_metadata.get(n, GraphNode(n, NodeType.DISEASE, n))
            for n in visited
            if node_type_filter is None or
               (n in self.nodes_metadata and self.nodes_metadata[n].node_type == node_type_filter)
        ]

        elapsed = (time.time() - start_time) * 1000
        print(f"[GraphEngine] DFS from '{start_node}': {len(visited_nodes)} nodes, {elapsed:.2f}ms")

        return TraversalResult(
            visited_nodes=visited_nodes,
            paths=paths,
            distances=distances,
            depth_distribution=depth_distribution,
            partition_coverage=partition_coverage
        )

    def shortest_path(
        self,
        source: str,
        target: str
    ) -> Tuple[Optional[List[str]], Optional[float]]:
        """
        Find shortest path between two nodes using Dijkstra's algorithm.
        Returns (path, total_weight).
        """
        if self.graph is None:
            return None, None

        if source not in self.graph or target not in self.graph:
            return None, None

        try:
            path = nx.dijkstra_path(self.graph, source, target, weight="weight")
            weight = nx.dijkstra_path_length(self.graph, source, target, weight="weight")
            return path, weight
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None, None

    def get_shortest_paths_from_field(
        self,
        field_name: str,
        max_distance: int = 3
    ) -> Dict[str, Tuple[int, List[str]]]:
        """Get all shortest paths from a medical field node."""
        field_node_id = f"field_{field_name}"
        if field_node_id not in self.graph:
            # Try to find by label
            for node_id, node in self.nodes_metadata.items():
                if node.label == field_name and node.node_type == NodeType.MEDICAL_FIELD:
                    field_node_id = node_id
                    break

        if field_node_id not in self.graph:
            return {}

        result = self.traverse_bfs(field_node_id, max_depth=max_distance)
        paths = {}

        for node_id, distance in result.distances.items():
            if node_id != field_node_id and distance <= max_distance:
                path = result.paths.get(node_id, [])
                paths[node_id] = (distance, path)

        return paths

    # ============================================================
    # Graph Analysis & Statistics
    # ============================================================

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get comprehensive graph statistics."""
        if self.graph is None:
            return {}

        metrics = {}
        n = self.graph.number_of_nodes()

        # Basic metrics
        metrics["node_count"] = n
        metrics["edge_count"] = self.graph.number_of_edges()
        metrics["avg_degree"] = round(sum(dict(self.graph.degree()).values()) / n, 2) if n > 0 else 0
        metrics["density"] = round(nx.density(self.graph), 4)

        # Degree distribution
        degrees = dict(self.graph.degree())
        metrics["degree_stats"] = {
            "min": min(degrees.values()),
            "max": max(degrees.values()),
            "mean": round(sum(degrees.values()) / n, 2),
        }

        # Node type distribution
        node_types = {}
        for node_id in self.graph.nodes():
            if node_id in self.nodes_metadata:
                nt = self.nodes_metadata[node_id].node_type.value
            else:
                nt = self.graph.nodes[node_id].get("node_type", "unknown")
            node_types[nt] = node_types.get(nt, 0) + 1
        metrics["node_type_distribution"] = node_types

        # Edge type distribution
        edge_types = {}
        for u, v, data in self.graph.edges(data=True):
            et = data.get("edge_type", "unknown")
            edge_types[et] = edge_types.get(et, 0) + 1
        metrics["edge_type_distribution"] = edge_types

        # Centrality metrics
        degree_centrality = nx.degree_centrality(self.graph)
        metrics["top_central_nodes"] = sorted(
            degree_centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Partition stats
        if self.partitions:
            partition_stats = {}
            for pid, part in self.partitions.items():
                partition_stats[f"partition_{pid}"] = {
                    "nodes": len(part.node_ids),
                    "internal_edges": part.internal_edges,
                    "cut_edges": part.cut_edges,
                }
            metrics["partition_statistics"] = partition_stats

        return metrics

    def get_disease_nodes_in_field(
        self,
        field_name: str,
        max_distance: int = 3
    ) -> List[Tuple[GraphNode, int]]:
        """Get all disease nodes within max_distance from a medical field."""
        paths = self.get_shortest_paths_from_field(field_name, max_distance)
        diseases = []

        for node_id, (distance, path) in paths.items():
            if node_id in self.nodes_metadata:
                node = self.nodes_metadata[node_id]
                if node.node_type == NodeType.DISEASE:
                    diseases.append((node, distance))

        # Also include the field node itself
        field_node_id = f"field_{field_name}"
        if field_node_id in self.nodes_metadata:
            diseases.append((self.nodes_metadata[field_node_id], 0))

        return diseases

    def get_graph_distance(self, node_id: str, field_name: str) -> Optional[int]:
        """Get the shortest path distance from a node to a medical field."""
        field_node_id = f"field_{field_name}"
        if field_node_id not in self.graph:
            return None

        try:
            path_length = nx.shortest_path_length(self.graph, field_node_id, node_id)
            return path_length if path_length <= 3 else None
        except nx.NetworkXNoPath:
            return None

    # ============================================================
    # Vertex-Cut Partitioning (for comparison)
    # ============================================================

    def vertex_cut_partition(self, n_parts: int = 4) -> Dict[str, List[int]]:
        """
        Vertex-cut partitioning: nodes can belong to multiple partitions.
        Used for hypergraph-like distribution where diseases span multiple fields.
        """
        # For medical graph: diseases that connect multiple fields get replicated
        field_nodes = [
            n for n, meta in self.nodes_metadata.items()
            if meta.node_type == NodeType.MEDICAL_FIELD
        ]

        vertex_cuts: Dict[str, List[int]] = {n: [] for n in self.graph.nodes()}

        for disease_node, meta in self.nodes_metadata.items():
            if meta.node_type != NodeType.DISEASE:
                continue

            # Find which partitions this disease touches
            covered_partitions = set()
            for neighbor in self.graph.neighbors(disease_node):
                p = self.partition_map.get(neighbor, 0)
                covered_partitions.add(p)

            for p in covered_partitions:
                vertex_cuts[disease_node].append(p)

        return vertex_cuts

    def compute_edge_cut_ratio(self) -> float:
        """Compute the edge-cut ratio (edges crossing partitions / total edges)."""
        if not self.partition_map:
            return 0.0

        unique_parts = set(self.partition_map.values())
        if len(unique_parts) < 2:
            print(f"[GraphEngine] WARNING: compute_edge_cut_ratio found only {len(unique_parts)} partition(s), all nodes in same partition => ECR = 0")
            return 0.0

        cut_edges = 0
        total_edges = self.graph.number_of_edges()

        for u, v in self.graph.edges():
            p_u = self.partition_map.get(u, -1)
            p_v = self.partition_map.get(v, -1)
            if p_u != p_v:
                cut_edges += 1

        print(f"[GraphEngine] compute_edge_cut_ratio: total_edges={total_edges}, cut_edges={cut_edges}, parts={sorted(unique_parts)}")
        return cut_edges / total_edges if total_edges > 0 else 0.0

    # ============================================================
    # Serialization
    # ============================================================

    def export_to_json(self, output_path: Path) -> None:
        """Export graph data to JSON for visualization."""
        data = {
            "nodes": [
                {
                    "id": node_id,
                    "label": self.nodes_metadata.get(node_id, GraphNode(node_id, NodeType.DISEASE, node_id)).label,
                    "type": self.nodes_metadata.get(node_id, GraphNode(node_id, NodeType.DISEASE, node_id)).node_type.value,
                    "partition": self.partition_map.get(node_id, 0),
                    "degree": self.graph.degree(node_id) if self.graph else 0,
                    "field": self.nodes_metadata.get(node_id, GraphNode(node_id, NodeType.DISEASE, node_id)).properties.get("medical_field", None),
                }
                for node_id in self.graph.nodes()
            ],
            "links": [
                {
                    "source": u,
                    "target": v,
                    "type": self.graph[u][v].get("edge_type", "unknown"),
                    "weight": self.graph[u][v].get("weight", 1.0),
                }
                for u, v in self.graph.edges()
            ],
            "partitions": {
                pid: {"nodes": part.node_ids, "cut_edges": part.cut_edges}
                for pid, part in self.partitions.items()
            }
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[GraphEngine] Exported graph to {output_path}")
