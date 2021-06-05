#! /usr/bin/python -u
import discord
import logging
from logging.handlers import WatchedFileHandler
from os import path
from os import remove
from os import getenv
from discord.abc import GuildChannel
from dotenv import load_dotenv
import asyncio
import random
import re
import urllib
import atexit
from dataLayer import DataLayer

##########################################
# Empty .env sample                      #
#                                        #
# TOKEN = ''                             #
# logLevel = logging.DEBUG               #
# connectionString = ""                  #
# refreshTick = 240                      #
# logPath = ""                           #
# logFileName = "spacepigeon.log"        #
##########################################

TOKEN = getenv("TOKEN")
VERSION = "3.0"
REFRESH = int(getenv("refreshTick"))
CURRENTTICK = 0
ARXAVGPRICE = 0.0006213672

dataLocker = asyncio.Lock()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

#console handler
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(formatter)
logger.addHandler(console)

#logfile handler
logfile = WatchedFileHandler(path.join(getenv("logPath"), getenv("logFileName")))
logfile.setLevel(logging.DEBUG)
logfile.setFormatter(formatter)
logger.addHandler(logfile)

client = discord.Client()
dataLayer = DataLayer()
allRegisteredServer = []



def GetRole(serverId, roleId):
    server = client.get_guild(serverId)
    for role in server.roles:
        if role.id == roleId:
            return role



async def PerfomManualRefresh():
    async with dataLocker:
        await client.change_presence(activity = discord.Game(name="Inspecte le store"), status = discord.Status.dnd)
        await dataLayer.RefreshFromStore()
        await client.change_presence(game = None, status = discord.Status.online)



async def checkNotify():
    
    await client.wait_until_ready()    
    while not client.is_closed() and client.is_ready():
        logger.debug("Check for notification")
        
        serverToNotify = dataLayer.GetServerToNotify()
        logger.debug("server to notify: {0}".format(serverToNotify))

        if serverToNotify:

            newItemsToBuy = dataLayer.WhatNew()

            if newItemsToBuy:
                for server in serverToNotify:

                    role = client.guilds[0].get_role(int(server.RoleId))
                    channel = client.guilds[0].get_channel(int(server.ChannelId))

                    if len(newItemsToBuy) > 0:
                        dataLayer.SetServerAsNotified(server.ServerId)
                        await client.send_message(channel, "Il y a du neuf sur le store {0.mention} !".format(role))

                        if len(newItemsToBuy) < 6:
                            for item in newItemsToBuy:
                                discordFrontierStoreEmbed = discord.Embed(title = "Je craque !", url = item.Url)
                                discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                                if item.DeltaPrice == None:
                                    await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value} ARX** ({1}€ environ) seulement!".format(item, item.Value * ARXAVGPRICE), embed = discordFrontierStoreEmbed)
                                else:
                                    await client.send_message(channel, "Un superbe **{0.Name}** a **{0.Value} ARX** seulement!\nUne réduction de **{0.DeltaPricePercent:.2f}%** soit une économie de **{0.DeltaPrice}€** ! Rendez-vous compte!".format(item), embed = discordFrontierStoreEmbed)
                        else:
                            newItems = 0
                            newItemsList = []
                            discountedItems = 0
                            discountedItemsList = []
                            totalDiscount = 0
                            for item in newItemsToBuy:
                                if not item.DeltaPrice:
                                    newItems += 1
                                    newItemsList.append(item)
                                else:
                                    discountedItems += 1
                                    discountedItemsList.append(item)
                                    totalDiscount += item.DeltaPrice
                            
                            sentence = ""
                            if newItems != 0:
                                sentence = str(newItems) + " nouveaux objets"
                            if sentence != "" and discountedItems != 0:
                                sentence += " et "
                            if discountedItems !=0:
                                sentence += "{0} objets en réduction (une économie possible de **{1:.2f}€**)".format(discountedItems, totalDiscount)
                            sentence += "\nPar souci pour votre portefeuille, j'en ai sélectionné 5."

                            await client.send_message(channel, sentence)
                            await client.send_typing(channel)
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

        global CURRENTTICK
        CURRENTTICK += 1
        if CURRENTTICK > REFRESH:
            CURRENTTICK = 0
            await PerfomManualRefresh()
        
        await asyncio.sleep(60)


@atexit.register
async def close_handle():
    print("test")
    client.close()



@client.event
async def on_message(message):

    if message.author != client.user:
        
        if client.user.mentioned_in(message):

            #help command
            match = re.match(r"^{0.mention}\s+help$".format(client.user), message.content)
            if match:
                discordEmbed = discord.Embed(title = "Commandes disponibles")

                #regular commands
                discordEmbed.add_field(name = "@Mention help", value = "Affiche cette aide", inline = False)
                discordEmbed.add_field(name = "@Mention objet_du_store ?", value = "Recherche un objet sur le store frontier", inline = False)

                if message.author.server_permissions.administrator:
                    #admin command
                    discordEmbed.add_field(name = "@Mention !pigeon_channel", value = "Change le canal de notification des Space Pigeon pour le canal courant; celui d'où cette commande a été lancée.", inline = False)
                    discordEmbed.add_field(name = "@Mention !pigeon_role @Role", value = "Change le role de notification des space pigeon pour le mentionné", inline = False)
                    discordEmbed.add_field(name = "@Mention !store", value = "Lance une vérification du store frontier; tous les serveurs seront notifiés si il y a du neuf.", inline = False)
                
                await client.send_message(message.author, "Voici ce que votre humble serviteur peut faire pour vous", embed = discordEmbed)
                return
            
            if message.author.guild_permissions.administrator: 
                #Admin Command regex
                match = re.match(r"^{0.mention}\s+!(?P<command>\S*)\s+(?P<parameters>.*)$".format(client.user), message.content)
                logger.debug(match)
                logger.debug(message.content)
                if match:
                    command = match.group("command")
                    logger.info("Admin command found :{0}".format(command))
                    logger.info("Parameters :{0}".format(match.group("parameters")))
                    
                    #List of command
                    if command == "pigeon_channel":
                        dataLayer.SetPigeonChannel(message.server.id, message.channel.id, message.channel.name)
                        await client.send_message(message.channel, "Ok {0.author.mention}, je communiquerai les infos dans ce canal".format(message))
                        return

                    elif command == "pigeon_role":
                        if message.role_mentions:
                            dataLayer.SetPigeonRole(message.server.id, message.role_mentions[0].id, message.role_mentions[0].name)
                            await client.send_message(message.channel, "Ok {0.author.mention}, le rôle {1.name} sera pingé".format(message, message.role_mentions[0]))
                            return
                    
                    elif command == "store":
                        await client.send_message(message.channel, "Ok {0.author.mention}, je vais vérifier".format(message))
                        await PerfomManualRefresh()
                        if not dataLayer.WhatNew():
                            await client.send_message(message.channel, "Désolé, rien de nouveau sur le store")
                        return

                    elif command == "reset_tick":
                        global CURRENTTICK
                        CURRENTTICK = 0
                        logger.info("Tick reset. Next refresh in 4 hours")
                        return


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



@client.event
async def on_guild_join(server):
    logger.info("Server {0.name} add the bot, registering it".format(server))
    dataLayer.RegisterDiscordServer(server.id, server.name)



@client.event
async def on_guild_join(server):
    logger.info("Server {0.name} removed the bot, unregistering it".format(server))
    dataLayer.UnregisterDiscordServer(server.id, server.name)



@client.event
async def on_ready():

    logger.info("Logged in as {0.user.name}".format(client))
    logger.debug("Client id is {0.user.id}".format(client))
    logger.debug("Checking DB consistance")
    for server in client.guilds:
        if not dataLayer.ServerExists(server):
            logger.warning("Server {0.name} does not exists".format(server))
            dataLayer.RegisterDiscordServer(server)



#@client.event
#async def on_error():


client.loop.create_task(checkNotify())
client.run(TOKEN)