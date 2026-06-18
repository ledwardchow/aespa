# Web Scanning - Screen Walkthrough

This is the Sites landing page:
![Sites page](images/sitescreen.png)
The **Export** button on each row will let you export the whole site (including any scan data) as a single JSON file; these files will often be very large (as they will include crawled screenshots). 

You can use the **Import site** button on the top right to re-import these on a different instance of AESPA.

## Creating a site configuration
![create site screen](images/createsite.png)
Enter details as necessary. 
The **Default login page URL** will be used by default for each credential added. If your app has multiple login pages, you can override this for a specific set of credentails by entering the url in the **Login URL (optional override)** field. 

The **Auth Mode** field allows you to select one of three modes:
- **auto** - this will fill in the username/password on a standard form on the website.
- **totp** - this will fill in the username/password field, and use the entered TOTP seed to fill a TOTP field as well.
- **guided** - For complex login forms/passkeys/multi-page/multipath logins i.e. Entra. This mode only works if you are running AESPA on a machine with a GUI shell (i.e. not running on a headless server). AESPA will pop a message on the top of the screen when the scanner wants to log in; click on the button to pop open a Chromium browser at the login form, and complete the login; go back to AESPA and click the Done button to close the browser. AESPA will then capture your authentication tokens and continue.

## Site configuration
![run selector screen](images/runselector.png)
Click on **New Run** to make a new test run.
![test run edit](images/editrun.png)
On this screen you can enter the breadth-first search depth/max pages for the crawler to spider, and select an LLM profile.

## Run Status screen
When you open a test run, you will be presented with the Status screen, which displays the status of each agent. 
![run status](images/runlanding.png)
You can kick off a scan action by doing one or more of the following:
- Clicking **Start Crawl**
- Clicking **Start Pentest** (although I recommend doing a crawl first)
- Telling the A.L.I.C.E. chat agent what you want it to do


## Crawler
This will spider the site using the configured URLs and credentials (similar to Burp Spider). The crawler uses one instance of a Playwright-powered Chromium browser in the background **per authentication credential configured**; therefore, each auth cred will mean ~500MB RAM usage, if you have 4 login credentials configured it will consume ~2GB RAM during the crawl. Because it uses a browser, it is aware of SPA page navigation/popup modal boxes and will cope with functionality presented on these. 

The crawler populates the Site Map, Intelligence, Task Graph, and seeds the Workprogram with the crawled pages.

## Site Map
![site map](images/sitemap.png)
The Site Map screen shows the crawled context; all the information on this page can be retrieved by the scanner and ALICE as a tool call. 
Clicking the **By Scope** and **By User** buttons on the top right will switch between scope view (colour page routes based on whether it is marked in scope or not) and user view (colour page routes based on what user had access to that page).

You can click on each page node to view the page in the side panel, where the **Mark in/out of scope** buttons are present. The Page Categories information is used by the scanner as a hint for what to test. The OWASP Top 10:2025 is used to seed the workprogram. (Note that the scanner may choose to not follow this guidance and test a page for a category marked "No".)

## Intelligence/Task Graph
This section is populated by the crawler; if you didn't run this, they will remain blank through the scan. If populated the information is made available as context_tool calls to both the scanner and ALICE.

Intelligence is a simple key-value store of things the crawler saw:
![intelligence screen](images/intelligence.png)

The attack surface documents pages which are public/normal user access/admin access:
![attack surface](images/attacksurface.png)

The task queue is a list of hypotheses which the scanner can choose to test for (it may not!):
![task queue](images/taskqueue.png)

## Sessions
The sessions screen displays authentication tokens that are captured during the crawl, or during scans/by ALICE. All sessions are made available to the scanner and ALICE for re-use. You can remove credentials you don't want/expired by clicking on Deactivate.
![sessions](images/sessions.png)

## Findings
![web findings](images/webfindings.png)

## Workprogram
![workprogram](images/workprogram.png)

