"""Extract 2025 IPL mega-auction prices and retention salaries from Wikipedia.

Output: data/processed/prices_2025.csv  (player, team, price_cr, acquired)
"""
import re
from io import StringIO
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "wiki_2025_personnel.html"
OUT = ROOT / "data" / "processed" / "prices_2025.csv"

TEAMS = ["Chennai Super Kings", "Delhi Capitals", "Gujarat Titans", "Kolkata Knight Riders",
         "Lucknow Super Giants", "Mumbai Indians", "Punjab Kings", "Rajasthan Royals",
         "Royal Challengers Bengaluru", "Sunrisers Hyderabad"]


def crore(text):
    """'₹18 crore (US$1.9 million)' -> 18.0 ; '₹30 lakh' -> 0.3"""
    m = re.search(r"([\d.]+)\s*(crore|lakh)", str(text))
    if not m:
        return None
    return float(m.group(1)) / (1 if m.group(2) == "crore" else 100)


def main():
    tables = pd.read_html(StringIO(RAW.read_text(encoding="utf-8")))
    rows = []

    # Retentions: each wrapper table names two teams side by side; the next two
    # player/salary sub-tables belong to those teams in order
    pending = []
    for t in tables[:18]:
        cells = [str(x) for x in t.iloc[0].tolist()] if len(t) else []
        named = [next(x for x in TEAMS if c.startswith(x)) for c in cells if any(c.startswith(x) for x in TEAMS)]
        if named:
            pending = named
            continue
        if list(t.columns[:4]) == ["No.", "Player", "Nationality", "Salary"] and pending:
            team = pending.pop(0)
            for _, r in t.iterrows():
                rows.append(dict(player=r["Player"], team=team, price_cr=crore(r["Salary"]), acquired="Retained"))

    # Auction: every table with an "Auctioned price (₹ lakhs)" column
    for t in tables:
        price_col = [c for c in t.columns if str(c).startswith("Auctioned price")]
        if not price_col or "2025 IPL team" not in t.columns:
            continue
        for _, r in t.iterrows():
            lakhs = pd.to_numeric(str(r[price_col[0]]).replace(",", ""), errors="coerce")
            if pd.notna(lakhs) and r["2025 IPL team"] in TEAMS:
                rows.append(dict(player=r["Name"], team=r["2025 IPL team"], price_cr=lakhs / 100, acquired="Auction"))

    df = pd.DataFrame(rows).dropna(subset=["price_cr"])
    df["player"] = df.player.str.replace(r"\[.*?\]|\(.*?\)|†|\*", "", regex=True).str.strip()
    df = df.drop_duplicates(["player", "team"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} players | spend by team (₹ cr):")
    print(df.groupby("team").price_cr.agg(["count", "sum"]).round(1).to_string())


if __name__ == "__main__":
    main()
