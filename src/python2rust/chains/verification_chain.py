from typing import Dict, Any, Optional, List
from pathlib import Path
from langchain_core.language_models import BaseLanguageModel
from langchain.chains import LLMChain
from ..prompts.verification_prompts import VERIFICATION_PROMPT
from ..utils.logging import setup_logger
import json
from langchain.callbacks.base import BaseCallbackHandler


logger = setup_logger()

class VerificationChain:
    """Chain for verifying Rust implementation against Python original."""
    
    def __init__(self, llm: BaseLanguageModel, specs_file: Path, callbacks: Optional[List[BaseCallbackHandler]] = None):
        self.chain = LLMChain(
            llm=llm,
            prompt=VERIFICATION_PROMPT,
            output_key="verification",
            callbacks=callbacks,
            verbose=True 
        )
        self.specs_file = specs_file
        self.migration_specs = self._load_migration_specs()

    def _load_migration_specs(self) -> Dict[str, Any]:
        """Load migration specifications from file."""
        try:
            if self.specs_file.exists():
                return json.loads(self.specs_file.read_text())
            else:
                logger.warning(f"Specs file {self.specs_file} not found, using defaults")
                return {
                    "ignorable_differences": [],
                    "critical_differences": {
                        "core": ["Algorithm correctness"],
                        "routing": {},
                        "image": {},
                        "template": {},
                        "build": {},
                    }
                }
        except Exception as e:
            logger.error(f"Failed to load migration specs: {e}")
            raise

    def _should_ignore_difference(self, difference: str) -> bool:   # pylint: disable=
        """Check if a difference should be ignored based on specs."""
        difference_lower = difference.lower()
        
        # Check if any ignorable pattern matches this difference
        return any(
            ignore_pattern.lower() in difference_lower
            for ignore_pattern in self.migration_specs["ignorable_differences"]
        )

    def _filter_critical_differences(self, differences: Dict[str, Any]) -> Dict[str, Any]:
        """Remove ignorable differences from verification results."""
        filtered = {}
        
        for category, issues in differences.get("critical_differences", {}).items():
            if category == "build" and "clippy" in issues:
                # Always include Clippy errors as critical
                filtered[category] = issues
            elif isinstance(issues, list):
                # Filter out ignorable differences for other categories
                critical_issues = [
                    issue for issue in issues
                    if not self._should_ignore_difference(issue)
                ]
                if critical_issues:
                    filtered[category] = critical_issues
            else:
                # Keep non-list values as is
                filtered[category] = issues
        
        return filtered

    async def verify(
        self,
        python_code: str,
        rust_code: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify Rust implementation against Python original."""
        try:
            result = await self.chain.ainvoke({
                "python_code": python_code,
                "rust_code": rust_code,
                "analysis": analysis,
                "migration_specs": self.migration_specs
            }, include_run_info=True)
            
            verification_result = result["verification"]
            logger.info("Verification result: %s", verification_result)
            if isinstance(verification_result, str):
                verification_result = json.loads(verification_result)

            critical_differences = verification_result["critical_differences"]
            
            # Update the matches flag based on remaining critical differences
            has_critical_differences = any(
                isinstance(issues, list) and issues
                for issues in critical_differences.values()
            )
            
            filtered_result = {
                "matches": not has_critical_differences,
                "critical_differences": critical_differences,
                "suggestions": verification_result.get("suggestions", [])
            }

            logger.info(
                f"Verification {'succeeded' if filtered_result['matches'] else 'failed'}"
            )
            if not filtered_result["matches"]:
                logger.info("Critical differences found:")
                for category, issues in filtered_result["critical_differences"].items():
                    if isinstance(issues, list) and issues:
                        logger.info(f"- {category}:")
                        for issue in issues:
                            logger.info(f"  - {issue}")

            return filtered_result
            
        except Exception as e:
            logger.exception(f"Verification failed: {e}")
            raise