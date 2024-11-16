from langchain.schema.runnable import RunnableSequence
from typing import Dict, Any
from ..utils.logging import setup_logger
from ..utils.build_output import update_rust_files

logger = setup_logger()


class MigrationWorkflow:
    """Handles the core migration workflow from Python to Rust."""

    def __init__(self, chains: Dict[str, Any], state: "MigrationState"):
        self.chains = chains
        self.state = state
        self.max_fix_attempts = 4

    def setup(self) -> RunnableSequence:
        """Setup the migration workflow sequence."""
        return RunnableSequence(
            self._run_analysis,
            self._run_generation,
            self._run_verification,
            self._apply_fixes_if_needed,
            # TODO update_rust_files
        )

    async def _run_analysis(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run analysis on Python code."""
        logger.info("Running code analysis")
        analysis_result = await self.chains["analysis"].analyze(inputs["python_code"])
        self.state.current_analysis = analysis_result
        inputs["analysis"] = analysis_result
        return inputs

    async def _run_generation(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate initial Rust code."""
        logger.info("Generating Rust code")
        generation_result = await self.chains["generation"].generate(
            python_code=inputs["python_code"],
            analysis=inputs["analysis"]
        )
        self.state.latest_generation = generation_result
        inputs["rust_code"] = generation_result["rust_code"]
        inputs["toml_content"] = generation_result["toml_content"]
        return inputs

    async def _run_verification(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Verify generated Rust code."""
        logger.info("Verifying generated code")
        verification_result = await self.chains["verification"].verify(
            python_code=inputs["python_code"],
            rust_code=inputs["rust_code"],
            analysis=inputs["analysis"]
        )
        self.state.last_verification_result = verification_result
        inputs["verification"] = verification_result
        return inputs

    async def _apply_fixes_if_needed(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply fixes if verification found issues, preserving improvements."""
        verification_result = inputs["verification"]

        if verification_result["matches"]:
            logger.info("No fixes needed - verification passed")
            return inputs

        logger.info(
            "Verification failed - attempting fixes while preserving improvements")
        best_result = None
        best_score = float('-inf')

        for attempt in range(self.max_fix_attempts):
            logger.info(f"Fix attempt {attempt + 1}/{self.max_fix_attempts}")

            try:
                # Apply fixes while preserving improvements
                fix_result = await self.chains["fix"].fix(
                    rust_code=inputs["rust_code"],
                    toml_content=inputs["toml_content"],
                    verification_result=verification_result,
                    analysis=inputs["analysis"]
                )

                # Re-verify the fixed code
                new_verification = await self.chains["verification"].verify(
                    python_code=inputs["python_code"],
                    rust_code=fix_result["rust_code"],
                    analysis=inputs["analysis"]
                )

                # Calculate score based on remaining differences
                score = self._calculate_fix_score(new_verification)
                logger.info(f"Score: {score}")

                # Update best result if this attempt is better
                if score > best_score:
                    logger.info(f"New best score achieved: {score}")
                    best_score = score
                    best_result = {
                        "rust_code": fix_result["rust_code"],
                        "toml_content": fix_result["toml_content"],
                        "verification": new_verification
                    }

                # Use this verification result for next iteration to build upon fixes
                verification_result = new_verification
                inputs["rust_code"] = fix_result["rust_code"]
                inputs["toml_content"] = fix_result["toml_content"]

                if new_verification["matches"]:
                    logger.info(f"Fixes successful on attempt {attempt + 1}")
                    return inputs

            except Exception as e:
                logger.error(f"Fix attempt {attempt + 1} failed: {e}")
                continue

        # If we have a best result but didn't achieve perfect matching
        if best_result:
            logger.info("Using best achieved result")
            inputs["rust_code"] = best_result["rust_code"]
            inputs["toml_content"] = best_result["toml_content"]
            inputs["verification"] = best_result["verification"]
        else:
            logger.warning("No successful fixes achieved")
            logger.info("Proceeding with the best available result, if any")

        return inputs

    def _calculate_fix_score(self, verification_result: Dict[str, Any]) -> float:
        """Calculate a score for the fix attempt based on remaining differences."""
        score = 0.0

        if verification_result["matches"]:
            return float('inf')

        differences = verification_result.get("critical_differences", {})

        # Count remaining differences by category
        for category, issues in differences.items():
            # More weight to core functionality
            weight = 2.0 if category == "core" else 1.0
            score -= len(issues) * weight

        return score
