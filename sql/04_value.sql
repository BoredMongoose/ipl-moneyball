-- Price vs. performance for every player bought or retained before IPL 2025.
-- Players who never took the field still cost money, so they keep a 0 impact.
CREATE OR REPLACE TABLE value_2025 AS
WITH perf AS (
    SELECT * FROM player_impact WHERE season = 2025
),
joined AS (
    SELECT p.player AS player_full, p.team, p.price_cr, p.acquired, p.cricsheet_name,
           COALESCE(f.matches, 0)          AS matches,
           COALESCE(f.runs, 0)             AS runs,
           COALESCE(f.balls_faced, 0)      AS balls_faced,
           COALESCE(f.wickets, 0)          AS wickets,
           COALESCE(f.balls_bowled, 0)     AS balls_bowled,
           COALESCE(f.runs_conceded, 0)    AS runs_conceded,
           COALESCE(f.bat_runs_added, 0)   AS bat_runs_added,
           COALESCE(f.bowl_runs_added, 0)  AS bowl_runs_added,
           COALESCE(f.total_runs_added, 0) AS total_runs_added
    FROM prices p
    LEFT JOIN perf f ON f.player = p.cricsheet_name AND f.team = p.team
),
fit AS (
    -- simple linear "fair price" line: how many runs added a rupee normally buys
    SELECT REGR_SLOPE(total_runs_added, price_cr)     AS slope,
           REGR_INTERCEPT(total_runs_added, price_cr) AS intercept
    FROM joined
)
SELECT j.*,
       ROUND(fit.intercept + fit.slope * j.price_cr, 1)                          AS expected_runs_added,
       ROUND(j.total_runs_added - (fit.intercept + fit.slope * j.price_cr), 1)   AS surplus,
       CASE WHEN j.price_cr >= 10 THEN 'Marquee (₹10cr+)'
            WHEN j.price_cr >= 3  THEN 'Mid (₹3-10cr)'
            ELSE 'Budget (<₹3cr)' END                                            AS price_band,
       RANK() OVER (ORDER BY j.total_runs_added - (fit.intercept + fit.slope * j.price_cr) DESC) AS steal_rank,
       RANK() OVER (ORDER BY j.total_runs_added - (fit.intercept + fit.slope * j.price_cr) ASC)  AS bust_rank
FROM joined j CROSS JOIN fit;
