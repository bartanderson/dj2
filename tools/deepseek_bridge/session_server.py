#!/usr/bin/env python3
"""
Persistent DeepSeek session server (socket version).
Listens on a local TCP port, accepts JSON commands, and returns JSON responses.
Browser stays open between commands.
"""
import re
import sys
import json
import base64
import socket
import threading
import time
import os
import signal
from pathlib import Path
import subprocess
from tools.nativeclaw.nativeclaw import Session, PROJECT_ROOT  # ensure PROJECT_ROOT is defined or passed

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.deepseek_bridge.bridge_lib import consult
from tools.bridge.unified_core import BridgeCore

# Session directory
SESSION_DIR = PROJECT_ROOT / "ai_context" / "session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
PORT_FILE = SESSION_DIR / "port.txt"

# Global driver and running flag
core = None
running = True

def maybe_decode_base64(content):
    """If content is valid base64, decode and return as utf-8 string; otherwise return as is."""
    try:
        # Check if it looks like base64 (only allowed chars, length multiple of 4)
        if re.match(r'^[A-Za-z0-9+/=]+$', content) and len(content) % 4 == 0:
            decoded = base64.b64decode(content).decode('utf-8')
            return decoded
    except:
        pass
    return content

def handle_client(conn, addr):
    """Handle one client connection: read command, execute, send response."""
    global core
    print(f"Connection from {addr}")
    try:
        data = conn.recv(8192)
        if not data:
            return
        cmd = json.loads(data.decode('utf-8'))
        cmd_id = cmd.get('id', 'unknown')
        op = cmd.get('operation')
        print(f"Received command: {cmd}, Cmd_id: {cmd_id}: operation: {op}")

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
                        # Use the already open browser
                        resp_text = consult(core.driver, path, prompt)
                        response = {"status": "success", "data": resp_text}
                    except Exception as e:
                        response = {"status": "error", "error": str(e)}
        elif op == 'stop':
            response = {"status": "success", "data": "Shutting down"}
            # Send response before stopping
            conn.sendall((json.dumps(response) + '\n').encode('utf-8'))
            conn.close()
            # Signal main loop to exit
            global running
            running = False
            return
        elif op == 'run_nativeclaw':
            subcmd = cmd.get('subcommand')
            args_list = cmd.get('args', [])
            if not subcmd:
                response = {"status": "error", "error": "Missing 'subcommand'"}
            else:
                try:
                    nativeclaw_script = PROJECT_ROOT / "tools" / "nativeclaw" / "nativeclaw.py"
                    cmd_line = [sys.executable, str(nativeclaw_script), subcmd] + args_list
                    result = subprocess.run(
                        cmd_line,
                        cwd=PROJECT_ROOT,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        timeout=120
                    )
                    response = {
                        "status": "success",
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }
                except subprocess.TimeoutExpired:
                    response = {"status": "error", "error": "Timeout"}
                except Exception as e:
                    response = {"status": "error", "error": str(e)}

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
                        content = path.read_text(encoding='utf-8')
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
                    session = Session("auto_apply", PROJECT_ROOT)
                    branch = session.start()
                    for change in plan:  # assuming plan is a list
                        file_path = PROJECT_ROOT / change['file']
                        op_type = change['operation']
                        if 'content' in change:
                            # Decode if base64
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
                    response = {"status": "success", "review_path": str(archive_dir)}
                except Exception as e:
                    response = {"status": "error", "error": str(e)}
        else:
            response = {"status": "error", "error": f"Unknown operation: {op}"}

        # Send response
        conn.sendall((json.dumps(response) + '\n').encode('utf-8'))
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        conn.close()

def main():
    global core, running
    # Start browser
    core = BridgeCore(verbose=False)
    if not core.connect():
        print("Failed to connect to DeepSeek", file=sys.stderr)
        sys.exit(1)

    # Create socket server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 0))  # Let OS choose port
    port = server_socket.getsockname()[1]
    server_socket.listen(5)
    print(f"Session server listening on port {port}")

    # Write port to file
    with open(PORT_FILE, 'w') as f:
        f.write(str(port))

    print(f"Session server started. PID: {os.getpid()}")

    # Handle shutdown signals
    def signal_handler(sig, frame):
        global running
        print("Shutting down...")
        running = False
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Main loop: accept connections and spawn threads
    while running:
        try:
            server_socket.settimeout(1.0)
            conn, addr = server_socket.accept()
            # Handle each client in a new thread (so server can still accept others)
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
        except socket.timeout:
            continue
        except Exception as e:
            if running:
                print(f"Server error: {e}")
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
    print("Session server stopped.")

if __name__ == "__main__":
    main()