/* Create table registeredServer and spacepigeon_param before running this */
INSERT INTO RegisteredServer (select serverid from registeredbot);
INSERT INTO SpacePigeon_Parameter(ServerId, Notification_Role_Id, Notification_Channel_Id, Notification_Done) 
(SELECT serverid, roleid, channelid, true FROM registeredbot);