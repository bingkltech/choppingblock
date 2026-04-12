from playwright.sync_api import sync_playwright
import time
import os

def run_cuj(page):
    page.goto("http://localhost:4173")
    page.wait_for_timeout(1000)

    # Click on the Agents tab in sidebar
    page.click('#sidebar-agents')
    page.wait_for_timeout(1000)

    # Take screenshot of the agent manager main view
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)
    page.screenshot(path="/home/jules/verification/screenshots/agent_manager.png", full_page=True)
    page.wait_for_timeout(1000)

    # Click on "+ Hire New AI Worker"
    page.get_by_role("button", name="+ Hire New AI Worker").click()
    page.wait_for_timeout(1000)

    # Take screenshot of the hire modal
    page.screenshot(path="/home/jules/verification/screenshots/agent_manager_hire.png", full_page=True)
    page.wait_for_timeout(1000)

    # Click Jules Dispatch Tab
    page.get_by_text("Jules Operations").click()
    page.wait_for_timeout(1000)

    # Take screenshot of dispatch panel
    page.screenshot(path="/home/jules/verification/screenshots/agent_manager_dispatch.png", full_page=True)
    page.wait_for_timeout(1000)

    print("Success")


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
