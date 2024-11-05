from dataclasses import dataclass
from typing import Dict, Any, List, Union
from datetime import datetime
from pathlib import Path
import json
from ..utils.logging import setup_logger
from langchain_core.callbacks import StdOutCallbackHandler, BaseCallbackHandler
from ..config.settings import get_config_path

logger = setup_logger()

@dataclass
class ModelConfig:
    """Model configuration."""
    model: str
    hosting: str
    country: str
    energy_kwh: float
    token_base: int

@dataclass
class CountryEmissions:
    """Country-specific emissions data."""
    country: str
    gco2_per_kwh: float

class EmissionsCalculator:
    """Simplified emissions calculator."""
    
    def __init__(self, models_config: Path, emissions_config: Path):
        self.models = self._load_models_config(models_config)
        self.emissions = self._load_emissions_config(emissions_config)
        
    def _load_models_config(self, config_path: Path) -> Dict[str, ModelConfig]:
        """Load model configuration."""
        try:
            data = json.loads(config_path.read_text())
            return {
                model_data["model"]: ModelConfig(**model_data)
                for model_data in data["models"]
            }
        except Exception as e:
            logger.error(f"Error loading models config: {e}")
            raise

    def _load_emissions_config(self, config_path: Path) -> Dict[str, CountryEmissions]:
        """Load country emissions data."""
        try:
            data = json.loads(config_path.read_text())
            return {
                country_data["country"]: CountryEmissions(**country_data)
                for country_data in data["countries"]
            }
        except Exception as e:
            logger.error(f"Error loading emissions config: {e}")
            raise

    def calculate(self, total_tokens: int, model: str) -> Dict[str, Any]:
        """Calculate energy usage and emissions."""
        try:
            # Get model config or default to Claude Sonnet
            model_config = self.models.get(model, self.models["claude-3-sonnet"])
            
            # Get country emissions data or default to world average
            country_data = self.emissions.get(
                model_config.country, 
                self.emissions["world"]
            )
            
            # Calculate impacts
            energy_kwh = (total_tokens * model_config.energy_kwh) / model_config.token_base
            emissions_kgco2eq = energy_kwh * (country_data.gco2_per_kwh / 1000)
            
            return {
                "energy_kwh": energy_kwh,
                "emissions_kgco2eq": emissions_kgco2eq,
                "hosting": model_config.hosting,
                "country": model_config.country,
                "grid_carbon_intensity": f"{country_data.gco2_per_kwh} gCO2/kWh"
            }
        except Exception as e:
            logger.error(f"Error calculating impacts: {e}")
            return {
                "energy_kwh": 0.0,
                "emissions_kgco2eq": 0.0,
                "hosting": "unknown",
                "country": "unknown",
                "grid_carbon_intensity": "0 gCO2/kWh"
            }

class UnifiedTracker(BaseCallbackHandler):
    """Simplified unified token and emissions tracker."""

    def __init__(self, debug_dir: Path):
        super().__init__()
        self.traces_dir = debug_dir / "traces"
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.current_trace = {}
        
        self.calculator = EmissionsCalculator(
            models_config=get_config_path() / "models_config.json",
            emissions_config=get_config_path() / "emissions_config.json"
        )

    def _extract_token_usage(self, response) -> Dict[str, int]:
        """Extract token usage from Anthropic response."""
        try:
            if hasattr(response, 'generations') and response.generations:
                generation = response.generations[0][0]
                logger.info(f"Generation info: {generation}")
                
                # Try additional_kwargs first (newer format)
                if hasattr(generation, 'additional_kwargs'):
                    kwargs = generation.additional_kwargs
                    if 'usage' in kwargs:
                        usage = kwargs['usage']
                        prompt_tokens = usage.get('input_tokens', 0)
                        completion_tokens = usage.get('output_tokens', 0)
                        total_tokens = prompt_tokens + completion_tokens
                        return {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens
                        }
                
                # Try generation_info (older format)
                if hasattr(generation, 'generation_info'):
                    info = generation.generation_info or {}
                    if 'usage' in info:
                        usage = info['usage']
                        prompt_tokens = usage.get('input_tokens', 0)
                        completion_tokens = usage.get('output_tokens', 0)
                        total_tokens = prompt_tokens + completion_tokens
                        return {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens
                        }
            
            # Try llm_output (fallback)
            if hasattr(response, 'llm_output') and response.llm_output:
                if 'usage' in response.llm_output:
                    usage = response.llm_output['usage']
                    prompt_tokens = usage.get('input_tokens', 0)
                    completion_tokens = usage.get('output_tokens', 0)
                    total_tokens = prompt_tokens + completion_tokens
                    return {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens
                        }
                
            logger.warning("Could not find token usage in response structure")
            logger.debug(f"Response structure: {response}")
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
        except Exception as e:
            logger.error(f"Error extracting token usage: {e}")
            logger.debug(f"Response structure: {response}")
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Record start of LLM call."""
        self.current_trace = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": serialized.get("name", "unknown"),
            "start_time": datetime.utcnow().isoformat(),
            "prompts": prompts
        }

    def on_llm_end(self, response, **kwargs: Any) -> None:
        """Record end of LLM call with unified metrics."""
        try:
            # Get basic call info
            self.current_trace["end_time"] = datetime.utcnow().isoformat()
            self.current_trace["duration_seconds"] = (
                datetime.fromisoformat(self.current_trace["end_time"]) - 
                datetime.fromisoformat(self.current_trace["start_time"])
            ).total_seconds()
            
            # Get token usage
            token_usage = self._extract_token_usage(response)
            self.current_trace["token_usage"] = token_usage
            
            # Calculate environmental impact
            self.current_trace["environmental_impact"] = self.calculator.calculate(
                total_tokens=token_usage["total_tokens"],
                model=self.current_trace["model"]
            )
            
            # Add completion text if available
            if hasattr(response, 'generations') and response.generations:
                self.current_trace["completion"] = response.generations[0][0].text
            
            # Log summary
            self._log_summary()
            
            # Save trace
            self._save_trace()
            
        except Exception as e:
            logger.error(f"Error in on_llm_end: {e}")
            self.current_trace["error"] = str(e)
            self._save_trace()
        finally:
            self.current_trace = {}

    def _log_summary(self) -> None:
        """Log unified metrics summary."""
        impact = self.current_trace["environmental_impact"]
        usage = self.current_trace["token_usage"]
        
        logger.info("\n=== LLM Call Summary ===")
        logger.info(f"Model: {self.current_trace['model']}")
        logger.info(f"Tokens: {usage['total_tokens']:,} (prompt: {usage['prompt_tokens']:,}, "
                   f"completion: {usage['completion_tokens']:,})")
        logger.info(f"Impact: {impact['energy_kwh']:.6f} kWh, {impact['emissions_kgco2eq']:.6f} kgCO2e")
        logger.info(f"Location: {impact['country']} ({impact['hosting']}, {impact['grid_carbon_intensity']})")
        logger.info(f"Duration: {self.current_trace['duration_seconds']:.2f}s")
        logger.info("=====================\n")

    def _save_trace(self) -> None:
        """Save trace to file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        trace_file = self.traces_dir / f"trace_{timestamp}.json"
        trace_file.write_text(json.dumps(self.current_trace, indent=2))

def create_tracker(debug_dir: Path) -> List[BaseCallbackHandler]:
    """Create and return tracker handlers."""
    return [UnifiedTracker(debug_dir), StdOutCallbackHandler()]