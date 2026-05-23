CREATE OR REPLACE VIEW formula1_incr.gold.v_constructor_reference
AS

WITH base_results AS (
    SELECT 
        season
        , round
        , constructor_id
        , driver_id
     FROM 
        formula1_incr.gold.fact_session_results
     WHERE 
        season >= 2020 
        AND session_type IN ('RACE')
),

-- Resolves season-level constructor attribution using
-- the driver's latest race appearance of the season
driver_max_round AS (
    SELECT
        season
        , driver_id
        , MAX(round) AS max_round
     FROM 
        base_results
     GROUP BY 
        season
        , driver_id
)

SELECT 
    br.season
    , br.driver_id
    , br.constructor_id
    , COALESCE(
        cc.color_code,
        '#7C8AA5'
    ) AS color_code
    , COALESCE(
        cc.logo_svg,
        'https://raw.githubusercontent.com/sathiskumr/formula1-data-engineering-project/main/ref_images/constructors-svg/default.svg'
    ) AS cons_logo
 FROM
    base_results br
    INNER JOIN driver_max_round dmr
    ON dmr.season = br.season AND dmr.max_round = br.round AND dmr.driver_id = br.driver_id
    LEFT JOIN formula1_incr.gold.ref_constructor_color_code CC
    ON cc.constructor_id = br.constructor_id
    LEFT JOIN formula1_incr.gold.dim_races r
    ON r.season = br.season AND r.round = br.round;