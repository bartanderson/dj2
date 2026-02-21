#!/usr/bin/env python3
"""
Persistent DeepSeek session server (socket version).
Listens on a local TCP port, accepts JSON commands, and returns JSON responses.
Browser stays open between commands.
"""

import sys
import json
import socket
import threading
import time
import os
import signal
import logging
import traceback
import base64
import re
from pathlib import Path
import subprocess

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.deepseek_bridge.bridge_lib import consult
from tools.bridge.unified_core import BridgeCore
from tools.nativeclaw.nativeclaw import Session

# Session directory
SESSION_DIR = PROJECT_ROOT / "ai_context" / "session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
PORT_FILE = SESSION_DIR / "port.txt"

# Logging
logging.basicConfig(
    filename='session_server.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Global driver and running flag
core = None
running = True

def maybe_decode_base64(content):
    """If content is valid base64, decode and return as utf-8 string; otherwise return as is."""
    try:
        if re.match(r'^[A-Za-z0-9+/=]+$', content) and len(content) % 4 == 0:
            decoded = base64.b64decode(content).decode('utf-8')
            return decoded
    except:
        pass
    return content

def send_response(conn, response):
    """Send a JSON response with a 4‑byte length prefix."""
    try:
        response_json = json.dumps(response)
        data = response_json.encode('utf-8')
        logging.info(f"Sending response of length {len(data)} bytes")
        conn.sendall(len(data).to_bytes(4, 'big'))
        conn.sendall(data)
        logging.info("Response sent")
    except (BrokenPipeError, ConnectionResetError) as e:
        logging.error(f"Client disconnected while sending response: {e}")
    except Exception as e:
        logging.error(f"Error sending response: {e}")

def handle_client(conn, addr):
    """Handle one client connection: read command, execute, send response."""
    global core
    client_start = time.time()
    logging.info(f"Handling client from {addr} at {client_start}")
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # enable keepalive
    try:
        data = conn.recv(8192)
        if not data:
            logging.warning("Empty data received")
            return
        cmd = json.loads(data.decode('utf-8'))
        logging.info(f"Received command after {time.time()-client_start:.2f}s: {cmd}")
        cmd_id = cmd.get('id', 'unknown')
        op = cmd.get('operation')
        logging.info(f"Operation: {op}")

        if op == 'consult':
            file_path = cmd.get('file')
            prompt = cmd.get('prompt', '')
            if not file_path:
                response = {"status": "error", "error": "Missing 'file'"}
            else:
                path = Path(file_path)
                if not path.is_absolute():
                    path = PROJECT_ROOT / path
                if not path.exists():
                    response = {"status": "error", "error": f"File not found: {path}"}
                else:
                    try:
                        action_start = time.time()
                        resp_text = consult(core.driver, path, prompt)
                        logging.info(f"Consult took {time.time()-action_start:.2f}s")
                        response = {"status": "success", "data": resp_text}
                    except Exception as e:
                        response = {"status": "error", "error": str(e)}

        elif op == 'run_nativeclaw':
            subcmd = cmd.get('subcommand')
            args_list = cmd.get('args', [])
            if not subcmd:
                response = {"status": "error", "error": "Missing 'subcommand'"}
                logging.error("run_nativeclaw: missing subcommand")
            else:
                nativeclaw_script = PROJECT_ROOT / "tools" / "nativeclaw" / "nativeclaw.py"
                if not nativeclaw_script.exists():
                    error_msg = f"nativeclaw script not found at {nativeclaw_script}"
                    logging.error(error_msg)
                    response = {"status": "error", "error": error_msg}
                else:
                    cmd_line = [sys.executable, str(nativeclaw_script), subcmd] + args_list
                    logging.info(f"run_nativeclaw: executing {cmd_line}")
                    action_start = time.time()
                    try:
                        result = subprocess.run(
                            cmd_line,
                            cwd=PROJECT_ROOT,
                            capture_output=True,
                            text=True,
                            encoding='utf-8',
                            timeout=120
                        )
                        elapsed = time.time() - action_start
                        logging.info(f"run_nativeclaw completed in {elapsed:.2f}s, returncode {result.returncode}")
                        response = {
                            "status": "success",
                            "returncode": result.returncode,
                            "stdout": result.stdout,
                            "stderr": result.stderr
                        }
                    except subprocess.TimeoutExpired as e:
                        elapsed = time.time() - action_start
                        logging.error(f"run_nativeclaw timed out after {elapsed:.2f}s: {e}")
                        response = {"status": "error", "error": f"Timeout after {elapsed:.2f}s"}
                    except Exception as e:
                        elapsed = time.time() - action_start
                        logging.error(f"run_nativeclaw exception after {elapsed:.2f}s: {e}", exc_info=True)
                        response = {"status": "error", "error": str(e)}
            # Send response for this branch
            logging.info(f"run_nativeclaw: sending response")
            send_response(conn, response)

        elif op == 'get_file':
            file_path = cmd.get('file')
            if not file_path:
                response = {"status": "error", "error": "Missing 'file'"}
            else:
                path = Path(file_path)
                if not path.is_absolute():
                    path = PROJECT_ROOT / path
                if not path.exists():
                    response = {"status": "error", "error": f"File not found: {path}"}
                else:
                    try:
                        action_start = time.time()
                        content = path.read_text(encoding='utf-8')
                        logging.info(f"get_file took {time.time()-action_start:.2f}s")
                        response = {"status": "success", "content": content}
                    except Exception as e:
                        response = {"status": "error", "error": str(e)}
        elif op == 'apply_plan':
            plan = cmd.get('plan')
            if not plan:
                response = {"status": "error", "error": "Missing 'plan'"}
            else:
                try:
                    from datetime import datetime
                    action_start = time.time()
                    session = Session("auto_apply", PROJECT_ROOT)
                    branch = session.start()
                    for change in plan:
                        file_path = PROJECT_ROOT / change['file']
                        op_type = change['operation']
                        if 'content' in change:
                            decoded = maybe_decode_base64(change['content'])
                            change['content'] = decoded
                        if op_type in ('create', 'modify'):
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            file_path.write_text(change['content'], encoding='utf-8')
                            session.track_created(str(file_path.relative_to(PROJECT_ROOT)))
                        elif op_type == 'delete':
                            if file_path.exists():
                                file_path.unlink()
                    # Save review
                    archive_dir = PROJECT_ROOT / ".nativeclaw" / "archive" / datetime.now().strftime("%Y%m%d_%H%M%S")
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    state = {
                        'branch_name': branch,
                        'original_branch': session.original_branch,
                        'goal_name': 'auto_apply',
                        'timestamp': datetime.now().isoformat()
                    }
                    with open(archive_dir / "state.json", 'w', encoding='utf-8') as f:
                        json.dump(state, f, indent=2)
                    with open(archive_dir / "changes.diff", 'w', encoding='utf-8') as f:
                        subprocess.run(
                            ["git", "diff", f"{session.original_branch}..{branch}"],
                            cwd=PROJECT_ROOT, stdout=f, text=True
                        )
                    with open(archive_dir / "files.txt", 'w', encoding='utf-8') as f:
                        subprocess.run(
                            ["git", "ls-tree", "-r", branch, "--name-only"],
                            cwd=PROJECT_ROOT, stdout=f, text=True
                        )
                    with open(archive_dir / "RESUME.txt", 'w', encoding='utf-8') as f:
                        f.write(f"Resume with: nativeclaw resume {archive_dir}\n")
                    logging.info(f"apply_plan took {time.time()-action_start:.2f}s")
                    response = {"status": "success", "review_path": str(archive_dir)}
                except Exception as e:
                    response = {"status": "error", "error": str(e)}
        elif op == 'stop':
            response = {"status": "success", "data": "Shutting down"}
            send_response(conn, response)
            conn.close()
            global running
            running = False
            return
        else:
            response = {"status": "error", "error": f"Unknown operation: {op}"}

        send_response(conn, response)
        logging.info(f"Total handler time for {op}: {time.time()-client_start:.2f}s")
    except Exception as e:
        logging.error(f"Unhandled exception in handle_client: {e}\n{traceback.format_exc()}")
        try:
            conn.close()
        except:
            pass

def main():
    global core, running
    # Start browser
    core = BridgeCore(verbose=False)
    if not core.connect():
        print("Failed to connect to DeepSeek", file=sys.stderr)
        logging.error("Failed to connect to DeepSeek")
        sys.exit(1)

    # Create socket server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 0))  # Let OS choose port
    port = server_socket.getsockname()[1]
    server_socket.listen(5)
    print(f"Session server listening on port {port}")
    logging.info(f"Session server listening on port {port}")

    # Write port to file
    with open(PORT_FILE, 'w') as f:
        f.write(str(port))

    print(f"Session server started. PID: {os.getpid()}")
    logging.info(f"Session server started. PID: {os.getpid()}")

    # Handle shutdown signals
    def signal_handler(sig, frame):
        global running
        print("Shutting down...")
        logging.info("Shutdown signal received")
        running = False
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Main loop
    while running:
        try:
            server_socket.settimeout(1.0)
            conn, addr = server_socket.accept()
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            logging.info(f"Accepted connection from {addr}")
            # Handle each client in a new thread
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                logging.error(f"Server error: {e}")
            break

    # Cleanup
    server_socket.close()
    if core:
        core.close()
    # Remove port file
    try:
        PORT_FILE.unlink()
    except:
        pass
    logging.info("Session server stopped.")
    print("Session server stopped.")

if __name__ == "__main__":
    main()