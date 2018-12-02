CREATE TABLE public.storehistory 
(
    id character varying(255),
    name character varying(255),
    price numeric(6,2),
    url character varying(255),
    islastrun boolean DEFAULT true,
    historydate timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_histo_id ON public.storehistory USING btree (id);
CREATE INDEX idx_histo_lastrun ON public.storehistory USING btree (islastrun);