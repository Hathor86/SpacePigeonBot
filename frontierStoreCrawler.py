import re
import json
import math
import hashlib
import logging
import config
import asyncio
from time import sleep
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from urllib.request import urlopen
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

class FrontierStoreObject():

    urlbase = "https://dlc.elitedangerous.com"

    def __init__(self, name, value, url, imageUrl):
        self._id = hashlib.sha256(name).hexdigest()
        self._name = name
        self._value = value
        self._url = self.urlbase + url
        self._imageUrl =  self.urlbase + imageUrl

    @property
    def ID(self):
        return self._id
    
    @property 
    def Name(self):
        return self._name

    @property
    def Value(self):
        return self._value

    @property
    def Url(self):
        return self._url

    @property
    def ImageUrl(self):
        return self._imageUrl



class FrontierStoreCrawlerBase():

    initialPageUrl = ""
    store_itemType = {}
    
    def __init__(self):
        self._storeObjects = []

    
    
    def ParseCurrentPage(self):

        allProductInPage = self._currentPage.find("section", "c-products-list")

        name =""
        price = ""
        url = ""
        imgurl = ""

        for product in allProductInPage.find_all("article"):

            imgurl = product.find("figure").img["src"]
            price = product.find("span", "o-price").span.getText().strip()
            name = product.find("div", "o-product__info").h1.getText().strip()
            url = product.find("a")["href"]

            self._storeObjects.append(FrontierStoreObject(name, price, url, imgurl))


    

    async def Crawl(self):

        page = 1

        for t in self.store_itemType:

            while(page != 0):
                logger.debug("Parsing page {0}".format(page))

                soup = BeautifulSoup(urlopen("{0}extra_type={1}&page={2}".format(self.initialPageUrl, t, page)).read(), "html.parser")

                self._currentPage = soup
                self.ParseCurrentPage()

                if soup.find("ul", "pagination") != None and page != list(soup.find("ul", "pagination").descendants)[-7]:
                    page = page + 1
                else:
                    page = 0
                
                await asyncio.sleep(5)



    @property
    def AllItems(self):
        return self._storeObjects



class ShipFrontierStoreCrawler(FrontierStoreCrawlerBase):

    def __init__(self):
        super.initialPageUrl = "https://dlc.elitedangerous.com/ships/list?"
        super.store_itemType = {
    
        "178" : "Cockpit customization",
        "179" : "Decals",
        "180" : "Paint jobs",
        "203" : "Ship kits",
        "250" : "Name plates",
        "252" : "Detailing",
        "265" : "Covas"
        }
        logger.debug("Parsing ships")
        super().__init__()



class FleetCarrierFrontierStoreCrawler(FrontierStoreCrawlerBase):

    def __init__(self):
        super.initialPageUrl = "https://dlc.elitedangerous.com/catalog/carrier/list?"
        super.store_itemType = {
    
        "298" : "Fleet carrier layouts",
        "299" : "Fleet carrier paint jobs",
        "300" : "Fleet carrier detailing",
        "301" : "Fleet carrier ATC"
        }
        logger.debug("Parsing fleet carrier")
        super().__init__()



class CommanderFrontierStoreCrawler(FrontierStoreCrawlerBase):

    def __init__(self):
        super.initialPageUrl = "https://dlc.elitedangerous.com/catalog/cmdr/list?"
        super.store_itemType = {
    
        "216" : "CMDR customization",
        "312" : "Suit customization",
        "317" : "Weapon customization"
        }
        logger.debug("Parsing CMDR")
        super().__init__()