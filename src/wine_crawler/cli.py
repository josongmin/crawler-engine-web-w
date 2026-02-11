"""CLI for wine-crawler."""

from __future__ import annotations

# pyright: reportCallInDefaultInitializer=false
# Typer uses function calls in default values which is intentional
import contextlib
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import typer
from rich.console import Console
from rich.table import Table

from wine_crawler.config import Settings, ensure_dirs
from wine_crawler.core import CrawlResult, default_retry, with_browser
from wine_crawler.core.browser import with_session_browser
from wine_crawler.core.session import SessionManager, SessionMeta, list_sessions
from wine_crawler.logging import setup_logging
from wine_crawler.sites import get_crawler, list_sites

if TYPE_CHECKING:
    from pathlib import Path

app = typer.Typer(no_args_is_help=True, add_completion=False)
sites_app = typer.Typer(no_args_is_help=True)
session_app = typer.Typer(no_args_is_help=True)
app.add_typer(sites_app, name="sites")
app.add_typer(session_app, name="session")

console = Console()


# ======================================================================
# sites
# ======================================================================


@sites_app.command("list")
def sites_list() -> None:
    """List all registered site crawlers."""
    table = Table(title="Available sites")
    table.add_column("site", style="bold")
    for s in list_sites():
        table.add_row(s)
    console.print(table)


# ======================================================================
# session
# ======================================================================


@session_app.command("status")
def session_status(
    site: str | None = typer.Argument(None, help="Show details for a single site"),
) -> None:
    """Show saved sessions and their health."""
    settings = Settings()
    ensure_dirs(settings)

    if site:
        sm = SessionManager(settings, site)
        _ = sm.migrate_legacy()
        meta = sm.load_meta()
        _print_session_detail(sm, meta)
    else:
        sessions = list_sessions(settings)
        if not sessions:
            console.print("[dim]No saved sessions.[/dim]")
            return
        _print_session_table(sessions)


@session_app.command("clear")
def session_clear(
    site: str = typer.Argument(..., help="Site whose session to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete all session data for a site."""
    settings = Settings()
    ensure_dirs(settings)
    sm = SessionManager(settings, site)

    if not sm.has_session:
        console.print(f"[dim]No session for '{site}'.[/dim]")
        return

    if not yes:
        meta = sm.load_meta()
        console.print(f"Will delete session for [bold]{site}[/bold]  (uses: {meta.use_count})")
        confirm = typer.confirm("Are you sure?")
        if not confirm:
            raise typer.Abort

    sm.clear()
    console.print(f"[green]Session for '{site}' cleared.[/green]")


@session_app.command("refresh")
def session_refresh(
    site: str = typer.Argument(..., help="Site to re-login"),
    headful: bool = typer.Option(True, "--headful/--headless", help="Show browser window"),
) -> None:
    """Force re-login and save fresh session."""
    _do_login_command(site, headful=headful, force=True)


# ======================================================================
# login
# ======================================================================


@app.command("login")
def login(
    site: str = typer.Argument(..., help="Site name (see: winecrawl sites list)"),
    headful: bool = typer.Option(True, "--headful/--headless", help="Show browser window"),
    force: bool = typer.Option(False, "--force", help="Force re-login even if session exists"),
) -> None:
    """Login to a site and save session (credentials from .env)."""
    _do_login_command(site, headful=headful, force=force)


def _do_login_command(site: str, *, headful: bool, force: bool) -> None:
    settings = Settings(headless=not headful)
    ensure_dirs(settings)
    logger = setup_logging(log_dir=settings.logs_dir)

    crawler = get_crawler(site)
    if not hasattr(crawler, "_login"):
        console.print(f"[red]Site '{site}' does not support standalone login[/red]")
        raise typer.Exit(1)

    sm = SessionManager(settings, site)
    _ = sm.migrate_legacy()

    # If session is usable and not forcing, just validate
    if sm.is_usable and not force:
        meta = sm.load_meta()
        console.print(
            (f"[green]Session for '{site}' is still active[/green]  "
             f"(TTL remaining: {meta.ttl_remaining_human}, uses: {meta.use_count})")
        )
        console.print("[dim]Use --force to re-login anyway.[/dim]")
        return

    async def _do_login() -> None:
        persona = sm.get_or_create_persona(force_new=force)
        storage = sm.state_path if sm.state_path.exists() and not force else None

        async with with_browser(settings, storage_state=storage, persona=persona) as session:
            console.print(f"Logging in to [bold]{site}[/bold]…")

            success = await crawler._login(  # type: ignore[attr-defined]
                session,
                email=settings.burghound_email,
                password=settings.burghound_password,
                logger=logger,
                settings=settings,
                session_mgr=sm,
                force=force,
            )

            if success:
                console.print("[bold green]Login successful! Session saved.[/bold green]")
                meta = sm.load_meta()
                console.print(f"  TTL: {meta.ttl_remaining_human}  |  Dir: {sm.session_dir}")

                # Immediately logout to avoid account lockout
                console.print("Logging out to release server session…")
                await crawler._logout(  # type: ignore[attr-defined]
                    session,
                    logger=logger,
                    session_mgr=sm,
                )
                console.print("[green]Logged out cleanly.[/green]")
            else:
                console.print("[bold red]Login failed.[/bold red]")
                raise typer.Exit(1)

    import asyncio

    asyncio.run(_do_login())


# ======================================================================
# logout
# ======================================================================


@app.command("logout")
def logout(
    site: str = typer.Argument(..., help="Site name (see: winecrawl sites list)"),
    headful: bool = typer.Option(False, "--headful/--headless", help="Show browser window"),
) -> None:
    """Explicitly logout from a site to release the server session."""
    settings = Settings(headless=not headful)
    ensure_dirs(settings)
    logger = setup_logging(log_dir=settings.logs_dir)

    crawler = get_crawler(site)
    if not hasattr(crawler, "_logout"):
        console.print(f"[red]Site '{site}' does not support explicit logout[/red]")
        raise typer.Exit(1)

    sm = SessionManager(settings, site)
    _ = sm.migrate_legacy()

    async def _do_logout() -> None:
        persona = sm.get_or_create_persona()
        storage = sm.state_path if sm.state_path.exists() else None

        async with with_browser(settings, storage_state=storage, persona=persona) as session:
            console.print(f"Logging out of [bold]{site}[/bold]…")
            success = await crawler._logout(  # type: ignore[attr-defined]
                session,
                logger=logger,
                session_mgr=sm,
            )
            if success:
                console.print("[green]Logged out cleanly. Account is now free.[/green]")
            else:
                console.print("[yellow]Could not logout (maybe not logged in?).[/yellow]")

    import asyncio

    asyncio.run(_do_logout())


# ======================================================================
# run
# ======================================================================


@app.command("run")
def run(
    site: str = typer.Argument(..., help="Site name (see: winecrawl sites list)"),
    limit: int = typer.Option(10, "--limit", min=0, help="Max items to crawl"),
    headful: bool = typer.Option(False, "--headful", help="Run with visible browser"),
    slow_mo_ms: int = typer.Option(0, "--slowmo", min=0, help="Slow down actions (ms)"),
    out: Path | None = typer.Option(None, "--out", dir_okay=False, help="Output JSON path"),
) -> None:
    """Run a crawler for a specific site.

    Automatically logs out after crawling to avoid account lockout.
    """
    settings = Settings(headless=not headful, slow_mo_ms=slow_mo_ms)
    ensure_dirs(settings)
    logger = setup_logging(log_dir=settings.logs_dir)

    crawler = get_crawler(site)
    sm = SessionManager(settings, site)
    _ = sm.migrate_legacy()

    async def _run() -> None:
        async with with_session_browser(settings, site_name=site) as session:

            @default_retry(max_attempts=settings.max_retries)
            async def do_crawl() -> CrawlResult:
                return await crawler.crawl(
                    settings=settings,
                    session=session,
                    logger=logger,
                    limit=limit,
                )

            try:
                result = await do_crawl()
            finally:
                # Persist storage state even if crawl fails
                with contextlib.suppress(Exception):
                    _ = await session.context.storage_state(path=str(sm.state_path))

        out_path = out or _default_out_path(settings.data_dir, site)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": result.meta,
            "items": result.items,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        _ = out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[bold green]OK[/bold green] wrote {out_path}")

    import asyncio

    asyncio.run(_run())


# ======================================================================
# admin (FastAPI dev server)
# ======================================================================


@app.command("admin")
def admin(
    host: str | None = typer.Option(None, "--host", help="Bind host (default: settings.admin_host)"),
    port: int | None = typer.Option(None, "--port", help="Bind port (default: settings.admin_port)"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable auto-reload"),
) -> None:
    """Run the Admin Web Tool backend (FastAPI + Uvicorn).

    Requires: `pip install -e ".[admin]"`.
    """
    settings = Settings()
    ensure_dirs(settings)

    import uvicorn

    uvicorn.run(
        "wine_crawler.admin.app:create_app",
        factory=True,
        host=host or settings.admin_host,
        port=port or settings.admin_port,
        reload=reload,
        log_level="info",
    )


# ======================================================================
# Helpers
# ======================================================================


def _default_out_path(data_dir: Path, site: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return data_dir / site / f"{ts}.json"


def _print_session_table(sessions: list[SessionMeta]) -> None:
    table = Table(title="Saved Sessions")
    table.add_column("Site", style="bold")
    table.add_column("Status")
    table.add_column("Age")
    table.add_column("Last Used")
    table.add_column("TTL Left")
    table.add_column("Uses", justify="right")
    table.add_column("User-Agent", max_width=50, no_wrap=True)

    for m in sessions:
        status_style = {
            "active": "[green]active[/green]",
            "expired": "[red]expired[/red]",
            "inactive": "[dim]inactive[/dim]",
        }.get(m.status, m.status)

        table.add_row(
            m.site,
            status_style,
            m.age_human,
            m.freshness_human,
            m.ttl_remaining_human,
            str(m.use_count),
            (m.user_agent[:50] + "…") if len(m.user_agent) > 50 else m.user_agent,
        )
    console.print(table)


def _print_session_detail(sm: SessionManager, meta: Any) -> None:
    console.print(f"\n[bold]Session: {meta.site}[/bold]")
    console.print()

    status_str = {
        "active": "[green]ACTIVE[/green]",
        "expired": "[red]EXPIRED[/red]",
        "inactive": "[dim]INACTIVE[/dim]",
        "logged_out": "[cyan]LOGGED OUT[/cyan]",
    }.get(meta.status, meta.status)

    clean_close = (
        (
            "[green]yes[/green]"
            if meta.is_cleanly_closed
            else "[red]no (may cause account lock!)[/red]"
        )
        if meta.last_login_at
        else "—"
    )

    rows = [
        ("Status", status_str),
        ("Clean Close", clean_close),
        ("Created", meta.created_at or "—"),
        ("Last Login", meta.last_login_at or "—"),
        ("Last Logout", meta.last_logout_at or "—"),
        ("Last Used", meta.last_used_at or "—"),
        ("Age", meta.age_human),
        ("Freshness", meta.freshness_human),
        ("TTL", f"{meta.ttl_hours}h"),
        ("TTL Remaining", meta.ttl_remaining_human),
        ("Use Count", str(meta.use_count)),
        ("User-Agent", meta.user_agent or "—"),
        ("", ""),
        ("Session Dir", str(sm.session_dir)),
        ("State File", "exists" if sm.state_path.exists() else "[red]missing[/red]"),
        ("Persona File", "exists" if sm.persona_path.exists() else "[red]missing[/red]"),
        ("Meta File", "exists" if sm.meta_path.exists() else "[red]missing[/red]"),
    ]

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    for label, value in rows:
        table.add_row(label, value)
    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
