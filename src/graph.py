"""
Multi-Agent Trading System Graph
Updated for Gemini 3.0 Routing and LangGraph 1.x compatibility.
FIXED: Tool routing now tracks which agent called the tool via sender field.
FIXED: Added ticker logging to track contamination issues.
UPDATED: Added ticker-specific memory isolation to prevent cross-contamination.
"""

from typing import Literal, Dict, Optional
from dataclasses import dataclass
import structlog

from langgraph.graph import StateGraph, END
from langgraph.types import RunnableConfig
# Modern ToolNode import for LangGraph 1.x
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage

from src.agents import (
    AgentState, create_analyst_node, create_researcher_node, 
    create_research_manager_node, create_trader_node, 
    create_risk_debater_node, create_portfolio_manager_node, 
    create_state_cleaner_node
)
from src.llms import quick_thinking_llm, deep_thinking_llm
from src.toolkit import toolkit
from src.memory import (
    create_memory_instances, cleanup_all_memories,
    # Legacy imports for backwards compatibility (DEPRECATED)
    bull_memory as legacy_bull_memory, 
    bear_memory as legacy_bear_memory,
    invest_judge_memory as legacy_invest_judge_memory,
    trader_memory as legacy_trader_memory,
    risk_manager_memory as legacy_risk_manager_memory
)

logger = structlog.get_logger(__name__)

@dataclass
class TradingContext:
    """
    Context object passed to graph nodes via configuration.
    Includes parameters that control graph execution flow.
    
    UPDATED: Added ticker-specific memory management.
    """
    ticker: str
    trade_date: str
    quick_mode: bool = False
    enable_memory: bool = True
    max_debate_rounds: int = 2
    max_risk_rounds: int = 1
    # NEW: Ticker-specific memories to prevent cross-contamination
    ticker_memories: Optional[Dict[str, any]] = None
    # NEW: Whether to cleanup previous ticker memories
    cleanup_previous_memories: bool = True

def should_continue_analyst(state: AgentState, config: RunnableConfig) -> Literal["tools", "continue"]:
    """
    Determine if analyst should call tools or continue to next node.
    
    Args:
        state: Current agent state
        config: Runtime configuration
        
    Returns:
        "tools" if agent has pending tool calls, "continue" otherwise
    """
    messages = state.get("messages", [])
    if messages and hasattr(messages[-1], 'tool_calls') and messages[-1].tool_calls:
        return "tools"
    return "continue"

def route_tools(state: AgentState) -> str:
    """
    Route back to the agent that called the tool.
    Uses the 'sender' field from the state to determine which agent to return to.
    
    Args:
        state: Current agent state with sender information
        
    Returns:
        Name of the node to return to after tool execution
    """
    sender = state.get("sender", "")
    
    # Map internal agent keys to Node Names
    agent_map = {
        "market_analyst": "Market Analyst",
        "sentiment_analyst": "Social Analyst",
        "news_analyst": "News Analyst",
        "fundamentals_analyst": "Fundamentals Analyst"
    }
    
    node_name = agent_map.get(sender, "Market Analyst")
    
    logger.debug(
        "tool_routing",
        sender=sender,
        routing_to=node_name
    )
    
    return node_name

def create_trading_graph(
    max_debate_rounds: int = 2,
    max_risk_discuss_rounds: int = 1,
    enable_memory: bool = True,
    recursion_limit: int = 100,
    ticker: Optional[str] = None,
    cleanup_previous: bool = False
):
    """
    Create the multi-agent trading analysis graph with ticker-specific memory isolation.
    
    UPDATED: Now supports ticker-specific memories to prevent cross-contamination.
    
    Args:
        ticker: Stock ticker symbol (e.g., "0005.HK", "AAPL"). If provided, creates
                ticker-specific memories. If None, uses legacy global memories (NOT recommended).
        cleanup_previous: If True, deletes all previous memories before creating new ones.
                         Use this to ensure fresh analysis without contamination.
        max_debate_rounds: Maximum rounds of bull/bear debate (default: 2)
        max_risk_discuss_rounds: Maximum rounds of risk discussion (default: 1)
        enable_memory: Whether to enable agent memory (default: True)
        recursion_limit: Maximum recursion depth for graph execution (default: 100)
        
    Returns:
        Compiled LangGraph StateGraph ready for execution
        
    Example:
        # Recommended: Ticker-specific memory with cleanup
        graph = create_trading_graph(
            ticker="0005.HK",
            cleanup_previous=True,
            max_debate_rounds=2
        )
        
        # Legacy: Global memory (may cause contamination)
        graph = create_trading_graph(max_debate_rounds=2)
    """
    
    # Determine which memories to use
    if ticker and enable_memory:
        # RECOMMENDED: Create ticker-specific memories
        if cleanup_previous:
            logger.info(
                "cleaning_previous_memories",
                ticker=ticker,
                message="Deleting all previous memory collections to prevent contamination"
            )
            cleanup_all_memories(days=0)
        
        logger.info(
            "creating_ticker_memories",
            ticker=ticker,
            message="Creating ticker-specific memory collections"
        )
        memories = create_memory_instances(ticker)
        
        # Extract specific memories for each agent
        safe_ticker = ticker.replace(".", "_").replace("-", "_")
        bull_memory = memories.get(f"{safe_ticker}_bull_memory", legacy_bull_memory)
        bear_memory = memories.get(f"{safe_ticker}_bear_memory", legacy_bear_memory)
        invest_judge_memory = memories.get(f"{safe_ticker}_invest_judge_memory", legacy_invest_judge_memory)
        trader_memory = memories.get(f"{safe_ticker}_trader_memory", legacy_trader_memory)
        risk_manager_memory = memories.get(f"{safe_ticker}_risk_manager_memory", legacy_risk_manager_memory)
        
        logger.info(
            "ticker_memories_ready",
            ticker=ticker,
            bull_available=bull_memory.available,
            bear_available=bear_memory.available,
            judge_available=invest_judge_memory.available,
            trader_available=trader_memory.available,
            risk_available=risk_manager_memory.available
        )
    else:
        # LEGACY: Use global memories (will cause cross-contamination!)
        logger.warning(
            "using_legacy_memories",
            ticker=ticker,
            enable_memory=enable_memory,
            message="Using legacy global memories. This WILL cause cross-ticker contamination! "
                    "Use ticker-specific memories by passing ticker parameter."
        )
        bull_memory = legacy_bull_memory
        bear_memory = legacy_bear_memory
        invest_judge_memory = legacy_invest_judge_memory
        trader_memory = legacy_trader_memory
        risk_manager_memory = legacy_risk_manager_memory
    
    # Log graph creation
    logger.info(
        "creating_trading_graph",
        ticker=ticker,
        max_debate_rounds=max_debate_rounds,
        enable_memory=enable_memory,
        using_ticker_specific_memory=ticker is not None
    )
    
    # Nodes
    market = create_analyst_node(quick_thinking_llm, "market_analyst", toolkit.get_technical_tools(), "market_report")
    social = create_analyst_node(quick_thinking_llm, "sentiment_analyst", toolkit.get_sentiment_tools(), "sentiment_report")
    news = create_analyst_node(quick_thinking_llm, "news_analyst", toolkit.get_news_tools(), "news_report")
    fund = create_analyst_node(quick_thinking_llm, "fundamentals_analyst", toolkit.get_fundamental_tools(), "fundamentals_report")
    
    cleaner = create_state_cleaner_node()
    # Standard ToolNode initialized with all tools
    tool_node = ToolNode(toolkit.get_all_tools())
    
    # Research & Execution Nodes (now using ticker-specific or legacy memories)
    bull = create_researcher_node(quick_thinking_llm, bull_memory, "bull_researcher")
    bear = create_researcher_node(quick_thinking_llm, bear_memory, "bear_researcher")
    res_mgr = create_research_manager_node(deep_thinking_llm, invest_judge_memory)
    trader = create_trader_node(quick_thinking_llm, trader_memory)
    
    # Risk Nodes
    risky = create_risk_debater_node(quick_thinking_llm, "risky_analyst")
    safe = create_risk_debater_node(quick_thinking_llm, "safe_analyst")
    neutral = create_risk_debater_node(quick_thinking_llm, "neutral_analyst")
    pm = create_portfolio_manager_node(deep_thinking_llm, risk_manager_memory)

    workflow = StateGraph(AgentState)
    
    workflow.add_node("Market Analyst", market)
    workflow.add_node("Social Analyst", social)
    workflow.add_node("News Analyst", news)
    workflow.add_node("Fundamentals Analyst", fund)
    workflow.add_node("tools", tool_node)
    workflow.add_node("Cleaner", cleaner)
    
    # Add research and risk nodes
    workflow.add_node("Bull Researcher", bull)
    workflow.add_node("Bear Researcher", bear)
    workflow.add_node("Research Manager", res_mgr)
    workflow.add_node("Trader", trader)
    workflow.add_node("Risky Analyst", risky)
    workflow.add_node("Safe Analyst", safe)
    workflow.add_node("Neutral Analyst", neutral)
    workflow.add_node("Portfolio Manager", pm)

    # Flow
    workflow.set_entry_point("Market Analyst")
    
    # 1. Market Flow
    workflow.add_conditional_edges("Market Analyst", should_continue_analyst, {"tools": "tools", "continue": "Cleaner"})
    
    # 2. Social Flow (via cleaner nodes to reset history)
    workflow.add_node("Clean1", cleaner)
    workflow.add_edge("Cleaner", "Clean1")
    workflow.add_edge("Clean1", "Social Analyst")
    
    workflow.add_conditional_edges("Social Analyst", should_continue_analyst, {"tools": "tools", "continue": "News Analyst"})
    workflow.add_conditional_edges("News Analyst", should_continue_analyst, {"tools": "tools", "continue": "Fundamentals Analyst"})
    workflow.add_conditional_edges("Fundamentals Analyst", should_continue_analyst, {"tools": "tools", "continue": "Bull Researcher"})

    # Tool Return Logic
    workflow.add_conditional_edges("tools", route_tools, {
        "Market Analyst": "Market Analyst",
        "Social Analyst": "Social Analyst",
        "News Analyst": "News Analyst",
        "Fundamentals Analyst": "Fundamentals Analyst"
    })

    # Debate Flow
    def debate_router(state: AgentState, config: RunnableConfig):
        """
        Route debate flow between Bull and Bear researchers.
        """
        # Retrieve configuration from context
        context = config.get("configurable", {}).get("context")
        # Default to 2 rounds if context is missing or field is None
        max_rounds = getattr(context, "max_debate_rounds", 2) if context else 2
        
        # Total turns = rounds * 2 (Bull + Bear per round)
        limit = max_rounds * 2
        
        count = state.get("investment_debate_state", {}).get("count", 0)
        
        if count >= limit:
            return "Research Manager"
            
        # Alternating flow
        return "Bear Researcher" if count % 2 != 0 else "Bull Researcher"

    workflow.add_conditional_edges("Bull Researcher", debate_router, ["Bear Researcher", "Research Manager"])
    workflow.add_conditional_edges("Bear Researcher", debate_router, ["Bull Researcher", "Research Manager"])
    
    workflow.add_edge("Research Manager", "Trader")
    workflow.add_edge("Trader", "Risky Analyst")
    
    # Risk Flow
    workflow.add_edge("Risky Analyst", "Safe Analyst")
    workflow.add_edge("Safe Analyst", "Neutral Analyst")
    workflow.add_edge("Neutral Analyst", "Portfolio Manager")
    workflow.add_edge("Portfolio Manager", END)

    logger.info(
        "trading_graph_created",
        ticker=ticker,
        using_ticker_specific_memory=ticker is not None
    )
    return workflow.compile()