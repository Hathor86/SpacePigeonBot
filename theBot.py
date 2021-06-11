#! /usr/bin/python -u
import asyncio
import atexit
import logging
from math import e
import random
import re
from logging.handlers import WatchedFileHandler
from os import getenv, path

import discord
from discord.ext import commands
from dotenv import load_dotenv

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

load_dotenv()

TOKEN = getenv("TOKEN")
VERSION = "3.0"
REFRESH = int(getenv("refreshTick"))
ARXAVGPRICE = 0.0006213672
CURRENTTICK = 0

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

#client = discord.Client()
bot = commands.Bot(command_prefix="!")
dataLayer = DataLayer()
allRegisteredServer = []



async def PerfomManualRefresh():
    async with dataLocker:
        await bot.change_presence(activity = discord.Game(name="Inspecte le store"), status = discord.Status.dnd)
        await dataLayer.RefreshFromStore()
        await bot.change_presence(activity= None, status = discord.Status.online)


#@tasks.loop(seconds=60)
async def checkNotify():
    
    await bot.wait_until_ready()    
    while not bot.is_closed() and bot.is_ready():
        logger.debug("Check for notification")
        
        serverToNotify = dataLayer.GetServerToNotify()
        logger.debug("server to notify: {0}".format(serverToNotify))

        if serverToNotify:

            newItemsToBuy = dataLayer.WhatNew()

            if newItemsToBuy:
                for server in serverToNotify:

                    real_Server = bot.get_guild(int(server.ServerId))
                    role = real_Server.get_role(int(server.RoleId))
                    channel = real_Server.get_channel(int(server.ChannelId))    

                    if channel:
                        await channel.send("Il y a du neuf sur le store {0.mention} !".format(role))                        
                    else:
                        dataLayer.SetServerAsNotified(server.ServerId)
                        continue

                    if len(newItemsToBuy) < 6:
                        for item in newItemsToBuy:
                            discordFrontierStoreEmbed = discord.Embed(title = "Je craque !", url = item.Url)
                            discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                            if item.DeltaPrice == None:
                                await channel.send("Un superbe **{0.Name}** a **{0.Value} ARX** ({1:.2f}€ environ) seulement!".format(item, item.Value * ARXAVGPRICE), embed = discordFrontierStoreEmbed)
                            else:
                                await channel.send("Un superbe **{0.Name}** a **{0.Value} ARX** ({1:.2f}€ environ) seulement!\nUne réduction de **{0.DeltaPricePercent:.2f}%** soit une économie de **{0.DeltaPrice} ARX** ({2:.2f}€ environ) ! Rendez-vous compte!".format(item, item.Value * ARXAVGPRICE, int(item.DeltaPrice) * ARXAVGPRICE), embed = discordFrontierStoreEmbed)
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
                            sentence += "{0} objets en réduction (une économie possible de **{1:.2f} ARX** ({2:.2f}€ environ))".format(discountedItems, totalDiscount, totalDiscount * ARXAVGPRICE)
                        sentence += "\nPar souci pour votre portefeuille, j'en ai sélectionné 5."

                        await channel.send(sentence)

                        async with channel.typing():

                            await asyncio.sleep(5)
                            for item in random.sample(newItemsToBuy, 5):
                                    discordFrontierStoreEmbed = discord.Embed(title = "Je craque !", url = item.Url)
                                    discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
                                    if item.DeltaPrice == None:
                                        await channel.send("Un superbe **{0.Name}** a **{0.Value} ARX** ({1:.2f}€ environ) seulement!".format(item, item.Value * ARXAVGPRICE), embed = discordFrontierStoreEmbed)
                                    else:
                                        await channel.send("Un superbe **{0.Name}** a **{0.Value} ARX** ({1:.2f}€ environ) seulement!\nUne réduction de **{0.DeltaPricePercent:.2f}%** soit une économie de **{0.DeltaPrice} ARX** ({2:.2f}€ environ) ! Rendez-vous compte!".format(item, item.Value * ARXAVGPRICE, int(item.DeltaPrice) * ARXAVGPRICE), embed = discordFrontierStoreEmbed)      
                        
                    dataLayer.SetServerAsNotified(server.ServerId)

        global CURRENTTICK
        CURRENTTICK += 1
        if CURRENTTICK > REFRESH:
            CURRENTTICK = 0
            await PerfomManualRefresh()
        
        await asyncio.sleep(60)


@atexit.register
async def close_handle():
    print("test")
    bot.close()




@bot.command()
async def pigeon(ctx, *, args):
    storeItems = dataLayer.Query(args)

    if len(storeItems) == 0:
        await ctx.send("Hmmm, ça me dit rien ce truc")

    elif len(storeItems) < 4:
        await ctx.send("J'ai ça en stock:")
        for item in storeItems:
            discordFrontierStoreEmbed = discord.Embed(title = "Faire péter les ARX", url = item.Url)
            discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
            await ctx.send("**{0.Name}** a **{0.Value} ARX** ({1:.2f}€ environ) seulement!".format(item, item.Value * ARXAVGPRICE), embed = discordFrontierStoreEmbed)
    else:
        await ctx.send("J'ai {0} objets en stock. Ca fait beaucoup d'argent à dépenser!\nMais je suis sympa, je ne te montre que les 3 premiers:".format(len(storeItems)))
        for i in range(3):
            item = storeItems[i]
            discordFrontierStoreEmbed = discord.Embed(title = "Faire péter les ARX", url = item.Url)
            discordFrontierStoreEmbed.set_thumbnail(url = item.ImageUrl)
            await ctx.send("**{0.Name}** a **{0.Value} ARX**  ({1:.2f}€ environ) seulement!".format(item, item.Value * ARXAVGPRICE), embed = discordFrontierStoreEmbed)




@bot.command()
async def reset_tick(ctx, arg):
    ctx.send(arg)
    if ctx.author.guild_permissions.administrator:
        global CURRENTTICK
        CURRENTTICK = 0
        logger.info("Tick reset. Next refresh in 4 hours")



@bot.command()
async def refresh_store(ctx):
    if ctx.author.guild_permissions.administrator:
        await ctx.send("Ok {0.author.mention}, je vais vérifier".format(ctx))
        await PerfomManualRefresh()
        if not dataLayer.WhatNew():
            await ctx.send("Désolé, rien de nouveau sur le store")



@bot.event
async def on_guild_join(server):
    logger.info("Server {0.name} add the bot, registering it".format(server))
    dataLayer.RegisterDiscordServer(server.id, server.name)



@bot.event
async def on_guild_join(server):
    logger.info("Server {0.name} removed the bot, unregistering it".format(server))
    dataLayer.UnregisterDiscordServer(server.id, server.name)



@bot.event
async def on_ready():
    logger.info("Logged in as {0.user.name}".format(bot))
    logger.debug("Client id is {0.user.id}".format(bot))
    logger.debug("Checking DB consistance")
    for server in bot.guilds:
        if not dataLayer.ServerExists(server):
            logger.warning("Server {0.name} does not exists".format(server))
            dataLayer.RegisterDiscordServer(server)



#@client.event
#async def on_error():


bot.loop.create_task(checkNotify())
bot.run(TOKEN)
