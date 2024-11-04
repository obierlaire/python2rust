# initializers/chain_initializer.py
from typing import Dict, Any
from langchain_core.language_models import BaseLanguageModel
from ..config.settings import Settings, LLMChoice
from ..chains import AnalysisChain, GenerationChain, VerificationChain, FixChain
from ..utils.logging import setup_logger

logger = setup_logger()

class ChainInitializer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def initialize(
        self,
        llms: Dict[str, BaseLanguageModel]
    ) -> Dict[str, Any]:
        """Initialize all chains with appropriate LLMs."""
        chains = {}
        
        chains["analysis"] = self._initialize_analysis_chain(llms)
        chains["generation"] = self._initialize_generation_chain(llms)
        chains["verification"] = self._initialize_verification_chain(llms)
        chains["fix"] = self._initialize_fix_chain(llms)
        
        return chains

    def _initialize_analysis_chain(
        self,
        llms: Dict[str, BaseLanguageModel]
    ) -> AnalysisChain:
        """Initialize analysis chain."""
        return AnalysisChain(
            llm=llms[self.settings.llm_steps.analysis]
        )

    def _initialize_generation_chain(
        self,
        llms: Dict[str, BaseLanguageModel]
    ) -> GenerationChain:
        """Initialize generation chain."""
        return GenerationChain(
            llm=llms[self.settings.llm_steps.generation]
        )

    def _initialize_verification_chain(
        self,
        llms: Dict[str, BaseLanguageModel]
    ) -> VerificationChain:
        """Initialize verification chain."""
        return VerificationChain(
            llm=llms[self.settings.llm_steps.verification],
            specs_file=self.settings.specs_file
        )

    def _initialize_fix_chain(
        self,
        llms: Dict[str, BaseLanguageModel]
    ) -> FixChain:
        """Initialize fix chain."""
        return FixChain(
            llm=llms[self.settings.llm_steps.fixes],
            specs_file=self.settings.specs_file  # Add specs_file parameter
        )