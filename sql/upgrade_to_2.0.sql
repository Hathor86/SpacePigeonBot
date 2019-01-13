ALTER TABLE CurrentStore ADD COLUMN imageurl character varying(512);
CREATE OR REPLACE VIEW StoreDiff AS
SELECT 
    s.id,
    s.name,
    s.price,
    (s.price - h.price) AS deltaprice,
    CASE
        WHEN (h.price <> 0) THEN ((s.price - h.price) / h.price) * 100
        ELSE s.price - h.price
    END AS deltapricepercent,
    s.url,
    s.imageurl
FROM 
    CurrentStore s
    LEFT JOIN StoreHistory h 
    ON (h.id = s.id AND h.islastrun = true)
WHERE 
    h.id IS NULL OR s.price - h.price > 0;