import re
import json
import math
import logging
from time import sleep
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from urllib.request import urlopen

logger = logging.getLogger("storeCrawlerLogger")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

#consolehandler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formatter)
logger.addHandler(console)

class FrontierStoreObject():

        def __init__(self, id, name, value, url):
            self._id = id
            self._name = name
            self._value = value
            self._url = url

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

class FrontierStoreCrawler():

    initialPageUrl = "https://www.frontierstore.net/eur/game-extras/elite-dangerous-game-extras.html?limit=64"
    
    def __init__(self):

        soup = BeautifulSoup(urlopen(self.initialPageUrl).read(), "html.parser")

        self._storeObjects = []

        p = soup.find("p", "amount")

        logger.debug("{0.get_text} items in store".format(p))

        match = re.match(r"\s*Items \d+-\d+ of (?P<totalItem>\d+)", p.get_text())
        if match:
            logger.debug("Total item matched: {0}".format(match.group("totalItem")))
            self._totalItem = match.group("totalItem")
            self._currentPage = soup
        else:
            logger.error("Frontier store cannot be parsed due to impossible way to collect number of item")
            raise Exception()

    
    
    def ParseCurrentPage(self):

        allProductInPage = self._currentPage.find("div", "category-products")

        for item in allProductInPage.find_all("a", "product-image"):
            match = re.match(r"^dataPushToAnalytics\('productClick', 'click', {'list':'Product Pages'}, (?P<jsonData>{.*}) , null\)$", item["onclick"])
            if match:
                storeObjectParsed = json.loads(match.group("jsonData").replace("'","\""))
                self._storeObjects.append(FrontierStoreObject(storeObjectParsed["id"], storeObjectParsed["name"], storeObjectParsed["price"], item["href"]))

    

    def Crawl(self):

        self.ParseCurrentPage()

        numberOfPage = math.ceil(float(self.TotalItemInStore) / 64)

        logger.debug("{0} pages has been calculated".format(numberOfPage))

        for i in range(2, numberOfPage + 1):
            soup = BeautifulSoup(urlopen(self.initialPageUrl + "&p=" + str(i)).read(), "html.parser")
            self._currentPage = soup
            self.ParseCurrentPage()
            sleep(5)

                

    @property
    def TotalItemInStore(self):
        return self._totalItem

    @property
    def AllItems(self):
        return self._storeObjects