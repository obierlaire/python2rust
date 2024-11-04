import re
from typing import Tuple
from ..utils.logging import setup_logger

logger = setup_logger()

class CodeExtractor:
    """Utility for extracting code blocks from LLM responses."""
    
    def extract_code_blocks(self, text: str) -> Tuple[str, str]:
        """Extract Rust and TOML code blocks from text.
        
        Args:
            text: Text containing code blocks between ```rust and ```toml markers
            
        Returns:
            Tuple of (rust_code, toml_content)
            
        Raises:
            ValueError: If code blocks cannot be found
        """
        try:
            logger.info(f"Text for code extraction: {text}")
            # Extract Rust code
            rust_match = re.search(r"```rust\n(.*?)```", text, re.DOTALL)
            if not rust_match:
                raise ValueError("No Rust code block found in response")
            rust_code = rust_match.group(1).strip()
            
            # Extract TOML
            toml_match = re.search(r"```toml\n(.*?)```", text, re.DOTALL)
            if not toml_match:
                raise ValueError("No TOML code block found in response")
            toml_content = toml_match.group(1).strip()
            
            logger.debug("Successfully extracted code blocks")
            return rust_code, toml_content
            
        except Exception as e:
            logger.exception(f"Failed to extract code blocks: {e}")
            raise ValueError(f"Code extraction failed: {str(e)}")