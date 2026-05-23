CREATE OR REPLACE VIEW formula1_incr.gold.v_driver_stats
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
        season >= 2020
        AND session_type IN ('RACE')
),

driver_stats AS (
    SELECT
      season
      , driver_id
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
      , driver_id
)

SELECT
   ds.season
   , ds.driver_id
   , d.driver_name
   , dc.fia_driver_code AS driver_code
   , ds.wins
   , ds.podiums
   , ds.finish_in_points
   , ds.pole_positions
   , -1 * ds.`dnf/dns/dsq` AS `dnf/dns/dsq`
   , cr.color_code
 FROM
   driver_stats ds
   LEFT JOIN formula1_incr.gold.v_constructor_reference cr
   ON cr.season = ds.season AND cr.driver_id = ds.driver_id
   LEFT JOIN formula1_incr.gold.ref_driver_code dc
   ON dc.driver_id = ds.driver_id
   LEFT JOIN formula1_incr.gold.dim_drivers d
   ON d.driver_id = ds.driver_id;