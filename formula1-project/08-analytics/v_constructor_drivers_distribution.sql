CREATE OR REPLACE VIEW formula1_incr.gold.v_constructor_drivers_distribution
AS

WITH driver_constructor_points AS (
    SELECT 
        season
        , constructor_id
        , driver_id
        , SUM(points) AS driver_points
    FROM formula1_incr.gold.fact_session_results
    WHERE
        season >= 2020
        AND session_type IN ('RACE', 'SPRINT')
    GROUP BY
        season
        , constructor_id
        , driver_id
),

constructor_totals AS (
    SELECT
        season
        , constructor_id
        , SUM(driver_points) AS constructor_points
        , MAX(SUM(driver_points)) OVER (PARTITION BY season) AS max_constructor_points
    FROM 
        driver_constructor_points
    GROUP BY 
        season
        , constructor_id
    QUALIFY constructor_points = max_constructor_points
)

SELECT
    dcp.season
    , dcp.constructor_id
    , ct.max_constructor_points
    , dcp.driver_id
    , d.driver_name
    , CONCAT(
        LEFT(d.driver_name, 1),
        '. ',
        REVERSE(LEFT(REVERSE(d.driver_name), 
            CHARINDEX(' ', REVERSE(d.driver_name)) - 1))
    ) AS short_name
    , dcp.driver_points AS total_driver_points_for_his_constructor
    , COALESCE(cc.color_code, '#7C8AA5') AS color_code
FROM 
    driver_constructor_points AS dcp

    JOIN constructor_totals AS ct
    ON  dcp.season          = ct.season
    AND dcp.constructor_id  = ct.constructor_id

    LEFT JOIN formula1_incr.gold.dim_drivers d
    ON d.driver_id = dcp.driver_id

    LEFT JOIN formula1_incr.gold.ref_constructor_color_code cc
    ON cc.constructor_id = dcp.constructor_id;