'''
This module is responsible for initializing language models and setting up callbacks.
'''
from typing import Dict, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEndpoint
from langchain.callbacks.base import BaseCallbackHandler
from ..config.settings import Settings, LLMChoice
from ..utils.logging import setup_logger
import aiohttp
import json
from .codestral_llm import CodestralLLM

logger = setup_logger()


class LLMInitializer:
    '''Initialize language models and set up callbacks.'''

    def __init__(self, settings: Settings):
        self.settings = settings

    async def _test_hf_endpoint(self, endpoint_url: str, token: str) -> Dict:
        """Test HuggingFace endpoint with detailed error reporting."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        test_payload = {
            "inputs": "Test request",
            "parameters": {
                "max_new_tokens": 10,
                "return_full_text": False
            }
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    endpoint_url,
                    headers=headers,
                    json=test_payload,
                    timeout=30
                ) as response:
                    response_text = await response.text()
                    try:
                        response_json = json.loads(response_text)
                    except json.JSONDecodeError:
                        response_json = {"raw_response": response_text}

                    status = response.status
                    headers_dict = dict(response.headers)

                    return {
                        "status": status,
                        "headers": headers_dict,
                        "body": response_json,
                        "url": str(response.url)
                    }
            except aiohttp.ClientError as e:
                return {
                    "error": str(e),
                    "type": e.__class__.__name__,
                    "url": endpoint_url
                }

    def _initialize_claude(
        self,
        claude_token: str,
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ) -> ChatAnthropic:
        """Initialize Claude model."""
        logger.info("Initializing Claude")
        config = self.settings.llm_configs[LLMChoice.CLAUDE]

        llm = ChatAnthropic(
            anthropic_api_key=claude_token,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            callbacks=callbacks
        )

        return llm

    async def _test_mistral_endpoint(self, endpoint_url: str, token: str) -> Dict:
        """Test Mistral/Codestral endpoint."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        test_payload = {
            "messages": [{"role": "user", "content": "Test request"}],
            "model": "codestral-latest",
            "max_tokens": 10
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    endpoint_url,
                    headers=headers,
                    json=test_payload,
                    timeout=30
                ) as response:
                    response_text = await response.text()
                    try:
                        response_json = json.loads(response_text)
                    except json.JSONDecodeError:
                        response_json = {"raw_response": response_text}

                    return {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "body": response_json,
                        "url": str(response.url)
                    }
            except aiohttp.ClientError as e:
                return {
                    "error": str(e),
                    "type": e.__class__.__name__,
                    "url": endpoint_url
                }

    async def initialize(
        self,
        tokens: Dict[str, str],
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ) -> Dict[str, BaseLanguageModel]:
        """Initialize LLMs based on available tokens."""
        logger.info("Initializing LLMs with callbacks")
        llms: Dict[str, BaseLanguageModel] = {}

        # Initialize Claude (primary model)
        llms[LLMChoice.CLAUDE] = self._initialize_claude(
            tokens["claude"], callbacks)

        if tokens.get("hf"):
            logger.info("Testing Huggingface endpoints...")

            for model in [LLMChoice.CODELLAMA, LLMChoice.STARCODER]:
                config = self.settings.llm_configs[model]
                endpoint_url = config.endpoint_url or f"https://api-inference.huggingface.co/models/{config.model}"

                test_result = await self._test_hf_endpoint(endpoint_url, tokens["hf"])

                if test_result.get("status") == 200:
                    logger.info(f"Endpoint test successful for {model}")
                    try:
                        llms[model] = HuggingFaceEndpoint(
                            endpoint_url=endpoint_url,
                            huggingfacehub_api_token=tokens["hf"],
                            temperature=config.temperature,
                            task="text-completion",
                            max_new_tokens=config.max_tokens or 4000,
                            callbacks=callbacks,
                        )
                        if config.model_params is not None:
                            if config.model_params.return_full_text is not None:
                                llms[model].return_full_text = config.model_params.return_full_text
                            if config.model_params.stop_sequences is not None:
                                llms[model].stop_sequences = config.model_params.stop_sequences
                            if config.model_params.top_k is not None:
                                llms[model].top_k = config.model_params.top_k
                            if config.model_params.top_p is not None:
                                llms[model].top_p = config.model_params.top_p
                            if config.model_params.repetition_penalty is not None:
                                llms[model].repetition_penalty = config.model_params.repetition_penalty
                            if config.model_params.pad_token_id is not None:
                                llms[model].pad_token_id = config.model_params.pad_token_id

                        logger.info(f"Successfully initialized {model}")
                    except Exception as e:
                        logger.error(f"Failed to initialize {model}: {e}")
                        llms[model] = llms[LLMChoice.CLAUDE]
                else:
                    logger.error(f"Endpoint test failed for {model}")
                    logger.error(f"Status: {test_result.get('status')}")
                    logger.error(
                        f"Response: {json.dumps(test_result.get('body', {}), indent=2)}")
                    logger.info(f"Falling back to Claude for {model}")
                    llms[model] = llms[LLMChoice.CLAUDE]

        if tokens.get("mistral"):
            logger.info("Testing Mistral endpoint...")
            config = self.settings.llm_configs[LLMChoice.CODESTRAL]
            endpoint_url = config.endpoint_url or "https://codestral.mistral.ai/v1/chat/completions"

            test_result = await self._test_mistral_endpoint(endpoint_url, tokens["mistral"])

            if test_result.get("status") == 200:
                logger.info("Mistral endpoint test successful")
                try:
                    llms[LLMChoice.CODESTRAL] = CodestralLLM(
                        api_key=tokens["mistral"],
                        model=config.model,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                        callbacks=callbacks
                    )
                    logger.info("Successfully initialized Mistral")
                except Exception as e:
                    logger.error(f"Failed to initialize Mistral: {e}")
                    llms[LLMChoice.CODESTRAL] = llms[LLMChoice.CLAUDE]
            else:
                logger.error("Mistral endpoint test failed")
                logger.error(f"Status: {test_result.get('status')}")
                logger.error(
                    f"Response: {json.dumps(test_result.get('body', {}), indent=2)}")
                logger.info("Falling back to Claude for Mistral")
                llms[LLMChoice.CODESTRAL] = llms[LLMChoice.CLAUDE]

        return llms
