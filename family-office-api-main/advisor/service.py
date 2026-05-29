from advisor.ethan.context_engine import compact_context, compact_portfolio
from advisor.ethan.cache_policy import ETHAN_GLOBAL_CACHE_VERSION
from advisor.ethan.memory_engine import build_life_context, get_memory, update_memory
from advisor.ethan.openai_gateway import ethan_chat_completion, is_ethan_openai_configured
from advisor.ethan.output_renderer import ETHAN_TEXT_ORIGIN, render_ethan_output
from advisor.ethan.persistence_engine import (
    ensure_ethan_ai_tables,
    get_cache,
    get_daily_deep_usage,
    record_usage,
    set_cache,
)
from advisor.ethan.prompt_engine import build_advisor_messages
from advisor.ethan.response_engine import (
    build_llm_response_data as response_build_llm_response_data,
    build_fallback_response as response_build_fallback_response,
    get_context_score as response_get_context_score,
    get_llm_response as response_get_llm_response,
    is_legacy_ethan_response as response_is_legacy_ethan_response,
)
from advisor.ethan.runtime_engine import (
    ADVISOR_CACHE_VERSION,
    MODEL_FALLBACK,
    PLAN_CONFIG,
    build_advisor_cache_hash,
    choose_model,
    classify_request,
    classify_task,
    estimate_tokens,
    stable_hash,
)
from advisor.ethan.strategy_engine import build_response_strategy
from database import engine
from advisor.user_state import centralized_user_state_builder


def advisor_logic(user_email, message, level=None, bypass_cache=False):
    with engine.begin() as conn:
        ensure_ethan_ai_tables(conn)
        unified_state = centralized_user_state_builder(conn, user_email)
        user_id = unified_state["user_id"]
        plan = unified_state["plan"]
        config = PLAN_CONFIG[plan]
        tier = config["tier"]
        complexity = classify_request(message)
        task_type = classify_task(message, complexity)
        deep_sessions_used = get_daily_deep_usage(conn, user_id)
        model, soft_budget_active = choose_model(plan, complexity, deep_sessions_used)

        context = unified_state["dashboard_context"]
        portfolio = unified_state["portfolio"]
        opportunities = unified_state["opportunities"]
        memory = get_memory(conn, user_id)
        life_context = build_life_context(conn, user_id, memory)
        context["life_context"] = life_context
        response_strategy = build_response_strategy(message, memory)

        fingerprint = stable_hash({
            "version": ADVISOR_CACHE_VERSION,
            "context": compact_context(context),
            "portfolio": compact_portfolio(portfolio),
            "opportunity_count": (
                opportunities.get("count", 0)
                if isinstance(opportunities, dict)
                else len(opportunities)
                if isinstance(opportunities, list)
                else 0
            ),
            "memory": memory,
            "response_strategy": response_strategy,
        })[:16]
        cache_key = f"advisor:{build_advisor_cache_hash(user_email, message, plan, complexity, fingerprint)}"

        cached = None if bypass_cache else get_cache(cache_key)
        if cached and not response_is_legacy_ethan_response(cached):
            record_usage(conn, user_id, user_email, plan, tier, task_type, complexity, model, True)
            cached["cache_hit"] = True
            return cached

        messages = build_advisor_messages(
            context=context,
            portfolio=portfolio,
            opportunities=opportunities,
            memory=memory,
            message=message,
            plan=plan,
            tier=tier,
            complexity=complexity,
            response_strategy=response_strategy,
        )

        llm_text, llm_cache_hit, input_tokens, output_tokens, actual_model = response_get_llm_response(
            messages,
            model,
            config["max_output_tokens"],
            stable_hash_fn=stable_hash,
            get_cache_fn=get_cache,
            set_cache_fn=set_cache,
            estimate_tokens_fn=estimate_tokens,
            is_model_configured_fn=is_ethan_openai_configured,
            chat_completion_fn=ethan_chat_completion,
            fallback_model=MODEL_FALLBACK,
        )

        if not llm_text:
            response_data = response_build_fallback_response(
                context,
                opportunities,
                tier,
                message=message,
                portfolio=portfolio,
                response_strategy=response_strategy,
                compact_portfolio_fn=compact_portfolio,
                build_response_strategy_fn=build_response_strategy,
            )
        else:
            response_data = response_build_llm_response_data(
                llm_text,
                context,
                tier,
                complexity=complexity,
                soft_budget_active=soft_budget_active,
                cache_hit=llm_cache_hit,
            )

        rendered_text = render_ethan_output(
            response_data,
            context=context,
            message=message,
            response_strategy=response_strategy,
            tier=tier,
        )

        update_memory(
            conn,
            user_id,
            message,
            rendered_text,
            context,
            memory,
            response_strategy,
            classify_task_fn=classify_task,
            classify_request_fn=classify_request,
        )
        record_usage(
            conn,
            user_id,
            user_email,
            plan,
            tier,
            task_type,
            complexity,
            actual_model,
            llm_cache_hit,
            input_tokens,
            output_tokens,
        )

        result = {
            "status": response_data.get("status", "empty"),
            "analysis": rendered_text,
            "metadata": {
                "status": response_data.get("status", "empty"),
                "context_score": response_get_context_score(context),
                "tier": tier,
                "complexity": complexity,
                "soft_budget_active": soft_budget_active,
                "cache_hit": llm_cache_hit,
                "text_origin": ETHAN_TEXT_ORIGIN,
                "cache_version": ETHAN_GLOBAL_CACHE_VERSION,
            },
        }

        if not bypass_cache:
            set_cache(cache_key, result, ttl=900 if complexity != "high" else 300)
        return result

