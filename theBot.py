#! /usr/bin/python3.6 -u
import discord
import logging
import asyncio
import random
import re
import config
from dataLayer import DataLayer

##########################################
# Empty config.py sample                 #
#                                        #
# import logging                         #
# TOKEN = ''                             #
# logLevel = logging.DEBUG               #
# logLevel = "dbname=theDb user=theUser" #
##########################################

TOKEN = config.TOKEN
VERSION = "2.0"

dataLocker = asyncio.Lock()

logger = logging.getLogger(__name__)
logger.setLevel(config.logLevel)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

#consolehandler
console = logging.StreamHandler()
console.setLevel(config.logLevel)
console.setFormatter(formatter)
logger.addHandler(console)

client = discord.Client()
dataLayer = DataLayer()
allRegisteredServer = []



def SanityCheck():

    logger.info("Performing sanity check")

    currentRegistered = []
    currentRegisteredRole = []
    allServerId = []
    global allRegisteredServer

    allRegisteredServer = dataLayer.GetAllServer()

    for server in allRegisteredServer:
        currentRegistered.append(server.ServerId)
        currentRegisteredRole.append(server.RoleId)

    logger.debug("Checking server where bot is present")

    for server in client.servers:

        logger.debug("Checking {0.name}".format(server))

        allServerId.append(server.id)
        isListOk = False
        for serverId in currentRegistered:
            if serverId == server.id:
                isListOk = True

        if not isListOk:

            logger.info("Server {0.name} not registered, trying registering it".format(server))

            for role in server.roles:

                roleOk = False
                if role.name == "Space Pigeon":

                    logger.debug("Server {0.name} has a role named ""Space Pigeon"", registering it".format(server))

                    dataLayer.RegisterDiscordServerRole(server.id, role.id)
                    roleOk = True
                
                if not roleOk:
                    client.send_message(server.default_channel, "Pas de rôle ""Space Pigeon"" pour ce serveur. Créez-en et tapez .register")
                    logger.warn("No ""Space Pigeon"" role for server {0.name}".format(server))
        
        #TODO : Perfom role & channel check
           

    
    logger.info("Checking registered server in DB")
    logger.debug("Registered id: {0}".format(currentRegistered))

    for serverid in currentRegistered:

        isListOk = False
        for serverid2 in allServerId:
            if serverid2 == serverId:
                isListOk = True
        
        if not isListOk:
            logger.info("Server {0} doesn't use the bot anymore, removing it".format(str(serverid)))
            dataLayer.UnregisterDiscordServerRole(serverid)
    
    allRegisteredServer = dataLayer.GetAllServer()
    logger.info("Sanity check finished")
            


async def PerfomManualRefresh():
    async with dataLocker:
        await client.change_presence(game=discord.Game(name="Inspecte le store"), status=discord.Status.dnd)
        await dataLayer.RefreshFromStore()
        await client.change_presence(game=None, status=discord.Status.online)



async def checkNotify():
    
    await client.wait_until_ready()
    while not client.is_closed:
        logger.debug("Check for notification")
        
        serverToNotify = dataLayer.GetServerToNotify()
        logger.debug("server to notify: {0}".format(serverToNotify))

        if serverToNotify:

            newItemsToBuy = dataLayer.WhatNew()

            for server in serverToNotify:

                servertoPing = client.get_server(server.ServerId)
                logger.debug("server to notify: {0} - id:{1.ServerId}".format(servertoPing, server))
                for role in servertoPing.roles:

                    if role.id == server.RoleId:
                        channel = client.get_channel(server.ChannelId)

                        if len(newItemsToBuy) > 0:
                            dataLayer.SetServerAsNotified(server.ServerId)
                            await client.send_message(channel, "Il y a du neuf sur le store {0.mention} !".format(role))
                            for item in newItemsToBuy:
                                discordFrontierStoreEmbed = discord.Embed(title = "Je craque !", url = item.Url)
                                discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                                if item.DeltaPrice == None:
                                    await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value}€** seulement!".format(item), embed = discordFrontierStoreEmbed)
                                else:
                                    await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value} €** seulement!\nUne réduction de **{0.DeltaPricePercent:.2f}%** soit une économie de **{0.DeltaPrice}€** ! Rendez-vous compte!".format(item), embed = discordFrontierStoreEmbed)
                            
                        break

        await asyncio.sleep(60)



async def refreshData():
    await client.wait_until_ready()
    while not client.is_closed:
        await PerfomManualRefresh()
        await asyncio.sleep(random.randint(21600, 43200)) #6 to 12h



@client.event
async def on_message(message):

    if message.author != client.user:
        
        if message.author.server_permissions.administrator: 
            if client.user.mentioned_in(message):

                match = re.match(r"^.*\s+!(?P<command>\S*)", message.content)
                logger.debug(match)
                logger.debug(message.content)
                if match:
                    command = match.group("command")
                    logger.info("Command found :{0}".format(command))
                    
                    #List of command
                    if command == "channel":
                        dataLayer.SetChannelId(message.server.id, message.channel.id)
                        await client.send_message(message.channel, "Ok {0.author.mention}, je communiquerai les infos dans ce canal".format(message))
                    
                    elif command == "store":
                        await client.send_message(message.channel, "Ok {0.author.mention}, je vais vérifier".format(message))
                        await PerfomManualRefresh()
                        if not dataLayer.WhatNew():
                            await client.send_message(message.channel, "Désolé, rien de nouveau sur le store")


@client.event
async def on_server_join(server):

    roleOk = False
    for role in server.roles:
            if role.name == "Space Pigeon":
                roleOk = True
                logger.info("Server {0.name} add the bot and has a role ""Space Pigeon"", registering it".format(server))
                dataLayer.RegisterDiscordServerRole(server.id, role.id)

    if not roleOk:
        for chan in server.channels:
            if chan.type == discord.ChannelType.text:
                await client.send_message(chan, "Pas de rôle ""Space Pigeon"" pour ce serveur. Créez-en un et tapez .register")
                logger.warn("No ""Space Pigeon"" role for server {0.name}".format(server))
                break

    for channel in server.channels:
        if channel.type  == discord.ChannelType.text:
            dataLayer.SetChannelId(server.id, channel.id)
            await client.send_message(channel, "Je communiquerai dans ce canal, mentionnez-moi en indiquant ""par ici"" dans un autre canal pour changer")
            break



@client.event
async def on_server_remove(server):

    logger.info("Server {0.name} removed the bot, unregistering it".format(server))
    dataLayer.UnregisterDiscordServerRole(server.id)



@client.event
async def on_ready():

    logger.info("Logged in as {0.user.name}".format(client))
    logger.debug("Client id is {0.user.id}".format(client))

    #SanityCheck()


client.loop.create_task(refreshData())
client.loop.create_task(checkNotify())
client.run(TOKEN)