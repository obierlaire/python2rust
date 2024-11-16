import asyncio
import aiohttp
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
import signal
import psutil
import os
from datetime import datetime
import re

from ..utils.logging import setup_logger

logger = setup_logger()


class ServerTester:
    """Tests the generated Rust web server functionality using external test script."""

    ERROR_PATTERNS = [
        r'(?i)error',        # Case-insensitive error
        r'panic',            # Rust panics
        r'thread.*panic',    # Thread panics
        r'unwrap.*failed',   # Unwrap failures
        r'exception',        # General exceptions
        r'fail[a-z]*:',      # Failures (failed:, failing:, etc.)
        r'FATAL',            # Fatal errors
        r'ERROR:',           # Error logs
        r'WARN:',            # Warnings (optional, but might be important)
    ]

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        startup_timeout: int = 60,
        request_timeout: int = 30,
        test_script_path: Path = Path("./test.sh")
    ):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.test_script_path = test_script_path
        self.process: Optional[asyncio.subprocess.Process] = None
        self.log_file: Optional[Path] = None
        self.log_errors: List[str] = []

    def _validate_test_script(self) -> None:
        """Validate that test script exists and is executable."""
        if not self.test_script_path.exists():
            error_msg = f"Test script not found: {self.test_script_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if os.name != 'nt':  # Unix-like systems
            if not os.access(self.test_script_path, os.X_OK):
                error_msg = f"Test script is not executable: {self.test_script_path}"
                logger.error(error_msg)
                raise PermissionError(error_msg)

    def _check_log_for_errors(self) -> List[str]:
        """Check server log file for error patterns."""
        if not self.log_file or not Path(self.log_file.name).exists():
            return []

        errors = []
        try:
            # Ensure log is flushed
            if not self.log_file.closed:
                self.log_file.flush()

            # Read log content
            log_content = Path(self.log_file.name).read_text()

            # Check each line for error patterns
            for line in log_content.splitlines():
                for pattern in self.ERROR_PATTERNS:
                    if re.search(pattern, line):
                        errors.append(line.strip())
                        break  # Skip other patterns for this line

            return errors
        except Exception as e:
            logger.error(f"Error checking log file: {e}")
            return [f"Failed to check log file: {str(e)}"]

    async def _run_server(self, project_dir: Path) -> Tuple[asyncio.subprocess.Process, Path]:
        """Start the Rust server process."""
        try:
            # Prepare log file
            log_file = project_dir / "server.log"
            log_handle = open(log_file, "w")

            # Set environment variables
            env = {
                "RUST_BACKTRACE": "1",
                "RUST_LOG": "debug",
                **os.environ
            }

            # Start server process
            process = await asyncio.create_subprocess_exec(
                "cargo", "run", "--release",
                cwd=project_dir,
                stdout=log_handle,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )

            self.process = process
            self.log_file = log_handle

            return process, log_file

        except Exception as e:
            if 'log_handle' in locals() and not log_handle.closed:
                log_handle.close()
            logger.error(f"Failed to start server: {e}")
            raise

    async def _wait_for_server(self) -> bool:
        """Wait for server to be ready to accept connections."""
        start_time = datetime.now()

        async with aiohttp.ClientSession() as session:
            while (datetime.now() - start_time).total_seconds() < self.startup_timeout:
                # Check for early errors in logs
                errors = self._check_log_for_errors()
                if errors:
                    logger.error("Found errors in server log during startup:")
                    for error in errors:
                        logger.error(f"  {error}")
                    self.log_errors.extend(errors)
                    return False

                if self.process and self.process.returncode is not None:
                    if self.log_file and not self.log_file.closed:
                        self.log_file.flush()
                        log_content = Path(self.log_file.name).read_text()
                        logger.error(
                            f"Server process terminated. Log contents:\n{log_content}")
                    return False

                try:
                    async with session.get(
                        f"{self.base_url}/",
                        timeout=1
                    ) as response:
                        if response.status == 200:
                            logger.info("Server is ready")
                            return True
                except Exception:
                    await asyncio.sleep(0.5)
                    continue

        if self.log_file and not self.log_file.closed:
            self.log_file.flush()
            log_content = Path(self.log_file.name).read_text()
            logger.error(
                f"Server startup timeout. Log contents:\n{log_content}")

        return False

    def _stop_server(self) -> None:
        """Stop the server and cleanup resources."""
        # Check for final errors before stopping
        final_errors = self._check_log_for_errors()
        if final_errors:
            logger.error("Found errors in server log during shutdown:")
            for error in final_errors:
                logger.error(f"  {error}")
            self.log_errors.extend(final_errors)

        if self.process is None:
            return

        try:
            pid = self.process.pid
            if not pid:
                return

            try:
                process = psutil.Process(pid)

                if os.name != 'nt':  # Unix-like systems
                    try:
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, signal.SIGTERM)

                        try:
                            process.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            os.killpg(pgid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:  # Windows
                    try:
                        children = process.children(recursive=True)
                        process.terminate()

                        try:
                            process.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            process.kill()

                        for child in children:
                            try:
                                if child.is_running():
                                    child.terminate()
                                    try:
                                        child.wait(timeout=2)
                                    except psutil.TimeoutExpired:
                                        child.kill()
                            except psutil.NoSuchProcess:
                                pass
                    except psutil.NoSuchProcess:
                        pass

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        finally:
            if self.log_file and not self.log_file.closed:
                try:
                    self.log_file.flush()
                    self.log_file.close()
                except Exception as e:
                    logger.error(f"Error closing log file: {e}")

            self.process = None
            self.log_file = None

    async def _run_test_script(self, project_dir: Path) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Run the external test script."""
        try:
            env = {
                "SERVER_HOST": self.host,
                "SERVER_PORT": str(self.port),
                "PROJECT_DIR": str(project_dir),
                **os.environ
            }

            logger.info(
                f"Running test script: {self.test_script_path} in {project_dir}")

            process = await asyncio.create_subprocess_exec(
                f"./{self.test_script_path.name}",
                cwd=self.test_script_path.parent,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # Check for new server errors
            current_errors = self._check_log_for_errors()
            if current_errors:
                logger.error("Found errors in server log during tests:")
                for error in current_errors:
                    logger.error(f"  {error}")
                self.log_errors.extend(current_errors)

            success = process.returncode == 0 and not current_errors

            result = {
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "exit_code": process.returncode,
                "server_errors": self.log_errors
            }

            if not success:
                error_msg = stderr.decode() if stderr else "Test script failed with no error message"
                if self.log_errors:
                    error_msg += f"\nServer errors:\n" + \
                        "\n".join(self.log_errors)
                logger.error(f"Test script failed: {error_msg}")
                return False, error_msg, result

            logger.info("Test script completed successfully")
            return True, None, result

        except Exception as e:
            logger.error(f"Failed to run test script: {e}")
            return False, str(e), {"error": str(e), "test_error": self.log_errors}

    async def test_server(self, project_dir: Path) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Run server tests using external test script."""
        self.log_errors = []  # Reset error log for new test run

        try:
            self._validate_test_script()

            # Start server
            process, log_file = await self._run_server(project_dir)

            # Wait for server to be ready
            if not await self._wait_for_server():
                if self.log_file and not self.log_file.closed:
                    self.log_file.flush()
                    log_content = Path(self.log_file.name).read_text()
                    return False, f"Server failed to start. Log contents:\n{log_content}", {
                        "log_file": str(log_file),
                        "server_errors": self.log_errors
                    }
                return False, "Server failed to start", {
                    "log_file": str(log_file),
                    "server_errors": self.log_errors
                }

            # Run external test script
            success, error, results = await self._run_test_script(project_dir)

            # Ensure server errors are included in results
            results["server_errors"] = self.log_errors

            if not success:
                return False, f"Test script failed: {error}", results

            return True, None, results

        except FileNotFoundError as e:
            error_msg = str(e)
            logger.error(error_msg)
            return False, error_msg, {"error": "test script not found"}

        except PermissionError as e:
            error_msg = str(e)
            logger.error(error_msg)
            return False, error_msg, {"error": "test script not executable"}

        except Exception as e:
            logger.error(f"Server testing failed: {e}")
            return False, str(e), {}

        finally:
            self._stop_server()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._stop_server()
