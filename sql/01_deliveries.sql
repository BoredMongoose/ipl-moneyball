-- Clean ball-by-ball view: one row per delivery with phase and helper flags.
CREATE OR REPLACE VIEW deliveries AS
SELECT
    match_id,
    CAST(LEFT(CAST(season AS VARCHAR), 4) AS INTEGER)              AS season,
    innings,
    batting_team,
    bowling_team,
    striker,
    bowler,
    FLOOR(ball)::INTEGER                                           AS over_no,
    CASE WHEN FLOOR(ball) < 6  THEN 'Powerplay'
         WHEN FLOOR(ball) < 15 THEN 'Middle'
         ELSE 'Death' END                                          AS phase,
    runs_off_bat,
    COALESCE(wides, 0)                                             AS wides,
    COALESCE(noballs, 0)                                           AS noballs,
    -- a ball counts against the batter unless it is a wide
    (wides IS NULL)::INTEGER                                       AS faced,
    -- a legal ball counts towards the bowler's over
    (wides IS NULL AND noballs IS NULL)::INTEGER                   AS legal,
    -- byes and leg-byes are not charged to the bowler
    runs_off_bat + COALESCE(wides, 0) + COALESCE(noballs, 0)       AS bowler_runs,
    COALESCE(player_dismissed = striker, FALSE)::INTEGER           AS striker_out,  -- NULL-safe
    (wicket_type IS NOT NULL
     AND wicket_type NOT IN ('run out', 'retired hurt', 'retired out',
                             'obstructing the field'))::INTEGER    AS bowler_wicket
FROM balls
WHERE innings <= 2;   -- drop super overs
