import json
from typing import Any, Dict, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain.chains import LLMChain
from ..prompts.analysis_prompts import SYSTEM_MESSAGE, ANALYSIS_PROMPT
from langchain.prompts import ChatPromptTemplate
from langchain.callbacks.base import BaseCallbackHandler
from ..utils.logging import setup_logger

logger = setup_logger()

class AnalysisChain:
    """Chain for analyzing Python code."""
    
    def __init__(self, llm: BaseLanguageModel, callbacks: Optional[List[BaseCallbackHandler]] = None):
        # Create chat prompt template with system and human messages
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_MESSAGE),
            ("human", ANALYSIS_PROMPT.template)
        ])
        
        self.chain = LLMChain(
            llm=llm,
            prompt=chat_prompt,
            output_key="analysis",
            callbacks=callbacks,
            verbose=True 
        )
    
    async def analyze(self, python_code: str) -> Dict[str, Any]:
        """Run analysis on Python code."""
        try:
            # Get analysis from LLM
            result = await self.chain.ainvoke({"python_code": python_code}, include_run_info=True)
            
            # Parse analysis
            analysis = result["analysis"]
            if isinstance(analysis, str):
                analysis = json.loads(analysis)
            
            # Log important insights
            logger.info("Analysis completed. Key features:")
            if "program_purpose" in analysis:
                logger.info(f"Main functionality: {analysis['program_purpose'].get('main_functionality', 'Not specified')}")
            
            return {"analysis": analysis}
            
        except Exception as e:
            logger.exception(f"Analysis failed: {e}")
            return {"error": str(e)}