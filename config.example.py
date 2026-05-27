# Copy this file to config.py and edit for your term and courses.
# config.py is gitignored.

YEAR = 2026
# API base URL for your term (from College Scheduler; URL-encode spaces as %20)
ROOT_URL = f"https://tamu.collegescheduler.com/api/terms/Fall%20{YEAR}%20-%20College%20Station/"

# Sections to auto-register when a spot opens
DESIRED = {
    "MATH 101": {
        "001": "00000",
        "002": "00001",
    }
}

# All courses to monitor (include desired courses here too)
TRACKED = {
    "MATH 101": {
        "001": "00000",
        "002": "00001",
    },
    "ENGR 102": {
        "200": "00002",
    },
}

# CRN to drop when registering a desired section (time conflicts)
SWAP_MATRIX = {}

CHECK_INTERVAL = 30
KEEPALIVE_INTERVAL = 15 * 60
