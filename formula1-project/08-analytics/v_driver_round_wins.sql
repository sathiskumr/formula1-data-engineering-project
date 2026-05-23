CREATE OR REPLACE VIEW formula1_incr.gold.v_driver_round_wins
AS

WITH round_winners AS (
    SELECT
        season
        , round
        , driver_id
        , constructor_id
        , final_position
    FROM 
        formula1_incr.gold.fact_session_results
    WHERE 
        season >= 2020 
        AND session_type = 'RACE' 
        AND final_position IN (1, 2, 3, 4, 5)
)

SELECT
    rw.season
    , rw.round
    , rw.driver_id
    , rw.constructor_id
    , rw.final_position
    , d.driver_name
    , dc.fia_driver_code AS driver_code
    , CONCAT(
        LEFT(D.driver_name, 1),
        '. ',
        REVERSE(LEFT(REVERSE(D.driver_name), 
            CHARINDEX(' ', REVERSE(D.driver_name)) - 1))
    ) AS short_name
    , r.circuit_name
    , REPLACE(r.race_name, 'Grand Prix', 'GP') AS short_race_name
    , cr.color_code
    , cr.cons_logo
    , COALESCE(
      ci.flag_32_png,
      'https://raw.githubusercontent.com/sathiskumr/formula1-data-engineering-project/main/ref_images/country-flags-png/default-32px.png'
   ) AS flag_png
 FROM 
    round_winners rw
    LEFT JOIN formula1_incr.gold.dim_drivers d   
    ON d.driver_id = rw.driver_id

    LEFT JOIN formula1_incr.gold.dim_races r
    ON R.season = rw.season AND R.round = rw.round

    LEFT JOIN formula1_incr.gold.ref_driver_code dc
    ON dc.driver_id = rw.driver_id

    LEFT JOIN formula1_incr.gold.v_constructor_reference cr
    ON cr.season = rw.season AND cr.driver_id = rw.driver_id

    LEFT JOIN formula1_incr.gold.ref_country_image ci
    ON ci.country = r.country;