"""Load ball-by-ball data into DuckDB, run the SQL models, match auction names to
Cricsheet names, and export analysis tables to data/processed/."""
import difflib
import re
import sys
import unicodedata
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, SQL = ROOT / "data/raw", ROOT / "data/processed", ROOT / "sql"
WICKET_VALUE = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0

# Checked by hand: Cricsheet records these players under a different name
MANUAL = {"Varun Chakravarthy": "CV Varun", "Digvesh Singh": "DS Rathi",
          "Vaibhav Sooryavanshi": "V Suryavanshi", "Kamindu Mendis": "PHKD Mendis"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def match_names(prices, roster, people_names):
    """Map 'Ruturaj Gaikwad' -> 'RD Gaikwad' using the 2025 team roster.

    Order of attempts: exact name, Cricsheet's alternate-name register,
    same surname + first initial, then fuzzy match on the full name.
    """
    out, how = [], []
    for _, p in prices.iterrows():
        cands = roster.get(p.team, [])
        full = norm(p.player)
        parts = full.split()
        pick, method = None, "unmatched"
        exact = [c for c in cands if norm(c) == full]
        alias = [c for c in cands if full in people_names.get(c, set())]
        initial = [c for c in cands
                   if norm(c).split()[-1] == parts[-1] and norm(c)[0] == parts[0][0]]
        if p.player in MANUAL:
            pick, method = MANUAL[p.player], "manual"
        elif exact:
            pick, method = exact[0], "exact"
        elif len(alias) == 1:
            pick, method = alias[0], "register"
        elif len(initial) == 1:
            pick, method = initial[0], "surname+initial"
        else:
            fuzzy = difflib.get_close_matches(full, [norm(c) for c in cands], n=1, cutoff=0.75)
            if fuzzy:
                pick = next(c for c in cands if norm(c) == fuzzy[0])
                method = "fuzzy"
        out.append(pick)
        how.append(method)
    prices = prices.copy()
    prices["cricsheet_name"], prices["match_method"] = out, how
    return prices


def load_match_results(con):
    """Winner of every match, from Cricsheet's per-match info files."""
    rows = []
    with zipfile.ZipFile(RAW / "ipl_csv2.zip") as z:
        for name in z.namelist():
            if not name.endswith("_info.csv"):
                continue
            row, teams = {"match_id": int(name.split("_")[0])}, []
            for line in z.read(name).decode("utf-8").splitlines():
                parts = line.split(",")
                if parts[0] != "info":
                    continue
                if parts[1] == "team":
                    teams.append(parts[2])
                elif parts[1] in ("season", "winner"):
                    row[parts[1]] = parts[2]
            row["team1"], row["team2"] = teams[:2]
            rows.append(row)
    matches = pd.DataFrame(rows).astype({"season": str})
    con.register("matches_df", matches)
    con.execute("CREATE OR REPLACE TABLE matches AS SELECT * FROM matches_df")


def main():
    con = duckdb.connect(str(PROC / "ipl.duckdb"))
    with zipfile.ZipFile(RAW / "ipl_csv2.zip") as z:
        z.extract("all_matches.csv", RAW)
    con.execute(f"CREATE OR REPLACE TABLE balls AS SELECT * FROM read_csv_auto('{(RAW / 'all_matches.csv').as_posix()}', sample_size=-1, types={{'season': 'VARCHAR'}})")
    con.execute(f"SET VARIABLE wicket_value = {WICKET_VALUE}")
    for f in ("01_deliveries.sql", "02_baselines.sql", "03_player_impact.sql"):
        con.execute((SQL / f).read_text(encoding="utf-8"))

    # roster = everyone who appeared for each team in 2025
    imp = con.execute("SELECT team, player FROM player_impact WHERE season = 2025").df()
    roster = imp.groupby("team").player.apply(list).to_dict()

    # Cricsheet alternate names (e.g. 'Virat Kohli' for 'V Kohli'), keyed by display name
    people = pd.read_csv(RAW / "people.csv", usecols=["identifier", "name"])
    names = pd.read_csv(RAW / "names.csv")
    alt = names.merge(people, on="identifier", suffixes=("_alt", ""))
    people_names = alt.groupby("name").name_alt.apply(lambda s: {norm(x) for x in s}).to_dict()

    prices = match_names(pd.read_csv(PROC / "prices_2025.csv"), roster, people_names)
    con.register("prices_df", prices)
    con.execute("CREATE OR REPLACE TABLE prices AS SELECT * FROM prices_df")
    load_match_results(con)
    for f in ("04_value.sql", "05_team_validation.sql", "06_persistence.sql"):
        con.execute((SQL / f).read_text(encoding="utf-8"))

    value = con.execute("SELECT * FROM value_2025 ORDER BY surplus DESC").df()
    value.to_csv(PROC / f"value_2025_w{int(WICKET_VALUE)}.csv", index=False)
    if WICKET_VALUE == 6.0:  # the headline run feeds the charts and the Power BI export
        for table in ("player_impact", "team_validation", "persistence"):
            con.execute(f"SELECT * FROM {table}").df().to_csv(PROC / f"{table}.csv", index=False)
    print(prices.match_method.value_counts().to_string())
    print("unmatched (likely did not play in 2025):", ", ".join(prices[prices.cricsheet_name.isna()].player))


if __name__ == "__main__":
    main()
