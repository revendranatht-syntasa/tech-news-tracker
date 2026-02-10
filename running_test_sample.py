# from langchain_community.document_loaders import WebBaseLoader
from attrs import field
from langchain_community.document_loaders import PlaywrightURLLoader
# from langchain_community.document_loaders import SeleniumURLLoader
from bs4 import BeautifulSoup

from dotenv import load_dotenv
import os
from openai import OpenAI

# loader = WebBaseLoader("https://openai.com/index/sora-feed-philosophy/")
# docs = loader.load()

# loader = PlaywrightURLLoader(
#     urls=["https://openai.com/index/sora-feed-philosophy/"],
#     headless=False
# )

# loader = SeleniumURLLoader( urls=["https://openai.com/index/sora-feed-philosophy/"], browser="chrome", headless=False)

# docs = loader.load()

from playwright.sync_api import sync_playwright
import re
from datetime import datetime

# vector database of the article content for semantic search later
from langchain_core.documents import Document
from langchain_community.document_loaders import RSSFeedLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path
import feedparser

class FeedProcessor:

    @staticmethod
    def safe_filename(text: str) -> str:
        """Create safe filename from text"""
        return re.sub(r"[^\w\-]", "_", text)

    @staticmethod
    def parse_date(entry) -> str:
        """Parse date from feed entry"""
        try:
            return datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d %H:%M")
        except:
            return entry.get("updated", "unknown")

    @staticmethod
    def process_feed_entries(feed, feed_name: str, feed_url: str) -> List[Document]:
        """Convert feed entries to LangChain Documents"""
        documents = []

        for i, entry in enumerate(feed.entries, 1):
            # Extract summary
            summary = entry.get("summary") or \
                      entry.get("content", [{}])[0].get("value", "")

            cleaned_summary = DataUtils.clean_html(summary)

            # Truncate if too long
            # if len(cleaned_summary) > self.max_summary_length:
            #     cleaned_summary = cleaned_summary[:self.max_summary_length] + "\n... (truncated)"

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

    def save_documents_to_file(
        self,
        documents: List[Document],
        filepath: Path,
        feed_name: str,
        feed_url: str
    ):
        """Save LangChain documents to text file"""
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

    def fetch_github_releases(self, feeds: Dict[str, str], output_dir: Path):
        """Fetch GitHub release feeds"""
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
                documents = self.process_feed_entries(feed, name, url)
                all_documents.extend(documents)

                # Save to file
                filename = f"{self.safe_filename(name)}_{today}_news.txt"
                filepath = output_dir / filename
                self.save_documents_to_file(documents, filepath, name, url)

                print(f"✅ Saved {len(documents)} releases → {filepath}")

            except Exception as e:
                print(f"❌ Error processing {name}: {e}")

        return all_documents

    @staticmethod
    def fetch_rss_articles(name, url) -> List[Document]:
        # today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n Loading RSS feed: {name} → {url}")

        try:
            # Parse feed
            feed = feedparser.parse(url)

            if not feed.entries:
                return []

            # Process entries into documents
            documents = FeedProcessor.process_feed_entries(feed, name, url)
            return documents

            # Save to file
            # filename = f"{name}_{today}_news.txt"
            # filepath = output_dir / filename
            # self.save_documents_to_file(documents, filepath, name, url)
            # print(f"✅ Saved {len(documents)} articles → {filepath}")

        except Exception as e:
            print(f"❌ Error processing {name}: {e}")
            return []


class DataUtils:

    @staticmethod
    def extract_core_article(html: str):
        soup = BeautifulSoup(html, "html.parser")

        result = {
            "title": None,
            "author": None,
            "date": None,
            "body": None,
        }

        # 1) TITLE
        if soup.title:
            result["title"] = soup.title.get_text(strip=True)

        # Meta title fallback
        og_title = soup.find("meta", {"property": "og:title"})
        if not result["title"] and og_title:
            result["title"] = og_title.get("content")

        # 2) AUTHOR
        author_meta = soup.find("meta", {"name": "author"}) or \
                    soup.find("meta", {"property": "article:author"})

        if author_meta:
            result["author"] = author_meta.get("content")

        # Look for visible author text
        if not result["author"]:
            author_el = soup.find(attrs={"class": re.compile("author", re.I)})
            if author_el:
                result["author"] = author_el.get_text(strip=True)

        # 3) DATE
        date_meta = (
            soup.find("meta", {"property": "article:published_time"}) or
            soup.find("meta", {"name": "date"})
        )

        if date_meta:
            result["date"] = date_meta.get("content")

        # Fallback: search for YYYY-MM-DD
        if not result["date"]:
            text = soup.get_text(" ", strip=True)
            m = re.search(r"\d{4}-\d{2}-\d{2}", text)
            if m:
                result["date"] = m.group(0)

        # 4) BODY TEXT

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        article = (
            soup.find("article") or
            soup.find("main") or
            soup.find("div", {"class": re.compile("content|article|post|body", re.I)})
        )

        source = article if article else soup

        text = source.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)

        result["body"] = text

        return result

    @staticmethod
    def clean_html(html: str) -> str:
        """Clean HTML content and extract text"""
        if not html:
            return "No summary provided."

        soup = BeautifulSoup(html, "lxml")

        # Add newlines for better formatting
        for tag in soup.find_all(["br", "p", "div", "li"]):
            tag.append("\n")

        text = soup.get_text()

        # Clean up whitespace and emoji codes
        text = re.sub(r"\n\s*\n+", "\n", text)
        text = re.sub(r":\w+:", "", text)  # Remove :rocket: style emojis
        text = text.strip()

        return text


    @staticmethod
    def scrape_site(url):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto(url)
            result = page.content()
            # soup = BeautifulSoup(content, "lxml")

            # text = soup.get_text()
            browser.close()
        return result

    @staticmethod
    def fetch_and_parse(url: str):
        html = DataUtils.scrape_site(url)
        data = DataUtils.extract_core_article(html)
        return data

# =======================================================================================================

class VectorDBManager:
    def __init__(
        self,
        persist_directory: str = "chroma_db",
        collection_name: str = "summaries",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        # Initialize embeddings once
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model
        )

        # Initialize DB
        self.db = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings,
            collection_name=collection_name
        )

    def add_document(self, doc: Document):
        doc_id = doc.metadata.get("source_url")

        self.db.add_documents(
            [doc],
            ids=[doc_id]
        )

    def search(self, query: str, k=3):
        return self.db.similarity_search(query, k=k)

    def search_with_threshold(self, query, k=5, threshold=0.1):
        results = self.db.similarity_search_with_score(query, k=k)
        docs = []
        for doc, score in results:
            # print(f"Score: {score:.4f} - Title: {doc.metadata.get('title')}")
            if score <= threshold:
                docs.append(doc)
        return docs

    def delete_all(self):
        self.db.delete_collection()

@dataclass
class FeedConfig:
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
    feeds: FeedConfig = field(default_factory=FeedConfig)

    @classmethod
    def create_default(cls) -> "AppConfig":
        return cls()

class NewsPipeline:
    def __init__(self, config: AppConfig):
        load_dotenv()
        self.config = config

        self.client = OpenAI(api_key=os.getenv("GROQ_API_KEY"),
                             base_url="https://api.groq.com/openai/v1")

        self.vector_dbs: dict[str, VectorDBManager] = {}
        for feed_name in config.feeds.rss_feeds.keys():
            db_path = Path(".cache") / "vector_dbs" / feed_name
            self.vector_dbs[feed_name] = VectorDBManager(
                persist_directory=db_path,
                collection_name=feed_name
            )

    def run(self, query: str):
        # 1) Ingest feeds
        self._ingest_feeds()

        for feed_name in self.config.feeds.rss_feeds.keys():
            print(f"\nSearching in feed '{feed_name}' for query: '{query}'")
            results = self.vector_dbs[feed_name].search_with_threshold(query, k=5, threshold=1.4)

            # TODO: Store this result in a txt file(corresponding to the feed_name here) for later use instead of printing
            for doc in results:
                summary = self._summarize_text(doc.page_content)
                print(f"Title: {doc.metadata.get('title')}")
                print(f"Author: {doc.metadata.get('author')}")
                print(f"Date: {doc.metadata.get('date')}")
                print(f"URL: {doc.metadata.get('source_url')}")
                print(f"Summary: {summary}")
                print("-" * 80)

    def _ingest_feeds(self):
        for feed_name, url in self.config.feeds.rss_feeds.items():

            docs = FeedProcessor.fetch_rss_articles(feed_name, url)

            ## TODO:: REMOVE after testing
            count = 0
            max=5

            for doc in docs:
                url = doc.metadata.get("link")
                self._process_url(feed_name, url)

                count += 1
                if count >= max:
                    break

    def _process_url(self, feed_name: str, url: str):
            data = DataUtils.fetch_and_parse(url)

            # summary = summarize_text(data["body"])
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

    def _summarize_text(self, text):
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

    def search_single_source(self, feed_name: str, query: str, k=20, threshold=1.4):
        return self.vector_dbs[feed_name].search_with_threshold(query, k, threshold)

    def search_all_sources(self, query: str, k=100, threshold=1.4):
        results = []
        for feed_name, db in self.vector_dbs.items():
            docs = db.search_with_threshold(query, k, threshold)

            for doc in docs:
                doc.metadata["feed"] = feed_name
                results.append(doc)
        return results


config = AppConfig.create_default()
pipeline = NewsPipeline(config)
results = pipeline.run("openai")

# pipeline("https://openai.com/index/sora-feed-philosophy/")
# pipeline("https://research.google/blog/sequential-attention-making-ai-models-leaner-and-faster-without-sacrificing-accuracy/")
# pipeline("https://aws.amazon.com/blogs/aws/improve-model-accuracy-with-reinforcement-fine-tuning-in-amazon-bedrock/")

# query = "amazon aws"
# print(f"Search results for {query}...:\n")
# search_result = vectordb.search_with_threshold(query, 3, threshold=1.4)
# for doc in search_result:
#     print(f"Title: {doc.metadata.get('title')}")
#     print(f"Author: {doc.metadata.get('author')}")
#     print(f"Date: {doc.metadata.get('date')}")
#     print(f"URL: {doc.metadata.get('source_url')}")
#     print(f"Summary: {doc.page_content}")  # Print first 500 chars
#     print("-" * 80)
