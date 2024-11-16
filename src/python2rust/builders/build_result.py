from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class BuildResult:
    """Result of build step."""
    success: bool
    rust_code: str
    toml_content: str
    error: Optional[str] = None
    build_info: Optional[Dict[str, Any]] = None
