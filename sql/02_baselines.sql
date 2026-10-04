-- League-average rates per season and phase: the yardstick every player is compared against.
CREATE OR REPLACE TABLE baselines AS
SELECT
    season,
    phase,
    SUM(runs_off_bat) * 1.0 / SUM(faced)   AS bat_runs_per_ball,
    SUM(bowler_runs)  * 1.0 / SUM(legal)   AS bowl_runs_per_ball,
    SUM(striker_out)   * 1.0 / SUM(faced)  AS bat_outs_per_ball,
    SUM(bowler_wicket) * 1.0 / SUM(legal)  AS bowl_wkts_per_ball,
    SUM(faced)                             AS balls
FROM deliveries
GROUP BY season, phase;
