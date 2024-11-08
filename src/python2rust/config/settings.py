# config/settings.py
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import json
from enum import Enum
from dataclasses import dataclass

def get_default_specs_path() -> Path:
    """Get the default specs file path."""
    possible_paths = [
        Path.cwd() / "migration_specs.json",  # Current directory
        Path.home() / ".config" / "python2rust" / "migration_specs.json",  # User config
        Path(__file__).parent / "default_specs.json"  # Package default
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
            
    # If no file found, use package default
    return Path(__file__).parent / "default_specs.json"

def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path(__file__).parent

class LLMChoice(str, Enum):
    """Available LLM choices."""
    CLAUDE = "claude"
    CODELLAMA = "codellama"
    STARCODER = "starcoder"
    CODESTRAL = "codestral"

class ModelParameters(BaseModel):
    """Additional parameters for specific models."""
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    repetition_penalty: Optional[float] = None
    do_sample: Optional[bool] = None
    num_return_sequences: Optional[int] = None
    pad_token_id: Optional[int] = None
    return_full_text : Optional[bool] = True
    stop_sequences: Optional[List[str]] = None

class LLMConfig(BaseModel):
    """Configuration for a specific LLM."""
    model: str
    endpoint_url: Optional[str] = None
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    max_tokens: Optional[int] = None
    model_params: Optional[ModelParameters] = None
    fallback_model: Optional[str] = None  # Fallback model if this one fails

class MigrationSteps(BaseModel):
    """Configuration for each migration step."""
    analysis: LLMChoice = Field(default=LLMChoice.CLAUDE)
    generation: LLMChoice = Field(default=LLMChoice.CLAUDE)
    verification: LLMChoice = Field(default=LLMChoice.CLAUDE)
    fixes: LLMChoice = Field(default=LLMChoice.CLAUDE)

class Settings(BaseSettings):
    """Application settings."""
    # Project Paths
    base_dir: Path = Field(default=Path(__file__).parent.parent.parent.parent)
    output_dir: Path = Field(default=Path("generated"))
    debug_dir: Path = Field(default=Path("generated/debug"))
    specs_file: Path = Field(default_factory=get_default_specs_path)
    
    # LLM Configuration
    llm_steps: MigrationSteps = Field(default_factory=MigrationSteps)
    llm_configs: Dict[LLMChoice, LLMConfig] = Field(
        default_factory=lambda: {
            LLMChoice.CLAUDE: LLMConfig(
                model="claude-3-5-sonnet-20241022",
                temperature=0.1,
                max_tokens=4000,
                model_params=ModelParameters(
                    stop_sequences=["\n```", "```\n"]
                )
            ),
            LLMChoice.CODELLAMA: LLMConfig(
                model="codellama/CodeLlama-34b-Instruct-hf",
                temperature=0.7,
                max_tokens=4000,
                fallback_model=LLMChoice.CLAUDE,
                model_params=ModelParameters(
                    top_k=100,
                    top_p=0.95,
                    repetition_penalty=1.05,
                    #num_return_sequences=1,
                    #stop_sequences=["\n```", "```\n"],
                    return_full_text=False
                )
            ),
            LLMChoice.STARCODER: LLMConfig(
                model="bigcode/starcoder2-15b",
                temperature=0.2,
                max_tokens=4000,
                fallback_model=LLMChoice.CLAUDE,
                model_params=ModelParameters(
                    top_k=50,
                    top_p=0.95,
                    repetition_penalty=1.3,
                    do_sample=True,
                    #stop_sequences=["```\n\n"]
                )
            ),
             LLMChoice.CODESTRAL: LLMConfig(
                model="codestral-latest",
                temperature=0.1,
                max_tokens=4000,
                endpoint_url="https://codestral.mistral.ai/v1/chat/completions"
            ),
        }
    )
    
    # Migration Configuration
    max_attempts: int = Field(default=10)
    max_fixes_per_attempt: int = Field(default=10)
    build_timeout: int = Field(default=300)  # seconds
    
    # Model Selection Strategy
    preferred_models: Dict[str, List[LLMChoice]] = Field(
        default_factory=lambda: {
            "code_generation": [LLMChoice.CODELLAMA, LLMChoice.STARCODER, LLMChoice.CLAUDE],
            "analysis": [LLMChoice.CLAUDE, LLMChoice.CODELLAMA],
            "verification": [LLMChoice.CLAUDE],
            "fixes": [LLMChoice.CODELLAMA, LLMChoice.CLAUDE]
        }
    )
    
    # Verification Configuration
    expected_image_size: Tuple[int, int] = Field(default=(2000, 2000))
    
    # Server Configuration
    server_host: str = Field(default="127.0.0.1")
    server_port: int = Field(default=8080)
    server_timeout: int = Field(default=30)  # seconds
    
    class Config:
        env_file = ".env"
        env_prefix = "PYTHON2RUST_"

    def load_specs(self) -> Dict:
        """Load migration specifications from the appropriate location."""
        try:
            return json.loads(self.specs_file.read_text())
        except Exception as e:
            print(f"Warning: Could not load specs from {self.specs_file}: {e}")
            print("Using default specifications")
            default_specs_path = Path(__file__).parent / "default_specs.json"
            return json.loads(default_specs_path.read_text())

    def get_model_chain(self, task: str) -> List[LLMChoice]:
        """Get the chain of models to try for a specific task."""
        return self.preferred_models.get(task, [LLMChoice.CLAUDE])

# Create global settings instance
settings = Settings()