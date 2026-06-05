"""
Bộ nạp cấu hình (configuration) cho Hệ Thống Lưu Trữ Tài Liệu–Đồ Thị Kết Hợp (Hybrid Document-Graph Store).
Đọc các thiết lập từ tệp config.yaml và cung cấp quyền truy cập có kiểu (typed access).
"""
import os
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path


class Config:
    """Quản lý cấu hình trung tâm cho toàn bộ ứng dụng.
    
    Sử dụng Singleton pattern — chỉ một instance duy nhất.
    Đọc cấu hình từ config.yaml và cung cấp truy cập typed.
    """

    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls) -> 'Config':
        """Tạo instance Singleton. Gọi _load() nếu chưa có instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """Tải cấu hình từ file config.yaml.
        
        Luồng hoạt động:
        Bước 1: Xác định đường dẫn config.yaml (cùng cấp với thư mục gốc).
        Bước 2: Kiểm tra file tồn tại, nếu không thì raise FileNotFoundError.
        Bước 3: Dùng yaml.safe_load() để parse file thành dict.
        """
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"config.yaml not found at {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Lấy giá trị cấu hình theo chuỗi key (dot-notation).
        
        Duyệt qua từng key trong dict lồng nhau.
        Trả về default nếu key không tồn tại.
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value

    @property
    def project_name(self) -> str:
        """Tên dự án lấy từ config.yaml > project > name."""
        return self.get("project", "name")

    @property
    def dataset(self) -> Dict[str, Any]:
        """Cấu hình dataset: documents và graph."""
        return self._config.get("dataset", {})

    @property
    def document_engine(self) -> Dict[str, Any]:
        """Cấu hình Document Engine: Whoosh index, analyzer, scoring."""
        return self._config.get("document_engine", {})

    @property
    def graph_engine(self) -> Dict[str, Any]:
        """Cấu hình Graph Engine: NetworkX, METIS partitioning, traversal."""
        return self._config.get("graph_engine", {})

    @property
    def hybrid_engine(self) -> Dict[str, Any]:
        """Cấu hình Hybrid Engine: join cost, scoring weights, caching."""
        return self._config.get("hybrid_engine", {})

    @property
    def join_cost(self) -> Dict[str, Any]:
        """Cấu hình Join Cost Analysis: thresholds và metrics."""
        return self._config.get("join_cost", {})

    @property
    def server(self) -> Dict[str, Any]:
        """Cấu hình Flask server: host, port, debug, CORS."""
        return self._config.get("server", {})

    @property
    def visualization(self) -> Dict[str, Any]:
        """Cấu hình Visualization: layout, màu sắc, max nodes."""
        return self._config.get("visualization", {})

    @property
    def base_dir(self) -> Path:
        """Đường dẫn thư mục gốc của dự án."""
        return Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        """Đường dẫn thư mục data (raw + processed)."""
        return self.base_dir / "data"

    @property
    def logs_dir(self) -> Path:
        """Đường dẫn thư mục logs."""
        return self.base_dir / "logs"

    @property
    def processed_dir(self) -> Path:
        """Đường dẫn thư mục data/processed (index, graph, partitions)."""
        return self.data_dir / "processed"


config = Config()
