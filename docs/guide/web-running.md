# Running Web Scans

You can kick off a scan action by doing one or more of the following:
- Clicking **Start Crawl**
- Clicking **Start Pentest** (although I recommend doing a crawl first)
- Telling the A.L.I.C.E. chat agent what you want it to do

## Using the automated pentest mode
If you just want the whole application covered, click **Start Crawl**, wait for the crawl to finish, then click **Start Pentest**. 

You will see the progress of the scan/status of each agent on the Status screen as it goes:
![status screen](../images/agentstatus.png)

## Using A.L.I.C.E.
You can also talk to the ALICE bot; you can think of ALICE as a Test Lead you can talk to. 

ALICE is separate to the built-in Test Lead, you can use it concurrently if you like. 

ALICE has access to all tools that any other agent has, so you can ask it to do things like:
- Can you perform a penetration test of the admin section of this app only?
- Can you tell me what findings affect the customer section of the app?
- The are 3 SQL injection findings that look like duplicates. Can you go through all the findings, check whether they are duplicated, and merge/remove them as necessary?
- Can you clean up the workprogram? It looks like there are some URLs which you hit, but don't show properly - check your work? 
- The rating on the Information Disclosure finding looks a bit high - can you review all issues and reconsider the ratings? 

You can also use ALICE to "unstick" the automated pentester if it gets stuck - try giving it a fetch/curl command for a login function that's not well-exposed by the site:
![alt text](scans/images/aliceprompting.png)