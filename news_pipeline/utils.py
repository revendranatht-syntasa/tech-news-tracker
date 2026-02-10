"""Utility functions for data processing and web scraping."""

import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


class DataUtils:
    """Utilities for HTML parsing and text extraction."""

    @staticmethod
    def extract_core_article(html: str) -> dict:
        """
        Extract core article components from HTML.

        Args:
            html: Raw HTML content

        Returns:
            Dictionary containing title, author, date, and body text
        """
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
        """
        Clean HTML content and extract text.

        Args:
            html: Raw HTML string

        Returns:
            Cleaned text content
        """
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
    def scrape_site(url: str) -> str:
        """
        Scrape website content using Playwright.

        Args:
            url: URL to scrape

        Returns:
            Raw HTML content
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto(url)
            result = page.content()
            browser.close()
        return result

    @staticmethod
    def fetch_and_parse(url: str) -> dict:
        """
        Fetch and parse article from URL.

        Args:
            url: URL to fetch and parse

        Returns:
            Parsed article data
        """
        html = DataUtils.scrape_site(url)
        data = DataUtils.extract_core_article(html)
        return data