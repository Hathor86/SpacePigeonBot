import mariadb
import logging
import asyncio
import discord
from frontierStoreCrawler import ShipFrontierStoreCrawler
from frontierStoreCrawler import FleetCarrierFrontierStoreCrawler
from frontierStoreCrawler import CommanderFrontierStoreCrawler
from frontierStoreCrawler import FrontierStoreObject
from logging.handlers import WatchedFileHandler
from dotenv import load_dotenv
from os import path
from os import getenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

#consolehandler
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logger.addHandler(console)

#logfile handler
logfile = WatchedFileHandler(path.join(getenv("logPath"), getenv("logFileName")))
logfile.setLevel(logging.DEBUG)
logfile.setFormatter(formatter)
logger.addHandler(logfile)

class NicedFrontierStoreObject(FrontierStoreObject):

        def __init__(self, id, name, price, url, imageurl, deltaPrice, deltaPricePercent):
            
            self._id = id
            self._name = name
            self._value = price
            self._url = url
            self._imageUrl = imageurl
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

        self._connectionString = getenv("connecionString")
        self._database = getenv("database")
        self._dbUser = getenv("dbUser")
        self._dbPassword = getenv("dbPassword")
        self._dbHost = getenv("dbHost")



    async def RefreshFromStore(self):

        logger.info("Refreshing from store")

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        cursor.execute("UPDATE StoreHistory SET islastrun = 'f' WHERE islastrun = 't'")
        cursor.execute("INSERT INTO StoreHistory(id, name, price, url) SELECT id, name, price, url FROM CurrentStore")
        cursor.execute("DELETE FROM CurrentStore")
        connection.commit()

        logger.debug("Current store deleted")

        storeCrawler = [ShipFrontierStoreCrawler(), FleetCarrierFrontierStoreCrawler(), CommanderFrontierStoreCrawler()]
        for crawler in storeCrawler:
            await crawler.Crawl()

            for item in crawler.AllItems:
                logger.debug("Inserting {0.Name} into DB".format(item))
                cursor.execute("INSERT INTO CurrentStore(id, name, price, url, imageurl) VALUES(%s, %s, %s, %s, %s)", (item.ID, item.Name, item.Value, item.Url, item.ImageUrl))

        logger.debug("Cleaning history")
        cursor.execute("DELETE FROM StoreHistory WHERE islastrun = 'f' AND historydate < Date_Sub(Now(), INTERVAL 8 HOUR)")
        connection.commit()

        logger.debug("Checking if notifications are necessary")
        if self.WhatNew():
            cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Done = false")
            logger.debug("Setting notification")
            connection.commit()

        cursor.close()
        connection.close()

        logger.info("Refresh completed")



    def ServerExists(self, server: discord.Guild):

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        cursor.execute("SELECT 1 FROM RegisteredServer WHERE ServerID = %s", (server.id, None))

        test = len(cursor.fetchall()) == 1
        cursor.close()
        connection.close()

        return test




    def RegisterDiscordServer(self, server: discord.Guild):

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        cursor.execute("INSERT INTO RegisteredServer(ServerId, ServerName) VALUES(%s, %s)", (server.id, server.name))
        cursor.execute("INSERT INTO SpacePigeon_Parameter (ServerId, Notification_Role_Id, Notification_Role_Name, Notification_Channel_Id, Notification_Channel_Name, Notification_Done) VALUES (%s, %s, %s, %s, %s, true)", (server.id, server.channels[0].id, server.channels[0].name, server.roles[0].id, server.roles[0].name))
        logger.info("Server {0} (id: {1}) sucessfully registered".format(server.name, server.id))

        connection.commit()

        cursor.close()
        connection.close()



    def UnregisterDiscordServer(self, server: discord.Guild):

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        cursor.execute("DELETE FROM RegisteredServer WHERE serverId = %s", (server.id))
        cursor.execute("DELETE FROM SpacePigeon_Parameter WHERE serverId = %s", (server.id))
        logger.info("Server {0} (id: {1}) sucessfully removed".format(server.name, server.id))

        connection.commit()

        cursor.close()
        connection.close()


    def SetPigeonChannel(self, server: discord.Guild, channel: discord.TextChannel):

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Channel_Id = %s, Notification_Channel_Name = %s WHERE serverId = %s", (channel.id, channel.name, server.id))
        logger.debug("Server {0} set its pigeon channel to {1}".format(server.name, channel.name))

        connection.commit()

        cursor.close()
        connection.close()



    def SetPigeonRole(self, server: discord.Guild, role: discord.Role):

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Role_Id = %s, Notification_Role_Name = %s WHERE serverId = %s", (role.id, role.name, server.id))
        logger.debug("Server {0} set its pigeon role to {1}".format(server.name, role.name))

        connection.commit()

        cursor.close()
        connection.close()



    def GetAllServer(self):

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        servers = []

        cursor.execute("SELECT serverid, Notification_Role_Id, Notification_Channel_Id FROM SpacePigeon_Parameter")
        for record in cursor.fetchall():
            servers.append(DiscordServer(record[0], record[1], record[2]))

        cursor.close()
        connection.close()

        return servers

    

    def GetServerToNotify(self):
        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        servers = []

        cursor.execute("SELECT ServerId, Notification_Role_Id, Notification_Channel_Id FROM SpacePigeon_Parameter WHERE Notification_Done = false")
        for record in cursor.fetchall():
            servers.append(DiscordServer(record[0], record[1], record[2]))

        cursor.close()
        connection.close()

        return servers



    def SetServerAsNotified(self, serverId):
        
        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Done = true WHERE ServerId = '" + serverId + "'")
        logger.debug("Server with ID {0} has been notified".format(serverId))

        connection.commit()

        cursor.close()
        connection.close()



    def Query(self, item):

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
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

        connection = mariadb.connect(database=self._database, user=self._dbUser, password=self._dbPassword, host=self._dbHost)
        cursor = connection.cursor()

        diff = []

        cursor.execute("SELECT id, name, price, deltaPrice, deltaPricePercent, url, imageurl FROM StoreDiff")
        for record in cursor.fetchall():
            diff.append(NicedFrontierStoreObject(record[0], record[1], record[2], record[5], record[6], record[3], record[4]))

        cursor.close()
        connection.close()

        return diff
