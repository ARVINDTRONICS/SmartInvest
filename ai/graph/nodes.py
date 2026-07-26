import logging
from datetime import datetime, time
from sqlalchemy import select
from app.core.database import async_session_factory
from app.config.config import settings
from ai.graph.state import GraphState
from database.models import MarketData, TechnicalIndicator, News

logger = logging.getLogger(__name__)


async def market_collector_node(state: GraphState) -> dict:
    """
    Graph node: Fetches market pricing and technical indicators on target date.
    """
    symbol = state["symbol"]
    eval_date = state["date"]
    
    async with async_session_factory() as db:
        # Fetch pricing close
        stmt_m = (
            select(MarketData.close)
            .where(MarketData.symbol == symbol)
            .where(MarketData.date == eval_date)
            .limit(1)
        )
        res_m = await db.execute(stmt_m)
        close = res_m.scalar_one_or_none()

        # Fetch technical indicators
        stmt_t = (
            select(TechnicalIndicator)
            .where(TechnicalIndicator.symbol == symbol)
            .where(TechnicalIndicator.date == eval_date)
            .limit(1)
        )
        res_t = await db.execute(stmt_t)
        t_rec = res_t.scalar_one_or_none()

    if close is None:
        market_text = f"Market data for {symbol} on {eval_date} is unavailable."
    else:
        sma_50 = t_rec.sma_50 if t_rec else None
        sma_200 = t_rec.sma_200 if t_rec else None
        rsi = t_rec.rsi if t_rec else None
        vix = t_rec.fear_index if t_rec else None
        
        market_text = (
            f"Asset pricing close: {close:.2f}\n"
            f"SMA 50: {f'{sma_50:.2f}' if sma_50 is not None else 'N/A'}\n"
            f"SMA 200: {f'{sma_200:.2f}' if sma_200 is not None else 'N/A'}\n"
            f"RSI: {f'{rsi:.2f}' if rsi is not None else 'N/A'}\n"
            f"Fear Index (VIX): {f'{vix:.2f}' if vix is not None else 'N/A'}"
        )

    return {"market_text": market_text}


async def news_analysis_node(state: GraphState) -> dict:
    """
    Graph node: Fetches news articles published on target date and summaries sentiment.
    """
    eval_date = state["date"]
    
    start_dt = datetime.combine(eval_date, time.min)
    end_dt = datetime.combine(eval_date, time.max)
    
    async with async_session_factory() as db:
        stmt_n = (
            select(News.headline, News.source)
            .where(News.published_date.between(start_dt, end_dt))
        )
        res_n = await db.execute(stmt_n)
        articles = res_n.all()

    if not articles:
        news_text = "No news articles found on evaluation date."
    else:
        news_lines = [f"- [{a.source}] {a.headline}" for a in articles]
        news_text = "Recent Headlines:\n" + "\n".join(news_lines)

    return {"news_text": news_text}


async def macro_analysis_node(state: GraphState) -> dict:
    """
    Graph node: Summarizes current macroeconomic interest rates policies context.
    """
    # Defaults to neutral macro text as macro collection is a skipped phase
    macro_text = "Macro Environment: Central bank policy rates remained steady (neutral stance)."
    return {"macro_text": macro_text}


async def feature_summary_node(state: GraphState) -> dict:
    """
    Graph node: Integrates market, news, and macro summaries into one payload.
    """
    summary = (
        "=== FEATURE ENGINEERED INPUTS SUMMARY ===\n"
        f"{state.get('market_text', '')}\n\n"
        f"{state.get('news_text', '')}\n\n"
        f"{state.get('macro_text', '')}\n"
        "========================================"
    )
    return {"summary_text": summary}


async def explanation_agent_node(state: GraphState) -> dict:
    """
    Graph node: Uses LLM reasoning to explain the Decision Engine recommendations.
    """
    symbol = state["symbol"]
    rec = state["recommendation"]
    
    fallback_explanation = (
        f"Decided to {rec['decision']} today for {symbol}. Confidence: {rec['confidence']}%.\n"
        f"Primary triggers: {', '.join(rec['triggered_rules'])}."
    )

    # 1. Fallback default if OpenAI API Key is missing (e.g. testing)
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        explanation = fallback_explanation
    # 2. Invoke LLM
    else:
        # Check if the target is Google Gemini API
        api_base = settings.OPENAI_API_BASE or ""
        if "generativelanguage.googleapis.com" in api_base:
            import httpx
            # Append API key to the raw Google REST endpoint url
            url = f"{api_base}?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    f"You are SmartInvest AI, an explanation model. Explain the decision made by the deterministic "
                                    f"rule engine. Do not recommend or decide. Analyze why the rules decided what they did "
                                    f"based on the provided indicators, VIX, news context, and remaining window days.\n\n"
                                    f"Symbol: {symbol}\n"
                                    f"Decision: {rec['decision']} (Confidence: {rec['confidence']}%)\n"
                                    f"Triggered Rules: {rec['triggered_rules']}\n"
                                    f"Market Context:\n{state['summary_text']}"
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3
                }
            }
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        resp_json = response.json()
                        explanation = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        logger.error(f"Gemini API returned error code {response.status_code}: {response.text}")
                        explanation = fallback_explanation
            except Exception as e:
                logger.error(f"Error calling Gemini API: {e}. Falling back to clean text summary.")
                explanation = fallback_explanation
        else:
            # Fall back to standard OpenAI / Groq / OpenRouter LangChain client
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = ChatOpenAI(
                openai_api_key=api_key,
                openai_api_base=settings.OPENAI_API_BASE,
                model=settings.LLM_MODEL_NAME,
                temperature=0.3
            )
            system_prompt = (
                "You are SmartInvest AI, an explanation model. Explain the decision made by the deterministic "
                "rule engine. Do not recommend or decide. Analyze why the rules decided what they did "
                "based on the provided indicators, VIX, news context, and remaining window days."
            )
            human_msg = (
                f"Symbol: {symbol}\n"
                f"Decision: {rec['decision']} (Confidence: {rec['confidence']}%)\n"
                f"Triggered Rules: {rec['triggered_rules']}\n"
                f"Market Context:\n{state['summary_text']}"
            )
            try:
                response = await llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_msg)
                ])
                explanation = response.content
            except Exception as e:
                logger.error(
                    f"Error calling OpenAI API: {e}. "
                    f"Falling back to clean rule-engine text explanation."
                )
                explanation = fallback_explanation

    return {"ai_explanation": explanation}


async def telegram_formatter_node(state: GraphState) -> dict:
    """
    Graph node: Formats the final Telegram markdown alert block.
    """
    symbol = state["symbol"]
    rec = state["recommendation"]
    ai_exp = state["ai_explanation"] or "No explanation generated."
    
    # Render clean Telegram text block
    telegram_text = (
        f"🚨 *Today's Smart SIP Status: {symbol}*\n\n"
        f"*Decision*:\n`{rec['decision']}`\n\n"
        f"*Confidence*:\n`{rec['confidence']}%`\n\n"
        f"*SIP Window*:\nRemaining Days: {rec['remaining_window_days']}\n\n"
        f"*Triggered Rules*:\n`{', '.join(rec['triggered_rules'])}`\n\n"
        f"*AI Reasoning*:\n{ai_exp}"
    )
    return {"telegram_text": telegram_text}
