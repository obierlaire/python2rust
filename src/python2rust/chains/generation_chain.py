from typing import Dict, Any
from langchain_core.language_models import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

from ..prompts.generation_prompts import SYSTEM_MESSAGE, GENERATION_PROMPT
from ..utils.logging import setup_logger
from ..utils.code_extractor import CodeExtractor

logger = setup_logger()

class GenerationChain:
    """Chain for initial Python to Rust code conversion."""
    
    def __init__(self, llm: BaseLanguageModel):
         # Create chat prompt template with system and human messages
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_MESSAGE),
            ("human", GENERATION_PROMPT.template)
        ])
        
        self.chain = LLMChain(
            llm=llm,
            prompt=chat_prompt,
            output_key="generated_code"
        )
        self.code_extractor = CodeExtractor()
    
    async def generate(self, python_code: str, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate initial Rust code from Python code.
        
        Args:
            python_code: Source Python code to convert
            analysis: Analysis results from the analysis chain
            
        Returns:
            Dict containing generated rust_code and toml_content
        """
        try:
            response = await self.chain.ainvoke({
                "python_code": python_code,
                "analysis": analysis
            })
            result = response["generated_code"]
            logger.info("Generated initial Rust code")

            rust_code, toml_content = self.code_extractor.extract_code_blocks(result)
            
            logger.info("Initial code generation completed")
            return {
                "rust_code": rust_code,
                "toml_content": toml_content
            }
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise