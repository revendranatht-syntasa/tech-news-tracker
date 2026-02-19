import uuid

from langgraph.graph import StateGraph, START, END

from .config import TrackerConfig
from .models import TrackerState
from .prompts import Prompts
from .agents import BrowserAgent, EmailAgent
from .nodes import TrackerNodes


class NewsTracker:
    """
    Assembles the LangGraph pipeline and exposes a single async `run` method.

    Usage:
        tracker = NewsTracker()                      # defaults
        tracker = NewsTracker(config=TrackerConfig(...), prompts=Prompts(...))
        state   = await tracker.run("OpenAI")
    """

    def __init__(
        self,
        config: TrackerConfig | None = None,
        prompts: Prompts | None = None,
    ) -> None:
        self.config  = config  or TrackerConfig()
        self.prompts = prompts or Prompts()
        self.browser = BrowserAgent()
        self.emailer = EmailAgent(self.config)
        self.nodes   = TrackerNodes(self.config, self.prompts, self.browser, self.emailer)
        self.graph   = self._build_graph()

    # ── Graph assembly ────────────────────────────────────────────────────────

    def _build_graph(self):
        builder = StateGraph(TrackerState)

        builder.add_node("feed_fetcher", self.nodes.feed_fetcher_node)
        builder.add_node("pick_next",    self.nodes.pick_next_link_node)
        builder.add_node("get_text",     self.nodes.summarizer_node)
        builder.add_node("writer",       self.nodes.writer_node)
        builder.add_node("emailer",      self.nodes.email_node)

        builder.add_edge(START,          "feed_fetcher")
        builder.add_edge("feed_fetcher", "pick_next")
        builder.add_edge("pick_next",    "get_text")
        builder.add_conditional_edges(
            "get_text",
            self.nodes.has_pending_links,
            {"pick_next": "pick_next", "writer": "writer"},
        )
        builder.add_edge("writer",       "emailer")
        builder.add_edge("emailer",      END)

        # return builder.compile(checkpointer=MemorySaver())
        return builder.compile()

    # ── Public entrypoint ─────────────────────────────────────────────────────

    async def run(self, source_name: str) -> dict:
        assert source_name in self.config.sources, f"Unknown source: {source_name}"
        initial_state: TrackerState = {
            "source_name":      source_name,
            "feed_urls":        self.config.sources[source_name],
            "raw_links":        [],
            "pending_links":    [],
            "current_url":      None,
            "summaries":        [],
            "final_report":     None,
            "email_recipients": self.config.email_recipients,
        }
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        try:
            result = await self.graph.ainvoke(initial_state, config=config)
        finally:
            await self.browser.close()
        return result