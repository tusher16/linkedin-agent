from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from ..schemas import AgentState
from .nodes import (
    draft_post_node,
    guardrails_node,
    human_approval_node,
    mark_failed_cost,
    mark_failed_quality,
    plan_outline_node,
    publish_node,
    review_node,
    should_redraft,
)


def build_graph(checkpointer: Any | None = None) -> Any:
    workflow: StateGraph = StateGraph(AgentState)

    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("plan_outline", plan_outline_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("draft_post", draft_post_node)
    workflow.add_node("review", review_node)
    workflow.add_node("publish", publish_node)
    workflow.add_node("fail_cost", mark_failed_cost)
    workflow.add_node("fail_quality", mark_failed_quality)

    workflow.set_entry_point("guardrails")
    workflow.add_edge("guardrails", "plan_outline")
    workflow.add_edge("plan_outline", "human_approval")
    workflow.add_edge("human_approval", "draft_post")
    workflow.add_edge("draft_post", "review")

    workflow.add_conditional_edges(
        "review",
        should_redraft,
        {
            "redraft": "draft_post",
            "publish": "publish",
            "fail_cost": "fail_cost",
            "fail_quality": "fail_quality",
        },
    )

    workflow.add_edge("publish", END)
    workflow.add_edge("fail_cost", END)
    workflow.add_edge("fail_quality", END)

    return workflow.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["human_approval"],
    )
