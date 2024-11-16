from typing import Any, Dict
from ..builders.build_result import BuildResult
from ..utils.logging import setup_logger

logger = setup_logger()


async def ensure_build_output(self, build_result: BuildResult) -> BuildResult:
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


async def update_rust_files(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    # TODO also write files to disk
    return inputs
