import aiohttp
import json
import re
from urllib.parse import urlparse
from storage import save_storage, load_storage
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

print("[CHECKERS] Loaded with CurseForge API, Modrinth API, and MrCrayfish support")

with open("config.json") as f:
    config = json.load(f)
CF_API_KEY = config.get("curseforge_api_key")

USE_CURSEFORGE_API = False  # Set to True when Overwolf access is fixed

def normalize_url(url):
    if "curseforge.com" in url:
        parts = url.split("/files")[0].rstrip("/")
        return parts + "/files/all"
    elif "modrinth.com" in url:
        parts = url.split("/")
        return "/".join(parts[:5]) + "/versions"
    return url

async def fetch(session, url, headers=None):
    async with session.get(url, headers=headers or {}) as resp:
        if resp.status != 200:
            print(f"[ERROR] Fetch failed for {url} (HTTP {resp.status})")
        return await resp.text()

async def fetch_json(session, url, headers=None):
    async with session.get(url, headers=headers or {}) as resp:
        if resp.status == 403:
            print(f"[ERROR] JSON fetch failed for {url} (HTTP 403 - Forbidden)")
        elif resp.status != 200:
            print(f"[ERROR] JSON fetch failed for {url} (HTTP {resp.status})")
        return await resp.json()

async def check_mod_updates(mod):
    url = normalize_url(mod["url"])
    mod["url"] = url
    print(f"[DEBUG] Checking mod: {url}")

    last_version = mod.get("last_version", "0.0.0")
    mc_versions = [v.lower() for v in mod.get("mc_versions", ["all"])]
    loaders = [l.lower() for l in mod.get("loaders", ["all"])]

    async with aiohttp.ClientSession() as session:
        if "curseforge.com" in url:
            result = None
            if USE_CURSEFORGE_API:
                result = await check_curseforge_api(url, session, mc_versions, loaders, last_version)
                if not result:
                    print("[FALLBACK] CurseForge API failed, using Playwright")
                    result = await check_curseforge_playwright(url, last_version)
            else:
                result = await check_curseforge_playwright(url, last_version)


        elif "modrinth.com" in url:
            result = await check_modrinth(url, session, mc_versions, loaders, last_version)

        elif "mrcrayfish.com" in url:
            result = await check_mrcrayfish(url, session, last_version)

        else:
            print(f"[DEBUG] Unknown platform for {url}")
            return None

    if result:
        mod["last_version"] = result["version"]
        print(f"[DEBUG] [UPDATE] {url} → {result['version']}")
        save_storage_on_change(mod)
    else:
        print(f"[DEBUG] [NO UPDATE] {url}")

    return result

def save_storage_on_change(mod):
    data = load_storage()
    for gid, info in data.items():
        for m in info.get("mods", []):
            if normalize_url(m.get("url", "")) == mod["url"]:
                m["last_version"] = mod["last_version"]
                save_storage(data)
                print(f"[DEBUG] [STORAGE] Updated for {mod['url']}")
                return

# ✅ CurseForge API
async def check_curseforge_api(url, session, mc_versions, loaders, last_version):
    slug = urlparse(url).path.strip("/").split("/")[2]
    headers = {"x-api-key": CF_API_KEY}
    search_url = f"https://api.curseforge.com/v1/mods/search?gameId=432&searchFilter={slug}"
    project_info = await fetch_json(session, search_url, headers)

    if not project_info.get("data"):
        print(f"[ERROR] No CurseForge project found for {slug}")
        return None

    mod_data = project_info["data"][0]
    mod_id = mod_data["id"]
    mod_name = mod_data["name"]
    print(f"[DEBUG] [CF] Found project {mod_name} (ID: {mod_id})")

    files_url = f"https://api.curseforge.com/v1/mods/{mod_id}/files"
    files_data = await fetch_json(session, files_url, headers)

    for file in files_data.get("data", []):
        game_versions = [v.lower() for v in file["gameVersions"]]
        print(f"[ROW] {file['displayName']} → {game_versions}")

        if (
            any(v in game_versions for v in mc_versions if v != "all") or "all" in mc_versions
        ) and (
            any(l in game_versions for l in loaders if l != "all") or "all" in loaders
        ):
            match = re.search(r"\b(\d+\.\d+(?:\.\d+)*)\b", file["displayName"])
            if match:
                found_version = match.group(1)
                print(f"[MATCH] CurseForge found {found_version} vs {last_version}")
                if found_version != last_version:
                    return {
                        "mod_name": mod_name,
                        "platform": "CurseForge",
                        "version": found_version,
                        "url": f"https://www.curseforge.com/minecraft/mc-mods/{slug}/files"
                    }

    return None

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import re

async def check_curseforge_playwright(url, last_version):
    print("[FALLBACK] Using Playwright for CurseForge")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)

            # Wait for at least one mod tile title to appear
            await page.wait_for_selector("a.file-row-details span.name", timeout=30000)
            elements = await page.query_selector_all("a.file-row-details span.name")

            for el in elements:
                text = await el.text_content()
                if text:
                    # Example text: "Create 6.0.6 for mc1.21.1"
                    match = re.search(r"\b(\d+\.\d+(?:\.\d+)*)\b", text)
                    if match:
                        version = match.group(1)
                        if version != last_version:
                            print(f"[MATCH] CurseForge found {version} vs {last_version}")
                            return {
                                "mod_name": "CurseForge Mod",
                                "platform": "CurseForge",
                                "version": version,
                                "url": url
                            }
                        else:
                            print(f"[DEBUG] No new version. Found {version}")
                    break  # only check the latest visible file

            await browser.close()
            print("[ERROR] Could not extract mod version from page.")

    except PlaywrightTimeoutError as e:
        print(f"[ERROR] Playwright timeout: {e}")
    except Exception as e:
        print(f"[ERROR] Playwright failed: {e}")
    return None

# ✅ Modrinth API
async def check_modrinth(url, session, mc_versions, loaders, last_version):
    slug = urlparse(url).path.strip("/").split("/")[1]
    api_url = f"https://api.modrinth.com/v2/project/{slug}"
    version_url = f"https://api.modrinth.com/v2/project/{slug}/version"

    try:
        project = await fetch_json(session, api_url)
        versions = await fetch_json(session, version_url)
    except Exception as e:
        print(f"[ERROR] Failed to fetch Modrinth data for {slug}: {e}")
        return None

    for v in versions:
        v_mc = [ver.lower() for ver in v.get("game_versions", [])]
        v_ld = [l.lower() for l in v.get("loaders", [])]
        print(f"[ROW] {v['name']} → MC: {v_mc}, Loader: {v_ld}")

        if (
            any(ver in v_mc for ver in mc_versions if ver != "all") or "all" in mc_versions
        ) and (
            any(ld in v_ld for ld in loaders if ld != "all") or "all" in loaders
        ):
            found_version = v["version_number"]
            print(f"[MATCH] Found {found_version} vs last={last_version}")
            if found_version != last_version:
                return {
                    "mod_name": project["title"],
                    "platform": "Modrinth",
                    "version": found_version,
                    "url": f"https://modrinth.com/mod/{slug}/version/{v['id']}"
                }

    return None

# ✅ MrCrayfish
async def check_mrcrayfish(url, session, last_version):
    html = await fetch(session, url)
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title else "MrCrayfish Mod"
    match = re.search(r"v?([\d.]+)", html)
    if match:
        found_version = match.group(1)
        print(f"[MATCH] MrCrayfish {found_version} vs {last_version}")
        if found_version != last_version:
            return {
                "mod_name": title,
                "platform": "MrCrayfish",
                "version": found_version,
                "url": url
            }
    return None
