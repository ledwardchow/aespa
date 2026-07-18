#!/usr/bin/env python3
"""
Documentation Screenshot Capture Utility for AESPA

Automatically inspects aespa.db to locate top web and API scan runs,
launches headless Playwright, navigates all UI routes and tab views,
and saves updated documentation screenshots to docs/images/.
"""

import argparse
import asyncio
import os
import sqlite3
import sys

from playwright.async_api import async_playwright


def get_top_runs(db_path: str):
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query web run with highest findings/traffic
    cursor.execute("""
        SELECT tr.id
        FROM test_run tr
        ORDER BY 
            (SELECT COUNT(*) FROM scan_finding sf WHERE sf.test_run_id = tr.id) DESC,
            (SELECT COUNT(*) FROM traffic_entry ht WHERE ht.test_run_id = tr.id) DESC
        LIMIT 1
    """)
    row_web = cursor.fetchone()
    web_run_id = row_web[0] if row_web else 1

    # Query site_id for web_run_id
    cursor.execute("SELECT site_id FROM test_run WHERE id = ?", (web_run_id,))
    row_site = cursor.fetchone()
    site_id = row_site[0] if row_site else 1

    # Query API run with highest findings/traffic
    cursor.execute("""
        SELECT atr.id
        FROM api_test_run atr
        ORDER BY 
            (SELECT COUNT(*) FROM scan_finding sf WHERE sf.api_test_run_id = atr.id) DESC,
            (SELECT COUNT(*) FROM traffic_entry ht WHERE ht.api_test_run_id = atr.id) DESC
        LIMIT 1
    """)
    row_api_run = cursor.fetchone()
    api_run_id = row_api_run[0] if row_api_run else 1

    # Query collection_id for api_run_id
    cursor.execute("SELECT collection_id FROM api_test_run WHERE id = ?", (api_run_id,))
    row_api_col = cursor.fetchone()
    collection_id = row_api_col[0] if row_api_col else 1

    conn.close()
    return web_run_id, site_id, api_run_id, collection_id


async def capture_screenshots(
    base_url: str,
    out_dir: str,
    web_run_id: int,
    site_id: int,
    api_run_id: int,
    collection_id: int,
):
    os.makedirs(out_dir, exist_ok=True)
    base_url = base_url.rstrip("/")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        print(
            f"Capturing screenshots into {out_dir} (Web Run: #{web_run_id}, API Run: #{api_run_id})..."
        )

        # 1. Sites list
        print(" -> sites.png")
        await page.goto(f"{base_url}/#/")
        await asyncio.sleep(1.5)
        await page.screenshot(path=os.path.join(out_dir, "sites.png"))

        # 2. Site creation form
        print(" -> sitesetup.png")
        await page.goto(f"{base_url}/#/sites/new")
        await asyncio.sleep(1.0)
        await page.screenshot(path=os.path.join(out_dir, "sitesetup.png"))

        # 3. Site detail (runs selector)
        print(" -> testruns.png")
        await page.goto(f"{base_url}/#/sites/{site_id}")
        await asyncio.sleep(1.5)
        await page.screenshot(path=os.path.join(out_dir, "testruns.png"))

        # 4. New run form
        print(" -> editrun.png")
        await page.goto(f"{base_url}/#/sites/{site_id}/runs/new")
        await asyncio.sleep(1.0)
        await page.screenshot(path=os.path.join(out_dir, "editrun.png"))

        # Web Run tab navigation
        web_run_url = f"{base_url}/#/runs/{web_run_id}"
        await page.goto(web_run_url)
        await asyncio.sleep(2.0)

        # 5. Status / runlanding / agentstatus (with ALICE minimized)
        print(" -> agentstatus.png & runlanding.png")
        await page.click('button.tab-btn:has-text("Status")')
        await asyncio.sleep(1.0)
        alice_role = page.locator('.agent-row:has-text("A.L.I.C.E") .agent-role-name')
        if await alice_role.count() > 0:
            await alice_role.first.click()
            await asyncio.sleep(1.0)
        await page.screenshot(path=os.path.join(out_dir, "agentstatus.png"))
        await page.screenshot(path=os.path.join(out_dir, "runlanding.png"))

        # 6. Site Map
        print(" -> sitemap.png")
        await page.click('button.tab-btn:has-text("Site Map")')
        await asyncio.sleep(3.0)
        await page.screenshot(path=os.path.join(out_dir, "sitemap.png"))

        # 7. Attack Surface & Coverage
        print(" -> attacksurface.png")
        await page.click('button.tab-btn:has-text("Attack Surface")')
        await asyncio.sleep(2.5)
        await page.screenshot(path=os.path.join(out_dir, "attacksurface.png"))

        # 8. Web Findings
        print(" -> findings.png & webfindings.png")
        await page.click('button.tab-btn:has-text("Findings")')
        await asyncio.sleep(2.5)
        await page.screenshot(path=os.path.join(out_dir, "findings.png"))
        await page.screenshot(path=os.path.join(out_dir, "webfindings.png"))

        # 9. Traffic Log
        print(" -> trafficlog.png")
        await page.click('button.tab-btn:has-text("Traffic Log")')
        await asyncio.sleep(2.5)
        await page.screenshot(path=os.path.join(out_dir, "trafficlog.png"))

        # 10. SAST Leads
        print(" -> sastleads.png")
        await page.click('button.tab-btn:has-text("SAST Leads")')
        await asyncio.sleep(2.0)
        await page.screenshot(path=os.path.join(out_dir, "sastleads.png"))

        # 11. ALICE expanded screen
        print(" -> alice.png")
        await page.click('button.tab-btn:has-text("Status")')
        await asyncio.sleep(1.0)
        # Ensure ALICE container is open
        alice_container = page.locator(".alice-chat-container")
        if not await alice_container.is_visible():
            await alice_role.first.click()
            await asyncio.sleep(1.0)
        # Drag resizer handle to expand ALICE panel to bottom of viewport
        resizer = page.locator(".alice-chat-resizer")
        if await resizer.count() > 0:
            box = await resizer.first.bounding_box()
            if box:
                sx = box["x"] + box["width"] / 2
                sy = box["y"] + box["height"] / 2
                await page.mouse.move(sx, sy)
                await page.mouse.down()
                await page.mouse.move(sx, sy + 260)
                await page.mouse.up()
                await asyncio.sleep(1.0)
        await page.screenshot(path=os.path.join(out_dir, "alice.png"))

        # API Section
        # 12. APIs list
        print(" -> apis.png & apisetup.png")
        await page.goto(f"{base_url}/#/apis")
        await asyncio.sleep(1.5)
        await page.screenshot(path=os.path.join(out_dir, "apis.png"))
        await page.screenshot(path=os.path.join(out_dir, "apisetup.png"))

        # 13. API Collection Detail
        print(" -> apispecparsed.png")
        await page.goto(f"{base_url}/#/apis/{collection_id}")
        await asyncio.sleep(2.0)
        await page.screenshot(path=os.path.join(out_dir, "apispecparsed.png"))

        # API Run Detail
        print(f" -> API Run #{api_run_id} tabs...")
        await page.goto(f"{base_url}/#/api-runs/{api_run_id}")
        await asyncio.sleep(2.0)

        # 14. API Findings
        print(" -> apifindings.png")
        await page.click('button.tab-btn:has-text("Findings")')
        await asyncio.sleep(2.5)
        await page.screenshot(path=os.path.join(out_dir, "apifindings.png"))

        # 15. API OWASP Coverage Matrix
        print(" -> apiworkprogram.png")
        await page.click('button.tab-btn:has-text("OWASP Coverage")')
        await asyncio.sleep(2.5)
        await page.screenshot(path=os.path.join(out_dir, "apiworkprogram.png"))

        await browser.close()
        print("Successfully captured all documentation screenshots.")


def main():
    parser = argparse.ArgumentParser(
        description="Capture AESPA documentation screenshots."
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000", help="Base URL of AESPA web server"
    )
    parser.add_argument(
        "--out-dir", default="docs/images", help="Target output directory for images"
    )
    parser.add_argument("--db-path", default="aespa.db", help="Path to SQLite database")
    args = parser.parse_args()

    web_run_id, site_id, api_run_id, collection_id = get_top_runs(args.db_path)
    asyncio.run(
        capture_screenshots(
            args.url, args.out_dir, web_run_id, site_id, api_run_id, collection_id
        )
    )


if __name__ == "__main__":
    main()
