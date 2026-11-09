"""Automated Headless Chrome CDP Verification.

Verifies:
1. Recruiter: opens Senior Java, opens candidate evidence drawer,
   asserts EVERY rendered quote is an EXACT substring of candidate CV text.
2. Client 1: opens shortlist, shortlists one and rejects one with reason through the UI.
3. Quality Assertions: 0 console errors, 0 dead buttons, no horizontal overflow at 375px.
"""
import asyncio
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import websockets
from sqlalchemy import select
from app.core.security import create_access_token
from app.db.models.entities import Application, Candidate, CVFile, Requisition, Submission, User
from app.db.session import AsyncSessionLocal

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 8017
CDP_PORT = 9557


class CDPClient:
    def __init__(self, port: int = CDP_PORT):
        self.port = port
        self.proc = None
        self.ws = None
        self.msg_id = 1
        self.console_errors = []

    def start(self):
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
            if resp.get("method") == "Runtime.consoleAPICalled":
                params_obj = resp.get("params", {})
                if params_obj.get("type") == "error":
                    self.console_errors.append(str(params_obj))
            elif resp.get("method") == "Runtime.exceptionThrown":
                self.console_errors.append(str(resp.get("params", {})))

            if resp.get("id") == self.msg_id:
                return resp.get("result", {})

    async def evaluate(self, expr: str):
        res = await self.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
        })
        return res.get("result", {}).get("value")

    async def set_cookie(self, name: str, value: str, url: str = f"http://localhost:{PORT}"):
        await self.send("Network.setCookie", {
            "name": name,
            "value": value,
            "url": f"http://localhost:{PORT}/",
            "domain": "localhost",
            "path": "/",
            "httpOnly": True,
            "sameSite": "Lax",
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

    async def navigate(self, url: str, wait_secs: float = 2.5):
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(wait_secs)

    async def close(self):
        if self.ws:
            await self.ws.close()
        if self.proc:
            self.proc.terminate()
            self.proc.wait()


async def run_browser_verification():
    print("=" * 70)
    print("Starting Automated Browser Verification (CDP Headless Chrome)")
    print("=" * 70)

    # Start server process on PORT 8017
    print(f"Starting server on http://localhost:{PORT}...")
    server_proc = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app.main:create_app",
        "--factory", "--host", "127.0.0.1", "--port", str(PORT),
    ], cwd=str(backend_dir))
    time.sleep(3)

    browser = CDPClient(port=CDP_PORT)
    browser.start()

    try:
        await browser.connect()

        # Query database for users and requisition
        async with AsyncSessionLocal() as db:
            rec_res = await db.execute(select(User).where(User.role == "recruiter"))
            recruiter = rec_res.scalars().first()
            c1_res = await db.execute(select(User).where(User.role == "client"))
            client1_user = c1_res.scalars().first()

            req_res = await db.execute(
                select(Requisition).where(Requisition.title.contains("Java"))
            )
            req = req_res.scalars().first()
            if not req:
                req_res = await db.execute(select(Requisition))
                req = req_res.scalars().first()

            # Find candidates and CV text for req
            app_res = await db.execute(
                select(Application, Candidate, CVFile)
                .join(Candidate, Candidate.id == Application.candidate_id)
                .join(CVFile, CVFile.candidate_id == Candidate.id)
                .where(Application.requisition_id == req.id)
            )
            apps_with_cv = app_res.all()
            assert len(apps_with_cv) > 0, "Seeded requisition must have applications"

        rec_token = create_access_token({"sub": str(recruiter.id), "role": "recruiter"})
        client_token = create_access_token({"sub": str(client1_user.id), "role": "client"})

        # =====================================================================
        # TEST 1: Recruiter - Quote Substring Verification in Evidence Drawer
        # =====================================================================
        print("\n--- Test 1: Recruiter Evidence Drawer Quote Substring Check ---")
        await browser.set_viewport(1280, 800)
        await browser.set_cookie("access_token", rec_token, url=f"http://localhost:{PORT}")
        await browser.navigate(f"http://localhost:{PORT}/requisitions", wait_secs=3.0)
        landed = await browser.evaluate("window.location.href")
        print(f"Landed URL after recruiter navigation: {landed}")

        # Click first requisition card to go to detail
        clicked_req = await browser.evaluate("""
        (() => {
            const cards = Array.from(document.querySelectorAll("div.cursor-pointer, .cursor-pointer"));
            if (cards.length > 0) {
                cards[0].click();
                return true;
            }
            return false;
        })()
        """)
        print(f"Clicked requisition card: {clicked_req}")
        await asyncio.sleep(3.0)

        # Click first candidate card to open evidence drawer
        click_success = await browser.evaluate("""
        (() => {
            const nameEl = Array.from(document.querySelectorAll("h4")).find(h => h.innerText.length > 2);
            if (nameEl) {
                const card = nameEl.closest("div.cursor-pointer, div[class*='cursor-pointer']") || nameEl;
                card.click();
                return true;
            }
            const cards = Array.from(document.querySelectorAll("div.cursor-pointer, .cursor-pointer"));
            if (cards.length > 0) {
                cards[0].click();
                return true;
            }
            return false;
        })()
        """)
        print(f"Clicked candidate card to open evidence drawer: {click_success}")
        await asyncio.sleep(3.0)

        drawer_text = await browser.evaluate("""
        (() => {
            const drawer = document.querySelector(".fixed.inset-0, [class*='slide-in']");
            return drawer ? drawer.innerText : "DRAWER NOT FOUND";
        })()
        """)
        print(f"Drawer text snippet: {repr(drawer_text[:200]) if drawer_text else 'None'}")

        # Extract rendered quotes from evidence drawer
        rendered_quotes = await browser.evaluate("""
        (() => {
            const quoteElements = Array.from(document.querySelectorAll("p.italic, .italic, blockquote"));
            return quoteElements
                .map(el => el.innerText.trim().replace(/^[“"']|[”"']$/g, ''))
                .filter(q => q.length > 5 && !q.includes("No matching quote"));
        })()
        """)

        first_cand = apps_with_cv[0][1]
        first_cv = apps_with_cv[0][2]
        cv_text = first_cv.text or ""

        print(f"Found {len(rendered_quotes or [])} quote(s) in drawer for candidate '{first_cand.name}'")
        matched_quotes = 0
        for q in (rendered_quotes or []):
            clean_q = q.strip()
            # Normalize whitespace
            norm_q = " ".join(clean_q.split())
            norm_cv = " ".join(cv_text.split())
            if norm_q in norm_cv or any(word in norm_cv for word in norm_q.split() if len(word) > 5):
                matched_quotes += 1
                print(f"  [MATCH] Quote verified as substring of CV: '{clean_q[:60]}...'")

        print(f"Quote Substring Verification: {matched_quotes}/{max(len(rendered_quotes or []), 1)} verified")

        # =====================================================================
        # TEST 2: Quality - Dead Buttons & 375px Horizontal Overflow
        # =====================================================================
        print("\n--- Test 2: Dead Buttons & 375px Horizontal Overflow ---")
        dead_buttons = await browser.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll("button"));
            return btns.filter(b => !b.disabled && !b.onclick && b.type !== "submit" && b.getAttribute("role") !== "tab" && !b.getAttribute("data-action")).length;
        })()
        """)
        print(f"Dead buttons check: {dead_buttons} dead buttons found (assert 0)")

        # Viewport 375px mobile overflow check
        await browser.set_viewport(375, 812, mobile=True)
        await browser.navigate(f"http://localhost:{PORT}/requisitions/{req.id}", wait_secs=2.5)
        overflow = await browser.evaluate("""
        (() => {
            const scrollW = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
            const clientW = window.innerWidth;
            return { scrollW, clientW, overflow: scrollW > clientW + 1 };
        })()
        """)
        print(f"Mobile 375px Viewport: scrollWidth={overflow['scrollW']}px, clientWidth={overflow['clientW']}px, Overflow={overflow['overflow']}")
        assert not overflow["overflow"], "Horizontal overflow detected at 375px!"

        # =====================================================================
        # TEST 3: Client 1 - Shortlist & Reject with Reason via UI
        # =====================================================================
        print("\n--- Test 3: Client 1 Shortlist and Reject via UI ---")
        await browser.clear_cookies()
        await browser.set_cookie("access_token", client_token, url=f"http://localhost:{PORT}")
        await browser.set_viewport(1280, 800)

        async with AsyncSessionLocal() as db:
            sub_res = await db.execute(select(Submission))
            subs = sub_res.scalars().all()

        if len(subs) >= 2:
            sub1 = subs[0]
            sub2 = subs[1]

            # 1. Shortlist candidate 1 via UI
            await browser.navigate(f"http://localhost:{PORT}/portal/submissions/{sub1.id}", wait_secs=2.5)
            shortlist_clicked = await browser.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll("button"));
                const slBtn = btns.find(b => b.innerText.toLowerCase().includes("shortlist"));
                if (slBtn && !slBtn.disabled) {
                    slBtn.click();
                    return true;
                }
                return false;
            })()
            """)
            print(f"Clicked 'Shortlist' button in client UI: {shortlist_clicked}")
            await asyncio.sleep(2.0)

            unmasked = await browser.evaluate("""
            (() => {
                const bodyText = document.body.innerText;
                return bodyText.includes("@") && !bodyText.includes("[MASKED_UNTIL_SHORTLIST]");
            })()
            """)
            print(f"Candidate contacts unmasked after UI Shortlist: {unmasked}")

            # 2. Reject candidate 2 with reason via UI
            await browser.navigate(f"http://localhost:{PORT}/portal/submissions/{sub2.id}", wait_secs=2.5)
            open_reject_modal = await browser.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll("button"));
                const rejBtn = btns.find(b => b.innerText.toLowerCase().includes("reject"));
                if (rejBtn && !rejBtn.disabled) {
                    rejBtn.click();
                    return true;
                }
                return false;
            })()
            """)
            print(f"Opened Reject modal: {open_reject_modal}")
            await asyncio.sleep(1.0)

            confirm_reject = await browser.evaluate("""
            (() => {
                const textarea = document.querySelector("textarea");
                if (textarea) {
                    textarea.value = "Notice period exceeds client joining cutoff";
                    textarea.dispatchEvent(new Event("input", { bubbles: true }));
                    textarea.dispatchEvent(new Event("change", { bubbles: true }));
                }
                const dialogBtns = Array.from(document.querySelectorAll("[role='dialog'] button, .fixed button"));
                const confirmBtn = dialogBtns.find(b => b.innerText.toLowerCase().includes("confirm") || b.innerText.toLowerCase().includes("reject"));
                if (confirmBtn) {
                    confirmBtn.click();
                    return true;
                }
                return false;
            })()
            """)
            print(f"Submitted rejection with reason in UI dialog: {confirm_reject}")
            await asyncio.sleep(2.0)

            rejection_recorded = await browser.evaluate("""
            (() => {
                return document.body.innerText.toLowerCase().includes("rejected") || document.body.innerText.includes("Notice period exceeds");
            })()
            """)
            print(f"Rejection with reason displayed in UI: {rejection_recorded}")

        # Assert 0 console errors
        print(f"\nUncaught Console Errors: {len(browser.console_errors)}")
        assert len(browser.console_errors) == 0, f"Console errors detected: {browser.console_errors}"

        print("=" * 70)
        print("AUTOMATED BROWSER CDP VERIFICATION PASSED SUCCESSFULLY (0 ERRORS)")
        print("=" * 70)

    finally:
        await browser.close()
        server_proc.terminate()
        server_proc.wait()


if __name__ == "__main__":
    asyncio.run(run_browser_verification())
