"""
Mintlify AI Assistant API Client

A Python client for interacting with Mintlify's AI assistant API.
Works with any documentation site using Mintlify's AI feature.

Example sites:
- docs.metronome.com
- docs.notte.cc
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Generator, Optional, List, Dict, Any
from dataclasses import dataclass, field
import requests


@dataclass
class Message:
    """Represents a message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to API format."""
        return {
            "id": self.id,
            "createdAt": self.created_at,
            "role": self.role,
            "content": self.content,
            "parts": [{"type": "text", "text": self.content}]
        }


@dataclass
class SearchResult:
    """Represents a search result from the AI's knowledge base."""
    content: str
    path: str
    title: str
    href: str


@dataclass
class AssistantResponse:
    """Represents the full response from the assistant."""
    content: str
    message_id: str
    search_results: List[SearchResult] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    usage: Optional[Dict[str, int]] = None


class MintlifyClient:
    """
    Client for interacting with Mintlify AI Assistant API.

    The API works by sending messages to Mintlify's backend which uses RAG
    (Retrieval Augmented Generation) to search the documentation and provide
    contextual answers.

    Attributes:
        subdomain: The Mintlify subdomain identifier (e.g., "metronome-b35a6a36")
        base_url: The documentation site URL (e.g., "https://docs.metronome.com")
        session: Requests session for HTTP calls
    """

    # Mintlify AI backend URL
    API_BASE = "https://leaves.mintlify.com/api/assistant"

    def __init__(
        self,
        docs_url: str,
        subdomain: Optional[str] = None,
        filter_groups: Optional[List[str]] = None,
        filter_version: Optional[str] = None,
    ):
        """
        Initialize the Mintlify client.

        Args:
            docs_url: The documentation site URL (e.g., "https://docs.metronome.com")
            subdomain: Optional Mintlify subdomain. If not provided, will be auto-detected.
            filter_groups: Optional list of content groups to filter (default: ["*"])
            filter_version: Optional version filter for the documentation
        """
        self.docs_url = docs_url.rstrip("/")
        self.subdomain = subdomain
        self.filter_groups = filter_groups or ["*"]
        self.filter_version = filter_version
        self.session = requests.Session()
        self.messages: List[Message] = []

        # Set default headers
        self.session.headers.update({
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": self.docs_url,
            "Referer": f"{self.docs_url}/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })

        # Auto-detect subdomain if not provided
        if not self.subdomain:
            self._detect_subdomain()

    def _detect_subdomain(self) -> None:
        """
        Auto-detect the Mintlify subdomain from the documentation site.

        The subdomain can be found in:
        1. The page source looking for mintlify configuration
        2. API calls to the site
        3. Asset URLs containing the subdomain
        """
        try:
            response = self.session.get(self.docs_url, timeout=15)
            response.raise_for_status()

            # Try to find subdomain in HTML/JS
            # Common patterns: "subdomain":"xxx" or mintlify-xxx or /xxx/ in asset paths
            patterns = [
                r'"subdomain"\s*:\s*"([a-zA-Z0-9-]+)"',
                r'mintlify-assets/_mintlify/favicons/([a-zA-Z0-9-]+)/',
                r'/api/assistant/([a-zA-Z0-9-]+)/',
                r'data-subdomain="([a-zA-Z0-9-]+)"',
            ]

            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    self.subdomain = match.group(1)
                    return

            # Try fetching a known endpoint that might reveal the subdomain
            # Check the mintlify asset path
            asset_match = re.search(r'/mintlify-assets/_mintlify/[^/]+/([a-zA-Z0-9-]+)/', response.text)
            if asset_match:
                self.subdomain = asset_match.group(1)
                return

            raise ValueError("Could not auto-detect Mintlify subdomain. Please provide it manually.")

        except requests.RequestException as e:
            raise ValueError(f"Failed to detect subdomain: {e}")

    def _get_api_url(self) -> str:
        """Get the full API URL for the message endpoint."""
        return f"{self.API_BASE}/{self.subdomain}/message"

    def _build_request_body(self, current_path: str = "/") -> Dict[str, Any]:
        """Build the request body for the API call."""
        body = {
            "id": self.subdomain,
            "messages": [msg.to_dict() for msg in self.messages],
            "fp": self.subdomain,
            "filter": {
                "groups": self.filter_groups,
            },
            "currentPath": current_path,
        }

        if self.filter_version:
            body["filter"]["version"] = self.filter_version

        return body

    def _parse_stream_line(self, line: str) -> tuple[str, Any]:
        """
        Parse a line from the Vercel AI Data Stream.

        Format: TYPE:DATA
        Types:
            f: Message metadata (messageId)
            9: Tool invocation start
            a: Tool result
            e: Usage stats
            0: Text chunk

        Returns:
            Tuple of (type, parsed_data)
        """
        if not line or ":" not in line:
            return ("", None)

        type_char = line[0]
        # Skip the type char and colon
        data = line[2:]

        try:
            if type_char in ("f", "9", "a", "e"):
                return (type_char, json.loads(data))
            elif type_char == "0":
                # Text chunk - it's a JSON string
                return (type_char, json.loads(data))
            else:
                return (type_char, data)
        except json.JSONDecodeError:
            return (type_char, data)

    def ask(
        self,
        question: str,
        current_path: str = "/",
        stream: bool = False,
    ) -> AssistantResponse | Generator[str, None, AssistantResponse]:
        """
        Ask a question to the Mintlify AI assistant.

        Args:
            question: The question to ask
            current_path: Current documentation page path (for context)
            stream: If True, yields text chunks as they arrive

        Returns:
            If stream=False: AssistantResponse with full response
            If stream=True: Generator yielding text chunks, returns AssistantResponse
        """
        # Add user message
        user_message = Message(role="user", content=question)
        self.messages.append(user_message)

        # Build request
        body = self._build_request_body(current_path)

        # Make request with streaming
        response = self.session.post(
            self._get_api_url(),
            json=body,
            stream=True,
            timeout=30,
        )
        response.raise_for_status()

        if stream:
            return self._process_stream_generator(response)
        else:
            return self._process_stream(response)

    def _process_stream(self, response: requests.Response) -> AssistantResponse:
        """Process the stream and return the complete response."""
        text_parts = []
        message_id = ""
        search_results = []
        usage = None

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            type_char, data = self._parse_stream_line(line)

            if type_char == "f" and isinstance(data, dict):
                message_id = data.get("messageId", "")
            elif type_char == "0" and data:
                text_parts.append(data)
            elif type_char == "a" and isinstance(data, dict):
                # Tool result (search results)
                result = data.get("result", {})
                if result.get("type") == "search":
                    for r in result.get("results", []):
                        search_results.append(SearchResult(
                            content=r.get("content", ""),
                            path=r.get("path", ""),
                            title=r.get("metadata", {}).get("title", ""),
                            href=r.get("metadata", {}).get("href", ""),
                        ))
            elif type_char == "e" and isinstance(data, dict):
                usage = data.get("usage")

        content = "".join(text_parts)

        # Parse suggestions from content (```suggestions block)
        suggestions = []
        suggestion_match = re.search(r"```suggestions\n(.*?)\n```", content, re.DOTALL)
        if suggestion_match:
            for line in suggestion_match.group(1).strip().split("\n"):
                # Format: (Title)[/path]
                title_match = re.match(r"\(([^)]+)\)\[([^\]]+)\]", line.strip())
                if title_match:
                    suggestions.append(title_match.group(2))
            # Remove suggestions block from content
            content = re.sub(r"\n*```suggestions\n.*?\n```\n*", "", content, flags=re.DOTALL)

        # Add assistant message to history
        assistant_message = Message(
            role="assistant",
            content=content,
            id=message_id or uuid.uuid4().hex[:16],
        )
        self.messages.append(assistant_message)

        return AssistantResponse(
            content=content.strip(),
            message_id=message_id,
            search_results=search_results,
            suggestions=suggestions,
            usage=usage,
        )

    def _process_stream_generator(
        self, response: requests.Response
    ) -> Generator[str, None, AssistantResponse]:
        """Process the stream and yield text chunks."""
        text_parts = []
        message_id = ""
        search_results = []
        usage = None

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            type_char, data = self._parse_stream_line(line)

            if type_char == "f" and isinstance(data, dict):
                message_id = data.get("messageId", "")
            elif type_char == "0" and data:
                text_parts.append(data)
                yield data
            elif type_char == "a" and isinstance(data, dict):
                result = data.get("result", {})
                if result.get("type") == "search":
                    for r in result.get("results", []):
                        search_results.append(SearchResult(
                            content=r.get("content", ""),
                            path=r.get("path", ""),
                            title=r.get("metadata", {}).get("title", ""),
                            href=r.get("metadata", {}).get("href", ""),
                        ))
            elif type_char == "e" and isinstance(data, dict):
                usage = data.get("usage")

        content = "".join(text_parts)

        # Parse suggestions
        suggestions = []
        suggestion_match = re.search(r"```suggestions\n(.*?)\n```", content, re.DOTALL)
        if suggestion_match:
            for line in suggestion_match.group(1).strip().split("\n"):
                title_match = re.match(r"\(([^)]+)\)\[([^\]]+)\]", line.strip())
                if title_match:
                    suggestions.append(title_match.group(2))
            content = re.sub(r"\n*```suggestions\n.*?\n```\n*", "", content, flags=re.DOTALL)

        # Add assistant message to history
        assistant_message = Message(
            role="assistant",
            content=content,
            id=message_id or uuid.uuid4().hex[:16],
        )
        self.messages.append(assistant_message)

        return AssistantResponse(
            content=content.strip(),
            message_id=message_id,
            search_results=search_results,
            suggestions=suggestions,
            usage=usage,
        )

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.messages = []

    def get_history(self) -> List[Message]:
        """Get the conversation history."""
        return self.messages.copy()


def create_client(docs_url: str, **kwargs) -> MintlifyClient:
    """
    Factory function to create a MintlifyClient.

    Args:
        docs_url: The documentation site URL
        **kwargs: Additional arguments passed to MintlifyClient

    Returns:
        Configured MintlifyClient instance
    """
    return MintlifyClient(docs_url, **kwargs)


# Convenience function for quick queries
def ask(docs_url: str, question: str, **kwargs) -> AssistantResponse:
    """
    Quick function to ask a single question without managing client state.

    Args:
        docs_url: The documentation site URL
        question: The question to ask
        **kwargs: Additional arguments passed to MintlifyClient

    Returns:
        AssistantResponse with the answer
    """
    client = create_client(docs_url, **kwargs)
    return client.ask(question)


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Mintlify AI Assistant API Client - Demo")
    print("=" * 60)

    # Test with Metronome docs
    print("\n[Test 1] Testing with docs.metronome.com...")
    print("-" * 40)

    try:
        client = MintlifyClient("https://docs.metronome.com")
        print(f"Detected subdomain: {client.subdomain}")

        response = client.ask("What is Metronome?")
        print(f"\nQuestion: What is Metronome?")
        print(f"\nAnswer:\n{response.content[:500]}...")
        print(f"\nSearch results: {len(response.search_results)} documents")
        print(f"Suggestions: {response.suggestions}")
        if response.usage:
            print(f"Token usage: {response.usage}")
        print("\n[SUCCESS] Metronome test passed!")

    except Exception as e:
        print(f"[ERROR] Metronome test failed: {e}")
        sys.exit(1)

    # Test with Notte docs
    print("\n" + "=" * 60)
    print("\n[Test 2] Testing with docs.notte.cc...")
    print("-" * 40)

    try:
        client2 = MintlifyClient("https://docs.notte.cc")
        print(f"Detected subdomain: {client2.subdomain}")

        response2 = client2.ask("What is Notte?")
        print(f"\nQuestion: What is Notte?")
        print(f"\nAnswer:\n{response2.content[:500]}...")
        print(f"\nSearch results: {len(response2.search_results)} documents")
        if response2.usage:
            print(f"Token usage: {response2.usage}")
        print("\n[SUCCESS] Notte test passed!")

    except Exception as e:
        print(f"[ERROR] Notte test failed: {e}")
        sys.exit(1)

    # Test streaming
    print("\n" + "=" * 60)
    print("\n[Test 3] Testing streaming response...")
    print("-" * 40)

    try:
        client3 = MintlifyClient("https://docs.metronome.com")
        print("Streaming response: ", end="", flush=True)

        generator = client3.ask("What is a billable metric?", stream=True)
        chunk_count = 0
        for chunk in generator:
            chunk_count += 1
            if chunk_count <= 10:  # Print first 10 chunks
                print(chunk, end="", flush=True)

        print(f"...\n\n[Received {chunk_count} chunks]")
        print("\n[SUCCESS] Streaming test passed!")

    except Exception as e:
        print(f"\n[ERROR] Streaming test failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("All tests passed successfully!")
    print("=" * 60)
