import json
from typing import Any, Dict
from langchain_core.language_models import BaseLanguageModel
from langchain.chains import LLMChain
from ..prompts.analysis_prompts import SYSTEM_MESSAGE, ANALYSIS_PROMPT
from langchain.prompts import ChatPromptTemplate

from ..utils.logging import setup_logger

logger = setup_logger()

class AnalysisChain:
    """Chain for analyzing Python code."""
    
    def __init__(self, llm: BaseLanguageModel):
         # Create chat prompt template with system and human messages
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_MESSAGE),
            ("human", ANALYSIS_PROMPT.template)
        ])
        
        self.chain = LLMChain(
            llm=llm,
            prompt=chat_prompt,
            output_key="analysis"
        )
    
    async def analyze(self, python_code: str) -> Dict[str, Any]:
        """Run analysis on Python code."""
        try:
            # Get analysis from LLM
            result = await self.chain.ainvoke({"python_code": python_code})
            
            # Parse analysis
            analysis = result["analysis"]
            if isinstance(analysis, str):
                analysis = json.loads(analysis)
            
            # Log important insights
            logger.info("Analysis completed. Program overview:")
            if "program_purpose" in analysis:
                logger.info(f"Main functionality: {analysis['program_purpose'].get('main_functionality', 'Not specified')}")
                logger.info(f"Key features: {analysis['program_purpose'].get('key_features', [])}")
            
            if "rust_requirements" in analysis:
                logger.info("Recommended Rust equivalents:")
                for py_lib, rust_info in analysis['rust_requirements'].get('equivalent_libraries', {}).items():
                    logger.info(f"- {py_lib} → {rust_info}")
            
            if "compatibility_needs" in analysis:
                logger.info("Critical aspects to preserve:")
                for must_match in analysis['compatibility_needs'].get('must_match', []):
                    logger.info(f"- {must_match}")
            
            return {"analysis": analysis}
            
        except Exception as e:
            logger.exception(f"Analysis failed: {e}")
            return {"error": str(e)}
            raise
