import os

import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
import asyncio

from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser

from .config import TrackerConfig
from .models import EmailOutput


class BrowserAgent:
    """Wraps the Playwright browser and exposes navigate + extract tools."""

    def __init__(self) -> None:
        self._browser      = create_async_playwright_browser(headless=False)
        toolkit            = PlayWrightBrowserToolkit.from_browser(async_browser=self._browser)
        tools              = toolkit.get_tools()
        tool_dict          = {tool.name: tool for tool in tools}
        self.navigate      = tool_dict.get("navigate_browser")
        self.extract_text  = tool_dict.get("extract_text")
        self.summarizer    = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async def close(self) -> None:
        """Close the Playwright browser if it is open."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        await asyncio.sleep(0.25)
        print("[BROWSER]: Closed.")

    async def __aenter__(self) -> "BrowserAgent":
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


class EmailAgent:
    """Wraps the LLM that formats emails and the SendGrid sender."""

    def __init__(self, config: TrackerConfig) -> None:
        self.config = config
        _llm        = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.llm    = _llm.with_structured_output(EmailOutput)

    def send(self, subject: str, html_body: str) -> bool:
        """ Send out an email with the given subject and HTML body. """
        try:
            sg         = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))
            from_email = Email(self.config.from_email)
            to_emails  = [To(email) for email in self.config.email_recipients]
            content    = Content("text/html", html_body)
            mail       = Mail(from_email, to_emails, subject, content).get()
            sg.client.mail.send.post(request_body=mail)
            return True
        except Exception as e:
            print(f"error: {e}")
            return False