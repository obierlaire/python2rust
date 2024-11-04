from typing import Dict, Optional
from langchain_core.language_models import BaseLanguageModel
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEndpoint
from ..config.settings import Settings, LLMChoice
from ..utils.logging import setup_logger

logger = setup_logger()

class LLMInitializer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def initialize(
        self,
        claude_token: str,
        hf_token: Optional[str] = None
    ) -> Dict[str, BaseLanguageModel]:
        """Initialize LLMs based on available tokens."""
        llms = {}
        
        # Initialize Claude
        llms[LLMChoice.CLAUDE] = self._initialize_claude(claude_token)
        
        # Initialize HuggingFace models if token available
        if hf_token:
            llms.update(self._initialize_huggingface(hf_token))
        
        return llms

    def _initialize_claude(self, claude_token: str) -> ChatAnthropic:
        """Initialize Claude model."""
        return ChatAnthropic(
            anthropic_api_key=claude_token,
            model=self.settings.llm_configs[LLMChoice.CLAUDE].model,
            temperature=self.settings.llm_configs[LLMChoice.CLAUDE].temperature,
            max_tokens=self.settings.llm_configs[LLMChoice.CLAUDE].max_tokens
        )

    def _initialize_huggingface(
        self,
        hf_token: str
    ) -> Dict[str, HuggingFaceEndpoint]:
        """Initialize HuggingFace models."""
        llms = {}
        for model in [LLMChoice.CODELLAMA, LLMChoice.STARCODER]:
            llms[model] = HuggingFaceEndpoint(
                endpoint_url=f"https://api-inference.huggingface.co/models/{self.settings.llm_configs[model].model}",
                huggingfacehub_api_token=hf_token,
                task="text-generation",
                temperature=self.settings.llm_configs[model].temperature,
                max_new_tokens=4000,
                top_p=0.95
            )
        return llms