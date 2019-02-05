#! /usr/bin/python3.6 -u
import discord
import logging
from logging.handlers import WatchedFileHandler
from os import path
from os import remove
import asyncio
import random
import re
import urllib
import config
from dataLayer import DataLayer
from contestEntrant import ContestEntrant
#temporary added for migration
import psycopg2

##########################################
# Empty config.py sample                 #
#                                        #
# import logging                         #
# TOKEN = ''                             #
# logLevel = logging.DEBUG               #
# logLevel = "dbname=theDb user=theUser" #
# refreshTick = 240                      #
# logPath = ""                           #
# logFileName = "spacepigeon.log"        #
##########################################

TOKEN = config.TOKEN
VERSION = "3.0"
REFRESH = config.refreshTick
CURRENTTICK = 0

dataLocker = asyncio.Lock()

logger = logging.getLogger(__name__)
logger.setLevel(config.logLevel)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

#console handler
console = logging.StreamHandler()
console.setLevel(config.logLevel)
console.setFormatter(formatter)
logger.addHandler(console)

#logfile handler
logfile = WatchedFileHandler(path.join(config.logPath, config.logFileName))
logfile.setLevel(config.logLevel)
logfile.setFormatter(formatter)
logger.addHandler(logfile)

client = discord.Client()
dataLayer = DataLayer()
allRegisteredServer = []



def GetRole(serverId, roleId):
    server = client.get_server(serverId)
    for role in server.roles:
        if role.id == roleId:
            return role



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

                    role = GetRole(server.ServerId, server.RoleId)
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



@client.event
async def on_message(message):

    if message.author != client.user:
        
        if client.user.mentioned_in(message):
            
            if message.author.server_permissions.administrator: 
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
                    
                    elif command == "contest" and "-contest" in message.channel.name:

                        parameters = match.group("parameters").split(" ")
                        contest = dataLayer.GetContestForServer(message.server.id)

                        if parameters and parameters[0] == "start":
                            if contest:
                                await client.send_message(message.channel, "Un contest est déjà en cours sur ce serveur. Il faut le clôturer en me mentionnant avec la commade `!contest finish`")
                                return
                            else:
                                contestName = parameters[1]
                                contestWinnerChannel = message.channel_mentions[0]
                                contestRole = message.role_mentions[0]

                                if contestName and contestWinnerChannel and contestRole:
                                    dataLayer.CreateContest(message.server.id, contestName, contestRole.id, contestRole.name, contestWinnerChannel.id, contestWinnerChannel.name)
                                    await client.send_message(message.channel, "Ok {0.author.mention}, le contest {1} a bien été créé.".format(message, contestName))
                                    return
                            return
                        
                        if parameters and parameters[0] == "finish":
                            dataLayer.RemoveContest(message.serverid)
                            await client.send_message(message.channel, "Ok {0.author.mention}, le contest {1.Name} a bien été supprimé.".format(message, contest))
                            return

                        contestRole = GetRole(message.server.id, contest.NotificationRole)
                        if parameters and parameters[0] == "prepare":
                            entrantCount = 0
                            async for msg in client.logs_from(message.channel, limit = 100):
                                if msg.attachments:
                                    await client.add_reaction(msg, "♥")
                                    entrantCount += 1
                            
                            if contest.ContestCount == 1:
                                sentence = "{0.mention}\nLa phase de soumission est terminée pour ce {1.ContestCount}er concours {1.ContestName}.\n".format(contestRole, contest)
                            else:
                                sentence = "{0.mention}\nLa phase de soumission est terminée pour ce {1.ContestCount}ème concours {1.ContestName}.\n".format(contestRole, contest)
                            sentence += "Vous avez jusqu'à **Dimanche 20:00** pour voter, en ajoutant une réaction ♥ aux images que préférez parmi les {0} proposées.".format(entrantCount)
                            await client.send_message(message.channel, sentence)
                            return

                        if parameters and parameters[0] == "winners":
                            
                            await client.change_presence(game=discord.Game(name="Déclare les gagnants du concours"), status=discord.Status.dnd)
                            if len(parameters) > 1:
                                try:
                                    numberOfWinner = int(parameters[1])
                                except:
                                    numberOfWinner = 3
                            else:
                                numberOfWinner = 3
                            
                            entrants = []
                            async for msg in client.logs_from(message.channel, limit = 100):
                                if msg.reactions:
                                    entrants.append(ContestEntrant(msg.author, msg.reactions[0].count, msg.attachments[0]["url"]))
                                    logger.debug("{0.author} : {0.reactions[0].count} vote(s)".format(msg))

                            entrants.sort(key = lambda ent: ent.VoteCount, reverse = True)

                            winnerChannel = message.server.get_channel(contest.WinnerChannel)
                            if contest.ContestCount == 1:
                                sentence = "{0.mention}\nLes heureux gagnants de ce {1.ContestCount}er photo contest {1.ContestName} sont...".format(contestRole, contest)
                            else:
                                sentence = "{0.mention}\nLes heureux gagnants de ce {1.ContestCount}ème photo contest {1.ContestName} sont...".format(contestRole, contest)
                            await client.send_message(winnerChannel, sentence)

                            currentVote = 0
                            winnerCount = 0
                            for winner in entrants:

                                if currentVote == winner.VoteCount:
                                    currentWinnerString = "ex aequo {0.mention} avec **{1}** votes également".format(winner.Author, winner.VoteCount)
                                else:
                                    currentWinnerString = "{0.mention} avec **{1}** votes".format(winner.Author, winner.VoteCount)
                                    currentVote = winner.VoteCount
                                    winnerCount += 1
                                
                                if winnerCount > numberOfWinner:
                                    break

                                if winnerCount == 1:
                                    await client.send_message(winnerChannel, "1er\n" + currentWinnerString)
                                else:
                                    await client.send_message(winnerChannel, "{0}ème\n{1}".format(winnerCount, currentWinnerString))
                                
                                await client.send_typing(winnerChannel)
                                request = urllib.request.Request(winner.ImageUrl, data = None, headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"})
                                filePath = "{0.Author.name}_{1.ContestName}_{1.ContestCount}{2}".format(winner, contest, winner.ImageUrl[winner.ImageUrl.rfind("."):])
                                with urllib.request.urlopen(request) as image, open(filePath, "wb") as localImgFile:
                                    localImgFile.write(image.read())
                                await client.send_file(winnerChannel, filePath)
                                remove(filePath)
                                

                            await client.send_typing(winnerChannel)
                            await client.send_message(winnerChannel, "**Bravo à eux !**")
                            dataLayer.IncrementContestCount(message.server.id)
                            await client.change_presence(game=None, status=discord.Status.online)
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
    logger.info("Server {0.name} add the bot, registering it".format(server))
    dataLayer.RegisterDiscordServer(server.id, server.name)



@client.event
async def on_server_remove(server):
    logger.info("Server {0.name} removed the bot, unregistering it".format(server))
    dataLayer.UnregisterDiscordServer(server.id, server.name)



@client.event
async def on_ready():

    logger.info("Logged in as {0.user.name}".format(client))
    logger.debug("Client id is {0.user.id}".format(client))

    for server in client.servers:
        print("server: {0.name} - id: {0.id}".format(server))
        
        #Run once
        logger.info("Upgrading to 3.0")
        connection = psycopg2.connect(dataLayer._connectionString)
        cursor = connection.cursor()

        cursor.execute("SELECT serverid FROM RegisteredServer WHERE serverid = %s", (server.id,))
        registeredServer = cursor.fetchall()
        if registeredServer:
            cursor.execute("UPDATE RegisteredServer SET ServerName = %s WHERE ServerId = %s", (server.name, server.id))
        else:
            cursor.execute("INSERT INTO RegisteredServer VALUES (%s, %s)", (server.name, server.id))

        cursor.execute("SELECT Notification_Role_Id, Notification_Channel_Id FROM SpacePigeon_Parameter WHERE serverid = %s", (server.id,))
        registeredServer = cursor.fetchall()
        if registeredServer:
            for record in registeredServer:
                for role in server.roles:
                    if role.id == record[0]:
                        cursor.execute("UPDATE SpacePigeon_Parameter SET Notification_Role_Name = %s, Notification_Channel_Name = %s WHERE ServerId = %s", (role.name, client.get_channel(record[1]).name, server.id))
                        break

        connection.commit()
        logger.info("Upgrade complete")
        cursor.close()
        connection.close()



client.loop.create_task(checkNotify())
client.run(TOKEN)