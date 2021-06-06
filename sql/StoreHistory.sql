CREATE TABLE StoreHistory 
(
    id character varying(255),
    name character varying(255),
    price numeric(10,0),
    url character varying(255),
    islastrun boolean DEFAULT true,
    historydate datetime DEFAULT NOW()
);

CREATE INDEX idx_histo_id ON StoreHistory (id);
CREATE INDEX idx_histo_lastrun ON StoreHistory (islastrun);