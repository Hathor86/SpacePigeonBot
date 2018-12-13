#! /usr/bin/python3.6 -u
import discord
import logging
import asyncio
import config
from dataLayer import DataLayer
from discord.ext import commands

TOKEN = config.TOKEN

logger = logging.getLogger("botLogger")
logger.setLevel(config.logLevel)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

#consolehandler
console = logging.StreamHandler()
console.setLevel(config.logLevel)
console.setFormatter(formatter)
logger.addHandler(console)

#client = discord.Client()
client = commands.Bot(command_prefix = ".", description = "Space Pigeon Bot")
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
            


async def checkNotify():
    
    await client.wait_until_ready()
    while not client.is_closed:
        logger.debug("Check for notification")        
        
        serverToNotify = dataLayer.GetServerToNotify()
        logger.debug("server to notify: {0}".format(serverToNotify))

        if serverToNotify:

            newItemsToBuy = dataLayer.WhatNew()
            discordFrontierStoreEmbed = discord.Embed(title="Frontier Store", url="https://www.frontierstore.net/eur/game-extras/elite-dangerous-game-extras.html")

            for item in newItemsToBuy:
                if item.DeltaPrice == None:
                    discordFrontierStoreEmbed.add_field(name = item.Name, value = "A **{0.Value}€** seulement!".format(item), inline = False)
                else:
                    discordFrontierStoreEmbed.add_field(name = item.Name, value = "A **{0.Value} €** seulement!\nUne réduction de **{0.DeltaPricePercent:.2f}%** soit une économie de **{0.DeltaPrice}€** ! Rendez-vous compte!".format(item), inline = False)


            for server in serverToNotify:

                servertoPing = client.get_server(server.ServerId)
                logger.debug("server to notify: {0} - id:{1.ServerId}".format(servertoPing, server))
                for role in servertoPing.roles:

                    if role.id == server.RoleId:
                        channel = client.get_channel(server.ChannelId)

                        if len(newItemsToBuy) == 0:
                            await client.send_message(channel, "Rien de neuf à acheter")
                        else:                        
                            await client.send_message(channel, "Il y a du neuf sur le store {0.mention} !".format(role), embed=discordFrontierStoreEmbed)                        
                            
                        dataLayer.SetServerAsNotified(server.ServerId)
                        break

        await asyncio.sleep(300)



@client.command(pass_context = True)
async def register(context):

    global allRegisteredServer

    if context.message.author.server_permissions.administrator:
        for server in allRegisteredServer:
            if server.ServerId == context.message.server.id:
                return

        for role in context.message.server.roles:
            if role.name == "Space Pigeon":
                logger.info("Server {0.name} add the bot and has a role ""Space Pigeon"", registering it".format(context.message.server))
                dataLayer.RegisterDiscordServerRole(context.message.server.id, role.id)
                allRegisteredServer = dataLayer.GetAllServer()
                return
        
        client.say("Pas de rôle ""Space Pigeon"" pour ce serveur. Créez-en et tapez .register")
    else:
        client.say("T'es pas admin, pigeon!")



@client.event
async def on_message(message):

    if message.author.server_permissions.administrator: 
        if client.user.mentioned_in(message):
            if "par ici" in message.content:
                dataLayer.SetChannelId(message.server.id, message.channel.id)
                await client.send_message(message.channel, "Ok, {0.author.mention}, je communiquerai les infos dans ce canal".format(message))

        


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