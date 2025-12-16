# AI Investment Agent - Streamlit Web UI

A modern, interactive web interface for the AI Investment Agent built with Streamlit.

## Features

### 1. Single Ticker Analysis
- Comprehensive AI-powered analysis for individual stocks
- Quick or Deep analysis modes
- Real-time market data integration
- Exportable reports (Markdown, JSON)
- Interactive decision cards with color-coded recommendations

### 2. Portfolio Management
- Upload portfolios via CSV or Excel
- Real-time P&L tracking
- Position-level analysis
- Portfolio-wide AI analysis
- Export capabilities

### 3. Backtesting Engine
- Historical strategy testing
- Performance metrics (Sharpe, Sortino, Max Drawdown)
- Interactive equity curves
- Trade history analysis
- Customizable parameters

### 4. Peer Comparison
- Auto-detect industry peers
- Multi-dimensional comparison (Valuation, Growth, Profitability, Financial Health)
- Interactive visualizations
- Ranking systems
- Export comparison data

## Installation

### Prerequisites
- Python 3.10+
- Poetry (recommended) or pip

### Install Dependencies

Using Poetry:
```bash
poetry install
```

Using pip:
```bash
pip install streamlit plotly openpyxl
```

## Running the Application

### Using Streamlit directly:
```bash
streamlit run ui/app.py
```

### Using Poetry:
```bash
poetry run streamlit run ui/app.py
```

The application will open in your default browser at `http://localhost:8501`

## Project Structure

```
ui/
├── app.py                      # Main application entry point
├── pages/
│   ├── 1_Single_Analysis.py    # Single ticker analysis
│   ├── 2_Portfolio.py          # Portfolio management
│   ├── 3_Backtesting.py        # Backtesting engine
│   └── 4_Peer_Comparison.py    # Peer comparison
├── components/
│   ├── __init__.py
│   ├── ticker_input.py         # Ticker input widgets
│   ├── analysis_view.py        # Analysis results display
│   ├── chart_view.py           # Interactive charts
│   └── decision_card.py        # Decision display cards
└── utils.py                    # Utility functions
```

## Usage Guide

### Single Analysis

1. Navigate to "Single Analysis" in the sidebar
2. Enter a ticker symbol (e.g., AAPL, MSFT, GOOGL)
3. Select analysis mode (Quick or Deep)
4. Click "Run Analysis"
5. View results and export if needed

### Portfolio Management

1. Navigate to "Portfolio" in the sidebar
2. Download the CSV template
3. Fill in your positions:
   - ticker: Stock symbol
   - quantity: Number of shares
   - cost_basis: Average purchase price
   - currency: Currency code (optional)
   - purchase_date: Purchase date (optional)
4. Upload the completed file
5. View portfolio summary and P&L
6. Analyze individual positions or entire portfolio

### Backtesting

1. Navigate to "Backtesting" in the sidebar
2. Enter ticker symbol
3. Select date range
4. Configure strategy parameters:
   - Initial capital
   - Position size
   - Commission per trade
5. Click "Run Backtest"
6. Review performance metrics and equity curve
7. Export results if needed

### Peer Comparison

1. Navigate to "Peer Comparison" in the sidebar
2. Enter ticker symbol
3. Choose auto-detect or manual peer selection
4. Select comparison dimensions
5. Click "Run Comparison"
6. Review comparison tables and rankings
7. Export comparison data

## Configuration

### Environment Variables

Ensure your `.env` file contains:
```
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
FINNHUB_API_KEY=your_finnhub_api_key
```

### Streamlit Configuration

Create `.streamlit/config.toml` for custom settings:
```toml
[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
```

## Features in Detail

### Interactive Charts
- Price and volume charts with Plotly
- Equity curves for backtesting
- Correlation heatmaps
- Performance comparisons
- Responsive and interactive

### Decision Cards
- Color-coded BUY (green), SELL (red), HOLD (yellow)
- Confidence levels
- Risk assessment
- Time horizons

### Export Options
- Markdown reports
- JSON data
- CSV exports
- PDF generation (coming soon)

### Session State Management
- Persistent analysis results
- Portfolio tracking across sessions
- Cached data for performance

## Performance Optimization

- Caching with `@st.cache_data`
- Lazy loading of analysis results
- Efficient data structures
- Minimal API calls

## Troubleshooting

### Common Issues

**Issue: "Module not found" error**
```bash
# Ensure you're in the project root
cd /path/to/ai-investment-agent

# Install dependencies
poetry install
```

**Issue: "Invalid ticker" error**
- Verify ticker symbol is correct
- Check internet connection
- Ensure yfinance can access data

**Issue: Analysis fails**
- Check API keys in `.env`
- Verify all dependencies installed
- Check logs for specific errors

**Issue: Slow performance**
- Clear Streamlit cache: `streamlit cache clear`
- Reduce analysis depth (use Quick mode)
- Check network connection

## Development

### Adding New Pages

1. Create new file in `ui/pages/` with numeric prefix (e.g., `5_New_Page.py`)
2. Import required components and utilities
3. Implement page layout and functionality
4. Streamlit will automatically add to navigation

### Adding New Components

1. Create new file in `ui/components/`
2. Define reusable component functions
3. Export in `__init__.py`
4. Import and use in pages

### Custom Styling

Add custom CSS in page files:
```python
st.markdown("""
    <style>
    .custom-class {
        /* Your styles */
    }
    </style>
    """, unsafe_allow_html=True)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Test thoroughly
5. Submit pull request

## License

See main project LICENSE file.

## Support

- GitHub Issues: [Report bugs](https://github.com/your-repo/issues)
- Documentation: [Main README](../README.md)
- Community: [Discord](https://discord.gg/your-server)

## Roadmap

- [ ] PDF export functionality
- [ ] Real-time streaming updates
- [ ] Multi-portfolio comparison
- [ ] Advanced charting options
- [ ] Custom strategy builder
- [ ] Mobile responsive improvements
- [ ] Dark mode theme
- [ ] User authentication
- [ ] Cloud deployment guide

## Credits

Built with:
- [Streamlit](https://streamlit.io/) - Web framework
- [Plotly](https://plotly.com/) - Interactive charts
- [yfinance](https://github.com/ranaroussi/yfinance) - Market data
- [Pandas](https://pandas.pydata.org/) - Data manipulation

---

**Version:** 1.0.0
**Last Updated:** December 2025
