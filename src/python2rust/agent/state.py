from dataclasses import dataclass, field
from typing import Set, Dict, Any, List, Optional

@dataclass
class MigrationState:
    """Tracks state and metrics during migration process."""
    successful_fixes: Set[str] = field(default_factory=set)
    failed_fixes: Set[str] = field(default_factory=set)
    partial_successes: Dict[str, Any] = field(default_factory=dict)
    best_verification_score: float = 0.0
    best_result: Optional[Dict[str, Any]] = None
    
    # Metrics tracking
    analysis_times: List[float] = field(default_factory=list)
    generation_times: List[float] = field(default_factory=list)
    verification_times: List[float] = field(default_factory=list)
    fix_times: Dict[str, List[float]] = field(default_factory=dict)
    token_usage: Dict[str, int] = field(default_factory=dict)

    # Additional state for workflow
    current_analysis: Optional[Dict[str, Any]] = None
    latest_generation: Optional[Dict[str, Any]] = None
    last_verification_result: Optional[Dict[str, Any]] = None
    current_differences: Optional[Dict[str, Any]] = None
    
    def update_metrics(self, step: str, duration: float, tokens: int):
        """Update metrics for a step."""
        if step == "analysis":
            self.analysis_times.append(duration)
        elif step == "generation":
            self.generation_times.append(duration)
        elif step == "verification":
            self.verification_times.append(duration)
        elif step.startswith("fix_"):
            if step not in self.fix_times:
                self.fix_times[step] = []
            self.fix_times[step].append(duration)
            
        self.token_usage[step] = self.token_usage.get(step, 0) + tokens

    def update_best_result(self, verification_result: Dict[str, Any], 
                          rust_code: str, toml_content: str):
        """Update best result if current is better."""
        score = 0
        if verification_result.get("critical_differences"):
            for differences in verification_result["critical_differences"].values():
                score -= len(differences)
        
        if score > self.best_verification_score:
            self.best_verification_score = score
            self.best_result = {
                "rust_code": rust_code,
                "toml_content": toml_content,
                "verification": verification_result
            }
