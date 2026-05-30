"""
Configuration loader for the Hybrid Document-Graph Store.
Loads settings from config.yaml and provides typed access.
"""
import os
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path


class Config:
    """Central configuration manager for the entire application."""

    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """Load configuration from config.yaml."""
        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"config.yaml not found at {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested configuration value by dot-notation keys."""
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
        return self.get("project", "name")

    @property
    def dataset(self) -> Dict[str, Any]:
        return self._config.get("dataset", {})

    @property
    def document_engine(self) -> Dict[str, Any]:
        return self._config.get("document_engine", {})

    @property
    def graph_engine(self) -> Dict[str, Any]:
        return self._config.get("graph_engine", {})

    @property
    def hybrid_engine(self) -> Dict[str, Any]:
        return self._config.get("hybrid_engine", {})

    @property
    def join_cost(self) -> Dict[str, Any]:
        return self._config.get("join_cost", {})

    @property
    def server(self) -> Dict[str, Any]:
        return self._config.get("server", {})

    @property
    def visualization(self) -> Dict[str, Any]:
        return self._config.get("visualization", {})

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"


config = Config()
