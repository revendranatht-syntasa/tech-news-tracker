from dataclasses import dataclass, field
from typing import List


@dataclass
class TrackerConfig:
    sources: dict[str, list[str]] = field(default_factory=lambda: {
        "OpenAI": [
            "https://openai.com/news/rss.xml",
        ],
    })

    email_recipients: List[str] = field(default_factory=lambda: [
        "mohnish.unity3d.dev@gmail.com",
        "h33t92@gmail.com",
    ])

    from_email: str = "mani.gamed3v@gmail.com"
    cache_path: str = ".cached/cache.json"
    fallback_lookback_days: int = 10