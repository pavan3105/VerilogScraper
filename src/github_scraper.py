import os
import requests


REPO_OWNER = "fabriziotappero"
REPO_NAME = "ip-cores"
BASE_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

HEADERS = {"Accept": "application/vnd.github.v3+json"}


SAVE_DIR = "verilog_files"
os.makedirs(SAVE_DIR, exist_ok=True)

def get_all_branches():
    """Fetch all branches from the repository."""
    url = f"{BASE_API_URL}/branches"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print("Failed to fetch branches:", response.status_code)
        return []

    branches = [branch["name"] for branch in response.json()]
    print(f"Found {len(branches)} branches: {branches}")
    return branches

def get_verilog_files(branch, path=""):
    """Recursively find and download all Verilog files from the given branch."""
    url = f"{BASE_API_URL}/contents/{path}?ref={branch}" if path else f"{BASE_API_URL}/contents?ref={branch}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"Failed to fetch {url}: {response.status_code}")
        return

    items = response.json()
    
    for item in items:
        if item["type"] == "dir":  
            get_verilog_files(branch, item["path"])
        elif item["type"] == "file" and item["name"].endswith(".v"):  
            download_verilog_file(item["download_url"], item["name"], branch)

def download_verilog_file(file_url, file_name, branch):
    """Download and save a Verilog file."""
    branch_dir = os.path.join(SAVE_DIR, branch)
    os.makedirs(branch_dir, exist_ok=True)

    print(f"Downloading {file_name} from branch {branch}...")
    response = requests.get(file_url, headers=HEADERS)

    if response.status_code == 200:
        file_path = os.path.join(branch_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"Saved: {file_path}")
    else:
        print(f"Failed to download {file_name}")

branches = get_all_branches()
for branch in branches:
    print(f"\n Searching for Verilog files in branch: {branch}...")
    get_verilog_files(branch)

print("\n Scraping complete! All Verilog files are saved in the 'verilog_files' folder.")
