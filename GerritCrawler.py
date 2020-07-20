
import GerritQueryHandler
import os
import pprint
import re
from tqdm import tqdm
from pymongo import MongoClient
from pymongo.database import Database
from typing import List, Union, Dict, Optional, Tuple


class GerritCrawler:
    """
    Manages the request process and saves the output into csv files and/or a Mongo Database.
    """

    def __init__(self, startPointIncrease: int, url: str, beforeDate: str = None, afterDate: str = None,
                 foldername: str = None, separator: str = ',', mongoDB: Database = None) -> None:
        """
        Initializes the Crawler.

        :param startPointIncrease: The amount that the startpoint needs to increase to get further commits. This is
        equivalent to the limit of commits in the response of a request.
        :type startPointIncrease: int
        :param url: The url of the request, should be one the endpoints of the REST API.
        :type url: str
        :param beforeDate:  Optional. A possible date for a 'before' parameter in your query. It has to be in the format
        of yyyy-mm-dd.
        :type beforeDate: str
        :param afterDate:Optional. A possible date for a 'after' parameter in your query. It has to be in the format
        of yyyy-mm-dd.
        :type afterDate: str
        :param foldername: Optional. If the result is supposed to be saved in csv files in a folder, enter a name
        for the folder. If the directonary doesn't exist already, it will be created.
        :type foldername: str
        :param separator: Optional. Decides how the csv data will be separated. The default is ','.
        :type separator: str
        :param mongoDB: Optional. If the result is supposed to be saved in a Mongo database enter it here.
        :type mongoDB: pymongo.database.Database
        """
        #handles the actual requests
        self.handler = GerritQueryHandler.GerritQueryHandler(url=url, beforeDate=beforeDate, afterDate=afterDate)

        #what amount the startpoint for the query needs to increase
        self.startpointIncrease = startPointIncrease

        #if csv files should be , or ; separated
        self.separator = separator

        #MongoDB setup
        self.db = mongoDB
        if mongoDB:
            # contains all individual information for the MongoDB (corresponding Collections, query limit)
            self.mongoDic = {
                "devs": self.db.allDevs,
                "noCommits": self.db.noCommits,
                "commitsCollections": [self.db['id{}'.format(x)] for x in range(10)],
            }

        #folder setup
        self.folder = foldername
        if foldername:

            #creates directory
            self.createFolder(foldername)
            self.folderpath = foldername + '/'

            #contains all individual information for the result folder (corresponding files, query limit)
            self.folderDic = {
                "devs": "allDevs.csv",
                "noCommits": "noCommitsUser.csv",
                "commitsCollections": ["id{}.csv".format(x) for x in range(10)],
            }

    def enterOneUserCommits(self, user: str) -> None:
        """
        Starts the request process and continues it as long as there are still more commits to be crawled.
        It saves the developers with their commit counter into one file/collection, the commenters into another
        and the commits into 10 different files/collection based on the user's id.

        :param user: The respective user of the request.
        :type user: str
        """
        startPoint = 0

        #gathers all commits of a user as a list
        commitsList, notDone, active = self.handler.getCommits(user, startPoint)


        #checks for commits, if yes into commits collection if no into no commit collection
        if commitsList:

            #gets account id out of the commits list
            userID = commitsList[0]['owner']['_account_id']

            #inserts commits into collection in DB if one given
            if self.db:
                self.mongoDic["commitsCollections"][userID % 10].insert_many(commitsList)

            #inserts commits into a file in a folder if one given
            if self.folder:
                with open(self.folderpath + self.folderDic["commitsCollections"][userID % 10], 'a') as f:
                    for i in commitsList:
                        f.write(str(i) +'\n')
        #handles no commits users and ends call
        else:
            #inserts user without commits into collection in DB if given one
            if self.db:
                self.mongoDic["noCommits"].insert_one({'author': user, 'active': active})

            #inserts user without commits into file in folder if given one
            if self.folder:
                userString = user + self.separator + str(active)
                with open(self.folderpath + self.folderDic["noCommits"], 'a') as f:
                    f.write(userString + "\n")
            return

        # loops request until all commits have been found
        while notDone:

            # adjusts query result limit accordingly
            startPoint += self.startpointIncrease

            #repeats query with new startPoint
            commitsList, notDone, active = self.handler.getCommits(user, startPoint)

            # inserts commits into corresponding collection in DB if one given
            if self.db:
                self.mongoDic["commitsCollections"][userID % 10].insert_many(commitsList)

            # inserts commits into a file in a folder if one given
            if self.folder:
                with open(self.folderpath + self.folderDic["commitsCollections"][userID % 10], 'a') as f:
                    for i in commitsList:
                        f.write(str(i) + "\n")

        #counts commits and puts user in dev collection with that count
        commitCounter = startPoint + len(commitsList)

        #enters developer into right collection in DB if one is given
        if self.db:
            self.mongoDic["devs"].insert_one({'author': user, 'user-id': userID, "commits": commitCounter,
                                                       'active': active})

        # inserts commits into a file in a folder if one given
        if self.folder:
            userString = user + self.separator + str(userID) + self.separator + str(commitCounter) + self.separator + \
                         str(active)
            with open(self.folderpath + self.folderDic["devs"], 'a') as f:
                f.write(str(userString) + "\n")

    def enterManyUsersCommits(self, userList) -> None:
        """
        Accepts a List of Users to crawl commits for and executes it for each user.

        :param userList: List of users.
        :type userList: List
        """
        for user in userList:
            self.enterOneUserCommits(user)

    def createFolder(self, foldername: str) -> None:
        """
        Creates a directory if it doesn't exist already

        :param foldername: The name of the new folder
        :type foldername: str
        """
        try:
            if not os.path.exists(foldername):
                os.makedirs(foldername)
        except OSError:
            print('Error: Creating following directory: ' + foldername)

