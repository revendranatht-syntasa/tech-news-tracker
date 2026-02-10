"""RSS feed processing utilities."""

import re
from datetime import datetime
from typing import List, Dict
from pathlib import Path

import feedparser
from langchain_core.documents import Document

from .utils import DataUtils


class FeedProcessor:
    """Handle RSS feed processing and document conversion."""

    @staticmethod
    def safe_filename(text: str) -> str:
        """
        Create safe filename from text.

        Args:
            text: Input text

        Returns:
            Sanitized filename
        """
        return re.sub(r"[^\w\-]", "_", text)

    @staticmethod
    def parse_date(entry) -> str:
        """
        Parse date from feed entry.

        Args:
            entry: Feed entry object

        Returns:
            Formatted date string
        """
        try:
            return datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d %H:%M")
        except:
            return entry.get("updated", "unknown")

    @staticmethod
    def process_feed_entries(feed, feed_name: str, feed_url: str) -> List[Document]:
        """
        Convert feed entries to LangChain Documents.

        Args:
            feed: Parsed feed object
            feed_name: Name of the feed
            feed_url: URL of the feed

        Returns:
            List of LangChain Document objects
        """
        documents = []

        for i, entry in enumerate(feed.entries, 1):
            # Extract summary
            summary = entry.get("summary") or \
                      entry.get("content", [{}])[0].get("value", "")

            cleaned_summary = DataUtils.clean_html(summary)

            # Create metadata
            metadata = {
                "source": feed_name,
                "feed_url": feed_url,
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "published": FeedProcessor.parse_date(entry),
                "article_number": i
            }

            # Create Document
            doc = Document(
                page_content=cleaned_summary,
                metadata=metadata
            )
            documents.append(doc)

        return documents

    @staticmethod
    def save_documents_to_file(
        documents: List[Document],
        filepath: Path,
        feed_name: str,
        feed_url: str
    ):
        """
        Save LangChain documents to text file.

        Args:
            documents: List of documents to save
            filepath: Output file path
            feed_name: Name of the feed
            feed_url: URL of the feed
        """
        with open(filepath, "w", encoding="utf-8") as f:
            # Header
            f.write(f"Feed Source: {feed_name}\n")
            f.write(f"URL: {feed_url}\n")
            f.write(f"Total Articles: {len(documents)}\n")
            f.write("=" * 60 + "\n\n")

            # Write each document
            for doc in documents:
                f.write(f"--- Article {doc.metadata['article_number']} ---\n")
                f.write(f"Title: {doc.metadata['title']}\n")
                f.write(f"Link: {doc.metadata['link']}\n")
                f.write(f"Published: {doc.metadata['published']}\n")
                f.write("Summary:\n")
                f.write(doc.page_content)
                f.write("\n\n" + "-" * 60 + "\n\n")

    @staticmethod
    def fetch_github_releases(feeds: Dict[str, str], output_dir: Path) -> List[Document]:
        """
        Fetch GitHub release feeds.

        Args:
            feeds: Dictionary of feed names to URLs
            output_dir: Directory to save output files

        Returns:
            List of all documents
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")

        all_documents = []

        for name, url in feeds.items():
            print(f"\n📦 Loading GitHub feed: {name} → {url}")

            try:
                # Parse feed
                feed = feedparser.parse(url)

                if not feed.entries:
                    print(f"⚠️  No entries found for {name}")
                    continue

                # Process entries into documents
                documents = FeedProcessor.process_feed_entries(feed, name, url)
                all_documents.extend(documents)

                # Save to file
                filename = f"{FeedProcessor.safe_filename(name)}_{today}_news.txt"
                filepath = output_dir / filename
                FeedProcessor.save_documents_to_file(documents, filepath, name, url)

                print(f"✅ Saved {len(documents)} releases → {filepath}")

            except Exception as e:
                print(f"❌ Error processing {name}: {e}")

        return all_documents

    @staticmethod
    def fetch_rss_articles(name: str, url: str) -> List[Document]:
        """
        Fetch RSS articles from a single feed.

        Args:
            name: Feed name
            url: Feed URL

        Returns:
            List of documents
        """
        print(f"\n Loading RSS feed: {name} → {url}")

        try:
            # Parse feed
            feed = feedparser.parse(url)

            if not feed.entries:
                return []

            # Process entries into documents
            documents = FeedProcessor.process_feed_entries(feed, name, url)
            return documents

        except Exception as e:
            print(f"❌ Error processing {name}: {e}")
            return []