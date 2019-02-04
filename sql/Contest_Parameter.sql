CREATE TABLE Contest_Parameter
(
    ServerId character varying(50) PRIMARY KEY NOT NULL REFERENCES RegisteredServer(ServerId)
    ,Contest_Name character varying(50) NOT NULL
    ,Notification_Role_Id character varying(50) NOT NULL 
    ,Notification_Role_Name character varying(50) NOT NULL
    ,Winner_Channel_Id character varying(50) NOT NULL
    ,Winner_Channel_Name character varying(50) NOT NULL
    ,Contest_Count integer NOT NULL DEFAULT 1
);