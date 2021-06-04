#import mariadb
import logging
import config
import asyncio
from frontierStoreCrawler import ShipFrontierStoreCrawler
from frontierStoreCrawler import FleetCarrierFrontierStoreCrawler
from frontierStoreCrawler import CommanderFrontierStoreCrawler
from frontierStoreCrawler import FrontierStoreObject
from logging.handlers import WatchedFileHandler
from os import path

logger = logging.getLogger(__name__)
logger.setLevel(config.logLevel)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

#consolehandler
console = logging.StreamHandler()
console.setLevel(config.logLevel)
console.setFormatter(formatter)
logger.addHandler(console)

#logfile handler
logfile = WatchedFileHandler(path.join(config.logPath, config.logFileName))
logfile.setLevel(config.logLevel)
logfile.setFormatter(formatter)
logger.addHandler(logfile)

class NicedFrontierStoreObject(FrontierStoreObject):

        def __init__(self, id, name, price, url, imageurl, deltaPrice, deltaPricePercent):
            
            super()._id = id
            super()._name = name
            super()._value = price
            super()._url = url
            super()._imageUrl = imageurl
            self._deltaPrice = deltaPrice
            self._deltaPricePercent = deltaPricePercent



        @property
        def DeltaPrice(self):
            return self._deltaPrice

        @property
        def DeltaPricePercent(self):
            return self._deltaPricePercent


class DiscordServer():

    def __init__(self, serverId, roleId, channelId = ""):

        self._serverId = serverId
        self._roleId = roleId
        self._channelId = channelId



    @property
    def ServerId(self):
        return self._serverId

    @property
    def RoleId(self):
        return self._roleId

    @property
    def ChannelId(self):
        return self._channelId



class DataLayer():

    def __init__(self):

        self._connectionString = config.connectionString



    async def RefreshFromStore(self):

        logger.info("Refreshing from store")

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("UPDATE storeHistory SET isLastRun = 'f' WHERE isLastRun = 't'")
        cursor.execute("INSERT INTO storeHistory(id, name, price, url) SELECT id, name, price, url FROM currentStore")
        cursor.execute("DELETE FROM currentStore")

        logger.debug("Current store deleted")

        storeCrawler = [ShipFrontierStoreCrawler(), FleetCarrierFrontierStoreCrawler(), CommanderFrontierStoreCrawler()]
        for crawler in storeCrawler:
            await crawler.Crawl()

            for item in crawler.AllItems:
                logger.debug("Inserting {0.Name} into DB".format(item))
                cursor.execute("INSERT INTO CurrentStore(id, name, price, url, imageurl) VALUES(%s, %s, %s, %s, %s)", (item.ID, item.Name, item.Value, item.Url, item.ImageUrl))

        logger.debug("Cleaning history")
        cursor.execute("DELETE FROM StoreHistory WHERE isLastRun = 'f' AND historydate < current_timestamp - interval '8 hour'")
        connection.commit()

        logger.debug("Checking if notifications are necessary")
        if self.WhatNew():
            cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Done = false")
            logger.debug("Setting notification")
            connection.commit()

        cursor.close()
        connection.close()

        logger.info("Refresh completed")



    def RegisterDiscordServer(self, serverId, serverName):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("INSERT INTO RegisteredBot(ServerId, ServerName) VALUES(%s, %s)", (serverId, serverName))
        logger.info("Server {0} (id: {1}) sucessfully registered".format(serverName, serverId))

        connection.commit()

        cursor.close()
        connection.close()



    def UnregisterDiscordServer(self, serverId, serverName):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("DELETE FROM RegisteredServer WHERE serverId = %s", (serverId))
        logger.info("Server {0} (id: {1}) sucessfully removed".format(serverName, serverId))

        connection.commit()

        cursor.close()
        connection.close()


    def SetPigeonChannel(self, serverId, channelId, channelName):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Channel_Id = %s, Notification_Channel_Name = %s WHERE serverId = %s", (channelId, channelName, serverId))
        logger.debug("Server id {0} set its pigeon channel to {1}".format(serverId, channelName))

        connection.commit()

        cursor.close()
        connection.close()



    def SetPigeonRole(self, serverId, roleId, roleName):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Role_Id = %s, Notification_Role_Name = %s WHERE serverId = %s", (roleId, roleName, serverId))
        logger.debug("Server id {0} set its pigeon role to {1}".format(serverId, roleName))

        connection.commit()

        cursor.close()
        connection.close()



    def GetAllServer(self):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        servers = []

        cursor.execute("SELECT serverid, Notification_Role_Id, Notification_Channel_Id FROM SpacePigeon_Parameter")
        for record in cursor.fetchall():
            servers.append(DiscordServer(record[0], record[1], record[2]))

        cursor.close()
        connection.close()

        return servers

    

    def GetServerToNotify(self):
        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        servers = []

        cursor.execute("SELECT ServerId, Notification_Role_Id, Notification_Channel_Id FROM SpacePigeon_Parameter WHERE Notification_Done = false")
        for record in cursor.fetchall():
            servers.append(DiscordServer(record[0], record[1], record[2]))

        cursor.close()
        connection.close()

        return servers



    def SetServerAsNotified(self, serverId):
        
        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Done = 't' WHERE ServerId = '" + serverId + "'")
        logger.debug("Server with ID {0} has been notified".format(serverId))

        connection.commit()

        cursor.close()
        connection.close()



    def Query(self, item):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        items = []

        item = "%" + item.lower().replace(" ", "%") + "%"
        logger.debug(item)
        cursor.execute("SELECT id, name, price, url, imageurl FROM CurrentStore WHERE lower(name) like %s", (item,))
        for record in cursor.fetchall():
            items.append(FrontierStoreObject(record[0], record[1], record[2], record[3], record[4]))
        
        cursor.close()
        connection.close()

        return items



    def WhatNew(self):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        diff = []

        cursor.execute("SELECT id, name, price, deltaPrice, deltaPricePercent, url, imageurl FROM StoreDiff")
        for record in cursor.fetchall():
            diff.append(NicedFrontierStoreObject(record[0], record[1], record[2], record[5], record[6], record[3], record[4]))

        cursor.close()
        connection.close()

        return diff
