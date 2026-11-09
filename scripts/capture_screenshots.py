"""Capture desktop and mobile (375px) screenshots for all application screens.

Includes an automated assertion verifying no horizontal overflow (scrollWidth <= innerWidth)
at 375px viewport width across all screens.
"""
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import websockets
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.db.models.entities import User, Requisition, Submission
from sqlalchemy import select


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = Path("docs/screenshots")


class CDPBrowser:
    def __init__(self, port: int = 9555):
        self.port = port
        self.proc = None
        self.ws = None
        self.msg_id = 1

    def start(self):
        import tempfile
        self.tmp_dir = tempfile.mkdtemp()
        cmd = [
            CHROME_PATH,
            "--headless=new",
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.tmp_dir}",
            "--remote-allow-origins=*",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "about:blank",
        ]
        self.proc = subprocess.Popen(cmd)
        time.sleep(2)

    async def connect(self):
        url = f"http://127.0.0.1:{self.port}/json"
        req = urllib.request.urlopen(url)
        tabs = json.loads(req.read().decode())
        page_tab = next(t for t in tabs if t.get("type") == "page")
        ws_url = page_tab["webSocketDebuggerUrl"]
        self.ws = await websockets.connect(ws_url, max_size=20 * 1024 * 1024)
        await self.send("Page.enable")
        await self.send("Network.enable")
        await self.send("Runtime.enable")

    async def send(self, method: str, params: dict | None = None) -> dict:
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(msg))
        while True:
            resp_raw = await self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == self.msg_id:
                return resp.get("result", {})

    async def set_cookie(self, name: str, value: str, url: str = "http://localhost:8015"):
        await self.send("Network.setCookie", {
            "name": name,
            "value": value,
            "url": url,
            "httpOnly": True,
        })

    async def clear_cookies(self):
        await self.send("Network.clearBrowserCookies")

    async def set_viewport(self, width: int, height: int, mobile: bool = False):
        await self.send("Emulation.setDeviceMetricsOverride", {
            "width": width,
            "height": height,
            "deviceScaleFactor": 2 if mobile else 1,
            "mobile": mobile,
        })

    async def check_horizontal_overflow(self) -> dict:
        expr = """
        (() => {
            const docW = document.documentElement ? document.documentElement.scrollWidth : 0;
            const bodyW = document.body ? document.body.scrollWidth : 0;
            const scrollW = Math.max(docW, bodyW);
            const clientW = window.innerWidth;
            return {
                scrollWidth: scrollW,
                clientWidth: clientW,
                overflow: scrollW > clientW + 1
            };
        })()
        """
        res = await self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        val = res.get("result", {}).get("value", {})
        return val

    async def capture(self, url: str, out_filename: str, wait_secs: float = 2.0, assert_no_overflow: bool = False):
        print(f"Navigating to {url} -> {out_filename}...")
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(wait_secs)

        if assert_no_overflow:
            overflow_info = await self.check_horizontal_overflow()
            scroll_w = overflow_info.get("scrollWidth", 0)
            client_w = overflow_info.get("clientWidth", 375)
            is_overflow = overflow_info.get("overflow", False)
            print(f"  [375px Overflow Check] scrollWidth: {scroll_w}px, clientWidth: {client_w}px -> Overflow: {is_overflow}")
            assert not is_overflow, (
                f"Horizontal overflow detected on {out_filename}: scrollWidth={scroll_w}px > clientWidth={client_w}px"
            )

        res = await self.send("Page.captureScreenshot", {"format": "png"})
        img_bytes = base64.b64decode(res["data"])
        out_path = SCREENSHOT_DIR / out_filename
        with open(out_path, "wb") as f:
            f.write(img_bytes)
        print(f"  Saved: {out_path} ({len(img_bytes) // 1024} KB)")

    async def close(self):
        if self.ws:
            await self.ws.close()
        if self.proc:
            self.proc.terminate()
            self.proc.wait()


async def main():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Start server process
    print("Starting background server on http://localhost:8015...")
    server_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app.main:create_app",
        "--factory", "--host", "127.0.0.1", "--port", "8015",
    ], cwd=str(backend_dir))
    time.sleep(3)

    # 2. Get tokens from DB
    async with AsyncSessionLocal() as db:
        rec_res = await db.execute(select(User).where(User.role == "recruiter"))
        recruiter = rec_res.scalars().first()
        client_res = await db.execute(select(User).where(User.role == "client"))
        client_user = client_res.scalars().first()

        req_res = await db.execute(select(Requisition))
        req = req_res.scalars().first()

        sub_res = await db.execute(select(Submission))
        sub = sub_res.scalars().first()

    rec_token = create_access_token({"sub": str(recruiter.id), "role": "recruiter"})
    client_token = create_access_token({"sub": str(client_user.id), "role": "client"})

    browser = CDPBrowser(port=9555)
    browser.start()

    try:
        await browser.connect()
        req_id = req.id if req else 1
        sub_id = sub.id if sub else 1

        # -------------------------------------------------------------
        # Screen 1: Login Page (Unauthenticated)
        # -------------------------------------------------------------
        await browser.clear_cookies()
        await browser.set_viewport(1280, 800)
        await browser.capture("http://localhost:8015/login", "01_login_desktop.png")
        await browser.set_viewport(375, 812, mobile=True)
        await browser.capture("http://localhost:8015/login", "01_login_mobile_375.png", assert_no_overflow=True)

        # -------------------------------------------------------------
        # Screen 2: Requisitions List (Recruiter)
        # -------------------------------------------------------------
        await browser.set_cookie("access_token", rec_token)
        await browser.set_viewport(1280, 800)
        await browser.capture("http://localhost:8015/requisitions", "02_requisitions_desktop.png")
        await browser.set_viewport(375, 812, mobile=True)
        await browser.capture("http://localhost:8015/requisitions", "02_requisitions_mobile_375.png", assert_no_overflow=True)

        # -------------------------------------------------------------
        # Screen 3: Requisition Detail - Scorecard Editor (Recruiter)
        # -------------------------------------------------------------
        await browser.set_viewport(1280, 800)
        await browser.capture(f"http://localhost:8015/requisitions/{req_id}?tab=scorecard", "03_scorecard_desktop.png", wait_secs=2.5)
        await browser.set_viewport(375, 812, mobile=True)
        await browser.capture(f"http://localhost:8015/requisitions/{req_id}?tab=scorecard", "03_scorecard_mobile_375.png", wait_secs=2.5, assert_no_overflow=True)

        # -------------------------------------------------------------
        # Screen 4: Requisition Detail - Bulk Upload Dropzone & Progress (Recruiter)
        # -------------------------------------------------------------
        await browser.set_viewport(1280, 800)
        await browser.capture(f"http://localhost:8015/requisitions/{req_id}?tab=upload", "04_upload_desktop.png", wait_secs=2.0)
        await browser.set_viewport(375, 812, mobile=True)
        await browser.capture(f"http://localhost:8015/requisitions/{req_id}?tab=upload", "04_upload_mobile_375.png", wait_secs=2.0, assert_no_overflow=True)

        # -------------------------------------------------------------
        # Screen 5: Requisition Detail - Candidates Ranked List & Evidence Drawer (Recruiter)
        # -------------------------------------------------------------
        await browser.set_viewport(1280, 800)
        await browser.capture(f"http://localhost:8015/requisitions/{req_id}?tab=candidates", "05_ranked_list_desktop.png", wait_secs=2.5)
        await browser.set_viewport(375, 812, mobile=True)
        await browser.capture(f"http://localhost:8015/requisitions/{req_id}?tab=candidates", "05_ranked_list_mobile_375.png", wait_secs=2.5, assert_no_overflow=True)

        # -------------------------------------------------------------
        # Screen 6: Requisition Detail - Kanban Pipeline Board (Recruiter)
        # -------------------------------------------------------------
        await browser.set_viewport(1280, 800)
        await browser.capture(f"http://localhost:8015/requisitions/{req_id}?tab=pipeline", "06_pipeline_desktop.png", wait_secs=2.5)
        await browser.set_viewport(375, 812, mobile=True)
        await browser.capture(f"http://localhost:8015/requisitions/{req_id}?tab=pipeline", "06_pipeline_mobile_375.png", wait_secs=2.5, assert_no_overflow=True)

        # -------------------------------------------------------------
        # Screen 7: Client Portal - Requisitions & Submissions (Client)
        # -------------------------------------------------------------
        await browser.clear_cookies()
        await browser.set_cookie("access_token", client_token)
        await browser.set_viewport(1280, 800)
        await browser.capture("http://localhost:8015/portal", "07_client_portal_desktop.png", wait_secs=2.5)
        await browser.set_viewport(375, 812, mobile=True)
        await browser.capture("http://localhost:8015/portal", "07_client_portal_mobile_375.png", wait_secs=2.5, assert_no_overflow=True)

        # -------------------------------------------------------------
        # Screen 8: Client Portal - Candidate Evaluation with Sticky Action Bar (Client)
        # -------------------------------------------------------------
        await browser.set_viewport(1280, 800)
        await browser.capture(f"http://localhost:8015/portal/submissions/{sub_id}", "08_client_review_desktop.png", wait_secs=2.5)
        await browser.set_viewport(375, 812, mobile=True)
        await browser.capture(f"http://localhost:8015/portal/submissions/{sub_id}", "08_client_review_mobile_375.png", wait_secs=2.5, assert_no_overflow=True)

        print("\nAll 8 screens captured successfully at Desktop and 375px Mobile with NO HORIZONTAL OVERFLOW!")

    finally:
        await browser.close()
        server_proc.terminate()
        server_proc.wait()


if __name__ == "__main__":
    asyncio.run(main())
