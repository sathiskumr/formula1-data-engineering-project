CREATE OR REPLACE VIEW formula1_incr.gold.v_driver_standings
AS

-- Base filter
WITH base_results AS (
    SELECT 
        season
        , round
        , constructor_id
        , driver_id
        , points
        , final_position
        , status
        , session_type
     FROM 
        formula1_incr.gold.fact_session_results
     WHERE 
        season >= 2020 
        AND session_type IN ('RACE', 'SPRINT')
),

-- Step 1: Driver summary (points + high-level stats)
driver_points_summary AS (
    SELECT
        r.season
        , d.driver_id
        , d.driver_name
        , d.nationality
        , SUM(r.points) AS total_points
    FROM 
        base_results r
        JOIN formula1_incr.gold.dim_drivers d
        ON r.driver_id = d.driver_id
    GROUP BY
        r.season
        , d.driver_id
        , d.driver_name
        , d.nationality
),

-- Step 2: Finish distribution + best finish + timing
driver_finish_stats AS (
    SELECT
        season
        , driver_id

        -- Best finish (handles >P20 and 0-point drivers)
        , MIN(final_position) AS best_finish

        -- Full distribution (FIA tie-breaking)
        , SUM(CASE WHEN final_position = 1 THEN 1 ELSE 0 END) AS p1
        , SUM(CASE WHEN final_position = 2 THEN 1 ELSE 0 END) AS p2
        , SUM(CASE WHEN final_position = 3 THEN 1 ELSE 0 END) AS p3
        , SUM(CASE WHEN final_position = 4 THEN 1 ELSE 0 END) AS p4
        , SUM(CASE WHEN final_position = 5 THEN 1 ELSE 0 END) AS p5
        , SUM(CASE WHEN final_position = 6 THEN 1 ELSE 0 END) AS p6
        , SUM(CASE WHEN final_position = 7 THEN 1 ELSE 0 END) AS p7
        , SUM(CASE WHEN final_position = 8 THEN 1 ELSE 0 END) AS p8
        , SUM(CASE WHEN final_position = 9 THEN 1 ELSE 0 END) AS p9
        , SUM(CASE WHEN final_position = 10 THEN 1 ELSE 0 END) AS p10
        , SUM(CASE WHEN final_position = 11 THEN 1 ELSE 0 END) AS p11
        , SUM(CASE WHEN final_position = 12 THEN 1 ELSE 0 END) AS p12
        , SUM(CASE WHEN final_position = 13 THEN 1 ELSE 0 END) AS p13
        , SUM(CASE WHEN final_position = 14 THEN 1 ELSE 0 END) AS p14
        , SUM(CASE WHEN final_position = 15 THEN 1 ELSE 0 END) AS p15
        , SUM(CASE WHEN final_position = 16 THEN 1 ELSE 0 END) AS p16
        , SUM(CASE WHEN final_position = 17 THEN 1 ELSE 0 END) AS p17
        , SUM(CASE WHEN final_position = 18 THEN 1 ELSE 0 END) AS p18
        , SUM(CASE WHEN final_position = 19 THEN 1 ELSE 0 END) AS p19
        , SUM(CASE WHEN final_position = 20 THEN 1 ELSE 0 END) AS p20

        -- Timing (only used if distribution is identical)
        , MIN(CASE WHEN final_position = 1 THEN round END) AS first_p1_round
        , MIN(CASE WHEN final_position = 2 THEN round END) AS first_p2_round
        , MIN(CASE WHEN final_position = 3 THEN round END) AS first_p3_round

     FROM 
        base_results
     WHERE 
        session_type = 'RACE'
        AND final_position IS NOT NULL
        AND final_position > 0
        AND (status = 'Finished' OR status LIKE '+%')
     GROUP BY
        season
        , driver_id
)

-- Step 3: Final ranking
SELECT
    dss.season
    , dss.driver_id
    , dss.driver_name
    , CONCAT(
        LEFT(dss.driver_name, 1),
        '. ',
        REVERSE(LEFT(REVERSE(dss.driver_name), 
            CHARINDEX(' ', REVERSE(dss.driver_name)) - 1))
    ) AS short_name
    , dss.nationality

    , DENSE_RANK() OVER (
        PARTITION BY dss.season
        ORDER BY
            -- 1. Points
            dss.total_points DESC

            -- 2. Distribution (FIA primary tie-breakers)
            , dfs.p1 DESC
            , dfs.p2 DESC
            , dfs.p3 DESC
            , dfs.p4 DESC
            , dfs.p5 DESC
            , dfs.p6 DESC
            , dfs.p7 DESC
            , dfs.p8 DESC
            , dfs.p9 DESC
            , dfs.p10 DESC
            , dfs.p11 DESC
            , dfs.p12 DESC
            , dfs.p13 DESC
            , dfs.p14 DESC
            , dfs.p15 DESC
            , dfs.p16 DESC
            , dfs.p17 DESC
            , dfs.p18 DESC
            , dfs.p19 DESC
            , dfs.p20 DESC

            -- 3. Best finish (handles >P20 and 0-point ties)
            , COALESCE(dfs.best_finish, 999) ASC

            -- 4. Timing (earliest achievement)
            , COALESCE(dfs.first_p1_round, 999) ASC
            , COALESCE(dfs.first_p2_round, 999) ASC
            , COALESCE(dfs.first_p3_round, 999) ASC

            -- 5. Deterministic fallback
            , dss.driver_id ASC
    ) AS standing

    , dss.total_points
    , cr.constructor_id
    , cr.color_code
    , cr.cons_logo

 FROM 
    driver_points_summary dss
    LEFT JOIN driver_finish_stats dfs
    ON dss.season = dfs.season AND dss.driver_id = dfs.driver_id
    LEFT JOIN formula1_incr.gold.v_constructor_reference cr
    ON cr.season = dss.season AND cr.driver_id = dss.driver_id;