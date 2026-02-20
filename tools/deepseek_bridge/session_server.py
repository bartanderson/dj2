#!/usr/bin/env python3
"""
Persistent DeepSeek session server.
Listens for commands via a file and executes them, keeping browser open.
Session files stored in ai_context/session/.
"""

import sys
import json
import time
import os
import signal
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.deepseek_bridge.bridge_lib import consult
from tools.bridge.unified_core import BridgeCore

# Session directory
SESSION_DIR = PROJECT_ROOT / "ai_context" / "session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

CMD_FILE = SESSION_DIR / "cmd.json"
RESP_DIR = SESSION_DIR / "responses"
RESP_DIR.mkdir(exist_ok=True)
PID_FILE = SESSION_DIR / "server.pid"

def main():
    poll_interval = 2  # seconds

    # Start browser
    core = BridgeCore(verbose=False)
    if not core.connect():
        print("Failed to connect to DeepSeek", file=sys.stderr)
        sys.exit(1)

    print(f"Session server started. PID: {os.getpid()}")
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    running = True
    processed_ids = set()

    def signal_handler(sig, frame):
        nonlocal running
        print("Shutting down...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while running:
        if CMD_FILE.exists():
            try:
                with open(CMD_FILE, 'r', encoding='utf-8') as f:
                    cmd = json.load(f)
                cmd_id = cmd.get('id')
                if cmd_id and cmd_id not in processed_ids:
                    processed_ids.add(cmd_id)
                    op = cmd.get('operation')
                    if op == 'consult':
                        file_path = cmd.get('file')
                        prompt = cmd.get('prompt', '')
                        if not file_path:
                            error = "Missing 'file'"
                            response_data = {"status": "error", "error": error}
                        else:
                            path = Path(file_path)
                            if not path.is_absolute():
                                path = PROJECT_ROOT / path
                            if not path.exists():
                                error = f"File not found: {path}"
                                response_data = {"status": "error", "error": error}
                            else:
                                try:
                                    response_text = consult(core.driver, path, prompt)
                                    response_data = {"status": "success", "data": response_text}
                                except Exception as e:
                                    response_data = {"status": "error", "error": str(e)}
                        # Write response
                        resp_file = RESP_DIR / f"resp_{cmd_id}.json"
                        with open(resp_file, 'w', encoding='utf-8') as f:
                            json.dump(response_data, f)
                    elif op == 'stop':
                        running = False
                    else:
                        resp_file = RESP_DIR / f"resp_{cmd_id}.json"
                        with open(resp_file, 'w', encoding='utf-8') as f:
                            json.dump({"status": "error", "error": f"Unknown operation: {op}"}, f)
                CMD_FILE.unlink()
            except Exception as e:
                print(f"Error processing command: {e}", file=sys.stderr)
        time.sleep(poll_interval)

    core.close()
    try:
        PID_FILE.unlink()
    except:
        pass
    print("Session server stopped.")

if __name__ == "__main__":
    main()