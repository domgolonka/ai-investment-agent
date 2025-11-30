from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv
import logging
import sys
from typing import Optional
import structlog

# Load environment variables early
load_dotenv()

# Step 1: Configure stdlib logging to use stderr
logging.basicConfig(
    format='%(asctime)s [%(levelname)-8s] %(message)s',
    stream=sys.stderr,
    level=logging.INFO,
    force=True
)

# Step 2: Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.KeyValueRenderer(key_order=['timestamp', 'level', 'event']),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = logging.getLogger(__name__)

def _get_env_var(var: str, required: bool = True, default: Optional[str] = None) -> str:
    """Get environment variable with validation."""
    value = os.environ.get(var, default)
    if required and not value:
        logger.error(f"Missing required environment variable: {var}")
        return ""
    return value or ""

def configure_langsmith_tracing() -> None:
    """Configure LangSmith tracing."""
    if _get_env_var("LANGSMITH_API_KEY", required=False):
        os.environ["LANGSMITH_TRACING"] = os.environ.get("LANGSMITH_TRACING", "true")
        os.environ["LANGSMITH_PROJECT"] = os.environ.get("LANGSMITH_PROJECT", "Deep-Trading-System-Gemini3")
        
        # Ensure endpoint is set if not present
        if not os.environ.get("LANGSMITH_ENDPOINT"):
            os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
            
        logger.info(f"LangSmith configured for project: {os.environ.get('LANGSMITH_PROJECT')}")

def validate_environment_variables() -> None:
    """Validate required environment variables."""
    required_vars = ["GOOGLE_API_KEY", "FINNHUB_API_KEY", "TAVILY_API_KEY"]
    
    # Check for EODHD key (Optional but recommended)
    if not _get_env_var("EODHD_API_KEY", required=False):
        logger.warning("EODHD_API_KEY missing - High quality international data will be disabled.")

    missing_vars = [var for var in required_vars if not _get_env_var(var, required=True)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    configure_langsmith_tracing()
    logger.info("Environment variables validated")

@dataclass
class Config:
    """Configuration class for the Multi-Agent Trading System."""
    
    results_dir: Path = Path(os.environ.get("RESULTS_DIR", "./results"))
    data_cache_dir: Path = Path(os.environ.get("DATA_CACHE_DIR", "./data_cache"))
    
    llm_provider: str = os.environ.get("LLM_PROVIDER", "google")
    deep_think_llm: str = os.environ.get("DEEP_MODEL", "gemini-3-pro-preview")
    quick_think_llm: str = os.environ.get("QUICK_MODEL", "gemini-2.5-flash")
    
    max_debate_rounds: int = int(os.environ.get("MAX_DEBATE_ROUNDS", "2"))
    max_risk_discuss_rounds: int = int(os.environ.get("MAX_RISK_DISCUSS_ROUNDS", "1"))
    
    online_tools: bool = os.environ.get("ONLINE_TOOLS", "true").lower() == "true"
    enable_memory: bool = os.environ.get("ENABLE_MEMORY", "true").lower() == "true"
    
    max_position_size: float = float(os.environ.get("MAX_POSITION_SIZE", "0.1"))
    max_daily_trades: int = int(os.environ.get("MAX_DAILY_TRADES", "5"))
    risk_free_rate: float = float(os.environ.get("RISK_FREE_RATE", "0.03"))
    default_ticker: str = os.environ.get("DEFAULT_TICKER", "AAPL")
    
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")
    
    # UPDATED: Significantly increased timeout and retries for large context handling
    # Timeout from 120 -> 300 seconds (5 minutes) to handle massive prefill
    api_timeout: int = int(os.environ.get("API_TIMEOUT", "300"))
    # Retries from 3 -> 10 to aggressively handle 504/503 transient errors
    api_retry_attempts: int = int(os.environ.get("API_RETRY_ATTEMPTS", "10"))
    
    chroma_persist_directory: str = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
    environment: str = os.environ.get("ENVIRONMENT", "dev")
    
    # LangSmith settings
    langsmith_tracing_enabled: bool = os.environ.get("LANGSMITH_TRACING", "true").lower() == "true"

    def __post_init__(self):
        for directory in [self.results_dir, self.data_cache_dir, Path(self.chroma_persist_directory)]:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Set logging level
        log_level = getattr(logging, self.log_level)
        logging.getLogger().setLevel(log_level)
        for name in logging.root.manager.loggerDict:
            logging.getLogger(name).setLevel(log_level)

config = Config()