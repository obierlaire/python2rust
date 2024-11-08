import asyncio
import aiohttp
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import signal
import psutil
import os
from datetime import datetime
import re

from ..utils.logging import setup_logger

logger = setup_logger()


class ServerTester:
    """Tests the generated Rust web server functionality."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        startup_timeout: int = 60,
        request_timeout: int = 30  # Increased timeout for heavy computation
    ):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout
        self.process: Optional[asyncio.subprocess.Process] = None
        self.log_file: Optional[Path] = None

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
                **os.environ  # Include existing environment variables
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

    def _validate_html_content(self, content: str, is_post_response: bool = False) -> Tuple[bool, Optional[str]]:
        """Validate the HTML content matches expected structure."""
        try:
            # Check basic HTML structure
            if not all(tag in content for tag in ['<!DOCTYPE html>', '<html', '<head>', '<body>']):
                return False, "Missing basic HTML structure"

            # Check for required elements
            if not all(element in content for element in [
                '<title>Performance Demo</title>',
                '<h1>Performance Demonstration</h1>',
                '<form action="/" method="post">',
                '<button type="submit">Run Heavy Computation</button>'
            ]):
                return False, "Missing required HTML elements"

            # Check CSS styles
            if not all(style in content for style in [
                'font-family: Arial, sans-serif',
                'max-width: 800px',
                'margin: 0 auto',
                'padding: 20px'
            ]):
                return False, "Missing required CSS styles"

            # For POST responses, check computation results
            if is_post_response:
                if not all(element in content for element in [
                    '<h2>Results:</h2>',
                    'Time taken:',
                    'Number of primes found:',
                    'Last few primes:',
                    'Matrix multiplication sum:'
                ]):
                    return False, "Missing computation results"

                # Extract and validate computation results
                try:
                    # Check prime count (should be > 0)
                    prime_count_match = re.search(
                        r'Number of primes found: (\d+)', content)
                    if not prime_count_match or int(prime_count_match.group(1)) <= 0:
                        return False, "Invalid prime count"

                    # Check last primes format (should be array-like)
                    last_primes_match = re.search(
                        r'Last few primes: \[([\d, ]+)\]', content)
                    if not last_primes_match:
                        return False, "Invalid last primes format"

                    # Check matrix sum (should be a number)
                    matrix_sum_match = re.search(
                        r'Matrix multiplication sum: (-?\d+)', content)
                    if not matrix_sum_match:
                        return False, "Invalid matrix sum"

                except Exception as e:
                    return False, f"Failed to validate computation results: {str(e)}"

            return True, None

        except Exception as e:
            return False, f"HTML validation failed: {str(e)}"

    async def test_server(self, project_dir: Path) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Run comprehensive server tests."""
        try:
            # Start server
            process, log_file = await self._run_server(project_dir)

            test_results = {}

            # Wait for server to be ready
            if not await self._wait_for_server():
                if self.log_file and not self.log_file.closed:
                    self.log_file.flush()
                    log_content = Path(self.log_file.name).read_text()
                    return False, f"Server failed to start. Log contents:\n{log_content}", {
                        "log_file": str(log_file)
                    }
                return False, "Server failed to start", {
                    "log_file": str(log_file)
                }

            async with aiohttp.ClientSession() as session:
                # Test GET request
                try:
                    async with session.get(
                        f"{self.base_url}/",
                        timeout=self.request_timeout
                    ) as response:
                        content = await response.text()
                        test_results["get"] = {
                            "status": response.status,
                            "content": content
                        }

                        if response.status != 200:
                            return False, "GET request failed", test_results

                        # Validate GET response HTML
                        valid, error = self._validate_html_content(
                            content, is_post_response=False)
                        if not valid:
                            return False, f"GET response validation failed: {error}", test_results

                except Exception as e:
                    return False, f"GET request failed: {str(e)}", test_results

                # Test POST request
                try:
                    async with session.post(
                        f"{self.base_url}/",
                        data={},
                        timeout=self.request_timeout
                    ) as response:
                        content = await response.text()
                        test_results["post"] = {
                            "status": response.status,
                            "content": content
                        }

                        if response.status != 200:
                            return False, "POST request failed", test_results

                        # Validate POST response HTML and computation results
                        valid, error = self._validate_html_content(
                            content, is_post_response=True)
                        if not valid:
                            return False, f"POST response validation failed: {error}", test_results

                except Exception as e:
                    return False, f"POST request failed: {str(e)}", test_results

                logger.info("All server tests passed successfully")
                return True, None, test_results

        except Exception as e:
            logger.error(f"Server testing failed: {e}")
            return False, str(e), {}

        finally:
            self._stop_server()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._stop_server()
