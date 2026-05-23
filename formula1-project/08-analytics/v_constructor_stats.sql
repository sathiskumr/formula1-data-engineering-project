CREATE OR REPLACE VIEW formula1_incr.gold.v_constructor_stats
AS

WITH base_results AS (
    SELECT 
        season
        , round
        , constructor_id
        , driver_id
        , grid_position
        , completed_laps
        , car_number
        , points
        , final_position
        , final_position_text
        , status
        , session_type
        , is_win
        , is_podium
        , has_points
        , is_pole
     FROM 
        formula1_incr.gold.fact_session_results
     WHERE 
        season >= 2010 
        AND session_type IN ('RACE')
),

constructor_stats AS (
    SELECT 
        season
        , constructor_id
        , COUNT_IF(is_win) AS wins
        , COUNT_IF(is_podium) AS podiums
        , COUNT_IF(has_points) AS finish_in_points
        , COUNT_IF(is_pole) AS pole_positions
        , COUNT_IF(
            status NOT IN ('Finished', 'Lapped')
            AND status NOT LIKE '+% Lap%'
        )  AS `DNF/DNS/DSQ`
     FROM
        base_results
     GROUP BY
        season
        , constructor_id
)

SELECT
    cs.season
    , cs.constructor_id
    , c.constructor_name
    , COALESCE(
        cc.color_code
        , '#7C8AA5'
    ) AS color_code

    , COALESCE(
        cc.logo_32_white_png
        , 'https://raw.githubusercontent.com/sathiskumr/formula1-data-engineering-project/main/ref_images/constructors-png/default.png'
    ) AS cons_logo_png
    , cs.wins
    , cs.podiums
    , cs.finish_in_points
    , cs.pole_positions
    , -1 * cs.`dnf/dns/dsq` AS `dnf/dns/dsq`
 FROM
    constructor_stats cs
    LEFT JOIN formula1_incr.gold.ref_constructor_color_code cc
    ON CC.constructor_id = cs.constructor_id
    LEFT JOIN formula1_incr.gold.dim_constructors c
    ON C.constructor_id = cs.constructor_id;