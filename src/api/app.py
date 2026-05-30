"""
Flask API Server for Hybrid Document-Graph Store.
Provides REST endpoints for hybrid querying and analysis.
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config import config
from src.core.models import HybridQuery, TraversalAlgorithm
from src.engines.data_generator import generate_all_data
from src.engines.document_engine import DocumentEngine
from src.engines.graph_engine import GraphEngine
from src.engines.hybrid_engine import HybridQueryEngine


# ============================================================
# Flask Application Setup
# ============================================================

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent.parent / "frontend" / "templates"),
    static_folder=str(Path(__file__).parent.parent / "frontend" / "static"),
)
app.config["JSON_SORT_KEYS"] = False
CORS(app)

# Global engine instances (lazy initialization)
_hybrid_engine: HybridQueryEngine = None
_initialized: bool = False


def get_engine() -> HybridQueryEngine:
    """Get or initialize the hybrid engine."""
    global _hybrid_engine, _initialized
    if not _initialized:
        initialize_system()
    return _hybrid_engine


def initialize_system() -> None:
    """Initialize the hybrid document-graph store."""
    global _hybrid_engine, _initialized
    if _initialized:
        return

    print("=" * 60)
    print("INITIALIZING HYBRID DOCUMENT-GRAPH STORE")
    print("=" * 60)

    # Check for existing data
    data_path = Path(__file__).parent.parent.parent / "data" / "raw"
    patient_file = data_path / "patient_symptoms.json"
    graph_file = data_path / "disease_graph.json"

    if not patient_file.exists() or not graph_file.exists():
        print("[API] Generating synthetic medical data...")
        generate_all_data()

    # Load patient data
    with open(patient_file, "r", encoding="utf-8") as f:
        patient_data = json.load(f)

    from src.core.models import PatientSymptom
    patients = [
        PatientSymptom(
            patient_id=p["patient_id"],
            patient_id_int=int(p["patient_id"][1:]) if p["patient_id"].startswith("P") else 0,
            age=p["age"],
            gender=p["gender"],
            chief_complaint=p["chief_complaint"],
            symptoms=p["symptoms"],
            medical_history=p["medical_history"],
            current_medications=p["current_medications"],
            initial_diagnosis=p["initial_diagnosis"],
            severity=p["severity"],
            department=p["department"],
            admission_date=p["admission_date"],
        )
        for p in patient_data
    ]

    # Load graph data
    with open(graph_file, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    from src.core.models import GraphNode, GraphEdge, NodeType, EdgeType
    nodes = [
        GraphNode(
            node_id=n["node_id"],
            node_type=NodeType(n["node_type"]),
            label=n["label"],
            properties=n.get("properties", {}),
            degree=n.get("degree", 0),
        )
        for n in graph_data["nodes"]
    ]
    edges = [
        GraphEdge(
            source_id=e["source_id"],
            target_id=e["target_id"],
            edge_type=EdgeType(e["edge_type"]),
            weight=e.get("weight", 1.0),
        )
        for e in graph_data["edges"]
    ]

    # Initialize engines
    print("[API] Initializing Document Engine (Whoosh BM25F)...")
    doc_engine = DocumentEngine(recreate=False)

    print("[API] Initializing Graph Engine (NetworkX)...")
    graph_engine = GraphEngine()

    _hybrid_engine = HybridQueryEngine(doc_engine, graph_engine)
    _hybrid_engine.load_data(patients, nodes, edges)

    # Re-index if needed
    try:
        stats = doc_engine.get_index_stats()
        if stats["document_count"] == 0:
            print("[API] Re-indexing documents...")
            doc_engine.index_documents(patients)
    except:
        print("[API] Indexing documents...")
        doc_engine.index_documents(patients)

    _initialized = True
    print("=" * 60)
    print("SYSTEM INITIALIZED SUCCESSFULLY")
    print("=" * 60)


# ============================================================
# API Routes - Pages
# ============================================================

@app.route("/")
def index():
    """Main application page — serves the full-featured single-page app."""
    root_index = Path(__file__).parent.parent.parent / "index.html"
    if root_index.exists():
        return root_index.read_text(encoding="utf-8")
    return render_template("index.html")


@app.route("/graph")
def graph_page():
    """Graph visualization page — redirects to main app (all-in-one UI)."""
    root_index = Path(__file__).parent.parent.parent / "index.html"
    if root_index.exists():
        return root_index.read_text(encoding="utf-8")
    return render_template("graph.html")


@app.route("/analysis")
def analysis_page():
    """Join cost analysis page — redirects to main app (all-in-one UI)."""
    root_index = Path(__file__).parent.parent.parent / "index.html"
    if root_index.exists():
        return root_index.read_text(encoding="utf-8")
    return render_template("analysis.html")


# ============================================================
# API Routes - Health & Info
# ============================================================

@app.route("/api/health")
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "system": "Hybrid Document-Graph Store: Medical Knowledge Base",
        "version": "1.0.0",
    })


@app.route("/api/info")
def system_info():
    """Get system information."""
    engine = get_engine()
    doc_stats = engine.doc_engine.get_index_stats()
    graph_stats = engine.graph_engine.get_graph_statistics()

    return jsonify({
        "system": "Hybrid Document-Graph Store: Medical Knowledge Base",
        "version": "1.0.0",
        "components": {
            "document_engine": {
                "engine": "Whoosh (BM25F)",
                "index": doc_stats,
            },
            "graph_engine": {
                "engine": "NetworkX + METIS",
                "statistics": graph_stats,
            }
        },
        "medical_fields": [
            "Cardiology", "Neurology", "Oncology", "Pulmonology",
            "Gastroenterology", "Orthopedics", "Infectious_Disease",
            "Endocrinology", "Nephrology", "Rheumatology"
        ],
        "partitions": config.get("graph_engine", "partitioning", "n_parts", default=4),
    })


# ============================================================
# API Routes - Hybrid Query
# ============================================================

@app.route("/api/query", methods=["POST"])
def execute_hybrid_query():
    """
    Execute a hybrid document-graph query.

    Request body:
    {
        "query_text": "chest pain and shortness of breath",
        "target_field": "Cardiology",
        "max_graph_distance": 3,
        "max_results": 20,
        "text_weight": 0.5,
        "graph_weight": 0.5,
        "traversal_algorithm": "bfs",
        "min_severity": 2,
        "department_filter": null
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    query_text = data.get("query_text", "")
    target_field = data.get("target_field", "Cardiology")
    max_distance = int(data.get("max_graph_distance", 3))
    max_results = int(data.get("max_results", 20))
    text_weight = float(data.get("text_weight", 0.5))
    graph_weight = float(data.get("graph_weight", 0.5))
    traversal_algo = data.get("traversal_algorithm", "bfs")
    min_severity = data.get("min_severity")
    department_filter = data.get("department_filter")

    # Map traversal algorithm
    algo_map = {
        "bfs": TraversalAlgorithm.BFS,
        "dfs": TraversalAlgorithm.DFS,
        "shortest_path": TraversalAlgorithm.SHORTEST_PATH,
    }
    traversal_algorithm = algo_map.get(traversal_algo.lower(), TraversalAlgorithm.BFS)

    query = HybridQuery(
        query_text=query_text,
        target_field=target_field,
        max_graph_distance=max_distance,
        max_results=max_results,
        text_weight=text_weight,
        graph_weight=graph_weight,
        traversal_algorithm=traversal_algorithm,
        min_severity=int(min_severity) if min_severity else None,
        department_filter=department_filter,
    )

    engine = get_engine()
    result = engine.execute_query(query)

    # Serialize results
    results_serialized = []
    for r in result.results:
        results_serialized.append({
            "patient": r.patient.to_dict(),
            "text_score": round(r.text_score, 4),
            "graph_importance": round(r.graph_importance, 4),
            "combined_score": round(r.combined_score, 4),
            "graph_distance": r.graph_distance,
            "distance_label": r.distance_label,
            "partition_id": r.partition_id,
        })

    return jsonify({
        "query": {
            "text": query_text,
            "target_field": target_field,
            "max_graph_distance": max_distance,
            "text_weight": text_weight,
            "graph_weight": graph_weight,
            "traversal_algorithm": traversal_algo,
        },
        "results": results_serialized,
        "total_results": len(results_serialized),
        "join_cost": result.join_cost.to_dict(),
        "execution_time_ms": round(result.execution_time_ms, 2),
        "partitions_accessed": result.partitions_accessed,
        "graph_statistics": result.graph_statistics,
    })


# ============================================================
# API Routes - Join Cost Analysis
# ============================================================

@app.route("/api/analyze/join-cost", methods=["POST"])
def analyze_join_cost():
    """
    Analyze join cost for a hybrid query.
    Compares different join strategies.
    """
    data = request.get_json()
    query_text = data.get("query_text", "chest pain")
    target_field = data.get("target_field", "Cardiology")

    query = HybridQuery(
        query_text=query_text,
        target_field=target_field,
        max_graph_distance=3,
        max_results=20,
    )

    engine = get_engine()
    analysis = engine.analyze_join_cost(query)

    return jsonify(analysis)


@app.route("/api/analyze/field-coverage")
def get_field_coverage():
    """Get coverage statistics for each medical field."""
    engine = get_engine()
    coverage = engine.get_field_coverage()
    return jsonify(coverage)


# ============================================================
# API Routes - Graph Data
# ============================================================

@app.route("/api/graph/export")
def export_graph_json():
    """Export graph data for visualization."""
    engine = get_engine()
    output_path = config.processed_dir / "graph_export.json"
    engine.graph_engine.export_to_json(output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data)


@app.route("/api/graph/debug")
def debug_graph():
    """Debug endpoint to check graph data structure."""
    engine = get_engine()

    # Get edge counts by type
    edge_counts = {}
    for u, v, data in engine.graph_engine.graph.edges(data=True):
        et = data.get("edge_type", "unknown")
        edge_counts[et] = edge_counts.get(et, 0) + 1

    # Get some sample edges
    sample_edges = []
    for i, (u, v, data) in enumerate(engine.graph_engine.graph.edges(data=True)):
        if i < 5:
            sample_edges.append({
                "source": u,
                "target": v,
                "type": data.get("edge_type"),
                "weight": data.get("weight")
            })

    # Get some sample nodes
    sample_nodes = []
    for i, node_id in enumerate(list(engine.graph_engine.graph.nodes())[:5]):
        meta = engine.graph_engine.nodes_metadata.get(node_id)
        if meta:
            sample_nodes.append({
                "id": node_id,
                "type": meta.node_type.value,
                "label": meta.label
            })

    return jsonify({
        "total_nodes": engine.graph_engine.graph.number_of_nodes(),
        "total_edges": engine.graph_engine.graph.number_of_edges(),
        "edge_counts_by_type": edge_counts,
        "sample_edges": sample_edges,
        "sample_nodes": sample_nodes,
    })


@app.route("/api/graph/statistics")
def graph_statistics():
    """Get comprehensive graph statistics."""
    engine = get_engine()
    stats = engine.graph_engine.get_graph_statistics()
    return jsonify(stats)


@app.route("/api/graph/partitions")
def get_partitions():
    """Get partition information."""
    engine = get_engine()
    partitions = []

    for pid, part in engine.graph_engine.partitions.items():
        partitions.append({
            "partition_id": pid,
            "node_count": len(part.node_ids),
            "internal_edges": part.internal_edges,
            "cut_edges": part.cut_edges,
        })

    return jsonify({
        "partitions": partitions,
        "edge_cut_ratio": engine.graph_engine.compute_edge_cut_ratio(),
        "partitioning_method": "METIS (Recursive Bisection)",
        "partition_type": "Edge-Cut",
    })


@app.route("/api/graph/traverse", methods=["POST"])
def traverse_graph():
    """
    Perform graph traversal from a medical field.

    Request body:
    {
        "field_name": "Cardiology",
        "max_depth": 3,
        "algorithm": "bfs"
    }
    """
    data = request.get_json()
    field_name = data.get("field_name", "Cardiology")
    max_depth = int(data.get("max_depth", 3))
    algorithm = data.get("algorithm", "bfs")

    engine = get_engine()
    field_node_id = f"field_{field_name}"

    if algorithm == "dfs":
        result = engine.graph_engine.traverse_dfs(field_node_id, max_depth)
    else:
        result = engine.graph_engine.traverse_bfs(field_node_id, max_depth)

    return jsonify({
        "field_name": field_name,
        "algorithm": algorithm,
        "max_depth": max_depth,
        "visited_nodes": len(result.visited_nodes),
        "depth_distribution": result.depth_distribution,
        "partition_coverage": result.partition_coverage,
        "nodes": [
            {
                "id": n.node_id,
                "label": n.label,
                "type": n.node_type.value,
                "partition_id": n.partition_id,
            }
            for n in result.visited_nodes
        ],
    })


@app.route("/api/graph/distance", methods=["GET"])
def get_graph_distance():
    """Get graph distance from a disease to a medical field."""
    disease = request.args.get("disease", "")
    field = request.args.get("field", "Cardiology")

    engine = get_engine()
    node_id = engine._find_node_id_for_disease(disease)

    if not node_id:
        return jsonify({"error": f"Disease '{disease}' not found"}), 404

    distance = engine.graph_engine.get_graph_distance(node_id, field)

    if distance is None:
        return jsonify({
            "disease": disease,
            "field": field,
            "distance": None,
            "message": "No path found within max distance",
        })

    importance = engine._distance_to_importance(distance)
    return jsonify({
        "disease": disease,
        "field": field,
        "distance": distance,
        "importance": round(importance, 4),
        "distance_label": f"{distance} hop(s)",
    })


@app.route("/api/graph/correlation-matrix")
def get_correlation_matrix():
    """
    Get disease-disease correlation matrix for heatmap visualization.
    Returns correlation strengths between all diseases.
    """
    engine = get_engine()
    graph = engine.graph_engine.graph
    nodes_meta = engine.graph_engine.nodes_metadata

    if graph is None:
        return jsonify({"error": "Graph not loaded"}), 500

    # Get all disease nodes
    disease_nodes = []
    for node_id, meta in nodes_meta.items():
        if meta.node_type.value == "disease":
            disease_nodes.append({
                "id": node_id,
                "label": meta.label,
                "field": None,
                "partition": engine.graph_engine.partition_map.get(node_id, 0)
            })
            # Find the field this disease belongs to
            for neighbor in graph.neighbors(node_id):
                if neighbor in nodes_meta and nodes_meta[neighbor].node_type.value == "medical_field":
                    disease_nodes[-1]["field"] = nodes_meta[neighbor].label
                    break

    # Build adjacency matrix for diseases
    disease_ids = [d["id"] for d in disease_nodes]
    n = len(disease_ids)
    disease_idx = {d_id: i for i, d_id in enumerate(disease_ids)}

    # Initialize matrix with 0s
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]

    # Fill matrix based on shared symptoms and direct connections
    for i, d1 in enumerate(disease_ids):
        for j, d2 in enumerate(disease_ids):
            if i == j:
                matrix[i][j] = 1.0
            elif i < j:
                # Count shared neighbors (symptoms)
                neighbors1 = set(graph.neighbors(d1))
                neighbors2 = set(graph.neighbors(d2))
                shared = neighbors1 & neighbors2
                shared_symptoms = [n for n in shared if n in nodes_meta and nodes_meta[n].node_type.value == "symptom"]

                # Direct edge weight
                direct_weight = 0.0
                if graph.has_edge(d1, d2):
                    direct_weight = graph[d1][d2].get("weight", 1.0)

                # Calculate correlation score
                correlation = min(1.0, (len(shared_symptoms) * 0.3 + direct_weight * 0.7) / 2.0)
                matrix[i][j] = correlation
                matrix[j][i] = correlation

    # Calculate field-level correlations for chord diagram
    field_diseases = {}
    for d in disease_nodes:
        field = d["field"] or "Other"
        if field not in field_diseases:
            field_diseases[field] = []
        field_diseases[field].append(d["id"])

    # Build cross-field correlation matrix
    fields = sorted(field_diseases.keys())
    field_matrix = {}
    for f1 in fields:
        field_matrix[f1] = {}
        for f2 in fields:
            if f1 == f2:
                # Within field: average intra-connections
                internal_corr = []
                for d1 in field_diseases[f1]:
                    for d2 in field_diseases[f1]:
                        if d1 != d2:
                            i, j = disease_idx[d1], disease_idx[d2]
                            internal_corr.append(matrix[i][j])
                field_matrix[f1][f2] = round(sum(internal_corr) / len(internal_corr), 3) if internal_corr else 0
            else:
                # Cross-field: average cross-connections
                cross_corr = []
                for d1 in field_diseases[f1]:
                    for d2 in field_diseases[f2]:
                        i, j = disease_idx[d1], disease_idx[d2]
                        cross_corr.append(matrix[i][j])
                field_matrix[f1][f2] = round(sum(cross_corr) / len(cross_corr), 3) if cross_corr else 0

    return jsonify({
        "diseases": disease_nodes,
        "matrix": matrix,
        "fields": fields,
        "field_matrix": field_matrix,
        "field_diseases": {f: [disease_ids.index(d) for d in ids] for f, ids in field_diseases.items()}
    })


# ============================================================
# API Routes - Document Search
# ============================================================

@app.route("/api/documents/search", methods=["GET"])
def search_documents():
    """Search documents without graph filtering."""
    query_text = request.args.get("q", "")
    max_results = int(request.args.get("max", 20))
    department = request.args.get("department", None)
    min_severity = request.args.get("severity", None, type=int)

    engine = get_engine()
    hits = engine.doc_engine.search(
        query_text=query_text,
        max_results=max_results,
        department=department,
        min_severity=min_severity,
    )

    results = [
        {"document": dict(doc), "score": round(score, 4)}
        for doc, score in hits
    ]

    return jsonify({
        "query": query_text,
        "results": results,
        "total": len(results),
    })


@app.route("/api/documents/<patient_id>")
def get_document(patient_id: str):
    """Get a specific patient document."""
    engine = get_engine()
    doc = engine.doc_engine.get_document_by_id(patient_id)

    if not doc:
        return jsonify({"error": f"Patient '{patient_id}' not found"}), 404

    return jsonify(doc)


# ============================================================
# Error Handlers
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ============================================================
# Main Entry Point
# ============================================================

def run_server(host: str = None, port: int = None):
    """Run the Flask development server."""
    host = host or config.get("server", "host", default="0.0.0.0")
    port = port or config.get("server", "port", default=5000)
    debug = config.get("server", "debug", default=True)

    print(f"\n{'='*60}")
    print(f"Starting Hybrid Document-Graph Store API Server")
    print(f"URL: http://{host}:{port}")
    print(f"{'='*60}\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
