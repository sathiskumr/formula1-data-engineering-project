CREATE OR REPLACE VIEW formula1_incr.gold.v_constructor_standings
AS

-- Base filter (same as drivers)
WITH base_results AS (
    SELECT 
        season
        , round
        , constructor_id
        , points
        , final_position
        , final_position_text
        , status
        , session_type
     FROM 
        formula1_incr.gold.fact_session_results
     WHERE 
        season >= 2020 
        AND session_type IN ('RACE', 'SPRINT')
),

-- Step 1: Constructor summary
constructor_points_summary AS (
    SELECT
        r.season
        , c.constructor_id
        , c.constructor_name
        , c.nationality
        , SUM(r.points) AS total_points
     FROM 
        base_results r
        JOIN formula1_incr.gold.dim_constructors c
        ON r.constructor_id = c.constructor_id
     GROUP BY
        r.season
        , c.constructor_id
        , c.constructor_name
        , c.nationality
),

-- Step 2: Finish distribution (TEAM level)
constructor_finish_stats AS (
    SELECT
        season
        , constructor_id

        -- Best finish
        , MIN(final_position) AS best_finish

        -- Full distribution (aggregated across both drivers)
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

        -- Timing
        , MIN(CASE WHEN final_position = 1 THEN round END) AS first_p1_round
        , MIN(CASE WHEN final_position = 2 THEN round END) AS first_p2_round
        , MIN(CASE WHEN final_position = 3 THEN round END) AS first_p3_round

     FROM 
        base_results
     WHERE 
        session_type = 'RACE' AND final_position IS NOT NULL
        AND final_position > 0
        AND (status = 'Finished' OR status LIKE '+%')
     GROUP BY 
        season, constructor_id
)

-- Step 3: Final ranking
SELECT
    css.season
    , css.constructor_id
    , css.constructor_name
    , css.nationality

    , DENSE_RANK() OVER (
        PARTITION BY css.season
        ORDER BY
            -- 1. Points
            css.total_points DESC

            -- 2. Distribution (team-level)
            , cfs.p1 DESC
            , cfs.p2 DESC
            , cfs.p3 DESC
            , cfs.p4 DESC
            , cfs.p5 DESC
            , cfs.p6 DESC
            , cfs.p7 DESC
            , cfs.p8 DESC
            , cfs.p9 DESC
            , cfs.p10 DESC
            , cfs.p11 DESC
            , cfs.p12 DESC
            , cfs.p13 DESC
            , cfs.p14 DESC
            , cfs.p15 DESC
            , cfs.p16 DESC
            , cfs.p17 DESC
            , cfs.p18 DESC
            , cfs.p19 DESC
            , cfs.p20 DESC

            -- 3. Best finish
            , COALESCE(cfs.best_finish, 999) ASC

            -- 4. Timing
            , COALESCE(cfs.first_p1_round, 999) ASC
            , COALESCE(cfs.first_p2_round, 999) ASC
            , COALESCE(cfs.first_p3_round, 999) ASC

            -- 5. Deterministic fallback
            , css.constructor_id ASC
    ) AS standing

    , css.total_points

    , COALESCE(
        cc.color_code
        , '#7C8AA5'
    ) AS color_code

    , COALESCE(
        cc.logo_svg
        , 'https://raw.githubusercontent.com/sathiskumr/formula1-data-engineering-project/main/ref_images/constructors-svg/default.svg'
    ) AS cons_logo

 FROM 
    constructor_points_summary css
    LEFT JOIN constructor_finish_stats cfs
    ON css.season = cfs.season AND css.constructor_id = cfs.constructor_id
    LEFT JOIN formula1_incr.gold.ref_constructor_color_code CC
    ON CC.constructor_id = css.constructor_id;