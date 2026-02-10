"""Main news pipeline orchestration."""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.documents import Document

from .config import AppConfig
from .feed_processor import FeedProcessor
from .utils import DataUtils
from .vector_db import VectorDBManager


class NewsPipeline:
    """Orchestrate news feed ingestion, processing, and semantic search."""

    def __init__(self, config: AppConfig):
        """
        Initialize the news pipeline.

        Args:
            config: Application configuration
        """
        load_dotenv()
        self.config = config

        # Initialize LLM client
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

        # Initialize vector databases for each feed
        self.vector_dbs: dict[str, VectorDBManager] = {}
        for feed_name in config.feeds.rss_feeds.keys():
            db_path = Path(".cache") / "vector_dbs" / feed_name
            self.vector_dbs[feed_name] = VectorDBManager(
                persist_directory=str(db_path),
                collection_name=feed_name
            )

    def run(self, query: str):
        """
        Run the complete pipeline: ingest feeds and search.

        Args:
            query: Search query
        """
        # 1) Ingest feeds
        self._ingest_feeds()

        # 2) Search across all feeds
        for feed_name in self.config.feeds.rss_feeds.keys():
            print(f"\nSearching in feed '{feed_name}' for query: '{query}'")
            results = self.vector_dbs[feed_name].search_with_threshold(
                query, k=5, threshold=1.4
            )

            if not results:
                print("No relevant articles found.")
                continue

            # Display results
            for doc in results:
                summary = self._summarize_text(doc.page_content)
                print(f"Title: {doc.metadata.get('title')}")
                print(f"Author: {doc.metadata.get('author')}")
                print(f"Date: {doc.metadata.get('date')}")
                print(f"URL: {doc.metadata.get('source_url')}")
                print(f"Summary: {summary}")
                print("-" * 80)

    def _ingest_feeds(self):
        """Ingest all configured RSS feeds."""
        for feed_name, url in self.config.feeds.rss_feeds.items():
            docs = FeedProcessor.fetch_rss_articles(feed_name, url)

            # TODO: REMOVE after testing
            count = 0
            max_articles = 5

            for doc in docs:
                url = doc.metadata.get("link")
                self._process_url(feed_name, url)

                count += 1
                if count >= max_articles:
                    break

    def _process_url(self, feed_name: str, url: str):
        """
        Process a single URL and add to vector database.

        Args:
            feed_name: Name of the feed
            url: URL to process
        """
        data = DataUtils.fetch_and_parse(url)

        doc = Document(
            page_content=data["body"],
            metadata={
                "title": data["title"],
                "author": data["author"],
                "date": data["date"],
                "source_url": url
            }
        )

        self.vector_dbs[feed_name].add_document(doc)

    def _summarize_text(self, text: str) -> str:
        """
        Summarize text using LLM.

        Args:
            text: Text to summarize

        Returns:
            Summary text
        """
        prompt = f"""
        Summarize the following text concisely while keeping key points. Keep the summary under 100 words with bullet points.
        Focus on the main ideas and avoid minor details:

        {text}
        """

        response = self.client.responses.create(
            input=prompt,
            model="openai/gpt-oss-20b"
        )

        return response.output_text

    def search_single_source(
        self,
        feed_name: str,
        query: str,
        k: int = 20,
        threshold: float = 1.4
    ) -> List[Document]:
        """
        Search within a single feed source.

        Args:
            feed_name: Name of the feed to search
            query: Search query
            k: Number of results
            threshold: Similarity threshold

        Returns:
            List of matching documents
        """
        return self.vector_dbs[feed_name].search_with_threshold(query, k, threshold)

    def search_all_sources(
        self,
        query: str,
        k: int = 100,
        threshold: float = 1.4
    ) -> List[Document]:
        """
        Search across all feed sources.

        Args:
            query: Search query
            k: Number of results per source
            threshold: Similarity threshold

        Returns:
            List of matching documents from all sources
        """
        results = []
        for feed_name, db in self.vector_dbs.items():
            docs = db.search_with_threshold(query, k, threshold)

            for doc in docs:
                doc.metadata["feed"] = feed_name
                results.append(doc)
        return results