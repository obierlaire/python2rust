import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..config.settings import Settings, LLMChoice
from .logging import setup_logger

logger = setup_logger()

class DebugManager:
    """Manages debug information and attempt history."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.current_attempt: Optional[int] = None
        self.current_attempt_dir: Optional[Path] = None
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.settings.output_dir.mkdir(parents=True, exist_ok=True)
        self.settings.debug_dir.mkdir(parents=True, exist_ok=True)

    def _get_next_attempt_number(self) -> int:
        """Get the next attempt number based on existing directories."""
        existing = [
            int(p.name.split("_")[1])
            for p in self.settings.debug_dir.glob("attempt_*")
            if p.is_dir() and p.name.startswith("attempt_")
        ]
        return max(existing, default=-1) + 1

    def start_attempt(self) -> Path:
        """Start a new migration attempt."""
        self.current_attempt = self._get_next_attempt_number()
        self.current_attempt_dir = self.settings.debug_dir / f"attempt_{self.current_attempt}"
        
        # Create attempt directory structure
        for subdir in ["config", "src", "prompts", "responses", "logs"]:
            (self.current_attempt_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Started attempt {self.current_attempt}")
        return self.current_attempt_dir

    def save_llm_config(self, step: str, llm: LLMChoice, token_usage: int) -> None:
        """Save LLM configuration for the current step."""
        if not self.current_attempt_dir:
            raise RuntimeError("No active attempt")
            
        config_file = self.current_attempt_dir / "config" / "llm_config.json"
        
        # Load existing config or create new
        if config_file.exists():
            config = json.loads(config_file.read_text())
        else:
            config = {}
        
        # Update config with current step
        llm_config = self.settings.llm_configs[llm].dict()
        config[step] = {
            "model": llm_config["model"],
            "temperature": llm_config["temperature"],
            "token_usage": token_usage,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save updated config
        config_file.write_text(json.dumps(config, indent=2))

    def save_prompt(self, step: str, prompt: str) -> None:
        """Save prompt used for the current step."""
        if not self.current_attempt_dir:
            raise RuntimeError("No active attempt")
            
        prompt_file = self.current_attempt_dir / "prompts" / f"{step}.txt"
        prompt_file.write_text(prompt)

    def save_response(self, step: str, response: str) -> None:
        """Save LLM response for the current step."""
        if not self.current_attempt_dir:
            raise RuntimeError("No active attempt")
            
        response_file = self.current_attempt_dir / "responses" / f"{step}.txt"
        response_file.write_text(response)

    def save_code(self, rust_code: str, toml_content: str) -> None:
        """Save generated Rust code."""
        if not self.current_attempt_dir:
            raise RuntimeError("No active attempt")
            
        # Save to debug directory
        (self.current_attempt_dir / "src").mkdir(parents=True, exist_ok=True)
        (self.current_attempt_dir / "src" / "main.rs").write_text(rust_code)
        (self.current_attempt_dir / "Cargo.toml").write_text(toml_content)

    def save_build_log(self, log_content: str) -> None:
        """Save build log."""
        if not self.current_attempt_dir:
            raise RuntimeError("No active attempt")
            
        (self.current_attempt_dir / "logs" / "build.log").write_text(log_content)

    def save_verification_result(self, result: Dict[str, Any]) -> None:
        """Save verification result."""
        if not self.current_attempt_dir:
            raise RuntimeError("No active attempt")
            
        result_file = self.current_attempt_dir / "logs" / "verification.json"
        result_file.write_text(json.dumps(result, indent=2))

    def mark_success(self) -> None:
        """Mark current attempt as successful and update latest symlink."""
        if not self.current_attempt_dir:
            raise RuntimeError("No active attempt")
            
        # Create success marker
        (self.current_attempt_dir / "SUCCESS").touch()
        
        # Update latest symlink
        latest_link = self.settings.output_dir / "latest"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(self.current_attempt_dir, target_is_directory=True)
        
        # Copy successful code to output directory
        shutil.copy2(
            self.current_attempt_dir / "src" / "main.rs",
            self.settings.output_dir / "src" / "main.rs"
        )
        shutil.copy2(
            self.current_attempt_dir / "Cargo.toml",
            self.settings.output_dir / "Cargo.toml"
        )

    def update_summary(self, status: str, error: Optional[str] = None) -> None:
        """Update the summary file with the current attempt's results."""
        if not self.current_attempt_dir:
            raise RuntimeError("No active attempt")
            
        summary_file = self.settings.debug_dir / "summary.json"
        
        # Load existing summary or create new
        if summary_file.exists():
            summary = json.loads(summary_file.read_text())
        else:
            summary = {"attempts": [], "total_attempts": 0, "successful_attempts": 0}
        
        # Load LLM config for this attempt
        llm_config_file = self.current_attempt_dir / "config" / "llm_config.json"
        llm_config = json.loads(llm_config_file.read_text()) if llm_config_file.exists() else {}
        
        # Update attempt information
        attempt_info = {
            "id": self.current_attempt,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "llm_config": llm_config
        }
        
        if error:
            attempt_info["error"] = error
        
        summary["attempts"].append(attempt_info)
        summary["total_attempts"] = len(summary["attempts"])
        summary["successful_attempts"] = sum(
            1 for attempt in summary["attempts"]
            if attempt["status"] == "success"
        )
        
        # Save updated summary
        summary_file.write_text(json.dumps(summary, indent=2))