from dataclasses import dataclass


@dataclass
class Prompts:
    scraper: str = """Get the content of the URL from the tools you are provided. No summarizing — just extract the text. """

    evaluator: str = """
        You are a quality gate for a technical news pipeline.

        The team is senior Python engineers on GCP using the OpenAI Assistants API, Chat Completions API, and openai-python SDK for RAG pipelines, multi-agent orchestration, function calling, and structured outputs.

        Hard discard: DALL-E, Sora, ChatGPT consumer app, mobile SDKs, pricing changes, enterprise sales.

        For each update: discard if it matches an irrelevance signal, doesn't relate to the team's stack, or lacks specific technical detail.

        Mark is_sufficient=True only if 3+ HIGH/MEDIUM updates remain and every summary contains a specific technical detail (param, endpoint, version, or date). If not, provide a precise insufficiency_reason and 2-3 targeted suggested_search_queries."""

    summarizer: str = """You are summarizing an update for a senior Python team on GCP.
        Skip anything about: pricing changes, enterprise sales, marketing content.

        Given the page content, return cleanly written markdown:
        - exact title of the update (should be a heading).
        - Next line should be the exact source URL you were provided inside square brackets '[]'. For example if the url was https://dasd.com then the link should be presented as [https://dasd.com] in the next line.
        - summary: 3 sentences — (1) what changed, (2) team impact, (3) action needed. Must include a specific technical detail. should be in bullet points. should be in markdown.

        Make sure there is no other accompanying text other than the ones mentioned above."""

    email: str = """
        Given a markdown report, You are able to come up with a succinct, to the point subject line and a nice formatted HTML body for the report to be meant to send emails.
        """