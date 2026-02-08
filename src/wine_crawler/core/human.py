"""Human-like interaction helpers for Playwright.

Every function introduces natural variance so automated actions don't produce
the perfectly regular timing / coordinate patterns that bot detectors flag.
"""

from __future__ import annotations

import asyncio
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

# ---------------------------------------------------------------------------
# Random delays
# ---------------------------------------------------------------------------


async def human_delay(*, base: float = 1.0, sigma: float = 0.3) -> None:
    """Sleep for a normally-distributed duration (clamped >= 0.05 s)."""
    await asyncio.sleep(max(0.05, random.gauss(base, sigma)))


async def short_pause() -> None:
    """Tiny pause between fine-grained actions (50-200 ms)."""
    await asyncio.sleep(random.uniform(0.05, 0.20))


async def medium_pause() -> None:
    """Medium pause simulating 'reading / thinking' (0.4-1.2 s)."""
    await asyncio.sleep(random.uniform(0.4, 1.2))


# ---------------------------------------------------------------------------
# Mouse helpers
# ---------------------------------------------------------------------------


def _bezier_point(t: float, p0: float, p1: float, p2: float, p3: float) -> float:
    """Cubic Bezier interpolation at parameter *t*."""
    u = 1.0 - t
    return u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3


async def human_move_mouse(page: Page, target_x: float, target_y: float) -> None:
    """Move the mouse from its current position to *(target_x, target_y)*
    along a randomised cubic Bezier curve with variable speed."""
    # Playwright doesn't expose current mouse position; we keep a rough
    # estimate by saving the last known position on the page object.
    start_x = getattr(page, "_last_mouse_x", random.uniform(200, 600))
    start_y = getattr(page, "_last_mouse_y", random.uniform(200, 400))

    # Random control points for the Bezier curve (creates a natural arc)
    dx = target_x - start_x
    dy = target_y - start_y
    cp1x = start_x + dx * random.uniform(0.1, 0.4) + random.uniform(-30, 30)
    cp1y = start_y + dy * random.uniform(0.1, 0.4) + random.uniform(-30, 30)
    cp2x = start_x + dx * random.uniform(0.6, 0.9) + random.uniform(-20, 20)
    cp2y = start_y + dy * random.uniform(0.6, 0.9) + random.uniform(-20, 20)

    steps = random.randint(12, 30)
    for i in range(1, steps + 1):
        t = i / steps
        # Ease-in-out: slow start and end, fast middle
        t_eased = (1.0 - math.cos(t * math.pi)) / 2.0
        x = _bezier_point(t_eased, start_x, cp1x, cp2x, target_x)
        y = _bezier_point(t_eased, start_y, cp1y, cp2y, target_y)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.025))

    # Cache last position
    page._last_mouse_x = target_x  # type: ignore[attr-defined]
    page._last_mouse_y = target_y  # type: ignore[attr-defined]


async def human_click(page: Page, locator: Locator) -> None:
    """Move the mouse to a random point inside *locator*'s bounding box,
    pause briefly, and click."""
    box = await locator.bounding_box()
    if box is None:
        # Fallback to plain click if bounding box unavailable
        await locator.click()
        return

    # Don't always hit dead-centre -- pick a random point inside
    target_x = box["x"] + box["width"] * random.uniform(0.25, 0.75)
    target_y = box["y"] + box["height"] * random.uniform(0.25, 0.75)

    await human_move_mouse(page, target_x, target_y)
    await asyncio.sleep(random.uniform(0.04, 0.12))
    await page.mouse.click(target_x, target_y)
    await short_pause()


# ---------------------------------------------------------------------------
# Typing
# ---------------------------------------------------------------------------


async def human_type(
    page: Page,
    locator: Locator,
    text: str,
    *,
    wpm: int = 65,
    click_first: bool = True,
) -> None:
    """Type *text* character-by-character with human-like timing.

    Uses ``press_sequentially`` under the hood so individual keydown/keypress/
    keyup events fire for each character, matching real keyboard behaviour.

    Args:
        page: Playwright page (used for focus management).
        locator: The input element to type into.
        text: The string to type.
        wpm: Approximate typing speed in words-per-minute.
        click_first: Whether to click the field before typing.
    """
    if click_first:
        await human_click(page, locator)
        await asyncio.sleep(random.uniform(0.1, 0.3))

    # Average inter-key interval from WPM (assuming 5 chars/word)
    avg_ms = 60_000.0 / (wpm * 5)

    for char in text:
        # Per-keystroke delay with Gaussian jitter
        delay = max(30, random.gauss(avg_ms, avg_ms * 0.25))
        await page.keyboard.press(char, delay=delay)

        # Occasional longer pause (simulates thinking / correcting)
        if random.random() < 0.04:
            await asyncio.sleep(random.uniform(0.2, 0.6))


# ---------------------------------------------------------------------------
# Scroll
# ---------------------------------------------------------------------------


async def human_scroll(page: Page, *, direction: str = "down", distance: int = 300) -> None:
    """Scroll the page with variable speed and distance.

    Args:
        page: Playwright page.
        direction: 'down' or 'up'.
        distance: Approximate scroll distance in pixels.
    """
    actual = int(distance * random.uniform(0.7, 1.3))
    sign = 1 if direction == "down" else -1

    chunks = random.randint(3, 7)
    for _ in range(chunks):
        delta = (actual // chunks) * sign
        await page.mouse.wheel(0, delta)
        await asyncio.sleep(random.uniform(0.03, 0.12))
