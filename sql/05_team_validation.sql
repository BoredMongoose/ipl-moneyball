-- Sanity check for the metric: do teams whose players add more runs actually win more?
CREATE OR REPLACE TABLE team_validation AS
WITH team_matches AS (
    SELECT CAST(LEFT(season, 4) AS INTEGER) AS season, team1 AS team, winner FROM matches
    UNION ALL
    SELECT CAST(LEFT(season, 4) AS INTEGER), team2, winner FROM matches
),
wins AS (
    SELECT season, team, COUNT(*) AS played, SUM((winner = team)::INTEGER) AS won
    FROM team_matches
    GROUP BY ALL
),
runs_added AS (
    SELECT season, team, SUM(total_runs_added) AS runs_added
    FROM player_impact
    GROUP BY ALL
)
SELECT w.season, w.team, w.played, w.won,
       ROUND(w.won * 1.0 / w.played, 3) AS win_pct,
       ROUND(r.runs_added)              AS runs_added
FROM wins w
JOIN runs_added r USING (season, team)
WHERE w.season >= 2015;
