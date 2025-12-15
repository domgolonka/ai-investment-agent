"""
Custom exception hierarchy for the AI Investment Agent.

This module provides a structured exception hierarchy to replace bare
except clauses throughout the codebase, enabling:
- Specific error handling and recovery strategies
- Better debugging with contextual information
- Selective retry logic based on exception type
- Clean separation between recoverable and fatal errors

Exception Hierarchy:
    InvestmentAgentError (base)
    ├── DataError
    │   ├── DataFetchError
    │   ├── DataValidationError
    │   ├── DataParsingError
    │   └── DataSourceUnavailableError
    ├── TickerError
    │   ├── TickerValidationError
    │   ├── TickerNotFoundError
    │   └── TickerUnsupportedError
    ├── MemoryError
    │   ├── MemoryInitError
    │   ├── MemoryQueryError
    │   └── MemoryStorageError
    ├── LLMError
    │   ├── RateLimitError
    │   ├── ModelUnavailableError
    │   ├── ContextLengthError
    │   └── ResponseParsingError
    ├── AnalysisError
    │   ├── RedFlagDetectionError
    │   ├── SentimentAnalysisError
    │   └── FundamentalsAnalysisError
    └── ConfigurationError
"""

from typing import Any, Optional, Dict


class InvestmentAgentError(Exception):
    """
    Base exception for all AI Investment Agent errors.

    All custom exceptions in this codebase should inherit from this class
    to enable catching all agent-specific errors with a single except clause
    when needed, while still allowing specific error handling.

    Attributes:
        message: Human-readable error description
        details: Additional context (ticker, source, etc.)
        cause: Original exception if this wraps another error
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the exception message with details."""
        msg = self.message
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            msg = f"{msg} [{detail_str}]"
        if self.cause:
            msg = f"{msg} (caused by: {type(self.cause).__name__}: {self.cause})"
        return msg


# =============================================================================
# Data-Related Exceptions
# =============================================================================

class DataError(InvestmentAgentError):
    """Base exception for all data-related errors."""
    pass


class DataFetchError(DataError):
    """
    Raised when data cannot be fetched from an external source.

    Examples:
        - API request timeout
        - Network connectivity issues
        - Invalid API response
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        ticker: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if source:
            details["source"] = source
        if ticker:
            details["ticker"] = ticker
        super().__init__(message, details=details, **kwargs)


class DataValidationError(DataError):
    """
    Raised when fetched data fails validation checks.

    Examples:
        - Missing required fields
        - Values outside expected ranges
        - Inconsistent data (e.g., negative prices)
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        if expected:
            details["expected"] = expected
        super().__init__(message, details=details, **kwargs)


class DataParsingError(DataError):
    """
    Raised when data cannot be parsed into expected format.

    Examples:
        - JSON decode errors
        - Unexpected data structure
        - Type conversion failures
    """

    def __init__(
        self,
        message: str,
        raw_data: Optional[str] = None,
        expected_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if raw_data:
            # Truncate raw data to prevent huge error messages
            details["raw_data"] = raw_data[:200] + "..." if len(raw_data) > 200 else raw_data
        if expected_type:
            details["expected_type"] = expected_type
        super().__init__(message, details=details, **kwargs)


class DataSourceUnavailableError(DataError):
    """
    Raised when a data source is completely unavailable.

    Examples:
        - API key invalid or expired
        - Service down for maintenance
        - Source deprecated
    """

    def __init__(
        self,
        message: str,
        source: str,
        reason: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["source"] = source
        if reason:
            details["reason"] = reason
        super().__init__(message, details=details, **kwargs)


# =============================================================================
# Ticker-Related Exceptions
# =============================================================================

class TickerError(InvestmentAgentError):
    """Base exception for all ticker-related errors."""
    pass


class TickerValidationError(TickerError):
    """
    Raised when a ticker symbol fails validation.

    Examples:
        - Invalid characters in ticker
        - Ticker too long
        - Missing exchange suffix for international stocks
    """

    def __init__(
        self,
        message: str,
        ticker: str,
        reason: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["ticker"] = ticker
        if reason:
            details["reason"] = reason
        super().__init__(message, details=details, **kwargs)


class TickerNotFoundError(TickerError):
    """
    Raised when a ticker symbol cannot be found in any data source.

    Examples:
        - Delisted stock
        - Typo in ticker symbol
        - Wrong exchange suffix
    """

    def __init__(
        self,
        message: str,
        ticker: str,
        sources_checked: Optional[list] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["ticker"] = ticker
        if sources_checked:
            details["sources_checked"] = sources_checked
        super().__init__(message, details=details, **kwargs)


class TickerUnsupportedError(TickerError):
    """
    Raised when a ticker is valid but not supported for analysis.

    Examples:
        - ADR-only restriction when primary listing needed
        - Unsupported exchange
        - Unsupported asset type (e.g., ETFs, bonds)
    """

    def __init__(
        self,
        message: str,
        ticker: str,
        reason: str,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["ticker"] = ticker
        details["reason"] = reason
        super().__init__(message, details=details, **kwargs)


# =============================================================================
# Memory-Related Exceptions
# =============================================================================

class MemorySystemError(InvestmentAgentError):
    """Base exception for all memory system errors."""
    pass


class MemoryInitError(MemorySystemError):
    """
    Raised when the memory system fails to initialize.

    Examples:
        - ChromaDB connection failure
        - Embedding model unavailable
        - Corrupted database file
    """

    def __init__(
        self,
        message: str,
        component: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if component:
            details["component"] = component
        super().__init__(message, details=details, **kwargs)


class MemoryQueryError(MemorySystemError):
    """
    Raised when a memory query fails.

    Examples:
        - Invalid query parameters
        - Collection not found
        - Embedding generation failure
    """

    def __init__(
        self,
        message: str,
        collection: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if collection:
            details["collection"] = collection
        if query:
            # Truncate query to prevent huge error messages
            details["query"] = query[:100] + "..." if len(query) > 100 else query
        super().__init__(message, details=details, **kwargs)


class MemoryStorageError(MemorySystemError):
    """
    Raised when memory storage operations fail.

    Examples:
        - Disk space exhausted
        - Write permission denied
        - Database locked
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        collection: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        if collection:
            details["collection"] = collection
        super().__init__(message, details=details, **kwargs)


# =============================================================================
# LLM-Related Exceptions
# =============================================================================

class LLMError(InvestmentAgentError):
    """Base exception for all LLM-related errors."""
    pass


class RateLimitError(LLMError):
    """
    Raised when LLM rate limits are exceeded.

    Examples:
        - Gemini free tier RPM limit (15/min)
        - OpenAI token limit exceeded
        - Too many concurrent requests
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if provider:
            details["provider"] = provider
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, details=details, **kwargs)


class ModelUnavailableError(LLMError):
    """
    Raised when an LLM model is unavailable.

    Examples:
        - Model deprecated or renamed
        - API key lacks access to model
        - Service outage
    """

    def __init__(
        self,
        message: str,
        model: str,
        provider: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        details["model"] = model
        if provider:
            details["provider"] = provider
        super().__init__(message, details=details, **kwargs)


class ContextLengthError(LLMError):
    """
    Raised when input exceeds model's context length.

    Examples:
        - Prompt too long
        - Too much retrieved context
        - Large report generation
    """

    def __init__(
        self,
        message: str,
        token_count: Optional[int] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if token_count:
            details["token_count"] = token_count
        if max_tokens:
            details["max_tokens"] = max_tokens
        super().__init__(message, details=details, **kwargs)


class ResponseParsingError(LLMError):
    """
    Raised when LLM response cannot be parsed.

    Examples:
        - Expected JSON but got plain text
        - Missing required fields in structured output
        - Malformed tool call response
    """

    def __init__(
        self,
        message: str,
        expected_format: Optional[str] = None,
        raw_response: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if expected_format:
            details["expected_format"] = expected_format
        if raw_response:
            # Truncate response to prevent huge error messages
            details["raw_response"] = raw_response[:200] + "..." if len(raw_response) > 200 else raw_response
        super().__init__(message, details=details, **kwargs)


# =============================================================================
# Analysis-Related Exceptions
# =============================================================================

class AnalysisError(InvestmentAgentError):
    """Base exception for all analysis-related errors."""
    pass


class RedFlagDetectionError(AnalysisError):
    """
    Raised when red flag detection fails.

    Examples:
        - Cannot parse financial data for validation
        - Missing required metrics for red flag checks
    """

    def __init__(
        self,
        message: str,
        ticker: Optional[str] = None,
        check: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if ticker:
            details["ticker"] = ticker
        if check:
            details["check"] = check
        super().__init__(message, details=details, **kwargs)


class SentimentAnalysisError(AnalysisError):
    """
    Raised when sentiment analysis fails.

    Examples:
        - StockTwits API unavailable
        - No sentiment data found
        - Language detection failure
    """

    def __init__(
        self,
        message: str,
        ticker: Optional[str] = None,
        source: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if ticker:
            details["ticker"] = ticker
        if source:
            details["source"] = source
        super().__init__(message, details=details, **kwargs)


class FundamentalsAnalysisError(AnalysisError):
    """
    Raised when fundamentals analysis fails.

    Examples:
        - Insufficient data coverage
        - Contradictory data from sources
        - Missing critical metrics
    """

    def __init__(
        self,
        message: str,
        ticker: Optional[str] = None,
        missing_metrics: Optional[list] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if ticker:
            details["ticker"] = ticker
        if missing_metrics:
            details["missing_metrics"] = missing_metrics
        super().__init__(message, details=details, **kwargs)


# =============================================================================
# Configuration Exceptions
# =============================================================================

class ConfigurationError(InvestmentAgentError):
    """
    Raised when configuration is invalid or missing.

    Examples:
        - Missing required API key
        - Invalid model name
        - Conflicting configuration options
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        if expected:
            details["expected"] = expected
        super().__init__(message, details=details, **kwargs)


# =============================================================================
# Utility Functions
# =============================================================================

def is_retryable(error: Exception) -> bool:
    """
    Determine if an error is likely transient and worth retrying.

    Args:
        error: The exception to check

    Returns:
        True if the error is likely transient, False otherwise
    """
    retryable_types = (
        RateLimitError,
        DataFetchError,
        DataSourceUnavailableError,
        MemoryQueryError,
    )
    return isinstance(error, retryable_types)


def get_retry_delay(error: Exception, attempt: int = 1) -> int:
    """
    Get suggested retry delay in seconds based on error type.

    Args:
        error: The exception to get delay for
        attempt: Current retry attempt number (1-based)

    Returns:
        Suggested delay in seconds
    """
    base_delay = 5

    if isinstance(error, RateLimitError):
        # Use retry_after if provided, otherwise exponential backoff
        if error.details.get("retry_after_seconds"):
            return error.details["retry_after_seconds"]
        base_delay = 60  # Default to 60s for rate limits
    elif isinstance(error, DataFetchError):
        base_delay = 10
    elif isinstance(error, DataSourceUnavailableError):
        base_delay = 30

    # Exponential backoff with cap at 5 minutes
    return min(base_delay * (2 ** (attempt - 1)), 300)
