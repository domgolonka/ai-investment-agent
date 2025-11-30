"""
Quiet Mode Report Generator for Multi-Agent Trading System
FIXED: Handles LangGraph list outputs to prevent 'list object has no attribute startswith' errors.
FIXED: Added deduplication to prevent stuttering output in final reports.
FIXED: Case-insensitive regex matching for decision extraction.
"""

import sys
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import re

# Local import for utility function to avoid circular dependency at module level
# We import inside the method where it is needed

class QuietModeReporter:
    """Generates clean markdown reports with minimal output."""
    
    def __init__(self, ticker: str, company_name: Optional[str] = None):
        self.ticker = ticker.upper()
        self.company_name = company_name
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _normalize_string(self, content: Any) -> str:
        """
        Safely convert content to string, handling lists from LangGraph state accumulation.
        FIXED: Deduplicates list items to prevent repetition loop artifacts.
        """
        if content is None:
            return ""
        
        if isinstance(content, list):
            # Deduplication logic
            seen = set()
            unique_items = []
            for item in content:
                if not item:
                    continue
                item_str = str(item).strip()
                # Simple hash check for duplicates
                # We check if the first 100 chars match to catch near-duplicates
                # or identical tool outputs repeated in the loop
                key = item_str[:100] 
                if key not in seen:
                    seen.add(key)
                    unique_items.append(item_str)
            
            return "\n\n".join(unique_items)
            
        return str(content)

    def extract_decision(self, final_decision: str) -> str:
        """Extract BUY/SELL/HOLD decision from final decision text."""
        
        # Normalize input first
        final_decision = self._normalize_string(final_decision)

        # Look for explicit decision markers in order of preference
        # Use UPPER CASE matching since we upper() the input string
        
        # 1. "Action:" in FINAL EXECUTION PARAMETERS (highest priority)
        action_match = re.search(
            r'\bACTION\s*:\s*\*?\*?([A-Z]+)\*?\*?',
            final_decision.upper()
        )
        if action_match:
            decision = action_match.group(1)
            if decision in ['BUY', 'SELL', 'HOLD']:
                return decision

        # 2. "FINAL DECISION:"
        final_decision_match = re.search(
            r'\bFINAL\s+DECISION\s*:\s*\*?\*?([A-Z]+)\*?\*?',
            final_decision.upper()
        )
        if final_decision_match:
            decision = final_decision_match.group(1)
            if decision in ['BUY', 'SELL', 'HOLD']:
                return decision

        # 3. "Decision:" fallback
        decision_match = re.search(
            r'\bDECISION\s*:\s*\*?\*?([A-Z]+)\*?\*?',
            final_decision.upper()
        )
        if decision_match:
            decision = decision_match.group(1)
            if decision in ['BUY', 'SELL', 'HOLD']:
                return decision
        
        # 4. Generic keyword search (risky, but better than nothing)
        generic_match = re.search(r'\b(BUY|SELL|HOLD)\b', final_decision.upper())
        if generic_match:
            decision = generic_match.group(1)
            return decision

        return "HOLD"  # Default to HOLD if completely unclear
    
    def generate_report(self, result: Dict) -> str:
        """Generate markdown report from analysis results."""
        
        # Normalize the final decision to ensure it's a string
        final_decision_raw = self._normalize_string(result.get('final_trade_decision', ''))
        decision = self.extract_decision(final_decision_raw)
        
        # Build title
        if self.company_name:
            title = f"# {self.ticker} ({self.company_name}): {decision}"
        else:
            title = f"# {self.ticker}: {decision}"
        
        # Build report sections
        report_parts = [
            title,
            f"\n**Analysis Date:** {self.timestamp}\n",
            "---\n"
        ]
        
        # Executive Summary
        if final_decision_raw:
            report_parts.append("## Executive Summary\n")
            cleaned = self._clean_text(final_decision_raw)
            report_parts.append(f"{cleaned}\n\n---\n")
        
        # Helper function to add sections safely
        def add_section(key, title):
            raw_content = result.get(key, '')
            content = self._normalize_string(raw_content)
            
            if content and not content.startswith('Error'):
                report_parts.append(f"## {title}\n")
                report_parts.append(f"{self._clean_text(content)}\n\n")

        add_section('market_report', 'Technical Analysis')
        
        # Clean fundamentals: keep only final self-corrected DATA_BLOCK
        # Import inside function to prevent circular dependency with utils.py
        fund_report = result.get('fundamentals_report', '')
        if fund_report:
            try:
                from src.utils import clean_duplicate_data_blocks
                fund_report = self._normalize_string(fund_report)
                fund_report = clean_duplicate_data_blocks(fund_report)
                result['fundamentals_report'] = fund_report
            except ImportError:
                pass # Fallback if utils not available

        add_section('fundamentals_report', 'Fundamental Analysis')
        add_section('sentiment_report', 'Market Sentiment')
        add_section('news_report', 'News & Catalysts')
        add_section('investment_plan', 'Investment Recommendation')
        add_section('trader_investment_plan', 'Trading Strategy')
        
        # Risk Assessment (handle dictionary nesting)
        risk_state = result.get('risk_debate_state', {})
        # Risk state itself might be a list if not merged properly, check that too
        if isinstance(risk_state, list) and risk_state:
            risk_state = risk_state[-1] # Take last state
            
        if isinstance(risk_state, dict) and risk_state.get('history'):
            history = self._normalize_string(risk_state.get('history', ''))
            report_parts.append("## Risk Assessment\n")
            report_parts.append(f"{self._clean_text(history)}\n\n")
        
        # Footer
        report_parts.append("---\n")
        report_parts.append(
            f"*Generated by Multi-Agent Trading System - {self.timestamp}*\n"
        )
        
        return "".join(report_parts)
    
    def _clean_text(self, text: str) -> str:
        """Clean up text for markdown output."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        # Remove agent prefixes if present
        text = re.sub(
            r'^(Bull Analyst:|Bear Analyst:|Risky Analyst:|Safe Analyst:|'
            r'Neutral Analyst:|Trader:|Portfolio Manager:)\s*',
            '',
            text,
            flags=re.MULTILINE
        )
        
        return text


def suppress_logging():
    """
    Suppress all logging output except critical errors.
    Ensures logging goes to stderr so it doesn't pollute stdout reports.
    """
    import logging
    import warnings
    
    # Configure root logger to only show CRITICAL errors, directed to stderr
    logging.basicConfig(
        level=logging.CRITICAL,
        format='%(message)s',
        stream=sys.stderr,
        force=True
    )
    
    # Silence all existing loggers
    for logger_name in list(logging.root.manager.loggerDict.keys()):
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        logging.getLogger(logger_name).propagate = False
    
    # Specifically silence noisy libraries
    for logger_name in ['httpx', 'openai', 'httpcore', '__main__', 'src.config', 
                        'src.llms', 'src.graph', 'src.agents', 'src.toolkit',
                        'src.memory', 'langchain', 'langgraph']:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    
    # Configure structlog to use null processors
    import structlog
    
    def null_processor(logger, method_name, event_dict):
        return ""
    
    structlog.configure(
        processors=[
            null_processor,
            structlog.processors.KeyValueRenderer(key_order=[], drop_missing=True),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    warnings.filterwarnings('ignore')