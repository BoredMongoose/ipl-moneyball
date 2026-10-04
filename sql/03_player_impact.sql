-- Runs Added: how many runs a player contributed versus a league-average player
-- facing / bowling the same balls in the same phase of the innings.
--   batting:  (runs - expected runs) - wicket_value x (dismissals - expected dismissals)
--   bowling:  (expected runs - runs conceded) + wicket_value x (wickets - expected wickets)
-- Both sides are compared with the league average for that phase, so an average
-- player scores ~0 and the whole league sums to ~0.
-- wicket_value is set by the pipeline (default 6 runs) and stress-tested in the analysis.
CREATE OR REPLACE TABLE player_impact AS
WITH bat AS (
    SELECT d.season, d.batting_team AS team, d.striker AS player,
           COUNT(DISTINCT d.match_id)                                   AS bat_matches,
           SUM(d.runs_off_bat)                                          AS runs,
           SUM(d.faced)                                                 AS balls_faced,
           SUM(d.striker_out)                                           AS dismissals,
           SUM(d.runs_off_bat - d.faced * b.bat_runs_per_ball)
             - SUM(d.striker_out - d.faced * b.bat_outs_per_ball)
               * getvariable('wicket_value')                            AS bat_runs_added
    FROM deliveries d JOIN baselines b USING (season, phase)
    GROUP BY ALL
),
bowl AS (
    SELECT d.season, d.bowling_team AS team, d.bowler AS player,
           COUNT(DISTINCT d.match_id)                                   AS bowl_matches,
           SUM(d.legal)                                                 AS balls_bowled,
           SUM(d.bowler_runs)                                           AS runs_conceded,
           SUM(d.bowler_wicket)                                         AS wickets,
           SUM(CASE WHEN d.phase = 'Death' THEN d.legal END)            AS death_balls,
           SUM(d.legal * b.bowl_runs_per_ball - d.bowler_runs)
             + SUM(d.bowler_wicket - d.legal * b.bowl_wkts_per_ball)
               * getvariable('wicket_value')                            AS bowl_runs_added
    FROM deliveries d JOIN baselines b USING (season, phase)
    GROUP BY ALL
),
appearances AS (
    -- anyone who batted, was at the non-striker's end, or bowled
    SELECT season, batting_team AS team, striker AS player, match_id FROM deliveries
    UNION SELECT CAST(LEFT(CAST(season AS VARCHAR), 4) AS INTEGER), batting_team, non_striker, match_id FROM balls WHERE innings <= 2
    UNION SELECT season, bowling_team, bowler, match_id FROM deliveries
)
SELECT
    a.season, a.team, a.player,
    COUNT(DISTINCT a.match_id)                                          AS matches,
    COALESCE(bat.runs, 0)                AS runs,
    COALESCE(bat.balls_faced, 0)         AS balls_faced,
    COALESCE(bat.dismissals, 0)          AS dismissals,
    COALESCE(bowl.balls_bowled, 0)       AS balls_bowled,
    COALESCE(bowl.runs_conceded, 0)      AS runs_conceded,
    COALESCE(bowl.wickets, 0)            AS wickets,
    COALESCE(bowl.death_balls, 0)        AS death_balls,
    ROUND(COALESCE(bat.bat_runs_added, 0), 1)                           AS bat_runs_added,
    ROUND(COALESCE(bowl.bowl_runs_added, 0), 1)                         AS bowl_runs_added,
    ROUND(COALESCE(bat.bat_runs_added, 0) + COALESCE(bowl.bowl_runs_added, 0), 1) AS total_runs_added
FROM appearances a
LEFT JOIN bat  USING (season, team, player)
LEFT JOIN bowl USING (season, team, player)
GROUP BY ALL;
