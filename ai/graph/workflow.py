from langgraph.graph import StateGraph, START, END
from ai.graph.state import GraphState
from ai.graph.nodes import (
    market_collector_node,
    news_analysis_node,
    macro_analysis_node,
    feature_summary_node,
    explanation_agent_node,
    telegram_formatter_node
)

# 1. Initialize StateGraph
workflow = StateGraph(GraphState)

# 2. Register all node executors
workflow.add_node("market_collector", market_collector_node)
workflow.add_node("news_analysis", news_analysis_node)
workflow.add_node("macro_analysis", macro_analysis_node)
workflow.add_node("feature_summary", feature_summary_node)
workflow.add_node("explanation_agent", explanation_agent_node)
workflow.add_node("telegram_formatter", telegram_formatter_node)

# 3. Connect nodes to construct permitted sequential data flow
workflow.add_edge(START, "market_collector")
workflow.add_edge("market_collector", "news_analysis")
workflow.add_edge("news_analysis", "macro_analysis")
workflow.add_edge("macro_analysis", "feature_summary")
workflow.add_edge("feature_summary", "explanation_agent")
workflow.add_edge("explanation_agent", "telegram_formatter")
workflow.add_edge("telegram_formatter", END)

# 4. Compile the graph
app = workflow.compile()
