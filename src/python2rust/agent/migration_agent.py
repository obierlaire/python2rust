# agents/migration_agent.py
from typing import Optional, Tuple, Dict, Any, TYPE_CHECKING
from pathlib import Path
from ..initializers import LLMInitializer, ChainInitializer
from .state import MigrationState
from ..workflows import MigrationWorkflow, BuildWorkflow, TestWorkflow
from ..config.settings import Settings
from ..utils.logging import setup_logger
from langchain.schema.runnable import RunnableSequence
from ..utils.debug_manager import DebugManager
from ..utils.trackers import create_tracker
from langchain_anthropic import ChatAnthropic 
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
        claude_token: str,
        hf_token: Optional[str] = None,
        output_dir: Optional[Path] = None,
        settings: Optional[Settings] = None
    ):

        # Initialize settings and state
        self.settings = settings or Settings()
        if output_dir:
            self.settings.output_dir = output_dir
        self.state = MigrationState()


        # Initialize components with callbacks
        llm_initializer = LLMInitializer(self.settings)
        chain_initializer = ChainInitializer(
            settings=self.settings,
            callbacks=create_tracker(debug_dir=self.settings.debug_dir)
        )
        
        # Initialize LLMs and chains
        self.llms = llm_initializer.initialize(
            claude_token=claude_token,
            hf_token=hf_token,
            callbacks=create_tracker(debug_dir=self.settings.debug_dir)
        )
        self.chains = chain_initializer.initialize(self.llms)
        
        # Initialize builders
        self.rust_builder = RustBuilder(output_dir=self.settings.output_dir)
        self.server_tester = ServerTester(
            host=self.settings.server_host,
            port=self.settings.server_port
        )
        
        # Setup workflows
        self.migration_workflow = MigrationWorkflow(self.chains, self.state)
        self.build_workflow = BuildWorkflow(self.chains, self.rust_builder, self.state)
        self.test_workflow = TestWorkflow(self.chains, self.server_tester, self.state)
        
        # Setup main pipeline
        self.migration_chain = self._setup_migration_chain()

    def _setup_migration_chain(self):
        return RunnableSequence(
            self.migration_workflow.setup(),
            self._maybe_proceed_to_build,
            self.build_workflow.setup(),
            self._maybe_proceed_to_test,
            self.test_workflow.setup(),
            self._format_final_result
        )
    
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return

    async def migrate(self, python_code: str) -> Tuple[bool, Optional[str], Optional[str]]:
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

    def _extract_result(self, result: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Extract the final result tuple from the pipeline result."""
        if result and result.get("success"):
            return (
                True,
                result.get("rust_code"),
                result.get("toml_content")
            )
        return False, None, None
        
    def _maybe_proceed_to_build(self, migration_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process migration result and prepare for build phase."""
        return {
            "rust_code": migration_result.get("rust_code"),
            "toml_content": migration_result.get("toml_content"),
            "analysis": migration_result.get("analysis"),
            "code": migration_result.get("verification", {}),
            "output_dir": self.settings.output_dir  # Ensure output_dir is passed through
        }

    def _maybe_proceed_to_test(self, build_result: Any) -> Dict[str, Any]:
        """Process build result and prepare for test phase."""
        # Handle BuildResult object
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
        
        # Don't proceed to testing if build failed
        if not build_result.success:
            logger.error(f"Build failed, skipping tests. Error: {build_result.error}")
            result["test"] = {
                "success": False,
                "error": "Build failed, tests skipped",
                "skipped": True
            }
            return result
            
        return result

    def _format_final_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format the final result and update state."""
        logger.info(f"Final result structure: {list(result.keys())}")
        
        # Extract build info
        build_info = result.get("build", {})
        test_info = result.get("test", {})
        
        # Update state with best result
        self.state.update_best_result(
            verification_result=result.get("code", {}),
            rust_code=build_info.get("rust_code"),
            toml_content=build_info.get("toml_content")
        )
        
        return {
            "success": build_info.get("success", False),
            "rust_code": build_info.get("rust_code"),
            "toml_content": build_info.get("toml_content"),
            "output_dir": self.settings.output_dir,  # Include output_dir in final result
            "metrics": {
                "build_duration": build_info.get("build_info", {}).get("duration"),
                "test_success": test_info.get("success", False),
                "verification_score": self.state.best_verification_score
            }
        }

    def _handle_failure(self) -> Tuple[bool, Optional[str], Optional[str]]:
        logger.error("Migration failed")
        return False, None, None