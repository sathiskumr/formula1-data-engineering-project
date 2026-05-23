CREATE OR REPLACE VIEW formula1_incr.gold.v_driver_evolution
AS

WITH base_results AS (
    SELECT 
        season
        , round
        , driver_id
        , points
        , final_position
        , session_type
        , is_win
        , is_podium
        , has_points
        , is_pole
     FROM 
        formula1_incr.gold.fact_session_results
     WHERE 
        season >= 2020 
        AND session_type IN ('RACE', 'SPRINT')
),

points_by_round AS (
    SELECT
        season
        , round
        , driver_id
        , SUM(points) AS round_points
     FROM 
        base_results
     GROUP BY
        season
        , round
        , driver_id

),

all_season_rounds AS (
    SELECT 
        DISTINCT season, round 
     FROM 
        points_by_round
),

all_season_drivers AS (
    SELECT 
        DISTINCT season, driver_id 
     FROM 
        points_by_round
),

all_rounds_for_drivers AS (
    SELECT 
        r.season
        , r.round
        , d.driver_id
    FROM 
        all_season_rounds r
        JOIN all_season_drivers d 
        ON d.season = r.season
),

points_for_missing_rounds AS (
    SELECT
        ard.season
        , ard.round
        , ard.driver_id
        , COALESCE(pbr.round_points, 0) AS round_points  -- 0 for missing rounds
    FROM 
        all_rounds_for_drivers ard
        LEFT JOIN points_by_round pbr
            ON  pbr.season    = ard.season
            AND pbr.round     = ard.round
            AND pbr.driver_id = ard.driver_id
),

seasonal_cumulative_points AS (
    SELECT
        season
        , round
        , driver_id
        , round_points
        , SUM(round_points) OVER (
            PARTITION BY season, driver_id
            ORDER BY round ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_points
     FROM 
        points_for_missing_rounds
)


SELECT
    cp.season
    , cp.round
    , cp.driver_id
    , dc.fia_driver_code AS driver_code
    , d.driver_name
    , CONCAT(
        LEFT(d.driver_name, 1),
        '. ',
        REVERSE(
            LEFT(
                REVERSE(d.driver_name), 
                CHARINDEX(' ', REVERSE(d.driver_name)) - 1
            )
        )
    ) AS short_name
    , cp.round_points
    , cp.cumulative_points
    , RANK() OVER (PARTITION BY cp.season, cp.round ORDER BY cp.cumulative_points DESC) AS driver_rank
    , r.race_name
    , REPLACE(r.race_name, 'Grand Prix', 'GP') AS short_race_name
    , r.circuit_name
    , cr.color_code
    , cr.cons_logo

 FROM 
    seasonal_cumulative_points cp

    LEFT JOIN formula1_incr.gold.v_constructor_reference cr
    ON cr.season = cp.season
    AND cr.driver_id = cp.driver_id

    LEFT JOIN formula1_incr.gold.ref_driver_code dc
    ON dc.driver_id = cp.driver_id

    LEFT JOIN formula1_incr.gold.dim_drivers d
    ON d.driver_id = cp.driver_id
        
    LEFT JOIN formula1_incr.gold.dim_races r
    ON r.season = cp.season AND r.round = cp.round;