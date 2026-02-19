import operator
from typing import Annotated, TypedDict, List, Optional

from pydantic import BaseModel, Field


class ArticleSummary(BaseModel):
    title: str      = Field(description="The headline or title of the news article")
    source_url: str = Field(description="The original URL of the article")
    summary: str    = Field(description="A concise summary of the article in 3 to 5 concise bullet points")


class TrackerState(TypedDict):
    source_name: str
    feed_urls:   List[str]

    # Feed fetcher output
    raw_links:   List[str]

    # Per-link processing queue
    pending_links:   List[str]
    current_url:     Optional[str]

    # Accumulated results
    summaries:       Annotated[List[ArticleSummary], operator.add]
    current_text: str

    # Final output
    final_report:    Optional[str]


class EmailOutput(BaseModel):
    subject: str
    """The subject line for the email. """

    html_body: str
    """Nicely formatted HTML body for the email. """