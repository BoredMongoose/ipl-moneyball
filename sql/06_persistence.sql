-- Is a big season skill or luck? Compare each player's runs added per match
-- in 2025 with 2026 (any team), for players with 7+ matches in both seasons.
CREATE OR REPLACE TABLE persistence AS
WITH per_season AS (
    SELECT season, player,
           SUM(matches)                              AS matches,
           SUM(total_runs_added) / SUM(matches)      AS ra_per_match
    FROM player_impact
    WHERE season IN (2025, 2026)
    GROUP BY ALL
)
SELECT a.player,
       ROUND(a.ra_per_match, 2) AS ra_per_match_2025,
       ROUND(b.ra_per_match, 2) AS ra_per_match_2026,
       v.player_full, v.price_cr, v.surplus,
       NTILE(5) OVER (ORDER BY a.ra_per_match) AS quintile_2025
FROM per_season a
JOIN per_season b ON a.player = b.player AND b.season = 2026
LEFT JOIN value_2025 v ON v.cricsheet_name = a.player
WHERE a.season = 2025 AND a.matches >= 7 AND b.matches >= 7;
