# workflows/build_workflow.py
from langchain.schema.runnable import RunnableSequence
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from ..utils.logging import setup_logger
from ..builders import RustBuilder

logger = setup_logger()

@dataclass
class BuildResult:
    """Result of build step."""
    success: bool
    rust_code: str
    toml_content: str
    error: Optional[str] = None
    build_info: Optional[Dict[str, Any]] = None

class BuildWorkflow:
    def __init__(self, chains: Dict[str, Any], rust_builder: RustBuilder, state: "MigrationState"):
        self.chains = chains
        self.rust_builder = rust_builder
        self.state = state
        self.max_fix_attempts = 6

    def setup(self) -> RunnableSequence:
        return RunnableSequence(
            self._run_cargo_check,
            self._apply_build_fixes_if_needed,
            self._run_clippy,
            self._apply_clippy_fixes_if_needed,
            self._ensure_build_output
        )

    async def _run_cargo_check(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run cargo check on the code."""
        logger.info("Running cargo check")
        success, error, check_info = await self.rust_builder.check(
            inputs["rust_code"],
            inputs["toml_content"]
        )
        
        if success:
            logger.info("Cargo check passed")
            return inputs
            
        logger.error(f"Cargo check failed: {error}")
        inputs["build_error"] = error
        inputs["build_info"] = check_info
        return inputs

    async def _apply_build_fixes_if_needed(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply fixes for build errors if needed."""
        if "build_error" not in inputs:
            return inputs
            
        current_rust_code = inputs["rust_code"]
        current_toml_content = inputs["toml_content"]
        
        for attempt in range(self.max_fix_attempts):
            logger.info(f"Attempting build fix {attempt + 1}")
            
            try:
                fix_result = await self.chains["fix"].fix(
                    rust_code=current_rust_code,
                    toml_content=current_toml_content,
                    verification_result={
                        "critical_differences": {
                            "build": {
                                "compilation": inputs["build_error"]
                            }
                        }
                    },
                    analysis=inputs.get("analysis")
                )
                
                success, error, check_info = await self.rust_builder.check(
                    fix_result["rust_code"],
                    fix_result["toml_content"]
                )
                
                if success:
                    logger.info("Build fix successful")
                    inputs["rust_code"] = fix_result["rust_code"]
                    inputs["toml_content"] = fix_result["toml_content"]
                    inputs.pop("build_error")
                    return inputs

                current_rust_code = fix_result["rust_code"]
                current_toml_content = fix_result["toml_content"]
                inputs["build_error"] = error
                
            except Exception as e:
                logger.error(f"Build fix attempt {attempt + 1} failed: {e}")
                continue
                
        return inputs

    async def _run_clippy(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run clippy on the code."""
        if "build_error" in inputs:
            logger.info("Skipping Clippy due to build errors")
            return inputs
            
        logger.info("Running Clippy checks")
        success, error, clippy_info = await self.rust_builder.clippy(
            inputs["rust_code"],
            inputs["toml_content"]
        )
        
        if success:
            logger.info("Clippy checks passed")
            return inputs
            
        logger.error(f"Clippy checks failed: {error}")
        inputs["clippy_error"] = error
        inputs["clippy_info"] = clippy_info
        return inputs

    async def _apply_clippy_fixes_if_needed(self, inputs: Dict[str, Any]) -> BuildResult:
        """Apply fixes for clippy errors if needed."""
        if "build_error" in inputs:
            return BuildResult(
                success=False,
                rust_code=inputs["rust_code"],
                toml_content=inputs["toml_content"],
                error=inputs["build_error"],
                build_info=inputs.get("build_info")
            )
            
        if "clippy_error" not in inputs:
            return BuildResult(
                success=True,
                rust_code=inputs["rust_code"],
                toml_content=inputs["toml_content"],
                build_info=inputs.get("clippy_info")
            )
            
        current_rust_code = inputs["rust_code"]
        current_toml_content = inputs["toml_content"]
        clippy_error = inputs["clippy_error"]
            
        for attempt in range(self.max_fix_attempts):
            logger.info(f"Attempting Clippy fix {attempt + 1}")
            
            try:
                # Format Clippy errors as critical differences
                fix_result = await self.chains["fix"].fix(
                    rust_code=current_rust_code,
                    toml_content=current_toml_content,
                    verification_result={
                        "critical_differences": {
                            "build": {
                                "clippy": clippy_error
                            }
                        }
                    },
                    analysis=inputs.get("analysis")
                )
                
                # Check if fix worked
                success, error, clippy_info = await self.rust_builder.clippy(
                    fix_result["rust_code"],
                    fix_result["toml_content"]
                )
                
                if success:
                    logger.info("Clippy fix successful")
                    return BuildResult(
                        success=True,
                        rust_code=fix_result["rust_code"],
                        toml_content=fix_result["toml_content"],
                        build_info=clippy_info
                    )
                
                # Update current code for next attempt
                current_rust_code = fix_result["rust_code"]
                current_toml_content = fix_result["toml_content"]
                clippy_error = error
                    
            except Exception as e:
                logger.error(f"Clippy fix attempt {attempt + 1} failed: {e}")
                continue
                
        return BuildResult(
            success=False,
            rust_code=current_rust_code,
            toml_content=current_toml_content,
            error=f"Failed to fix Clippy errors after {self.max_fix_attempts} attempts: {clippy_error}",
            build_info=inputs.get("clippy_info")
        )
    
    async def _ensure_build_output(self, build_result: BuildResult) -> BuildResult:
        """Ensure the build output directory is properly prepared."""
        if not build_result.success:
            logger.error(f"Build failed: {build_result.error}")
            return build_result
            
        try:
            project_dir = self.rust_builder.prepare_project(
                build_result.rust_code,
                build_result.toml_content
            )
            build_result.build_info = build_result.build_info or {}
            build_result.build_info["output_dir"] = str(project_dir)
        except Exception as e:
            logger.error(f"Failed to prepare project directory: {e}")
            build_result.success = False
            build_result.error = str(e)
        
        return build_result