CREATE OR REPLACE VIEW formula1_incr.gold.v_constructor_round_wins
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
        season >= 2020 
        AND session_type = 'RACE'
     GROUP BY
        season
        , round
        , constructor_id
),

round_winners AS (
    SELECT
        season
        , round
        , constructor_id
        , round_points
        , RANK() OVER(PARTITION BY season, round ORDER BY round_points DESC) AS round_rank
     FROM
        constructor_points_for_round
     QUALIFY
        round_rank IN (1)
)

SELECT
    rw.season
    , rw.round
    , rw.constructor_id
    , rw.round_rank AS final_position
    , c.constructor_name
    , r.circuit_name
    , REPLACE(r.race_name, 'Grand Prix', 'GP') AS short_race_name
    , COALESCE(cc.color_code, '#7C8AA5') AS color_code
    , cc.logo_svg AS cons_logo
    , COALESCE(
      ci.flag_32_png,
      'https://raw.githubusercontent.com/sathiskumr/formula1-data-engineering-project/main/ref_images/country-flags-png/default-32px.png'
   ) AS flag_png

 FROM 
    round_winners rw

    LEFT JOIN formula1_incr.gold.dim_constructors c   
    ON c.constructor_id = rw.constructor_id

    LEFT JOIN formula1_incr.gold.dim_races r
    ON r.season = rw.season AND r.round = rw.round

    LEFT JOIN formula1_incr.gold.ref_constructor_color_code cc
    ON cc.constructor_id = rw.constructor_id

    LEFT JOIN formula1_incr.gold.ref_country_image ci
    ON ci.country = r.country;