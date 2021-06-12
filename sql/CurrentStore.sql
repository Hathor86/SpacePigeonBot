CREATE TABLE CurrentStore 
(
    id character varying(255) NOT NULL PRIMARY KEY,
    name character varying(255),
    price numeric(10,0),
    url character varying(255),
    imageurl character varying(512)
);
CREATE FULLTEXT INDEX idx_item_name ON CurrentStore(name);