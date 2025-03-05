import os
import asyncio
import aiohttp
import aiofiles
import logging
import base64
from dotenv import load_dotenv
from urllib.parse import quote

# Load environment variables from .env if available
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("AsyncVerilogScraper")

# Global GitHub API configuration
GITHUB_API_URL = "https://api.github.com"
GITHUB_SEARCH_URL = f"{GITHUB_API_URL}/search/repositories"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {"Accept": "application/vnd.github.v3+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

# Target repository details for uploading scraped files
TARGET_OWNER = "pavan3105"           # <-- Replace with your GitHub username
TARGET_REPO = "VerilogCode"           # <-- Replace with your target repository name
TARGET_BRANCH = "data_collection"          # Branch where files will be uploaded

# Scraping settings: process 90 repos (3 pages x 30 results per page)
RESULTS_PER_PAGE = 30
MAX_PAGES = 10

# Concurrency control
CONCURRENT_REQUESTS = 5
semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

async def fetch_json(session: aiohttp.ClientSession, url: str):
    """Fetch JSON data from a URL with error handling."""
    async with semaphore:
        try:
            async with session.get(url, headers=HEADERS) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch {url}: {response.status}")
                    return None
        except Exception as e:
            logger.exception(f"Exception while fetching {url}: {e}")
            return None

async def upload_verilog_file_to_target(session: aiohttp.ClientSession, download_url: str, repo_full_name: str, file_path: str, file_name: str):
    # Download the file content
    async with semaphore:
        try:
            async with session.get(download_url, headers=HEADERS) as response:
                if response.status != 200:
                    logger.error(f"Failed to download {download_url}: {response.status}")
                    return
                content = await response.read()
        except Exception as e:
            logger.exception(f"Exception downloading file {download_url}: {e}")
            return

    # Base64-encode the file content
    encoded_content = base64.b64encode(content).decode("utf-8")
    
    # Construct a target file path
    repo_dir = repo_full_name.replace("/", "_")
    relative_dir = os.path.dirname(file_path)
    if relative_dir:
        target_path = f"verilog_data/{repo_dir}/{relative_dir}/{file_name}"
    else:
        target_path = f"verilog_data/{repo_dir}/{file_name}"
    target_path_encoded = quote(target_path)
    
    # Check if the file already exists
    get_url = f"{GITHUB_API_URL}/repos/{TARGET_OWNER}/{TARGET_REPO}/contents/{target_path_encoded}?ref={TARGET_BRANCH}"
    
    # Use a separate semaphore acquisition for the check and the put
    async with semaphore:
        existing_file = None
        try:
            async with session.get(get_url, headers=HEADERS) as get_response:
                if get_response.status == 200:
                    existing_file = await get_response.json()
        except Exception as e:
            logger.exception(f"Exception checking if file exists {target_path}: {e}")
    
    # Prepare the payload
    payload = {
        "message": f"Add/update {target_path}",
        "content": encoded_content,
        "branch": TARGET_BRANCH
    }
    
    if existing_file and "sha" in existing_file:
        payload["sha"] = existing_file["sha"]
    
    logger.info(f"{'Updating' if existing_file else 'Uploading'} file to target repo: {target_path}")
    
    # Use a retry mechanism with exponential backoff
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(1, max_retries + 1):
        async with semaphore:
            try:
                upload_url = f"{GITHUB_API_URL}/repos/{TARGET_OWNER}/{TARGET_REPO}/contents/{target_path_encoded}"
                async with session.put(upload_url, json=payload, headers=HEADERS) as put_response:
                    if put_response.status in (200, 201):
                        logger.info(f"✅ Uploaded: {target_path}")
                        return
                    elif put_response.status == 409:  # Conflict
                        text = await put_response.text()
                        logger.warning(f"Conflict when uploading {target_path}. Attempt {attempt}/{max_retries}. Response: {text}")
                        if attempt < max_retries:
                            # Get the latest SHA and try again
                            try:
                                async with session.get(get_url, headers=HEADERS) as get_response:
                                    if get_response.status == 200:
                                        latest_file = await get_response.json()
                                        if latest_file and "sha" in latest_file:
                                            payload["sha"] = latest_file["sha"]
                            except Exception as e:
                                logger.exception(f"Exception getting latest SHA: {e}")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                    else:
                        text = await put_response.text()
                        logger.error(f"❌ Failed to upload {target_path}. Status: {put_response.status}. Response: {text}")
                        return
            except Exception as e:
                logger.exception(f"Exception while uploading {target_path}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return


async def get_verilog_files_from_repo(session: aiohttp.ClientSession, repo_full_name: str, branch: str, path: str = ""):
    """
    Recursively searches the given repo path for Verilog files (.v) and uploads them.
    """
    encoded_path = quote(path) if path else ""
    url = (f"{GITHUB_API_URL}/repos/{repo_full_name}/contents/{encoded_path}?ref={branch}"
           if path else f"{GITHUB_API_URL}/repos/{repo_full_name}/contents?ref={branch}")
    data = await fetch_json(session, url)
    if data is None:
        return
    if isinstance(data, dict):
        data = [data]
    tasks = []
    for item in data:
        if item["type"] == "dir":
            tasks.append(get_verilog_files_from_repo(session, repo_full_name, branch, item["path"]))
        elif item["type"] == "file" and item["name"].endswith(".v"):
            tasks.append(upload_verilog_file_to_target(session, item["download_url"], repo_full_name, item["path"], item["name"]))
    if tasks:
        await asyncio.gather(*tasks)
    await asyncio.sleep(0.5)  # gentle delay to avoid rate limit issues

async def get_repo_default_branch(session: aiohttp.ClientSession, repo_full_name: str):
    """Retrieves the default branch for a repository."""
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}"
    data = await fetch_json(session, url)
    if data:
        return data.get("default_branch", "master")
    logger.error(f"Failed to get default branch for {repo_full_name}")
    return "master"

async def process_repo(session: aiohttp.ClientSession, repo_full_name: str):
    """Processes one repository: get its default branch and recursively upload its Verilog files."""
    default_branch = await get_repo_default_branch(session, repo_full_name)
    logger.info(f"Processing repo: {repo_full_name} (default branch: {default_branch})")
    await get_verilog_files_from_repo(session, repo_full_name, default_branch)

async def search_verilog_repos(query="language:Verilog", max_pages=MAX_PAGES):
    """
    Searches GitHub for repositories matching the query.
    Returns a list of repository items.
    """
    repos = []
    async with aiohttp.ClientSession() as session:
        for page in range(1, max_pages + 1):
            url = GITHUB_SEARCH_URL + f"?q={query}&per_page={RESULTS_PER_PAGE}&page={page}"
            data = await fetch_json(session, url)
            if data is None:
                break
            items = data.get("items", [])
            if not items:
                break
            repos.extend(items)
            logger.info(f"Page {page}: Found {len(items)} repositories")
            await asyncio.sleep(2)
    return repos

async def main():
    # Step 1: Search for Verilog repositories
    logger.info("Searching for Verilog repositories on GitHub...")
    repositories = await search_verilog_repos(max_pages=MAX_PAGES)
    logger.info(f"Total repositories found: {len(repositories)}")

    # Step 2: Process each repository one at a time
    async with aiohttp.ClientSession() as session:
        for repo in repositories:
            logger.info(f"Processing repository: {repo['full_name']}")
            await process_repo(session, repo["full_name"])
            # Add a delay between repositories to further reduce concurrency issues
            await asyncio.sleep(2)
    
    logger.info("🎉 Finished uploading Verilog files for selected repositories.")

if __name__ == "__main__":
    asyncio.run(main())
