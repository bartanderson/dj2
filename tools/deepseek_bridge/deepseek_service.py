#!/usr/bin/env python3
"""
deepseek_service.py - Main DeepSeek automation service.
Replaces session_server.py and provides HTTP API for consultations.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import traceback
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from fastapi import FastAPI, HTTPException
import uvicorn

PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
SESSION_DIR = PROJECT_ROOT / "ai_context" / "session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
PORT_FILE = SESSION_DIR / "port.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "deepseek_service.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("deepseek_service")


@dataclass
class ConversationTurn:
    turn_number: int
    timestamp: str
    prompt: str
    file_attached: Optional[str] = None
    response_text: Optional[str] = None
    extracted_data: Optional[Dict] = None
    duration_ms: float = 0
    status: str = "pending"


@dataclass
class ConversationSession:
    session_id: str
    created_at: str
    turns: List[ConversationTurn] = field(default_factory=list)
    current_turn: int = 0
    state: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "current_turn": self.current_turn,
            "status": self.status,
            "state": self.state,
            "turns": [asdict(t) for t in self.turns]
        }


class DeepSeekController:
    def __init__(self, cdp_url: Optional[str] = None):
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.sessions: Dict[str, ConversationSession] = {}
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> bool:
        try:
            logger.info("Starting browser...")
            self.playwright = await async_playwright().start()
            
            if self.cdp_url:
                self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
                logger.info(f"Connected to Chrome: {self.cdp_url}")
            else:
                self.browser = await self.playwright.chromium.launch(headless=False)
                logger.info("Launched new browser")
            
            self.context = await self.browser.new_context(viewport={"width": 1920, "height": 1080})
            self.page = await self.context.new_page()
            await self.page.goto("https://chat.deepseek.com", wait_until="networkidle")
            await self._wait_for_ready()
            
            logger.info("Ready for conversations")
            return True
            
        except Exception as e:
            logger.error(f"Init failed: {e}")
            await self.cleanup()
            return False
    
    async def cleanup(self):
        try:
            if self.page: await self.page.close()
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    async def recover(self) -> bool:
        logger.warning("Recovering browser...")
        await self.cleanup()
        return await self.initialize()
    
    async def health_check(self) -> bool:
        try:
            if not self.page or self.page.is_closed():
                return False
            await self.page.evaluate("1 + 1")
            return True
        except:
            return False
    
    async def _wait_for_ready(self):
        selectors = ["textarea", "[contenteditable='true']", "button[type='submit']"]
        for sel in selectors:
            try:
                await self.page.wait_for_selector(sel, timeout=10000)
                return
            except:
                continue
        raise Exception("DeepSeek not ready")
    
    def create_session(self) -> str:
        sid = str(uuid.uuid4())[:12]
        self.sessions[sid] = ConversationSession(
            session_id=sid,
            created_at=datetime.now().isoformat()
        )
        logger.info(f"Created session: {sid}")
        return sid
    
    async def consult(self, session_id: str, file_path: Optional[Path], prompt: str) -> Dict:
        async with self._lock:
            if not await self.health_check():
                if not await self.recover():
                    raise Exception("Browser dead")
            
            session = self.sessions.get(session_id)
            if not session:
                raise Exception(f"No session: {session_id}")
            
            turn = ConversationTurn(
                turn_number=session.current_turn + 1,
                timestamp=datetime.now().isoformat(),
                prompt=prompt,
                file_attached=str(file_path) if file_path else None
            )
            session.turns.append(turn)
            session.current_turn = turn.turn_number
            
            start = time.time()
            
            try:
                if file_path and file_path.exists():
                    await self._upload_file(file_path)
                
                await self._send_message(prompt)
                response = await self._capture_response()
                
                turn.response_text = response
                turn.duration_ms = (time.time() - start) * 1000
                turn.status = "complete"
                
                # Try extract JSON
                turn.extracted_data = self._extract_json(response)
                
                if self._is_done_signal(response):
                    session.status = "completed"
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "turn": turn.turn_number,
                    "response": response,
                    "extracted_data": turn.extracted_data,
                    "status": session.status
                }
                
            except Exception as e:
                turn.status = "error"
                session.status = "error"
                raise
    
    async def _upload_file(self, file_path: Path):
        logger.info(f"Uploading: {file_path.name}")
        input_el = await self.page.query_selector("input[type='file']")
        if input_el:
            await input_el.set_input_files(str(file_path))
            await asyncio.sleep(2)  # Wait for processing
            return
        raise Exception("No file input found")
    
    async def _send_message(self, text: str):
        logger.info(f"Sending: {text[:50]}...")
        el = await self.page.query_selector("textarea, [contenteditable='true']")
        if not el:
            raise Exception("No input found")
        
        is_edit = await el.evaluate("el => el.contentEditable === 'true'")
        if is_edit:
            await el.click()
            await el.evaluate("el => el.innerHTML = ''")
            await el.type(text)
        else:
            await el.fill(text)
        
        await el.press("Enter")
        await asyncio.sleep(0.5)
    
    async def _capture_response(self) -> str:
        logger.info("Waiting for response...")
        
        # Inject monitor
        await self.page.evaluate("""
            window._ds = {
                lastText: '',
                stable: 0,
                done: false,
                check() {
                    const msgs = document.querySelectorAll('[class*="message"], [class*="chat-item"]');
                    if (!msgs.length) return;
                    const last = msgs[msgs.length - 1];
                    const text = last.innerText || '';
                    if (text === this.lastText && text.length > 10) {
                        this.stable++;
                        if (this.stable >= 3) this.done = true;
                    } else {
                        this.stable = 0;
                        this.lastText = text;
                    }
                }
            };
            new MutationObserver(() => window._ds.check())
                .observe(document.body, {childList: true, subtree: true, characterData: true});
        """)
        
        start = time.time()
        while time.time() - start < 7200:
            if await self.page.evaluate("window._ds.done"):
                text = await self.page.evaluate("window._ds.lastText")
                await self.page.evaluate("delete window._ds")
                return text
            await asyncio.sleep(1)
        
        return await self.page.evaluate("window._ds.lastText || ''")
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        import re
        # Try code block
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
        # Try raw object
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                pass
        return None
    
    def _is_done_signal(self, text: str) -> bool:
        signals = ["TASK_COMPLETE", '"done":true', '"status":"complete"', "===DONE==="]
        return any(s in text for s in signals)


# FastAPI app
app = FastAPI()
controller: Optional[DeepSeekController] = None

@app.on_event("startup")
async def startup():
    global controller
    cdp = os.getenv("DEEPSEEK_CDP_URL")
    controller = DeepSeekController(cdp)
    if not await controller.initialize():
        logger.error("Failed to start")
        return
    # Write port file
    PORT_FILE.write_text("8000")

@app.on_event("shutdown")
async def shutdown():
    global controller
    if controller:
        await controller.cleanup()
    try:
        PORT_FILE.unlink()
    except:
        pass

@app.get("/health")
async def health():
    if not controller:
        return {"status": "down"}
    ok = await controller.health_check()
    return {"status": "healthy" if ok else "degraded"}

@app.post("/session/create")
async def create_session():
    if not controller:
        raise HTTPException(503, "Not ready")
    sid = controller.create_session()
    return {"session_id": sid}

@app.post("/session/{sid}/consult")
async def consult(sid: str, prompt: str, file_path: Optional[str] = None):
    if not controller:
        raise HTTPException(503, "Not ready")
    
    path = Path(file_path) if file_path else None
    if path and not path.is_absolute():
        path = PROJECT_ROOT / path
    
    try:
        result = await controller.consult(sid, path, prompt)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/session/{sid}")
async def get_session(sid: str):
    if not controller:
        raise HTTPException(503, "Not ready")
    s = controller.sessions.get(sid)
    if not s:
        raise HTTPException(404, "Not found")
    return s.to_dict()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdp-url", help="Chrome CDP URL")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    
    if args.cdp_url:
        os.environ["DEEPSEEK_CDP_URL"] = args.cdp_url
    
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")

if __name__ == "__main__":
    main()