import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

import feedparser
from langchain_core.messages import HumanMessage, SystemMessage

from .agents import BrowserAgent, EmailAgent
from .config import TrackerConfig
from .models import TrackerState
from .prompts import Prompts


class TrackerNodes:
    """
    Holds all LangGraph node methods.
    Each method matches the (state: TrackerState) -> dict signature LangGraph expects.
    """

    def __init__(self, config: TrackerConfig, prompts: Prompts, browser: BrowserAgent, emailer: EmailAgent) -> None:
        self.config  = config
        self.prompts = prompts
        self.browser = browser
        self.emailer = emailer

    # ── Cache helper ──────────────────────────────────────────────────────────

    def _get_last_run_date(self) -> datetime:
        cache_path = Path(self.config.cache_path)
        try:
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return datetime.fromisoformat(data["last_run"])
        except Exception:
            return datetime.now(timezone.utc) - timedelta(days=self.config.fallback_lookback_days)

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def feed_fetcher_node(self, state: TrackerState) -> dict:
        print("[FEED FETCHER]: Starting ...")
        links: List[str] = []
        cutoff = self._get_last_run_date()

        for url in state["feed_urls"]:
            feed = feedparser.parse(url)

            for entry in feed.entries:
                if not hasattr(entry, "link"):
                    continue

                # Prefer published_parsed, fallback to updated_parsed
                parsed_time = (
                    getattr(entry, "published_parsed", None)
                    or getattr(entry, "updated_parsed", None)
                )

                if not parsed_time:
                    continue

                published = datetime(
                    *parsed_time[:6],
                    tzinfo=timezone.utc
                )

                if published > cutoff:
                    links.append(entry.link)

        deduped = list(dict.fromkeys(links))
        print("[FEED FETCHER] Done.")
        return {
            "raw_links": deduped,
            "pending_links": deduped,
            "summaries": []
        }

    def pick_next_link_node(self, state: TrackerState) -> dict:
        pending = list(state["pending_links"])

        if not pending:
            return {
                "current_url": None,
                "pending_links": []
            }

        return {
            "current_url": pending.pop(0),
            "pending_links": pending
        }

    async def summarizer_node(self, state: TrackerState) -> dict:
        url = state["current_url"]

        if url is None:
            return {}

        # Scrape
        try:
            print(f"[SUMMARIZER]: scraping {url}...")
            await self.browser.navigate.arun({"url": url})
            page_text = await self.browser.extract_text.arun({})
        except Exception as e:
            print(f"could not load page {url}: {e}")
            return {"summaries": []}

        # Summarize
        messages = [
            SystemMessage(content=self.prompts.summarizer),
            HumanMessage(content=f"URL: {url}\n\nText To Summarize: {page_text}"),
        ]

        summary = await self.browser.summarizer.ainvoke(messages)
        print("[SUMMARIZER]: Done.")
        return {"summaries": [summary.content]}

    def writer_node(self, state: TrackerState) -> dict:
        print("[WRITER]: Writing Report ...")
        summaries = state["summaries"]

        if not summaries:
            print("No Updates available")
            return {}

        heading      = f"# {state['source_name']} UPDATES\n\n"
        body         = "\n\n".join(summaries)
        final_report = heading + body
        print("[WRITER]: Report Done.")

        return {"final_report": final_report}

    async def email_node(self, state: TrackerState) -> dict:
        print("[EMAIL]: Sending Emails ...")
        if not state["final_report"]:
            print("[EMAIL]: Couldn't send emails. No Final_Report available.")
            return {"success": "no final report available."}

        messages = [
            SystemMessage(content=self.prompts.email),
            HumanMessage(content=f"Report: {state['final_report']}"),
        ]
        email_output = await self.emailer.llm.ainvoke(messages)
        self.emailer.send(email_output.subject, email_output.html_body)
        print("[EMAIL]: Emails Sent.")
        return {"success": "ok"}

    # ── Conditional edge ──────────────────────────────────────────────────────

    def has_pending_links(self, state: TrackerState) -> str:
        return "pick_next" if state["pending_links"] else "writer"