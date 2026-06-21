"""Latest-release lookup for FireLabs firmware, cached to stay under GitHub limits.

GitHub's unauthenticated API allows 60 requests per hour per IP. Devices of the
same model share one firmware repo, so the result is cached per repo with a TTL
and refreshed in the background; entities read the cached value synchronously.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import aiohttp

from .const import GITHUB_LATEST, RELEASE_TTL

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Release:
    """The latest published firmware release for one model's repo."""

    version: str  # tag with any leading "v" stripped, e.g. "0.1.2"
    bin_url: str | None  # browser_download_url of the firmware .bin asset
    notes: str  # release body (markdown)
    url: str  # release html_url


def _pick_release(data: dict, model: str) -> Release:
    tag = (data.get("tag_name") or "").lstrip("vV")
    assets = data.get("assets") or []
    bins = [
        a for a in assets
        if isinstance(a.get("name"), str) and a["name"].lower().endswith(".bin")
    ]
    # Prefer an asset named for this model (repos may ship variants, e.g. a Lite),
    # otherwise take the first .bin.
    chosen = next(
        (a for a in bins if model.lower() in a["name"].lower()),
        bins[0] if bins else None,
    )
    return Release(
        version=tag,
        bin_url=chosen.get("browser_download_url") if chosen else None,
        notes=data.get("body") or "",
        url=data.get("html_url") or "",
    )


class ReleaseCache:
    """Shared, TTL'd cache of the latest release per firmware repo."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._cache: dict[str, tuple[float, Release | None]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def cached(self, repo: str) -> Release | None:
        entry = self._cache.get(repo)
        return entry[1] if entry else None

    def _is_stale(self, repo: str) -> bool:
        entry = self._cache.get(repo)
        return entry is None or (time.monotonic() - entry[0]) > RELEASE_TTL

    async def async_refresh(self, repo: str, model: str) -> Release | None:
        """Refresh the cached release for a repo if stale; return the cached value."""
        lock = self._locks.setdefault(repo, asyncio.Lock())
        async with lock:
            if not self._is_stale(repo):
                return self.cached(repo)
            rel = await self._fetch(repo, model)
            # Keep the last good value on a failed fetch rather than blanking it.
            if rel is not None or repo not in self._cache:
                self._cache[repo] = (time.monotonic(), rel)
            return self.cached(repo)

    async def _fetch(self, repo: str, model: str) -> Release | None:
        url = GITHUB_LATEST.format(repo=repo)
        try:
            async with asyncio.timeout(15):
                resp = await self._session.get(
                    url, headers={"Accept": "application/vnd.github+json"}
                )
                if resp.status == 404:
                    _LOGGER.debug("No releases yet for %s", repo)
                    return None
                resp.raise_for_status()
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Release check for %s failed: %s", repo, err)
            return None
        return _pick_release(data, model)
