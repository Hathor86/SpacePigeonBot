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

            if newItemsToBuy:
                for server in serverToNotify:

                    servertoPing = client.get_server(server.ServerId)
                    logger.debug("server to notify: {0} - id:{1.ServerId}".format(servertoPing, server))
                    for role in servertoPing.roles:

                        if role.id == server.RoleId:
                            channel = client.get_channel(server.ChannelId)

                            if len(newItemsToBuy) > 0:
                                dataLayer.SetServerAsNotified(server.ServerId)
                                await client.send_message(channel, "Il y a du neuf sur le store {0.mention} !".format(role))

                                if len(newItemsToBuy) < 6:
                                    for item in newItemsToBuy:
                                        discordFrontierStoreEmbed = discord.Embed(title = "Je craque !", url = item.Url)
                                        discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                                        if item.DeltaPrice == None:
                                            await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value}€** seulement!".format(item), embed = discordFrontierStoreEmbed)
                                        else:
                                            await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value} €** seulement!\nUne réduction de **{0.DeltaPricePercent:.2f}%** soit une économie de **{0.DeltaPrice}€** ! Rendez-vous compte!".format(item), embed = discordFrontierStoreEmbed)
                                else:
                                    newItems = 0
                                    newItemsList = []
                                    discountedItems = 0
                                    discountedItemsList = []
                                    totalDiscount = 0
                                    for item in newItemsToBuy:
                                        if item.DeltaPrice == 0:
                                            newItems += 1
                                            newItemsList.append(item)
                                        else:
                                            discountedItems += 1
                                            discountedItemsList.append(item)
                                            totalDiscount += item.DeltaPrice
                                    
                                    sentence = ""
                                    if newItems != 0:
                                        sentence = newItems + " nouveaux objets"
                                    if sentence != "" and discountedItems != 0:
                                        sentence += " et "
                                    if discountedItems !=0:
                                        sentence += "{0} objets en réduction (une économie possible de **{1:.2f}€**)".format(discountedItems, totalDiscount)
                                    sentence += "\nPar souci pour votre portefeuille, j'en ai sélectionné 5."

                                    await client.send_message(channel, sentence)
                                    await asyncio.sleep(5)

                                    if newItems > 5:
                                        for item in random.sample(newItemsToBuy, 5):
                                            discordFrontierStoreEmbed = discord.Embed(title = "Je craque !", url = item.Url)
                                            discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                                            if item.DeltaPrice == None:
                                                await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value}€** seulement!".format(item), embed = discordFrontierStoreEmbed)
                                            else:
                                                await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value} €** seulement!\nUne réduction de **{0.DeltaPricePercent:.2f}%** soit une économie de **{0.DeltaPrice}€** ! Rendez-vous compte!".format(item), embed = discordFrontierStoreEmbed)
                                    else:
                                        for item in newItemsList:
                                            discordFrontierStoreEmbed = discord.Embed(title = "Je craque !", url = item.Url)
                                            discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                                            await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value}€** seulement!".format(item), embed = discordFrontierStoreEmbed)
                                        for item in random.sample(discountedItemsList, 5 - newItems):
                                            discordFrontierStoreEmbed = discord.Embed(title = "Je craque !", url = item.Url)
                                            discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                                            if item.DeltaPrice == None:
                                                await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value}€** seulement!".format(item), embed = discordFrontierStoreEmbed)
                                            else:
                                                await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value} €** seulement!\nUne réduction de **{0.DeltaPricePercent:.2f}%** soit une économie de **{0.DeltaPrice}€** ! Rendez-vous compte!".format(item), embed = discordFrontierStoreEmbed)
                                
                            break

        await asyncio.sleep(60)



@client.event
async def on_message(message):

    if message.author != client.user:
        
        if client.user.mentioned_in(message):
            
            if message.author.server_permissions.administrator: 
                #Command regex
                match = re.match(r"^{0.mention}\s+!(?P<command>\S*)".format(client.user), message.content)
                logger.debug(match)
                logger.debug(message.content)
                if match:
                    command = match.group("command")
                    logger.info("Command found :{0}".format(command))
                    
                    #List of command
                    if command == "channel":
                        dataLayer.SetChannelId(message.server.id, message.channel.id)
                        await client.send_message(message.channel, "Ok {0.author.mention}, je communiquerai les infos dans ce canal".format(message))
                        return
                    
                    elif command == "store":
                        await client.send_message(message.channel, "Ok {0.author.mention}, je vais vérifier".format(message))
                        await PerfomManualRefresh()
                        if not dataLayer.WhatNew():
                            await client.send_message(message.channel, "Désolé, rien de nouveau sur le store")
                            return
            
            #Query command/regex
            match = re.match(r"^{0.mention}\s+(?P<query>(?:\w+\s*)+)\s*\?$".format(client.user), message.content)
            logger.debug(match)
            logger.debug(message.content)
            if match:
                storeItems = dataLayer.Query(match.group("query"))
                if len(storeItems) == 0:
                    await client.send_message(message.channel, "Hmmm, ça me dit rien ce truc")
                    return
                elif len(storeItems) < 4:
                    await client.send_message(message.channel, "J'ai ça en stock:")
                    for item in storeItems:
                        discordFrontierStoreEmbed = discord.Embed(title = "Faire péter la VISA", url = item.Url)
                        discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                        await client.send_message(message.channel, "**{0.Name}** a **{0.Value}€** seulement!".format(item), embed = discordFrontierStoreEmbed)
                    return
                else:
                    await client.send_message(message.channel, "J'ai {0} objets en stock. Ca fait beaucoup d'argent à dépenser!\nMais je suis sympa, je ne te montre que les 3 premiers:".format(len(storeItems)))
                    for i in range(3):
                        item = storeItems[i]
                        discordFrontierStoreEmbed = discord.Embed(title = "Faire péter la VISA", url = item.Url)
                        discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                        await client.send_message(message.channel, "**{0.Name}** a **{0.Value}€** seulement!".format(item), embed = discordFrontierStoreEmbed)
                    return

        #DSN command
        match = re.match(r"^!poi\s+(?P<poi1>(?P<number1>\d+)(?P<type1>g|b|h|G|t)\s?)?(?P<poi2>(?P<number2>\d+)(?P<type2>g|b|h|G|t)\s?)?(?P<poi3>(?P<number3>\d+)(?P<type3>g|b|h|G|t)\s?)?(?P<poi4>(?P<number4>\d+)(?P<type4>g|b|h|G|t)\s?)?(?P<poi5>(?P<number5>\d+)(?P<type5>g|b|h|G|t)\s?)$", message.content)
        logger.debug(match)
        if match:

            geo = 0
            bio = 0
            human = 0
            guardian = 0
            thargo = 0

            for i in range(1,6):
                if match.group("type" + str(i)):
                    poiType = match.group("type" + str(i))
                    poiCount = int(match.group("number" + str(i)))

                    logger.debug("POI:{0} - Number:{1}".format(poiType, poiCount))

                    if poiType == "g":
                        geo += poiCount
                    elif poiType == "b":
                        bio += poiCount
                    elif poiType == "h":
                        human += poiCount
                    elif poiType == "G":
                        guardian += poiCount
                    elif poiType == "t":
                        thargo += poiCount

            for i in range(1, geo + 1):
                messageSent = await client.send_message(message.channel, "Geological {0}".format(i))
                await client.add_reaction(messageSent, "▶")
            for i in range(1, bio + 1):
                messageSent = await client.send_message(message.channel, "Biological {0}".format(i))
                await client.add_reaction(messageSent, "▶")
            for i in range(1, human + 1):
                messageSent = await client.send_message(message.channel, "Human {0}".format(i))
                await client.add_reaction(messageSent, "▶")
            for i in range(1, guardian + 1):
                messageSent = await client.send_message(message.channel, "Guardian {0}".format(i))
                await client.add_reaction(messageSent, "▶")
            for i in range(1, thargo + 1):
                messageSent = await client.send_message(message.channel, "Thargoid {0}".format(i))
                await client.add_reaction(messageSent, "▶")

            return



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



client.loop.create_task(checkNotify())
client.run(TOKEN)