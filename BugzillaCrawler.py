import requests
import pprint
import ast
import os
import pickle
from pymongo import MongoClient
from pymongo.database import Database
from tqdm import tqdm
from multiprocessing.pool import ThreadPool as Pool
import numpy as np
from typing import List, Union, Dict, Optional, Tuple
import enum

class CrawlMode(enum.IntEnum):
    """
    Offers different signifier for the Crawling Modes of the Bugzilla Crawler.
    """
    BUG = 0
    COMMENT = 1
    BOTH = 2
    CFAST = 3
    BFAST = 4
    NO = 5

#class to crawl Bugzilla bugs and comments
class BugzillaCrawler:
    """
    A crawler for Bugzilla repos. Can crawl Bug Data, Bug IDs, and Comments belonging to Bug-Ids.
    Has a faster comment crawl mode achieved through parallelization.
    """
    def __init__(self, restUrl: str,
                 mode: CrawlMode = CrawlMode.NO,
                 loginUrl: str = None,
                 loginName: str = None,
                 loginPW: str = None,
                 furtherparams: str = None,
                 workers: int = 10,
                 mongoDB: Database = None,
                 foldername: str = None,
                 bugList: Union[List, str] = None) -> None:
        """
        Initializes the Crawler and decides which action to take based on the mode.

        :param restUrl: the access to the rest api of the bugzilla. Needs to look like "https://<bugzilla-url>/rest/".
        :type restUrl: str
        :param mode: Optional. Decides on which action should be taken. Default is CrawlMode.NO.
        Choices are CrawlMode.[BUG, COMMENT, BOTH, CFAST, BFAST, NO]. Each option means:
        BUG -> only Bug Data and Bug IDs are crawled.
        COMMENT -> only Comments from Bug-IDs are crawled. The buglist param needs to be set for it to work.
        BOTH -> crawls the Bug Data and Bug-IDS first and then the corresponding comments to the Bug-IDs.
        CFAST -> like COMMENT but with parallelisation. In the default 10 workers are used, can be changed in param workers.
        BFAST -> like BOTH but with parallelisation. In the default 10 workers are used, can be changed in param workers.
        NO -> No action is taken. The object just gets initialized.
        :type mode: CrawlMode
        :param loginUrl: Optional. If a login is required to access the data, the login url.
        :type loginUrl: str
        :param loginName: Optional. If a login is required to access the data, the login user name.
        :type loginName: str
        :param loginPW: Optional. If a login is required to access the data, the login password.
        :type loginPW: str
        :param furtherparams: Optional. Further params for the request. They need to start with '&'.
        :type furtherparams: str
        :param workers: Optional. The amount of workers in the parallelisation method. Default is 10.
        :type workers: int
        :param mongoDB: Optional. If the data should be saved into collection in the here entered MongoDB
        :type mongoDB: pymongo.database.Database
        :param foldername: Optional. If the data should be saved as files (txt, csv), enter the folder name here.
        :type foldername: str
        :param bugList: Optional. Needed for the COMMENT and CFAST mode. Either a list object or the name of a pickle
        object as a string (needs to contain .pickle) where bug IDS are saved in.
        :type bugList: List or str
        """

        self.session = requests.session()

        self.workers = workers

        if loginUrl:
            #bugzilla user data
            user = loginName
            pw = loginPW

            #login process
            loginURL = loginUrl
            self.session.post(loginURL, {'Bugzilla_login': user, 'Bugzilla_password': pw})

        #checks for the right ending of restUrl
        if restUrl[-1] != '/':
            restUrl += '/'

        #prepares URLs for crawling of bugs and comments
        self.bugURL = restUrl + 'bug?limit=500' + furtherparams
        self.commentURL = restUrl + 'bug/{}/comment'

        #database if given one
        self.mongoDB = mongoDB

        #foldername if given one
        self.folder = foldername
        if foldername:
            #creates directory
            self.createFolder(foldername)
            self.folderpath = foldername + '/'

        #checks on which crawl operation to execute
        self.decide_action(mode, bugList)

    def decide_action(self, mode: CrawlMode = CrawlMode.NO, bugList: Union[List, str] = None) -> None:
        """
        Decides which action to start depending on the mode.

        :param mode:  Optional. Decides on which action should be taken. Default is CrawlMode.NO.
        Choices are CrawlMode.[BUG, COMMENT, BOTH, CFAST, BFAST, NO]. Each option means:
        BUG -> only Bug Data and Bug IDs are crawled.
        COMMENT -> only Comments from Bug-IDs are crawled. The buglist param needs to be set for it to work.
        BOTH -> crawls the Bug Data and Bug-IDS first and then the corresponding comments to the Bug-IDs.
        CFAST -> like COMMENT but with parallelisation. In the default 10 workers are used, can be changed in param workers.
        BFAST -> like BOTH but with parallelisation. In the default 10 workers are used, can be changed in param workers.
        NO -> No action is taken. The object just gets initialized.
        :type mode: CrawlMode
        :param bugList: Optional. Needed for the COMMENT and CFAST mode. Either a list object or the name of a pickle
        object as a string (needs to contain .pickle) where bug IDS are saved in.
        :type bugList: List or str
        """
        # checks on which crawl operation to execute
        if mode == CrawlMode.BUG:
            self.get_all_bugs()
        elif mode == CrawlMode.COMMENT:
            if bugList:
                self.get_all_comments(bugList)
            else:
                print('Error: No buglist to be found. Please check your params and start again.')
                return
        elif mode == CrawlMode.BOTH:
            bugIDList = self.get_all_bugs()
            self.get_all_comments(bugIDList)
        elif mode == CrawlMode.CFAST:
            self.get_all_comments_mp(bugList, self.workers)
        elif mode == CrawlMode.BFAST:
            bugsIDList = self.get_all_bugs()
            self.get_all_comments_mp(bugsIDList, self.workers)
        else:
            return

    def get_all_bugs(self) -> List:
        """
        Crawls all requested bug data and bug ids.
        Saves them in files (bugIDListP.pickle, bugIDList.csv, bugsData.txt ) and/or
        Mongo DB collections (BugIDs, BugsData) depending if they are given at initialization.

        :return: returns a List object where the bug IDs are saved
        :rtype: List
        """
        #starting point
        offset = 0
        #list for all bugs
        resultBugList = []
        #list for bug IDs
        bugIDList = []
        #checks if there are still results returned
        notEmpty = True

        #queries in 500 bug steps until the result list is empty
        while notEmpty:
            print("entered")
            #interpretation of result as list plus formatting for eval errors
            result = ast.literal_eval(self.session.get(self.bugURL + "&offset=" + str(offset)).text.
                                      replace('true', 'True').replace('false', 'False').replace('null', 'None'))["bugs"]
            #checks if the query needs to be set again with a new offset
            if result:
                resultBugList += result
            else:
                notEmpty = False

            #gets the ID out of all comments
            partList = [bug["id"] for bug in result]
            bugIDList += partList
            #sets new starting point
            offset += 500

        #inserts bug ids and bugs into db if given one
        if self.mongoDB:
            for id in bugIDList:
                self.mongoDB["BugIDs"].insert_one({"ID": id})
            self.mongoDB["BugsData"].insert_many(resultBugList)

        #creates files for bug ids and bugs if given a folder
        if self.folder:
            #saves bug list as python object
            with open(self.folderpath + "bugIDListP.pickle", "wb") as a:
                pickle.dump(bugIDList, a)
            #saves bug list as csv
            with open(self.folderpath + "bugIDList.csv", "w") as b:
                for id in bugIDList:
                    b.write(str(id) + "\n")
            with open(self.folderpath + "bugsData.txt", "w") as c:
                for bug in resultBugList:
                    c.write(str(bug) + "\n")

        #returns List Object for further processing
        return(bugIDList)

    def get_all_comments(self, idList: Union[List, str]) -> None:
        """
        Crawls for all comments belonging to the bugs in the Bug-ID-List.

        :param idList: Either a list object or the name of a pickle
        object as a string (needs to contain .pickle) where bug IDS are saved in.
        :type idList: List or str
        """

        #loads pickle list if it is one
        if type(idList) == str and ".pickle" in idList:
            print("pickle load")
            with open(idList, "rb") as f:
                idList = pickle.load(f)
        elif type(idList) == str:
            print("Error: Buglist parameter seems to be neither a List object or the name of a pickle file "
                  "(needs to contain .pickle).")

        #goes through idList
        for id in tqdm(idList):
            #performs request and replaces trouble some parts
            commentsString = self.session.get(self.commentURL.format(id)).text.\
                replace('true', 'True').replace('false', 'False').replace('null', 'None')
            #gets only the comments
            commentsDict = ast.literal_eval(commentsString)["bugs"][str(id)]["comments"]

            #enters comments into db or file if there are any comments for the id
            if commentsDict:
                if self.mongoDB:
                    self.mongoDB["Comments"].insert_many(commentsDict)
                if self.folder:
                    with open(self.folderpath + "Bugzilla_Comments.txt", 'a') as f:
                        f.write(str(commentsDict) + "\n")

    def get_all_comments_mp(self, list: Union[List, str], workers: int = 10) -> None:
        """
        Crawls for all comments belonging to the bugs in the Bug-ID-List utilizing parallelization.

        :param list: Either a list object or the name of a pickle
        object as a string (needs to contain .pickle) where bug IDS are saved in.
        :type list: List or str
        :param workers: Optional. The amount of workers in the parallelisation method. Default is 10.
        :type workers: int
        """
        # loads pickle list if it is one
        if type(list) == str and ".pickle" in list:
            print("wat")
            with open(list, "rb") as f:
                list = pickle.load(f)
        elif type(list) == str:
            print("Error: Buglist parameter seems to be neither a List object or the name of a pickle file "
                  "(needs to contain .pickle).")

        #gets workers and splits list into chunks fitting the worker amount
        pool = Pool(workers)
        list = np.array(list)
        lists = np.array_split(list, workers)

        #each worker crawls for comments
        for sub_list in lists:
            print(sub_list)
            pool.apply_async(self.get_all_comments, (sub_list,))

        pool.close()
        pool.join()

    def createFolder(self, foldername: str):
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

