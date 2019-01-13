import psycopg2
import logging
import config
import asyncio
from frontierStoreCrawler import FrontierStoreCrawler
from frontierStoreCrawler import FrontierStoreObject

logger = logging.getLogger(__name__)
logger.setLevel(config.logLevel)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

#consolehandler
console = logging.StreamHandler()
console.setLevel(config.logLevel)
console.setFormatter(formatter)
logger.addHandler(console)

class NicedFrontierStoreObject(FrontierStoreObject):

        def __init__(self, id, name, price, url, imageurl, deltaPrice, deltaPricePercent):
            
            super().__init__(id, name, price, url, imageurl)
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

        storeCrawler = FrontierStoreCrawler()
        await storeCrawler.Crawl()

        for item in storeCrawler.AllItems:
            logger.debug("Inserting {0.Name} into DB".format(item))
            cursor.execute("INSERT INTO CurrentStore(id, name, price, url, imageurl) VALUES(%s, %s, %s, %s, %s)", (item.ID, item.Name, item.Value, item.Url, item.ImageUrl))

        logger.debug("Cleaning history")
        cursor.execute("DELETE FROM StoreHistory WHERE isLastRun = 'f' AND historydate < current_timestamp - interval '8 hour'")
        connection.commit()

        logger.debug("Checking if notifications are necessary")
        if self.WhatNew():
            cursor.execute("UPDATE RegisteredBot SET hasBeenNotified = 'f'")
            logger.debug("Setting notification")
            connection.commit()

        cursor.close()
        connection.close()

        logger.info("Refresh completed")



    def RegisterDiscordServerRole(self, serverId, roleId):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("INSERT INTO RegisteredBot(serverId, RoleId, channelId) VALUES(%s, %s, '')", (serverId, roleId))
        logger.info("Registering new server with ID " + serverId)

        connection.commit()

        cursor.close()
        connection.close()



    def UnregisterDiscordServerRole(self, serverId):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("DELETE FROM RegeristedBot WHERE serverId = %s", (serverId))
        logger.info("Removing server with ID " + serverId)

        connection.commit()

        cursor.close()
        connection.close()


    def SetChannelId(self, serverId, channelId):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("UPDATE RegisteredBot SET channelId = %s WHERE serverId = %s", (channelId, serverId))
        logger.debug("Server id {0} set its channel to {1}".format(serverId, channelId))

        connection.commit()

        cursor.close()
        connection.close()



    def GetAllServer(self):

        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        servers = []

        cursor.execute("SELECT serverid, roleid, channelid FROM RegisteredBot")
        for record in cursor.fetchall():
            servers.append(DiscordServer(record[0], record[1], record[2]))

        cursor.close()
        connection.close()

        return servers

    

    def GetServerToNotify(self):
        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        servers = []

        cursor.execute("SELECT serverid, roleid, channelid FROM RegisteredBot WHERE hasBeenNotified = 'f'")
        for record in cursor.fetchall():
            servers.append(DiscordServer(record[0], record[1], record[2]))

        cursor.close()
        connection.close()

        return servers



    def SetServerAsNotified(self, serverId):
        
        connection = psycopg2.connect(self._connectionString)
        cursor = connection.cursor()

        cursor.execute("UPDATE RegisteredBot SET hasBeenNotified = 't' WHERE serverid = '" + serverId + "'")
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