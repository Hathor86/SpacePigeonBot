CREATE TABLE SpacePigeon_Parameter
(
    ServerId character varying(50) PRIMARY KEY NOT NULL REFERENCES RegisteredServer(ServerId)
    ,Notification_Role_Id character varying(50) NOT NULL 
    ,Notification_Role_Name character varying(50)
    ,Notification_Channel_Id character varying(50) NOT NULL 
    ,Notification_Channel_Name character varying(50)
    ,Notification_Done boolean NOT NULL DEFAULT false
);