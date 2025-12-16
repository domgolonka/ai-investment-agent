# AI Investment Agent - Web UI Quick Start

## 1-Minute Setup

### Prerequisites
```bash
# Ensure you have Python 3.10+ and Poetry installed
python --version  # Should be 3.10+
poetry --version  # Or use pip
```

### Installation
```bash
# Navigate to project root
cd /Users/dom-personal/PycharmProjects/ai-investment-agent

# Install dependencies (includes streamlit, plotly, openpyxl)
poetry install

# OR with pip
pip install streamlit plotly openpyxl
```

### Launch
```bash
# Option 1: Use convenience script
./run_ui.sh

# Option 2: Direct Streamlit command
streamlit run ui/app.py

# Option 3: With Poetry
poetry run streamlit run ui/app.py
```

The UI will open automatically at `http://localhost:8501`

## Quick Feature Guide

### 1. Single Ticker Analysis
**Path:** Single Analysis (sidebar)

1. Enter ticker (e.g., AAPL)
2. Select mode: Quick (30-60s) or Deep (2-5 min)
3. Click "Run Analysis"
4. View color-coded decision (GREEN=BUY, RED=SELL, YELLOW=HOLD)
5. Export as Markdown or JSON

### 2. Portfolio Management
**Path:** Portfolio (sidebar)

1. Download CSV template
2. Fill in positions:
   - ticker, quantity, cost_basis (required)
   - currency, purchase_date (optional)
3. Upload file
4. View P&L and metrics
5. Analyze individual positions

### 3. Backtesting
**Path:** Backtesting (sidebar)

1. Enter ticker
2. Set date range
3. Configure:
   - Initial capital
   - Position size
   - Commission
4. Run backtest
5. View equity curve and metrics

### 4. Peer Comparison
**Path:** Peer Comparison (sidebar)

1. Enter ticker
2. Auto-detect peers OR manual input
3. Select comparison dimensions
4. Run comparison
5. View rankings and charts

## Environment Setup

Create `.env` file in project root:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
FINNHUB_API_KEY=your_finnhub_api_key_here
```

## Keyboard Shortcuts

- `Ctrl/Cmd + R` - Rerun app
- `Ctrl/Cmd + Shift + R` - Clear cache and rerun
- `C` - Clear cache
- `R` - Rerun script

## Common Issues

**"Module not found"**
```bash
poetry install  # or pip install streamlit plotly openpyxl
```

**"Invalid API key"**
```bash
# Check .env file has all required keys
cat .env
```

**"Port already in use"**
```bash
# Use different port
streamlit run ui/app.py --server.port 8502
```

## File Locations

- **Main App**: `/ui/app.py`
- **Pages**: `/ui/pages/*.py`
- **Components**: `/ui/components/*.py`
- **Config**: `/.streamlit/config.toml`
- **Docs**: `/ui/README.md`

## Key Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| app.py | 200+ | Main entry point, welcome page |
| 1_Single_Analysis.py | 300+ | Ticker analysis with Quick/Deep modes |
| 2_Portfolio.py | 400+ | Portfolio upload and management |
| 3_Backtesting.py | 300+ | Strategy backtesting |
| 4_Peer_Comparison.py | 400+ | Peer comparison and rankings |
| ticker_input.py | 150+ | Ticker validation widget |
| decision_card.py | 200+ | Color-coded decision display |
| analysis_view.py | 300+ | Analysis results renderer |
| chart_view.py | 350+ | Plotly charts |
| utils.py | 400+ | Utility functions |

**Total**: 4,114 lines of Python code

## Architecture

```
Streamlit App
    ↓
Main App (Welcome)
    ├→ Single Analysis → run_analysis() → src.main
    ├→ Portfolio → PortfolioManager → src.portfolio
    ├→ Backtesting → BacktestEngine → src.backtesting
    └→ Peer Comparison → PeerFinder → src.peers
```

## Component Integration

```python
# All pages use these shared components
from ui.components import (
    render_ticker_input,      # Validated ticker input
    render_decision_card,      # BUY/SELL/HOLD cards
    render_analysis_sections,  # Expandable analysis
    render_price_chart,        # Price/volume charts
    render_equity_curve        # Backtest equity curves
)

from ui.utils import (
    validate_ticker,           # Ticker validation
    format_currency,           # $1.23M formatting
    format_percentage,         # 12.34% formatting
    format_timestamp           # File naming
)
```

## Customization

### Change Theme
Edit `/.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#667eea"        # Main accent color
backgroundColor = "#ffffff"     # Page background
secondaryBackgroundColor = "#f0f2f6"  # Sidebar background
textColor = "#262730"           # Text color
```

### Add New Page
1. Create `/ui/pages/5_Your_Page.py`
2. Streamlit auto-discovers and adds to navigation
3. Use existing components for consistency

### Custom Component
```python
# In ui/components/your_component.py
import streamlit as st

def render_your_component(data):
    st.markdown("## Your Component")
    # Your logic here

# In ui/components/__init__.py
from .your_component import render_your_component
```

## Performance Tips

1. **Use caching**: `@st.cache_data` for data loading
2. **Quick mode first**: Start with Quick analysis
3. **Clear cache**: If experiencing slowness
4. **Limit date ranges**: For backtesting

## Support

- **Documentation**: `/ui/README.md`
- **Implementation Report**: `/UI_IMPLEMENTATION_REPORT.md`
- **Main Project**: `/README.md`

## Next Steps After Setup

1. **Test Single Analysis**: Try AAPL in Quick mode
2. **Upload Portfolio**: Use template to test portfolio features
3. **Run Backtest**: Test backtesting with 1-year AAPL data
4. **Compare Peers**: Try peer comparison for tech stocks

---

**Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: December 15, 2025
