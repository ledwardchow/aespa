from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Site / Credential ─────────────────────────────────────────────────────────

class Site(SQLModel, table=True):
    __tablename__ = "site"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    base_url: str
    requires_auth: bool = Field(default=False)
    login_url: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    credentials: List["Credential"] = Relationship(
        back_populates="site",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Credential(SQLModel, table=True):
    __tablename__ = "credential"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: int = Field(foreign_key="site.id", index=True)
    username: str
    password: str  # plaintext — local pentesting tool
    label: Optional[str] = Field(default=None)

    site: Optional[Site] = Relationship(back_populates="credentials")


# ── LLM config ────────────────────────────────────────────────────────────────

class LLMProvider(str, Enum):
    anthropic = "anthropic"
    openai = "openai"
    openai_compatible = "openai_compatible"


class LLMConfig(SQLModel, table=True):
    """Singleton row (id always = 1)."""

    __tablename__ = "llm_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(default=LLMProvider.anthropic)
    api_key: Optional[str] = Field(default=None)
    base_url: Optional[str] = Field(default=None)
    model: str = Field(default="claude-opus-4-5")
    max_tokens: int = Field(default=4096)
    temperature: float = Field(default=0.0)
    # Whether to include page screenshots in LLM prompts (requires vision model)
    use_vision: bool = Field(default=False)
    updated_at: datetime = Field(default_factory=_utcnow)


# ── Test runs ─────────────────────────────────────────────────────────────────

class TestRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"
    stopped = "stopped"


class TestRun(SQLModel, table=True):
    __tablename__ = "test_run"

    id: Optional[int] = Field(default=None, primary_key=True)
    site_id: int = Field(foreign_key="site.id", index=True)
    name: str
    status: str = Field(default=TestRunStatus.pending)
    # Crawl config
    use_screenshots: bool = Field(default=False)
    max_depth: int = Field(default=3)
    max_pages: int = Field(default=50)
    # Progress
    pages_discovered: int = Field(default=0)
    current_url: Optional[str] = Field(default=None)
    # Timestamps
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class CrawledPage(SQLModel, table=True):
    __tablename__ = "crawled_page"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    url: str = Field(index=True)
    title: Optional[str] = Field(default=None)
    page_text: Optional[str] = Field(default=None)   # truncated ~10k chars
    screenshot_b64: Optional[str] = Field(default=None)
    llm_context: Optional[str] = Field(default=None)
    depth: int = Field(default=0)
    status: str = Field(default="crawled")            # crawled | failed
    error_message: Optional[str] = Field(default=None)
    in_scope: bool = Field(default=True)
    discovered_at: datetime = Field(default_factory=_utcnow)


class PageLink(SQLModel, table=True):
    """Directed edge in the crawl graph: source page → target page."""

    __tablename__ = "page_link"

    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="test_run.id", index=True)
    source_page_id: int = Field(foreign_key="crawled_page.id", index=True)
    target_page_id: Optional[int] = Field(default=None, foreign_key="crawled_page.id")
    target_url: str
    link_text: Optional[str] = Field(default=None)
