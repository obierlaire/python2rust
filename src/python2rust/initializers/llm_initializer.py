# llm_initializer.py
from typing import Dict, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEndpoint
from langchain.callbacks.base import BaseCallbackHandler
from ..config.settings import Settings, LLMChoice
from ..utils.logging import setup_logger

logger = setup_logger()

class LLMInitializer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def initialize(
        self,
        claude_token: str,
        hf_token: Optional[str] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ) -> Dict[str, BaseLanguageModel]:
        """Initialize LLMs based on available tokens."""
        logger.info("Initializing LLMs with callbacks")
        llms = {}
        
        # Initialize Claude
        llms[LLMChoice.CLAUDE] = self._initialize_claude(claude_token, callbacks)
        
        # Initialize HuggingFace models if token available
        if hf_token:
            llms.update(self._initialize_huggingface(hf_token, callbacks=callbacks))
        
        return llms

    def _initialize_claude(
        self,
        claude_token: str,
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ) -> ChatAnthropic:
        """Initialize Claude model."""
        logger.info("Initializing Claude with callbacks")
        config = self.settings.llm_configs[LLMChoice.CLAUDE]
        
        llm = ChatAnthropic(
            anthropic_api_key=claude_token,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            callbacks=callbacks,
            model_kwargs={
                "metadata": {
                    "track_tokens": True,
                    "request_usage": True
                }
            }
        )
        
        logger.debug(f"Claude initialized with callbacks: {callbacks}")
        return llm

    def _initialize_huggingface(
        self,
        hf_token: str,
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ) -> Dict[str, HuggingFaceEndpoint]:
        """Initialize HuggingFace models."""
        llms = {}
        for model in [LLMChoice.CODELLAMA, LLMChoice.STARCODER]:
            config = self.settings.llm_configs[model]
            llms[model] = HuggingFaceEndpoint(
                endpoint_url=f"https://api-inference.huggingface.co/models/{config.model}",
                huggingfacehub_api_token=hf_token,
                task="text-generation",
                temperature=config.temperature,
                max_new_tokens=4000,
                callbacks=callbacks,
                verbose=True
            )
        return llms