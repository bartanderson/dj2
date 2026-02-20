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
from pathlib import Path

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
        print(f"Received command {cmd_id}: {op}")

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