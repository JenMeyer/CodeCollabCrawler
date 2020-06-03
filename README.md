# CodeCollabCrawler
Minimalistic library for crawling Gerrits and Bugzilla repos with MongoDB support.

This library aims at delivering a more easy but still customizable crawling process.
Both Crawler offer up the possibility of not only generating the output as files but also of inserting it into MongoDB
databases if wanted. 

Please install the for this library required packages with

> pip -r requirements


## Gerrit Crawler

A crawler for Gerrits. It is build to request Commits belonging to either one User or a list of Users.

### Requirements

Besides the packages mentioned in 'requirements' the crawler needs for a well working execution a so called 
*'Startpoint Increase'*. Most Gerrits only offer a limited amount of Commits for each request. The Startpoint Increase 
param needs to be set to this response limit to ensure the correct repeat of requests until all Commits for each user
are gathered.
It also needs the url to the REST API endpoint.

### Structure and Function

This Crawler is split into two files:
* #### GerritCrawler
  This class manages the request process as well as the output saving process. 
  It ensures the correct looping of requests for users who have more Commits than the limit returns while moving 
  the startpoint accordingly. It also saves the results as files or MongoDB entries or both if wanted.
  With objects of this class function calls for crawling for either one User's commits or for a list of Users are
  executed. It contains an object of GerritQueryHandler.
* #### GerritQueryHandler
  This class handles the actual execution of the request as well as the formatting of the responses.
  Here the request urls are build including the optional parameters. It performs the actual request and also checks for 
  inactive users. It formats the response into a processable list and also checks if there are more Commits to be
  requested for.  

### Customizable Options

* ### Timeframe
    By setting the optional *before* and *after* parameters is it possible to restrict in which timeframe the Commits
    should be crawled. It is also possible to set just one of them no matter which.
    The parameter need to follow the format **'yyyy-mm-dd'**
* #### MongoDB support
    Through assigning the *a MongoDB instance to an optional parameter* the query results can be directly written into
    different collections in the Mongo database. This can be in addition to the file directory or on its own.
    
* #### File Directory
    By setting an *optional parameter for a folder name* (if it doesn't exit already it will be created) the output of 
    the request will be saved in csv files in the chosen directory. This can be in additon to the MongoDB entries
    or on its own.
    
### Output

The Output can be saved as files in a directory or MongoDB entries. They are also possible at the same time.
The result of crawling Bug Data and Bug-IDs is:
* as files
  * __allDevs.csv__: a list of all developers and their number of commits as well as if they're active accounts.
  * __noCommitsUser.csv__: a list of all users without Commits
  * 10 __'id?.csv'__ with the ? being 0-9: all Commits and their data are saved into the file corresponding to the 
    last digit of the user-id. Their ownership can also be determined through that user-id.
* as MongoDB collections
  * __allDevs__: a collection of all developers and their number of commits as well as if they're active accounts.
  * __noCommits__:  a collection of all users without Commits
  * 10 __'id?'__ with the ? being 0-9:  Commits and their data are saved into the collection corresponding to the 
    last digit of the user-id. Their ownership can also be determined through that user-id.

## Bugzilla Crawler

A crawler for Bugzilla repos. It can crawl **Bug Data, Bug IDs, and Comments** belonging to specific Bug-Ids.
It also has a faster comment crawl mode by utilising parallelization.

### Requirements

Besides the packages mentioned in 'requirements' the crawler needs for its execution the REST API url for the 
bugzilla that is supposed to be crawled. This url should look like something along the lines of 
**https://"bugzilla-url"/rest/**.

### Customizable options

* #### Different Crawling Modes:
    This crawler class offers up different enum controlled modes for an easier application. 
    One can choose between **only crawling Bug Data and Bug-IDs, only Comments** if a Bug-ID-List is passed along 
    and **a combined mode** for first requesting the bug data and then the corresponding Comments. There are also 
    **two faster modes** for just requesting Comments and for the combined mode with a customizable amount of workers. 
    For manual function calls there is also a 'no further action' mode.

* #### Login
    There is also the possibility of performing a login if it is required to access the data. This is achieved through 
    optional parameters for the *login url, username and password*.

* #### MongoDB support
    Through assigning the *a MongoDB instance to an optional parameter* the query results can be directly written into
    different collections in the Mongo database. This can be in addition to the file directory or on its own.
    
* #### File Directory
    By setting an *optional parameter for a folder name* (if it doesn't exit already it will be created) the output of 
    the request will be saved in csv and txt files aswell as a pickled Bug-ID-List for faster processing. This can be 
    in additon to the MongoDB entries or on its own.

* #### Own Bug-ID-List
    For only crawling Comments belonging to specific Bugs the user needs to pass these *Bug-ID-List as either a List Object
    or as a pickle file* name in the pattern of **"name".pickle**
    
### Possible Output

The Output can be saved as files in a directory or MongoDB entries. They are also possible at the same time.
The result of crawling Bug Data and Bug-IDs is:
* as files
  * __bugIDListP.pickle__: The Bug-IDs as a pickled list for faster further processing.
  * __bugIDList.csv__: The Bug-IDs as a csv list.
  * __bugsData.txt__: The Bug Data as a txt file.
  * __Bugzilla_Comments.txt__: The Comments for each Bug as a txt file.
* as MongoDB collections
  * __BugIDs__: The Bug-IDs as a collection
  * __BugsData__: The Bug Data as a collection
  * __Comments__: The Comments for each Bug as a collection
