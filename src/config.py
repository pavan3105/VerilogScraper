BASE_URL = "https://opencores.org"
PROJECTS_URL = f"{BASE_URL}/projects"
FILE_SELECTOR = "a[href$='.v'], a[href$='.sv'], a[href$='.vh']"
PROJECT_SELECTOR = "div.project-list div.card a[href^='/project/']"
RATE_LIMIT = 0.5 # Seconds between requests
