"""
Main entry point for the Hybrid Document-Graph Store.
Run this script to start the system.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.app import run_server


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Hybrid Document-Graph Store: Medical Knowledge Base")
    print("  Patient Symptoms (Document) + Disease Correlations (Graph)")
    print("=" * 60)
    print()
    print("  Starting Flask API Server...")
    print("  Open http://localhost:5000 in your browser")
    print()
    run_server()
