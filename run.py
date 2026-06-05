"""
Điểm vào chính của Hệ Thống Lưu Trữ Tài Liệu–Đồ Thị Kết Hợp (Hybrid Document-Graph Store).
Chạy tập lệnh này để khởi động hệ thống.
"""
import sys
from pathlib import Path

# Thêm thư mục src vào đường dẫn (path) để import module
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.app import run_server


if __name__ == "__main__":
    # Điểm vào chính: In banner giới thiệu, sau đó khởi động Flask API
    print("\n" + "=" * 60)
    print("  Hybrid Document-Graph Store: Medical Knowledge Base")
    print("  Patient Symptoms (Document) + Disease Correlations (Graph)")
    print("=" * 60)
    print()
    print("  Starting Flask API Server...")
    print("  Open http://localhost:5000 in your browser")
    print()
    run_server()
