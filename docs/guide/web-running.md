# Running Web Scans

You can kick off a scan action by doing one or more of the following:
- Clicking **Start Crawl**
- Clicking **Start Pentest** (although I recommend doing a crawl first)
- Telling the A.L.I.C.E. chat agent what you want it to do

## Using the automated pentest mode
If you just want the whole application covered, click **Start Crawl**, wait for the crawl to finish, then click **Start Pentest**. 

You will see the progress of the scan/status of each agent on the Status screen as it goes:
![status screen](../images/agentstatus.png)

The Test Lead is an agentic loop which has a prompt instructing it to be a pentester working on the target site, with access to [tools](../agent-tool-reference.md) that give it information/memory on what it is working on. It can kick off the Specialist agent when it finds functionality which maybe susceptible to a particular vulnerability class; the specialist agent has a prompt which focuses only on that class (i.e. IDOR, business logic, SQLi) and a limited set of tools, to keep it focused. 

When it finds an issue, the Reporting agent writes it up and the Validator agent
tries to disprove it. Findings that cannot be reproduced remain unconfirmed.

## Using A.L.I.C.E.
You can also talk to the ALICE bot; you can think of ALICE as a Test Lead you can talk to. 

ALICE is separate to the built-in Test Lead, you can use it concurrently if you like. 

ALICE has a focused interactive subset of the [agent tools](../agent-tool-reference.md). It can make scoped HTTP requests, drive a real browser, inspect crawl and coverage context, refresh an expired configured login, and record or remove findings. In web Full mode it can also record a well-justified coverage skip. For API chats, it uses API inventory and safe request-analysis context instead of web-only tools. You can ask it to do things like:
- Can you perform a penetration test of the admin section of this app only?
- Can you tell me what findings affect the customer section of the app?
- The are 3 SQL injection findings that look like duplicates. Can you go through all the findings, check whether they are duplicated, and merge/remove them as necessary?
- Can you clean up the OWASP Coverage matrix? It looks like there are some URLs which you hit, but don't show properly - check your work? 
- The rating on the Information Disclosure finding looks a bit high - can you review all issues and reconsider the ratings? 

You can also use ALICE to "unstick" the automated pentester if it gets stuck - try giving it a fetch/curl command for a login function that's not well-exposed by the site:

For an interactive page from the crawl, tell ALICE which page/state to test. It can pass that
state's `page_id` to a request or browser action, and use the saved replay recipe when the page
depends on earlier navigation or form steps. The resulting traffic remains linked to that page
and the session used to reach it.
![ALICE prompting](../images/alice.png)

## Working with Findings
After a scan finishes you may find that, especially with non-frontier models the quality of the reporting may not be quite up to scratch:
- The same finding may be reported multiple times
- Findings may be over/underrated in severity 

You can click the **AI Review Issues** button to fix most of these problems; this will queue up a prompt with ALICE to clean up duplicates and ratings.

You can also edit supported finding fields from the finding details panel, retry
validation, or ask ALICE to review a group of findings.
