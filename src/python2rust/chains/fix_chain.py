# chains/fix_chain.py
from typing import Dict, Any, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain.chains import LLMChain
from pathlib import Path

from ..prompts.fix_prompts import FIX_PROMPT, SYSTEM_MESSAGE
from ..utils.logging import setup_logger
from ..utils.code_extractor import CodeExtractor
from langchain.prompts import ChatPromptTemplate
import json

logger = setup_logger()

class FixChain:
    """Chain for fixing Rust implementation based on verification results."""
    
    def __init__(self, llm: BaseLanguageModel, specs_file: Path):
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_MESSAGE),
            ("human", FIX_PROMPT.template)
        ])
        
        self.chain = LLMChain(
            llm=llm,
            prompt=chat_prompt,
            output_key="fixed_code"
        )
        self.code_extractor = CodeExtractor()
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
                        "build": {
                            "compilation": "Must compile without errors",
                            "clippy": "Must pass Clippy checks"
                        }
                    }
                }
        except Exception as e:
            logger.error(f"Failed to load migration specs: {e}")
            raise

    def _format_clippy_error(self, error: str) -> str:
        """Format Clippy error message for better LLM understanding."""
        lines = error.split('\n')
        formatted = []
        current_error = []
        
        for line in lines:
            if line.startswith('error:'):
                if current_error:
                    formatted.append('\n'.join(current_error))
                current_error = [line]
            elif line.strip() and current_error:
                current_error.append(line)
                
        if current_error:
            formatted.append('\n'.join(current_error))
            
        return '\n\n'.join(formatted)

    async def fix(
        self,
        rust_code: str,
        toml_content: str,
        verification_result: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """Fix Rust implementation based on verification results."""
        try:
            build_issues = verification_result.get("critical_differences", {}).get("build", {})
            
            # Special handling for Clippy errors
            if isinstance(build_issues, dict) and "clippy" in build_issues:
                logger.info("Processing Clippy errors")
                clippy_error = build_issues["clippy"]
                formatted_error = self._format_clippy_error(clippy_error)
                verification_result["critical_differences"]["build"] = {
                    "clippy": formatted_error
                }
                logger.info(f"Formatted Clippy error: {formatted_error}")

            response = await self.chain.ainvoke({
                "rust_code": rust_code,
                "toml_content": toml_content,
                "verification_result": verification_result,
                "analysis": analysis,
                "migration_specs": self.migration_specs
            })
            
            result = response["fixed_code"]
            fixed_rust, fixed_toml = self.code_extractor.extract_code_blocks(result)
            
            if "clippy" in str(verification_result):
                logger.info("Applied fixes for Clippy issues")
            else:
                logger.info("Applied fixes for critical differences")
                
            return {
                "rust_code": fixed_rust,
                "toml_content": fixed_toml
            }
        except Exception as e:
            logger.error(f"Fix application failed: {e}")
            raise