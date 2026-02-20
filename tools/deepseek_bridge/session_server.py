#!/usr/bin/env python3
"""
Persistent DeepSeek session server.
Listens for commands via a file and executes them, keeping browser open.
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

def main():
    cmd_file = Path("session_cmd.json")
    resp_dir = Path("session_responses")
    resp_dir.mkdir(exist_ok=True)
    poll_interval = 2  # seconds

    # Start browser
    core = BridgeCore(verbose=False)
    if not core.connect():
        print("Failed to connect to DeepSeek", file=sys.stderr)
        sys.exit(1)

    print(f"Session server started. PID: {os.getpid()}")
    # Write PID file for management
    with open("session_server.pid", "w") as f:
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
        if cmd_file.exists():
            try:
                with open(cmd_file, 'r', encoding='utf-8') as f:
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
                        resp_file = resp_dir / f"resp_{cmd_id}.json"
                        with open(resp_file, 'w', encoding='utf-8') as f:
                            json.dump(response_data, f)
                    elif op == 'stop':
                        running = False
                    else:
                        # unknown operation
                        resp_file = resp_dir / f"resp_{cmd_id}.json"
                        with open(resp_file, 'w', encoding='utf-8') as f:
                            json.dump({"status": "error", "error": f"Unknown operation: {op}"}, f)
                # Remove command file after processing
                cmd_file.unlink()
            except Exception as e:
                print(f"Error processing command: {e}", file=sys.stderr)
                # Optionally write error response
                # For simplicity, just log and continue
        time.sleep(poll_interval)

    core.close()
    # Clean up PID file
    try:
        os.unlink("session_server.pid")
    except:
        pass
    print("Session server stopped.")

if __name__ == "__main__":
    main()