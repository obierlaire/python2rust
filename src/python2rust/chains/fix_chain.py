from typing import Dict, Any, Optional, List, Tuple, Literal
from langchain_core.language_models import BaseLanguageModel
from langchain.chains import LLMChain
from pathlib import Path
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import ChatPromptTemplate
import json
import re

from ..prompts.fix_prompts import FIX_PROMPT, SYSTEM_MESSAGE
from ..utils.logging import setup_logger
from ..utils.code_extractor import CodeExtractor

logger = setup_logger()

ModelType = Literal["claude", "codellama"]

class FixChain:
    """Chain for fixing Rust implementation based on verification results."""
    
    def __init__(
        self, 
        llm: BaseLanguageModel,
        specs_file: Path, 
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ):
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_MESSAGE),
            ("human", FIX_PROMPT.template)
        ])
        
        self.chain = LLMChain(
            llm=llm,
            prompt=chat_prompt,
            output_key="fixed_code",
            callbacks=callbacks,
            verbose=True 
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

    def _format_verification_result(self, verification_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format verification result into a clear, structured format."""
        formatted = {
            "critical_differences": {},
            "issues_summary": self._format_issues_for_prompt(verification_result)
        }
        
        # Keep original structure for backward compatibility
        for category, issues in verification_result.get("critical_differences", {}).items():
            formatted["critical_differences"][category] = issues
                
        return formatted

    def _format_issues_for_prompt(self, verification_result: Dict[str, Any]) -> str:
        """Format all issues into a clear, readable format for the LLM."""
        sections = []
        
        for category, issues in verification_result.get("critical_differences", {}).items():
            if category == "build":
                if isinstance(issues, dict):
                    if "clippy" in issues:
                        # Add Clippy warnings section
                        sections.extend(self._format_clippy_section(issues["clippy"]))
                    if "compilation" in issues:
                        sections.extend(self._format_compilation_section(issues["compilation"]))
            else:
                if issues:  # Only add non-empty sections
                    sections.append(f"{category.title()} Issues:")
                    if isinstance(issues, list):
                        sections.extend(f"- {issue}" for issue in issues)
                    elif isinstance(issues, dict):
                        sections.extend(f"- {k}: {v}" for k, v in issues.items())
                    sections.append("---")
        
        return "\n".join(sections) if sections else "No issues found"

    def _format_clippy_section(self, error: str) -> List[str]:
        """Format Clippy errors in a clear, action-oriented way."""
        sections = ["Clippy Fix Required:"]
        
        # Parse the error message
        for line in error.split('\n'):
            line = line.strip()
            if line.startswith('error:'):
                sections.append(f"ISSUE: {line[6:].strip()}")
            elif '-->' in line:  # Location line
                sections.append(f"LOCATION: {line.split('-->')[1].strip()}")
            elif '|' in line and 'for k in' in line:  # Actual code line
                code = line.split('|')[1].strip()
                sections.append(f"CURRENT CODE: {code}")
            elif 'for (k, <item>)' in line:  # The suggested fix
                fix = line.strip()
                sections.append(f"REPLACE WITH: {fix}")
                break  # Stop after finding the fix
        
        return sections


    def _format_compilation_section(self, error: str) -> List[str]:
        """Format compilation errors into readable sections."""
        sections = ["Compilation Errors to Fix:"]
        
        # Track key information
        current_error = {
            "error": "",
            "location": "",
            "suggestion": ""
        }
        
        for line in error.split('\n'):
            line = line.strip()
            if 'error[' in line:
                # New error message found
                error_msg = line.split('error:')[1].strip()
                current_error["error"] = error_msg
            elif '-->' in line:
                # Location info
                location = line.split('-->')[1].strip()
                current_error["location"] = location
            elif 'help:' in line:
                # Suggestion found
                suggestion = line.split('help:')[1].strip()
                current_error["suggestion"] = suggestion
                # Add complete error message
                sections.append(f"Error: {current_error['error']}")
                sections.append(f"At: {current_error['location']}")
                sections.append(f"Fix: {current_error['suggestion']}")
                sections.append("---")
                current_error = {"error": "", "location": "", "suggestion": ""}
        
        return sections

    def _validate_output(
        self, 
        rust_code: str, 
        toml_content: str, 
        original_rust: str, 
        original_toml: str
    ) -> bool:
        """Validate model output with detailed diagnostics."""
        if not rust_code :
            logger.warning("Empty rust code returned")
            return False
        if not toml_content:
            logger.warning("Empty TOML returned")
            toml_content = original_toml

        # Compare lengths first
        logger.debug(f"Original Rust length: {len(original_rust)}")
        logger.debug(f"New Rust length: {len(rust_code)}")
        logger.debug(f"Original TOML length: {len(original_toml)}")
        logger.debug(f"New TOML length: {len(toml_content)}")
        
        # Compare content
        if rust_code == original_rust:
            logger.debug("Rust code is identical")
            logger.debug(f"First 100 chars of original: {original_rust[:100]}")
            logger.debug(f"First 100 chars of new: {rust_code[:100]}")
        else:
            logger.debug("Rust code has changes")
            
        if toml_content == original_toml:
            logger.debug("TOML is identical")
        else:
            logger.debug("TOML has changes")
            
        if rust_code == original_rust and toml_content == original_toml:
            logger.warning("Code unchanged")
            return False
            
        # Check for significant changes
        def count_differences(a: str, b: str) -> int:
            return sum(1 for x, y in zip(a.splitlines(), b.splitlines()) if x != y)
            
        rust_differences = count_differences(original_rust, rust_code)
        toml_differences = count_differences(original_toml, toml_content)
        
        logger.debug(f"Found {rust_differences} different lines in Rust")
        logger.debug(f"Found {toml_differences} different lines in TOML")

        # Normalize and compare again
        def normalize(code: str) -> str:
            return '\n'.join(line.strip() for line in code.splitlines())
            
        if normalize(rust_code) == normalize(original_rust):
            logger.warning("Code identical after normalization")
            return False

        return True
    
    async def fix(
        self,
        rust_code: str,
        toml_content: str,
        verification_result: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """Fix Rust implementation based on verification results."""
        try:
            formatted_result = self._format_verification_result(verification_result)
            logger.info(f"Formatted verification result: {formatted_result}")
            issues_summary = formatted_result["issues_summary"]
            logger.info(f"Issues summary: {issues_summary}")
            
            response = await self.chain.ainvoke({
                "rust_code": rust_code,
                "toml_content": toml_content,
                "verification_result": issues_summary,
                "analysis": analysis,
                "migration_specs": self.migration_specs,
            }, include_run_info=True)
            #logger.info(f"Fixed code: {response['fixed_code']}")
            fixed_rust, fixed_toml = self.code_extractor.extract_code_blocks(response["fixed_code"])
            
            if not self._validate_output(fixed_rust, fixed_toml, rust_code, toml_content):
                raise ValueError(f"Model returned invalid or unchanged code")
            
            if "clippy" in str(verification_result):
                logger.info("Applied fixes for Clippy issues")
            else:
                logger.info("Applied fixes for critical differences")
            
            return {
                "rust_code": fixed_rust,
                "toml_content": fixed_toml if fixed_toml else toml_content,
            }
            
        except Exception as e:
            logger.error(f"Fix application failed: {e}")
            raise