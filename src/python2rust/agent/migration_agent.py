# agents/migration_agent.py
from typing import Optional, Tuple, Dict, Any, TYPE_CHECKING
from pathlib import Path
from ..initializers import LLMInitializer, ChainInitializer
from .state import MigrationState
from ..workflows import MigrationWorkflow, BuildWorkflow, TestWorkflow
from ..config.settings import Settings
from ..utils.logging import setup_logger
from langchain.schema.runnable import RunnableSequence
from ..utils.trackers import create_tracker
import json

from ..builders.rust_builder import RustBuilder
from ..builders.server_tester import ServerTester

if TYPE_CHECKING:
    from ..builders import RustBuilder
    from ..builders import ServerTester

logger = setup_logger()


class MigrationAgent:
    def __init__(
        self,
        tokens: Dict[str, str],
        output_dir: Optional[Path] = None,
        settings: Optional[Settings] = None
    ):
        # Store initialization parameters
        self.tokens = tokens
        self.settings = settings or Settings()
        if output_dir:
            self.settings.output_dir = output_dir

        self.state = MigrationState()
        self.llm_initializer = LLMInitializer(self.settings)
        self.chain_initializer = ChainInitializer(
            settings=self.settings,
            callbacks=create_tracker(debug_dir=self.settings.debug_dir)
        )

        # Initialize builders
        self.rust_builder = RustBuilder(output_dir=self.settings.output_dir)
        self.server_tester = ServerTester(
            host=self.settings.server_host,
            port=self.settings.server_port
        )

        # These will be initialized in setup()
        self.llms = None
        self.chains = None
        self.migration_workflow = None
        self.build_workflow = None
        self.test_workflow = None
        self.migration_chain = None
        self._is_setup = False

    def _setup_migration_chain(self) -> RunnableSequence:
        """Setup the migration chain sequence."""
        return RunnableSequence(
            self.migration_workflow.setup(),
            self._maybe_proceed_to_build,
            self.build_workflow.setup(),
            self._maybe_proceed_to_test,
            self.test_workflow.setup(),
            self._format_final_result
        )

    def _maybe_proceed_to_build(self, migration_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process migration result and prepare for build phase."""
        return {
            "rust_code": migration_result.get("rust_code"),
            "toml_content": migration_result.get("toml_content"),
            "analysis": migration_result.get("analysis"),
            "code": migration_result.get("verification", {}),
            "output_dir": self.settings.output_dir
        }

    def _maybe_proceed_to_test(self, build_result: Any) -> Dict[str, Any]:
        """Process build result and prepare for test phase."""
        result = {
            "build": {
                "success": build_result.success,
                "rust_code": build_result.rust_code,
                "toml_content": build_result.toml_content,
                "error": build_result.error,
                "build_info": build_result.build_info
            },
            "output_dir": self.settings.output_dir
        }

        if not build_result.success:
            logger.error(
                f"Build failed, skipping tests. Error: {build_result.error}")
            result["test"] = {
                "success": False,
                "error": "Build failed, tests skipped",
                "skipped": True
            }

        return result

    def _format_final_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format the final result and update state."""
        logger.info(f"Final result structure: {list(result.keys())}")

        build_info = result.get("build", {})
        test_info = result.get("test", {})

        self.state.update_best_result(
            verification_result=result.get("code", {}),
            rust_code=build_info.get("rust_code"),
            toml_content=build_info.get("toml_content")
        )

        return {
            "success": build_info.get("success", False),
            "rust_code": build_info.get("rust_code"),
            "toml_content": build_info.get("toml_content"),
            "output_dir": self.settings.output_dir,
            "metrics": {
                "build_duration": build_info.get("build_info", {}).get("duration"),
                "test_success": test_info.get("success", False),
                "verification_score": self.state.best_verification_score
            }
        }

    def _extract_result(self, result: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Extract the final result tuple from the pipeline result."""
        if result and result.get("success"):
            return (
                True,
                result.get("rust_code"),
                result.get("toml_content")
            )
        return False, None, None

    def _handle_failure(self) -> Tuple[bool, Optional[str], Optional[str]]:
        logger.error("Migration failed")
        return False, None, None

    async def setup(self):
        """Async setup of components that require initialization."""
        if self._is_setup:
            return

        # Initialize LLMs
        self.llms = await self.llm_initializer.initialize(
            tokens=self.tokens,
            callbacks=create_tracker(debug_dir=self.settings.debug_dir)
        )

        # Initialize the rest of the components
        self.chains = self.chain_initializer.initialize(self.llms)
        self.migration_workflow = MigrationWorkflow(self.chains, self.state)
        self.build_workflow = BuildWorkflow(
            self.chains, self.rust_builder, self.state)
        self.test_workflow = TestWorkflow(
            self.chains, self.server_tester, self.state)
        self.migration_chain = self._setup_migration_chain()
        self._is_setup = True

    async def __aenter__(self):
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return

    async def migrate(self, python_code: str) -> Tuple[bool, Optional[str], Optional[str]]:
        if not self._is_setup:
            await self.setup()

        try:
            initial_context = {
                "python_code": python_code,
                "output_dir": self.settings.output_dir
            }
            result = await self.migration_chain.ainvoke(initial_context)
            return self._extract_result(result)
        except Exception as e:
            logger.exception(f"Migration failed: {e}")
            return self._handle_failure()
