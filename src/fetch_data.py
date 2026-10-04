"""Download the raw data into data/raw/ (files that already exist are skipped).

- Cricsheet IPL ball-by-ball data (ipl_csv2.zip) and its player register (people.csv, names.csv)
- Wikipedia's 2025 IPL personnel-changes page, pinned to the revision this analysis used

Cricsheet adds every new season to ipl_csv2.zip, so a later download also contains matches after IPL 2026.
"""
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

WIKI_REVISION = 1375677821
FILES = {
    "ipl_csv2.zip": "https://cricsheet.org/downloads/ipl_csv2.zip",
    "people.csv": "https://cricsheet.org/register/people.csv",
    "names.csv": "https://cricsheet.org/register/names.csv",
    "wiki_2025_personnel.html": "https://en.wikipedia.org/w/index.php?title="
                                f"List_of_2025_Indian_Premier_League_personnel_changes&oldid={WIKI_REVISION}",
}
HEADERS = {"User-Agent": "ipl-moneyball (https://github.com/BoredMongoose/ipl-moneyball)"}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        path = RAW / name
        if path.exists():
            print(f"{name}: already downloaded")
            continue
        r = requests.get(url, headers=HEADERS, timeout=120)
        r.raise_for_status()
        path.write_bytes(r.content)
        print(f"{name}: {len(r.content) / 1e6:.1f} MB")
