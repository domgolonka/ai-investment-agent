"""
Tests for report_generator.py
Covers normalization, decision extraction, and report generation.
"""

import pytest
from src.report_generator import QuietModeReporter, suppress_logging
from datetime import datetime


class TestNormalizeString:
    """Test _normalize_string() edge cases."""
    
    def test_normalize_none(self):
        """Test None input returns empty string."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string(None)
        assert result == ""
    
    def test_normalize_string_passthrough(self):
        """Test regular string passes through."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string("Hello World")
        assert result == "Hello World"
    
    def test_normalize_list_deduplication_logic(self):
        """
        REGRESSION TEST: Verify duplicate report sections are removed.
        This fixes the 'stuttering' output bug where analysis repeats.
        """
        reporter = QuietModeReporter("AAPL")
        input_list = [
            "Market analysis part 1",
            "Market analysis part 1", # Duplicate
            "Market analysis part 2"
        ]
        result = reporter._normalize_string(input_list)
        
        # Should only appear once
        assert result.count("Market analysis part 1") == 1
        assert "Market analysis part 2" in result
        # Should be joined by newlines
        assert result == "Market analysis part 1\n\nMarket analysis part 2"

    def test_normalize_empty_list(self):
        """Test empty list returns empty string."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string([])
        assert result == ""
    
    def test_normalize_list_single_item(self):
        """Test list with single item."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string(["Test"])
        assert result == "Test"
    
    def test_normalize_list_multiple_items(self):
        """Test list joins with double newlines."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string(["First", "Second", "Third"])
        assert result == "First\n\nSecond\n\nThird"
    
    def test_normalize_list_with_none(self):
        """Test list filters out None values."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string(["First", None, "Third", None])
        assert result == "First\n\nThird"
    
    def test_normalize_list_with_empty_strings(self):
        """Test list filters out empty strings."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string(["First", "", "Third"])
        assert result == "First\n\nThird"
    
    def test_normalize_integer(self):
        """Test integer converts to string."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string(42)
        assert result == "42"
    
    def test_normalize_float(self):
        """Test float converts to string."""
        reporter = QuietModeReporter("AAPL")
        result = reporter._normalize_string(3.14)
        assert result == "3.14"
    
    def test_normalize_nested_list(self):
        """Test nested list flattening."""
        reporter = QuietModeReporter("AAPL")
        # Lists within lists should be converted to strings
        result = reporter._normalize_string([["Nested", "List"], "Item"])
        assert "Nested" in result or "['Nested', 'List']" in result


class TestExtractDecision:
    """Test extract_decision() with various input formats."""
    
    def test_extract_action_field(self):
        """Test extraction from Action: field."""
        reporter = QuietModeReporter("AAPL")
        text = "### FINAL EXECUTION PARAMETERS\nAction: BUY\nPosition: 5%"
        assert reporter.extract_decision(text) == "BUY"
    
    def test_extract_final_decision_field(self):
        """Test extraction from FINAL DECISION: field."""
        reporter = QuietModeReporter("AAPL")
        text = "### FINAL DECISION: SELL\nRationale: Too risky"
        assert reporter.extract_decision(text) == "SELL"
    
    def test_extract_decision_field(self):
        """Test extraction from Decision: field."""
        reporter = QuietModeReporter("AAPL")
        text = "Decision: HOLD\nWaiting for clarity"
        assert reporter.extract_decision(text) == "HOLD"
    
    def test_extract_generic_keyword(self):
        """Test generic keyword extraction as fallback."""
        reporter = QuietModeReporter("AAPL")
        text = "I recommend to BUY this stock"
        assert reporter.extract_decision(text) == "BUY"
    
    def test_extract_bold_markdown(self):
        """Test extraction with markdown bold."""
        reporter = QuietModeReporter("AAPL")
        text = "Action: **SELL**"
        assert reporter.extract_decision(text) == "SELL"
    
    def test_extract_lowercase(self):
        """Test extraction converts to uppercase."""
        reporter = QuietModeReporter("AAPL")
        text = "Action: buy"
        assert reporter.extract_decision(text) == "BUY"
    
    def test_extract_with_extra_whitespace(self):
        """Test extraction handles extra whitespace."""
        reporter = QuietModeReporter("AAPL")
        text = "Action:    HOLD   "
        assert reporter.extract_decision(text) == "HOLD"
    
    def test_extract_multiple_decisions_priority(self):
        """Test priority order when multiple decisions present."""
        reporter = QuietModeReporter("AAPL")
        # Action: should take priority over FINAL DECISION:
        text = "FINAL DECISION: SELL\n\nAction: BUY"
        assert reporter.extract_decision(text) == "BUY"
    
    def test_extract_default_hold(self):
        """Test defaults to HOLD when no decision found."""
        reporter = QuietModeReporter("AAPL")
        text = "No clear decision in this text"
        assert reporter.extract_decision(text) == "HOLD"
    
    def test_extract_invalid_decision(self):
        """Test invalid decision word ignored."""
        reporter = QuietModeReporter("AAPL")
        text = "Action: MAYBE"
        assert reporter.extract_decision(text) == "HOLD"
    
    def test_extract_from_list(self):
        """Test extraction when input is a list (LangGraph accumulation)."""
        reporter = QuietModeReporter("AAPL")
        text_list = ["Some preamble", "Action: SELL"]
        assert reporter.extract_decision(text_list) == "SELL"
    
    def test_extract_none_input(self):
        """Test extraction from None input."""
        reporter = QuietModeReporter("AAPL")
        assert reporter.extract_decision(None) == "HOLD"


class TestCleanText:
    """Test _clean_text() cleanup functions."""
    
    def test_clean_excessive_newlines(self):
        """Test excessive newlines reduced to double."""
        reporter = QuietModeReporter("AAPL")
        text = "Line 1\n\n\n\n\nLine 2"
        result = reporter._clean_text(text)
        assert "\n\n\n" not in result
        assert "Line 1\n\nLine 2" in result
    
    def test_clean_agent_prefixes(self):
        """Test agent prefixes removed."""
        reporter = QuietModeReporter("AAPL")
        text = "Bull Analyst: This is great\nBear Analyst: This is bad"
        result = reporter._clean_text(text)
        assert "Bull Analyst:" not in result
        assert "Bear Analyst:" not in result
        assert "This is great" in result
    
    def test_clean_all_agent_types(self):
        """Test all agent types removed."""
        reporter = QuietModeReporter("AAPL")
        agents = [
            "Bull Analyst: Buy",
            "Bear Analyst: Sell",
            "Risky Analyst: High risk",
            "Safe Analyst: Low risk",
            "Neutral Analyst: Moderate",
            "Trader: Entry at $100",
            "Portfolio Manager: Approve"
        ]
        text = "\n".join(agents)
        result = reporter._clean_text(text)
        
        for agent in ["Bull", "Bear", "Risky", "Safe", "Neutral", "Trader", "Portfolio"]:
            assert f"{agent} Analyst:" not in result
    
    def test_clean_strips_whitespace(self):
        """Test leading/trailing whitespace removed."""
        reporter = QuietModeReporter("AAPL")
        text = "   \n\n  Content  \n\n  "
        result = reporter._clean_text(text)
        assert result == "Content\n"
    
    def test_clean_preserves_content(self):
        """Test content is preserved."""
        reporter = QuietModeReporter("AAPL")
        text = "This is important content\n"
        result = reporter._clean_text(text)
        assert result == text


class TestGenerateReport:
    """Test generate_report() main function."""
    
    def test_generate_basic_report(self):
        """Test basic report generation."""
        reporter = QuietModeReporter("AAPL", "Apple Inc.")
        result_dict = {
            'final_trade_decision': 'Action: BUY',
            'market_report': 'RSI: 45',
            'fundamentals_report': 'P/E: 25'
        }
        
        report = reporter.generate_report(result_dict)
        
        assert "AAPL" in report
        assert "Apple Inc." in report
        assert "BUY" in report
        assert "Technical Analysis" in report
        assert "Fundamental Analysis" in report
    
    def test_generate_report_no_company_name(self):
        """Test report without company name."""
        reporter = QuietModeReporter("GOOGL")
        result_dict = {'final_trade_decision': 'Action: SELL'}
        
        report = reporter.generate_report(result_dict)
        
        assert "GOOGL" in report
        assert "SELL" in report
    
    def test_generate_report_missing_sections(self):
        """Test report with missing optional sections."""
        reporter = QuietModeReporter("MSFT")
        result_dict = {'final_trade_decision': 'Action: HOLD'}
        
        report = reporter.generate_report(result_dict)
        
        # Should have basic structure even without sections
        assert "MSFT" in report
        assert "HOLD" in report
        assert "---" in report
    
    def test_generate_report_error_sections(self):
        """Test sections starting with 'Error' are excluded."""
        reporter = QuietModeReporter("TSLA")
        result_dict = {
            'final_trade_decision': 'Action: BUY',
            'market_report': 'Error: Could not fetch data',
            'fundamentals_report': 'P/E: 100'
        }
        
        report = reporter.generate_report(result_dict)
        
        # Error section should not appear
        assert "Technical Analysis" not in report
        # But fundamentals should
        assert "Fundamental Analysis" in report
    
    def test_generate_report_list_accumulation(self):
        """Test handling of LangGraph list accumulation."""
        reporter = QuietModeReporter("NVDA")
        result_dict = {
            'final_trade_decision': ['Preamble', 'Action: BUY'],
            'market_report': ['RSI: 50', 'MACD: Bullish']
        }
        
        report = reporter.generate_report(result_dict)
        
        assert "NVDA" in report
        assert "BUY" in report
        # List should be joined
        assert "RSI: 50" in report
        assert "MACD: Bullish" in report
    
    def test_generate_report_risk_state_dict(self):
        """Test risk assessment from nested dict."""
        reporter = QuietModeReporter("AMD")
        result_dict = {
            'final_trade_decision': 'Action: HOLD',
            'risk_debate_state': {
                'history': 'Risky: High risk\nSafe: Low risk'
            }
        }
        
        report = reporter.generate_report(result_dict)
        
        assert "Risk Assessment" in report
        assert "High risk" in report
    
    def test_generate_report_risk_state_list(self):
        """Test risk assessment from list (takes last item)."""
        reporter = QuietModeReporter("INTC")
        result_dict = {
            'final_trade_decision': 'Action: BUY',
            'risk_debate_state': [
                {'history': 'Old debate'},
                {'history': 'Latest debate: This is current'}
            ]
        }
        
        report = reporter.generate_report(result_dict)
        
        assert "Risk Assessment" in report
        assert "Latest debate" in report
        assert "Old debate" not in report
    
    def test_generate_report_timestamp_format(self):
        """Test timestamp is properly formatted."""
        reporter = QuietModeReporter("IBM")
        result_dict = {'final_trade_decision': 'Action: HOLD'}
        
        report = reporter.generate_report(result_dict)
        
        # Should have timestamp in YYYY-MM-DD HH:MM:SS format
        assert "Analysis Date:" in report
        assert reporter.timestamp in report
    
    def test_generate_report_all_sections(self):
        """Test report with all possible sections."""
        reporter = QuietModeReporter("META", "Meta Platforms")
        result_dict = {
            'final_trade_decision': 'Action: BUY',
            'market_report': 'Bullish trend',
            'fundamentals_report': 'Strong financials',
            'sentiment_report': 'Positive sentiment',
            'news_report': 'New product launch',
            'investment_plan': 'Recommend BUY',
            'trader_investment_plan': 'Entry: $300',
            'risk_debate_state': {'history': 'Moderate risk'}
        }
        
        report = reporter.generate_report(result_dict)
        
        # Check all sections present
        assert "Technical Analysis" in report
        assert "Fundamental Analysis" in report
        assert "Market Sentiment" in report
        assert "News & Catalysts" in report
        assert "Investment Recommendation" in report
        assert "Trading Strategy" in report
        assert "Risk Assessment" in report


class TestSuppressLogging:
    """Test suppress_logging() function."""
    
    def test_suppress_logging_no_errors(self):
        """Test suppress_logging runs without errors."""
        # Should not raise any exceptions
        suppress_logging()
    
    def test_logging_level_critical(self):
        """Test logging is set to CRITICAL after suppression."""
        import logging
        suppress_logging()
        
        # Root logger should be at CRITICAL
        assert logging.root.level == logging.CRITICAL


class TestEdgeCases:
    """Test edge cases and stress scenarios."""
    
    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        reporter = QuietModeReporter("NFLX")
        result_dict = {
            'final_trade_decision': 'Action: BUY 🚀',
            'market_report': 'Stock is trending 📈'
        }
        
        report = reporter.generate_report(result_dict)
        
        # Should handle unicode without crashing
        assert "NFLX" in report
    
    def test_very_long_report(self):
        """Test handling of very long report sections."""
        reporter = QuietModeReporter("AMZN")
        long_text = "X" * 100000  # 100k characters
        result_dict = {
            'final_trade_decision': 'Action: HOLD',
            'market_report': long_text
        }
        
        report = reporter.generate_report(result_dict)
        
        # Should not crash, should include long text
        assert len(report) > 100000
    
    def test_special_markdown_characters(self):
        """Test handling of special markdown characters."""
        reporter = QuietModeReporter("DIS")
        result_dict = {
            'final_trade_decision': 'Action: BUY',
            'market_report': '# Header\n**Bold** *Italic* `Code`'
        }
        
        report = reporter.generate_report(result_dict)
        
        # Should preserve markdown
        assert "**Bold**" in report or "Bold" in report
    
    def test_empty_result_dict(self):
        """Test handling of completely empty result dict."""
        reporter = QuietModeReporter("ORCL")
        result_dict = {}
        
        report = reporter.generate_report(result_dict)
        
        # Should still generate basic structure
        assert "ORCL" in report
        assert "HOLD" in report  # Default decision
    
    def test_malformed_decision_format(self):
        """Test various malformed decision formats."""
        reporter = QuietModeReporter("CSCO")
        
        test_cases = [
            "Action:BUY",  # No space
            "Action : BUY",  # Extra space
            "ACTION: buy",  # All caps label, lowercase value
            "action: BUY",  # Lowercase label
            "  Action:  BUY  ",  # Extra whitespace
        ]
        
        for text in test_cases:
            assert reporter.extract_decision(text) == "BUY"


class TestInitialization:
    """Test QuietModeReporter initialization."""
    
    def test_init_ticker_uppercase(self):
        """Test ticker is converted to uppercase."""
        reporter = QuietModeReporter("aapl")
        assert reporter.ticker == "AAPL"
    
    def test_init_with_company_name(self):
        """Test initialization with company name."""
        reporter = QuietModeReporter("GOOGL", "Alphabet Inc.")
        assert reporter.ticker == "GOOGL"
        assert reporter.company_name == "Alphabet Inc."
    
    def test_init_timestamp_format(self):
        """Test timestamp is in correct format."""
        reporter = QuietModeReporter("MSFT")
        
        # Timestamp should be parseable
        datetime.strptime(reporter.timestamp, "%Y-%m-%d %H:%M:%S")


# Integration-style test
class TestReportIntegration:
    """Integration tests with realistic data."""
    
    def test_realistic_hsbc_scenario(self):
        """Test with realistic HSBC-style data."""
        reporter = QuietModeReporter("0005.HK", "HSBC Holdings")
        result_dict = {
            'final_trade_decision': '''
### FINAL DECISION: HOLD

### THESIS COMPLIANCE SUMMARY
- Financial Health: [DATA MISSING]
- Analyst Coverage: 16 - FAIL
Risk Tally: 2.33

=== DECISION LOGIC ===
ZONE: HIGH >= 2.0
Default Decision: SELL
Actual Decision: HOLD
Override: YES
''',
            'fundamentals_report': '''
### --- START DATA_BLOCK ---
RAW_HEALTH_SCORE: 7/12
ADJUSTED_HEALTH_SCORE: 70% (based on 10 available points)
### --- END DATA_BLOCK ---
''',
            'market_report': 'Liquidity: $225M daily - PASS'
        }
        
        report = reporter.generate_report(result_dict)
        
        assert "0005.HK" in report
        assert "HSBC Holdings" in report
        assert "HOLD" in report
        assert "DATA_BLOCK" in report
        assert "Liquidity" in report