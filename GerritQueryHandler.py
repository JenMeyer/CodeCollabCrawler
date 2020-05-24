import requests
import ast
import re
import pprint
from typing import List, Union, Dict, Optional, Tuple


class GerritQueryHandler:
    """
    Handles the execution of the requests and the formatting of the responses.
    """

    def __init__(self, url: str, beforeDate: str = None, afterDate: str = None) -> None:
        """
        Initializes the Query Handler with url and optional time parameters.

        :param url: The url of the request, should be one the endpoints of the REST API.
        :type url: str
        :param beforeDate: Optional. A possible date for a 'before' parameter in your query. It has to be in the format
        of yyyy-mm-dd.
        :type beforeDate: str
        :param afterDate: Optional. A possible date for a 'after' parameter in your query. It has to be in the format
        of yyyy-mm-dd.
        :type afterDate: str
        """
        self.session = requests.session()

        self.url = url

        #optional request parameters
        self.before = beforeDate
        self.after = afterDate

    def buildURL(self, user: str, startpoint: int) -> str:
        """
        Builds the request url out the given parameters.

        :param user: The respective user of the request
        :type user: str
        :param startpoint: The startpoint of the query. Necessary as the response amount is restricted and the request
        needs to be executed multiple times with different startpoints.
        :type startpoint: int
        :return: The final request url
        :rtype: str
        """
        url = self.url

        if self.url[-1] != '/':
            url += '/'

        #enters user into request url
        url += '?q=owner:' + user

        #adds optional time params
        if self.before:
            url += '+before:' + self.before
        if self.after:
            url +='+after:' + self.after

        #adds the startpoint
        url += '&S=' + str(startpoint)

        #print(url)
        return url

    #makes request for commits and returns it as formatted list
    def getCommits(self, user: str, startpoint: int) -> Tuple[List[Dict], bool, bool]:
        """
        Executes the request and gets all commits fitting the parameters belonging to the user.

        :param user: The respective user of the request
        :type user: str
        :param startpoint: The startpoint of the query. Necessary as the response amount is restricted and the request
        needs to be executed multiple times with different startpoints.
        :type startpoint: int
        :return: Returns the commitList which contains the commits as dictionaries, if there are no commits it will
        be an empty list. Also returns if the request ist finished and if the user is active.
        :rtype: Tuple[List[Dict], bool, bool]
        """
        active = True
        url = self.buildURL(user, startpoint)

        #actual request
        userCommitsTime = self.session.get(url)

        #for control
        #print(userCommitsTime.text)

        #handles inactive accounts
        if "following exact account" in userCommitsTime.text:
            print("inactive!")

            active = False

            #extracts userID for inactive account
            ID_candidate = re.findall(r'(\d+):', userCommitsTime.text)

            if ID_candidate:
                url = self.buildURL(ID_candidate[0], startpoint)

                userCommitsTime = self.session.get(url)
            else:
                print("Error: no ID_candidate" + user)
                print(userCommitsTime.text)

        commitsList, notDone = self.formatStringToList(userCommitsTime)

        return commitsList, notDone, active

    def formatStringToList(self, string: str) -> Tuple[List[Dict], bool]:
        """
        Formats the text of the response (string) into a list of dictionaries.

        :param string: The to be formatted text.
        :type string: str
        :return: Returns the formatted list and if the request is finished
        :rtype: Tuple[List[Dict], bool]
        """

        #cuts first line
        commitsString = string.text.split("\n", 1)[1]

        if commitsString == '':
            return [], False

        #checks for more changes, sets notDone accordingly
        if '"_more_changes": true' in commitsString:
            commitsString = commitsString.replace('"_more_changes": true\n', '')
            notDone = True
        else:
            notDone = False

        commitsString = commitsString.replace('true', 'True').replace('false', 'False')
        # print(user)
        # print(commitsString)

        #converts string to a list
        commitsList = ast.literal_eval(commitsString)

        return commitsList, notDone
