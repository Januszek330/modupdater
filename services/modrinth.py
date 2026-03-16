import aiohttp

BASE = "https://api.modrinth.com/v2"


def normalize_slug(value: str) -> str:
    if "modrinth.com" in value:
        return value.rstrip("/").split("/")[-1]
    return value.strip()


async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                return None
            return await resp.json()


async def get_project(value: str):
    slug = normalize_slug(value)
    return await fetch_json(f"{BASE}/project/{slug}")


async def get_versions(slug: str):
    return await fetch_json(f"{BASE}/project/{slug}/version")


async def search_projects(query: str):
    data = await fetch_json(f"{BASE}/search?query={query}&limit=25")
    if not data:
        return []

    return data.get("hits", [])
