# workflows/test_workflow.py
from langchain.schema.runnable import RunnableSequence
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import shutil
import sys
from pathlib import Path
from ..utils.logging import setup_logger
from ..builders import ServerTester
from ..utils.error_formatter import format_error_for_fix
from ..utils.build_output import update_rust_files


logger = setup_logger()


class TestScriptError(Exception):
    """Custom exception for test script issues."""
    pass


@dataclass
class TestResult:
    """Result of test step."""
    success: bool
    rust_code: str
    toml_content: str
    error: Optional[str] = None
    test_info: Optional[Dict[str, Any]] = None


class TestWorkflow:
    def __init__(self, chains: Dict[str, Any], server_tester: ServerTester, state: "MigrationState"):
        self.chains = chains
        self.server_tester = server_tester
        self.state = state
        self.max_fix_attempts = 3

    def setup(self) -> RunnableSequence:
        return RunnableSequence(
            self._check_rust_installation,
            self._run_server_tests,
            self._handle_test_results,
            # TODO update_rust_files,
        )

    def _extract_compiler_errors(self, error_text: str) -> List[str]:
        """Extract compiler errors from the error text."""
        error_lines = []
        current_error = []
        in_error = False

        for line in error_text.split('\n'):
            if 'error[' in line or 'error:' in line:
                if in_error and current_error:
                    error_lines.append('\n'.join(current_error))
                current_error = [line]
                in_error = True
            elif in_error and line.strip() and not line.startswith('   Compiling'):
                current_error.append(line)
            elif in_error and not line.strip():
                if current_error:
                    error_lines.append('\n'.join(current_error))
                current_error = []
                in_error = False

        if current_error:
            error_lines.append('\n'.join(current_error))

        return error_lines

    def _check_rust_installation(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Verify Rust toolchain is available."""
        cargo_path = shutil.which('cargo')
        if not cargo_path:
            error_msg = """
Rust toolchain not found! Please install Rust:
- On Unix/macOS: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
- On Windows: https://rustup.rs/

After installation, restart your terminal and try again.
"""
            logger.error(error_msg)
            inputs["test_error"] = "Rust toolchain not found"
            inputs["test_success"] = False
            return inputs

        logger.info(f"Found cargo at: {cargo_path}")
        return inputs

    async def _run_server_tests(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run server tests."""
        try:
            if not self.server_tester.test_script_path.exists():
                error_msg = f"Test script not found: {self.server_tester.test_script_path}"
                logger.error(error_msg)
                raise TestScriptError(error_msg)

            if inputs.get("test_error"):
                return inputs

            logger.info("Running server tests")
            # Extract required fields from build result
            build_info = inputs.get("build", {})
            rust_code = build_info.get("rust_code")
            toml_content = build_info.get("toml_content")
            output_dir = inputs.get("output_dir")

            if not all([rust_code, toml_content, output_dir]):
                missing = []
                if not rust_code:
                    missing.append("rust_code")
                if not toml_content:
                    missing.append("toml_content")
                if not output_dir:
                    missing.append("output_dir")
                error = f"Missing required fields for server test: {', '.join(missing)}"
                logger.error(error)
                inputs["test_error"] = error
                inputs["test_success"] = False
                return inputs

            # Run the tests
            success, error, test_info = await self.server_tester.test_server(output_dir)

            inputs["test_success"] = success
            inputs["test_error"] = error
            inputs["test_info"] = test_info

            # Preserve the code for potential fixes
            inputs["rust_code"] = rust_code
            inputs["toml_content"] = toml_content

            return inputs

        except TestScriptError:
            raise
        except Exception as e:
            logger.exception(f"Server testing failed: {e}")
            inputs["test_success"] = False
            inputs["test_error"] = str(e)
            return inputs

    async def _handle_test_results(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle test results and attempt fixes if needed."""
        if inputs.get("test_success"):
            logger.info("Server tests passed")
            return inputs

        build_info = inputs.get("build", {})
        rust_code = build_info.get("rust_code")
        toml_content = build_info.get("toml_content")

        if not rust_code or not toml_content:
            logger.error("Missing code for fixes")
            return inputs

        current_rust_code = rust_code
        current_toml_content = toml_content

        for attempt in range(self.max_fix_attempts):
            logger.info(f"Attempting server fix {attempt + 1}")

            try:
                error_text = format_error_for_fix(inputs.get("test_error", ""))

                # Categorize the error
                if "Image verification failed" in error_text:
                    verification_result = {
                        "critical_differences": {
                            "image": [
                                "Image verification failed: Generated image format is invalid",
                                "Must properly encode image data for web display"
                            ]
                        }
                    }
                elif "cannot identify image file" in error_text:
                    verification_result = {
                        "critical_differences": {
                            "image": [
                                "Image encoding is incorrect",
                                "Must generate valid PNG image data before base64 encoding"
                            ]
                        }
                    }
                else:
                    verification_result = {
                        "critical_differences": {
                            "server": [error_text]
                        }
                    }

                logger.info(f"Fixing issues: {verification_result}")

                fix_result = await self.chains["fix"].fix(
                    rust_code=current_rust_code,
                    toml_content=current_toml_content,
                    verification_result=verification_result,
                    analysis=inputs.get("analysis")
                )

                # Update the code after fix
                current_rust_code = fix_result["rust_code"]
                current_toml_content = fix_result["toml_content"]

                # Check if fix worked
                success, error, test_info = await self.server_tester.test_server(
                    inputs["output_dir"]
                )

                if success:
                    logger.info("Server fix successful")
                    inputs["build"]["rust_code"] = current_rust_code
                    inputs["build"]["toml_content"] = current_toml_content
                    inputs["test_success"] = True
                    inputs["test_error"] = None
                    inputs["test_info"] = test_info
                    return inputs

                inputs["test_error"] = error
                inputs["test_info"] = test_info

            except Exception as e:
                logger.error(f"Server fix attempt {attempt + 1} failed: {e}")
                continue

        inputs["build"]["rust_code"] = current_rust_code
        inputs["build"]["toml_content"] = current_toml_content
        return inputs
