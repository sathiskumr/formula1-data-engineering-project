CREATE OR REPLACE VIEW formula1_incr.gold.v_dim_seasons
AS

SELECT 
    DISTINCT season
FROM 
    formula1_incr.gold.fact_session_results
WHERE 
    season >= 2020;