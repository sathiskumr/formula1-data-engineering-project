CREATE OR REPLACE VIEW formula1_incr.gold.v_constructor_evolution
AS

WITH constructor_points_for_round AS ( 
    SELECT
        season
        , round
        , constructor_id
        , SUM(points) AS round_points
    FROM 
        formula1_incr.gold.fact_session_results
    WHERE 
        season >= 2020 AND
        session_type IN ('RACE', 'SPRINT')
    GROUP BY
        season
        , round
        , constructor_id
), 

constructor_cumulative_points AS (
    SELECT
        season
        , round
        , constructor_id
        , round_points
        , SUM(round_points) OVER (
            PARTITION BY season, constructor_id
            ORDER BY round
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_points
    FROM
        constructor_points_for_round
)

SELECT
    cp.season
    , cp.round
    , cp.constructor_id
    , cp.round_points
    , c.constructor_name AS cons_name
    , REPLACE(c.constructor_name, ' Team', '') AS constructor_name
    , RANK() OVER (PARTITION BY cp.season, cp.round ORDER BY cp.cumulative_points DESC) AS constructor_rank
    , cp.cumulative_points
    , r.circuit_name        
    , REPLACE(r.race_name, 'Grand Prix', 'GP') AS short_race_name
    , COALESCE(cc.color_code, '#7C8AA5') AS color_code
    
 FROM
    constructor_cumulative_points cp

    LEFT JOIN formula1_incr.gold.dim_constructors c
    ON c.constructor_id = cp.constructor_id
    
    LEFT JOIN formula1_incr.gold.dim_races r
    ON r.season = cp.season AND r.round = cp.round

    LEFT JOIN formula1_incr.gold.ref_constructor_color_code cc
    ON cc.constructor_id = cp.constructor_id;