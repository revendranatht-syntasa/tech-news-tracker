"""Configuration classes for the news pipeline."""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class FeedConfig:
    """Configuration for RSS feeds."""

    rss_feeds: Dict[str, str] = field(default_factory=lambda: {
        "openai": "https://openai.com/blog/rss.xml",
        # "langchain": "https://changelog.langchain.com/feed",
        # "google_ai": "https://research.google/blog/rss/",
        # "aws_ai": "https://aws.amazon.com/blogs/aws/category/artificial-intelligence/feed/",
        # "apache": "https://news.apache.org/feed",
        # "databricks_apache": "https://www.databricks.com/feed"
    })


@dataclass
class AppConfig:
    """Main application configuration."""

    feeds: FeedConfig = field(default_factory=FeedConfig)

    @classmethod
    def create_default(cls) -> "AppConfig":
        """Create default configuration."""
        return cls()