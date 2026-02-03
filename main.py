import os
import re
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup

RSS_FEEDS = {
    "openai": "https://openai.com/blog/rss.xml",
    "langchain": "https://changelog.langchain.com/feed",
    "google_ai": "https://research.google/blog/rss/",
    "aws_ai": "https://aws.amazon.com/blogs/aws/category/artificial-intelligence/feed/",
    "apache": "https://news.apache.org/feed",
    "databricks_apache": "https://www.databricks.com/feed"
}

GITHUB_FEEDS = {
    "langchain_github": "https://github.com/langchain-ai/langchain/releases.atom",
    "llamaindex_github": "https://github.com/run-llama/llama_index/releases.atom",
    "crewAI_github": "https://github.com/crewAIInc/crewAI/releases.atom",
    "openai_python": "https://github.com/openai/openai-python/releases.atom",
    "apache_spark": "https://github.com/apache/spark/releases.atom",
    "pyspark": "https://github.com/apache/spark/releases.atom",
}

FOLDER_PATH = "data"

def parse_date(entry):
    try:
        return datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d %H:%M")
    except:
        return entry.get("updated", "unknown")

def clean_html(html):
    if not html:
        return "No summary provided."

    soup = BeautifulSoup(html, "lxml")

    for tag in soup.find_all(["br", "p", "div", "li"]):
        tag.append("\n")

    text = soup.get_text()

    text = re.sub(r"\n\s*\n+", "\n", text)
    text = re.sub(r":\w+:", "", text)      # :rocket: emojis
    text = text.strip()

    if len(text) > 3000:
        text = text[:3000] + "\n... (truncated)"

    return text


def safe(text):
    return re.sub(r"[^\w\-]", "_", text)

def fetch_github_feed():
    new_path = os.path.join(FOLDER_PATH, "github_releases")
    if not os.path.exists(new_path):
        os.makedirs(new_path)
    today = datetime.now().strftime("%Y-%m-%d")

    for name, url in GITHUB_FEEDS.items():
        print(f"\nLoading feed: {name} → {url}")

        filename = f"{safe(name)}_{today}_news.txt"
        path = os.path.join(new_path, filename)

        feed = feedparser.parse(url)

        with open(path, "w", encoding="utf-8") as f:

            f.write(f"Feed Source: {name}\n")
            f.write(f"URL: {url}\n")
            f.write(f"Total Articles: {len(feed.entries)}\n")
            f.write("=" * 60 + "\n\n")

            for i, entry in enumerate(feed.entries, 1):

                summary = entry.get("summary") or \
                          entry.get("content", [{}])[0].get("value", "")

                f.write(f"--- Article {i} ---\n")
                f.write(f"Title: {entry.get('title')}\n")
                f.write(f"Link: {entry.get('link')}\n")
                f.write(f"Published: {parse_date(entry)}\n")

                f.write("Summary:\n")
                f.write(clean_html(summary))
                f.write("\n\n" + "-"*60 + "\n\n")

        print(f"Saved → {path}")

def fetch_rss_feed():
    new_path = os.path.join(FOLDER_PATH, "rss_articles")
    if not os.path.exists(new_path):
        os.makedirs(new_path)

    today = datetime.now().strftime("%Y-%m-%d")

    for name, url in RSS_FEEDS.items():
        print(f"\nLoading feed: {name} → {url}")

        filename = f"{name}_{today}_news.txt"
        path = os.path.join(new_path, filename)

        feed = feedparser.parse(url)

        with open(path, "w", encoding="utf-8") as f:

            f.write(f"Feed Source: {name}\n")
            f.write(f"URL: {url}\n")
            f.write(f"Total Articles: {len(feed.entries)}\n")
            f.write("=" * 60 + "\n\n")

            for i, entry in enumerate(feed.entries, 1):
                f.write(f"--- Article {i} ---\n")
                f.write(f"Title: {entry.get('title')}\n")
                f.write(f"Link: {entry.get('link')}\n")
                f.write(f"Published: {entry.get('updated')}\n")
                f.write(f"Summary:\n{entry.get('summary')}\n")
                f.write("\n" + "-"*60 + "\n\n")

if __name__ == "__main__":
    fetch_rss_feed()
    fetch_github_feed()