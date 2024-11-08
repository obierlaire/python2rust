'''
Modules that handles build and testing Rust code.
'''
import asyncio
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from datetime import datetime

from ..utils.logging import setup_logger

logger = setup_logger()


class RustBuilder:
    """Handles building and testing Rust code."""

    def __init__(self, output_dir: Path, build_timeout: int = 300):
        self.output_dir = output_dir
        self.build_timeout = build_timeout
        self.src_dir = output_dir / "src"

    async def _run_command(self, cmd: list[str], cwd: Path) -> Tuple[int, str, str]:
        """Run a command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.build_timeout
                )
            except asyncio.TimeoutError as e:
                process.kill()
                raise TimeoutError(f"Command timed out after {self.build_timeout} seconds") from e

            return (
                process.returncode,
                stdout.decode() if stdout else "",
                stderr.decode() if stderr else ""
            )

        except Exception as e:
            logger.error("Command execution failed: %s", e)
            raise

    def prepare_project(self, rust_code: str, toml_content: str) -> Path:
        """Prepare Rust project structure."""
        try:
            # Create directories
            self.src_dir.mkdir(parents=True, exist_ok=True)

            # Write files
            (self.src_dir / "main.rs").write_text(rust_code)
            (self.output_dir / "Cargo.toml").write_text(toml_content)

            return self.output_dir

        except Exception as e:
            logger.error("Failed to prepare project: %s", e)
            raise

    def _create_build_log(
        self,
        cmd: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
        duration: float
    ) -> str:
        """Create a detailed build log."""
        return f"""
========== Build Log ==========
Command: {' '.join(cmd)}
Working Directory: {self.output_dir}
Exit Code: {returncode}
Duration: {duration:.2f} seconds
Timestamp: {datetime.now().isoformat()}

STDOUT:
{stdout}

STDERR:
{stderr}
==============================
"""

    async def build(
        self,
        rust_code: str,
        toml_content: str,
        release: bool = True
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Build Rust project and return status, error if any, and build info."""
        try:
            # Prepare project
            project_dir = self.prepare_project(rust_code, toml_content)

            # Build command
            cmd = ["cargo", "build"]
            if release:
                cmd.append("--release")

            # Record start time
            start_time = datetime.now()

            # Run build
            returncode, stdout, stderr = await self._run_command(cmd, project_dir)

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            # Create build log
            build_log = self._create_build_log(
                cmd=cmd,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
                duration=duration
            )

            # Save build log
            log_file = project_dir / "build.log"
            log_file.write_text(build_log)

            # Prepare build info
            build_info = {
                "success": returncode == 0,
                "duration": duration,
                "log_file": str(log_file),
                "output_dir": str(project_dir)
            }

            if returncode == 0:
                logger.info(f"Build successful in {duration:.2f} seconds")
                return True, None, build_info
            else:
                logger.error("Build failed")
                return False, stderr, build_info

        except Exception as e:
            logger.error("Build process failed: %s", str(e))
            return False, str(e), {"error": str(e)}

    async def check(
        self,
        rust_code: str,
        toml_content: str
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Run cargo check on the code."""
        try:
            # Prepare project
            project_dir = self.prepare_project(rust_code, toml_content)

            # Run check
            cmd = ["cargo", "check"]
            returncode, stdout, stderr = await self._run_command(cmd, project_dir)

            # Create check info
            check_info = {
                "success": returncode == 0,
                "output_dir": str(project_dir)
            }

            if returncode == 0:
                logger.info("Cargo check passed")
                return True, None, check_info
            else:
                logger.error("Cargo check failed")
                return False, stderr, check_info

        except Exception as e:
            logger.error(f"Check process failed: {e}")
            return False, str(e), {"error": str(e)}

    async def test(
        self,
        rust_code: str,
        toml_content: str
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Run cargo test on the code."""
        try:
            # Prepare project
            project_dir = self.prepare_project(rust_code, toml_content)

            # Run tests
            cmd = ["cargo", "test"]
            returncode, stdout, stderr = await self._run_command(cmd, project_dir)

            # Create test info
            test_info = {
                "success": returncode == 0,
                "output": stdout,
                "output_dir": str(project_dir)
            }

            if returncode == 0:
                logger.info("Tests passed")
                return True, None, test_info
            else:
                logger.error("Tests failed")
                return False, stderr, test_info

        except Exception as e:
            logger.error(f"Test process failed: {e}")
            return False, str(e), {"error": str(e)}

    async def clippy(
        self,
        rust_code: str,
        toml_content: str
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Run clippy lints on the code."""
        try:
            # Prepare project
            project_dir = self.prepare_project(rust_code, toml_content)

            # Run clippy
            cmd = ["cargo", "clippy", "--", "-D", "warnings"]
            returncode, stdout, stderr = await self._run_command(cmd, project_dir)

            # Create clippy info
            clippy_info = {
                "success": returncode == 0,
                "output": stdout,
                "output_dir": str(project_dir)
            }

            if returncode == 0:
                logger.info("Clippy checks passed")
                return True, None, clippy_info
            else:
                logger.error("Clippy checks failed")
                return False, stderr, clippy_info

        except Exception as e:
            logger.error(f"Clippy process failed: {e}")
            return False, str(e), {"error": str(e)}
