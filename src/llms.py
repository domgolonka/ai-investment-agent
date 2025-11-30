"""
LLM configuration and initialization module.
Updated for Google Gemini 3 with Safety Settings and Rate Limiting.
"""

import logging
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from langchain_core.language_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter
from src.config import config

logger = logging.getLogger(__name__)

# Relax safety settings slightly for financial/market analysis context
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

# Global rate limiter: 10 requests per minute (conservative for free tier)
# Adjust 'requests_per_second' based on your actual tier.
# Free tier is ~15 RPM, so 0.25 rps (1 request every 4 seconds) is safe across parallel agents.
GLOBAL_RATE_LIMITER = InMemoryRateLimiter(
    requests_per_second=0.25,  
    check_every_n_seconds=0.1,
    max_bucket_size=10
)

def create_gemini_model(
    model_name: str,
    temperature: float,
    timeout: int,
    max_retries: int,
    streaming: bool = False
) -> BaseChatModel:
    """Generic factory for Gemini models."""
    
    # Note: transport='rest' is sometimes more stable than grpc for large contexts on some networks
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        # Increased timeout is handled by the caller (config.api_timeout)
        timeout=timeout,
        # Retry logic handles 500, 503, 504 automatically by default in LangChain
        max_retries=max_retries,
        safety_settings=SAFETY_SETTINGS,
        streaming=streaming,
        rate_limiter=GLOBAL_RATE_LIMITER,
        convert_system_message_to_human=False,
        # EXPLICITLY set max_output_tokens to prevent truncation
        max_output_tokens=32768, 
    )
    return llm

def create_quick_thinking_llm(
    temperature: float = 0.3,
    model: Optional[str] = None,
    timeout: int = None, # Allow override or use config default
    max_retries: int = None, # Allow override or use config default
) -> BaseChatModel:
    """Create a quick thinking LLM (Gemini 2.5 Flash)."""
    model_name = model or config.quick_think_llm
    # Use config defaults if not provided
    final_timeout = timeout if timeout is not None else config.api_timeout
    final_retries = max_retries if max_retries is not None else config.api_retry_attempts
    
    logger.info(f"Initializing Quick LLM: {model_name} (timeout={final_timeout}, retries={final_retries})")
    return create_gemini_model(model_name, temperature, final_timeout, final_retries)

def create_deep_thinking_llm(
    temperature: float = 0.1,
    model: Optional[str] = None,
    timeout: int = None, # Allow override or use config default
    max_retries: int = None, # Allow override or use config default
) -> BaseChatModel:
    """Create a deep thinking LLM (Gemini 3 Pro)."""
    model_name = model or config.deep_think_llm
    # Use config defaults if not provided
    final_timeout = timeout if timeout is not None else config.api_timeout
    final_retries = max_retries if max_retries is not None else config.api_retry_attempts
    
    logger.info(f"Initializing Deep LLM: {model_name} (timeout={final_timeout}, retries={final_retries})")
    return create_gemini_model(model_name, temperature, final_timeout, final_retries)

# Initialize default instances
quick_thinking_llm = create_quick_thinking_llm()
deep_thinking_llm = create_deep_thinking_llm()