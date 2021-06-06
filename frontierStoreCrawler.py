import asyncio
import logging
from html.parser import HTMLParser
from logging.handlers import WatchedFileHandler
from os import getenv, path
from time import sleep
from urllib.request import urlopen

from bs4 import BeautifulSoup
from dotenv import load_dotenv

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

class FrontierStoreObject():

    urlbase = "https://dlc.elitedangerous.com"

    def __init__(self, name, value, url, imageUrl):
        self._id = imageUrl.split("/")[-1][:-4]
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
        return int(self._value)

    @property
    def Url(self):
        return self._url

    @property
    def ImageUrl(self):
        return self._imageUrl



class FrontierStoreCrawlerBase():
    
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
        #totalPage = 1000
        logger.debug("Parsing {0}".format(self.__class__))

        for t in self.StoreItemType:

            logger.debug("Parsing {0}".format(t))
            page = 1
            totalPage = 1000

            while(page <= totalPage):
                logger.debug("Parsing page {0}".format(page))

                soup = BeautifulSoup(urlopen("{0}extra_type={1}&page={2}".format(self.InitialPageURL, t, page)).read(), "html.parser")
                if totalPage == 1000:
                    if soup.find("ul", "pagination") == None:
                        totalPage = 1
                    else:
                        totalPage = int(list(soup.find("ul", "pagination").descendants)[-7])

                self._currentPage = soup
                self.ParseCurrentPage()

                page = page + 1
                
                await asyncio.sleep(5)



    @property
    def AllItems(self):
        return self._storeObjects



    @property
    def InitialPageURL(self):
        return self._initialPageURL

    @InitialPageURL.setter
    def InitialPageURL(self, value):
        self._initialPageURL = value



    @property
    def StoreItemType(self):
        return self._store_itemType

    @StoreItemType.setter
    def StoreItemType(self, value):
        self._store_itemType = value



class ShipFrontierStoreCrawler(FrontierStoreCrawlerBase):

    def __init__(self):
        self.InitialPageURL = "https://dlc.elitedangerous.com/ships/list?"
        self.StoreItemType = {
    
        "178" : "Cockpit customization",
        "179" : "Decals",
        "180" : "Paint jobs",
        "203" : "Ship kits",
        "250" : "Name plates",
        "252" : "Detailing",
        "265" : "Covas"
        }
        super().__init__()



class FleetCarrierFrontierStoreCrawler(FrontierStoreCrawlerBase):

    def __init__(self):
        self.InitialPageURL = "https://dlc.elitedangerous.com/catalog/carrier/list?"
        self.StoreItemType = {
    
        "298" : "Fleet carrier layouts",
        "299" : "Fleet carrier paint jobs",
        "300" : "Fleet carrier detailing",
        "301" : "Fleet carrier ATC"
        }
        super().__init__()



class CommanderFrontierStoreCrawler(FrontierStoreCrawlerBase):

    def __init__(self):
        self.InitialPageURL = "https://dlc.elitedangerous.com/catalog/cmdr/list?"
        self.StoreItemType = {
    
        "216" : "CMDR customization",
        "312" : "Suit customization",
        "317" : "Weapon customization"
        }
        super().__init__()
