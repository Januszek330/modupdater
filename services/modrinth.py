import aiohttp
import re
import time
from typing import Optional, List, Dict, Any

# Fast local query cache (Query -> (Timestamp, Results))
_search_cache: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 300  # Cache queries for 5 minutes to prevent hammering the API


def normalize_slug(project_input: str) -> str:
    """
    Extracts the clean slug from a raw user string or full Modrinth web URL.
    """
    if not project_input:
        return ""
    # Strip URL and extract slug if a full link is supplied
    match = re.search(r"modrinth\.com/(?:project|mod)/([^/]+)", project_input)
    if match:
        return match.group(1).strip()
    return project_input.strip()


async def search_projects(query: str, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
    """
    Asynchronously queries the Modrinth v2 search API with local memory caching.
    """
    query_clean = query.strip().lower()
    if not query_clean:
        return []

    current_time = time.time()

    # Attempt local cache lookup
    if query_clean in _search_cache:
        cached_time, cached_results = _search_cache[query_clean]
        if current_time - cached_time < CACHE_TTL_SECONDS:
            return cached_results

    url = "https://api.modrinth.com/v2/search"
    headers = {"User-Agent": "modcheck-discord-bot/2.0 (contact@modcheck.invalid)"}
    params = {
        "query": query_clean,
        "limit": 15
    }

    async def _fetch(s: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        async with s.get(url, params=params, headers=headers) as r:
            if r.status != 200:
                return []
            data = await r.json()
            return data.get("hits", [])

    try:
        if session:
            results = await _fetch(session)
        else:
            async with aiohttp.ClientSession() as ephemeral_session:
                results = await _fetch(ephemeral_session)

        # Update search cache
        _search_cache[query_clean] = (current_time, results)
        return results
    except Exception:
        # Graceful degradation to expired cache if remote API goes down
        if query_clean in _search_cache:
            return _search_cache[query_clean][1]
        return []


async def get_project(project_id_or_slug: str, session: Optional[aiohttp.ClientSession] = None) -> Optional[
    Dict[str, Any]]:
    """
    Fetches raw project metadata from the Modrinth API.
    """
    slug = normalize_slug(project_id_or_slug)
    if not slug:
        return None

    url = f"https://api.modrinth.com/v2/project/{slug}"
    headers = {"User-Agent": "modcheck-discord-bot/2.0 (contact@modcheck.invalid)"}

    async def _fetch(s: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        async with s.get(url, headers=headers) as r:
            if r.status == 200:
                return await r.json()
            return None

    try:
        if session:
            return await _fetch(session)
        async with aiohttp.ClientSession() as ephemeral_session:
            return await _fetch(ephemeral_session)
    except Exception:
        return None


async def get_versions(project_id_or_slug: str, session: Optional[aiohttp.ClientSession] = None) -> List[
    Dict[str, Any]]:
    """
    Gets all published versions of a project from the Modrinth API.
    """
    slug = normalize_slug(project_id_or_slug)
    if not slug:
        return []

    url = f"https://api.modrinth.com/v2/project/{slug}/version"
    headers = {"User-Agent": "modcheck-discord-bot/2.0 (contact@modcheck.invalid)"}

    async def _fetch(s: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        async with s.get(url, headers=headers) as r:
            if r.status == 200:
                return await r.json()
            return []

    try:
        if session:
            return await _fetch(session)
        async with aiohttp.ClientSession() as ephemeral_session:
            return await _fetch(ephemeral_session)
    except Exception:
        return []