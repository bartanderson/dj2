#!/usr/bin/env python
# coding=utf-8
"""Single script to run the entire Dungeon Journey 2 game"""
import subprocess
import sys
import time
import os
import threading
import requests

# --- LLM Configuration ---
LLAMA_SERVER_EXE = r"C:\Users\bartl\models\llama-server\llama-server.exe"
LLAMA_MODEL_PATH = r"C:\Users\bartl\models\gguf\Qwen_Qwen3-8B-Q4_K_M.gguf"
LLAMA_PORT = 8080  # Matches what the game expects

def run_server(script_name, port):
    """Run a Flask server and capture its output, handling encoding errors."""
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    process = subprocess.Popen(
        [sys.executable, script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env
    )
    
    def stream_output():
        for line in iter(process.stdout.readline, b''):
            try:
                decoded = line.decode('utf-8', errors='replace').rstrip()
            except:
                decoded = line.decode(sys.getdefaultencoding(), errors='replace').rstrip()
            print(f"[{script_name}:{port}] {decoded}")
    
    threading.Thread(target=stream_output, daemon=True).start()
    return process

def start_llama_server():
    """Start llama-server and wait for it to be healthy."""
    if not os.path.exists(LLAMA_SERVER_EXE) or not os.path.exists(LLAMA_MODEL_PATH):
        print("⚠️ LLM executable or model not found at configured paths. Skipping LLM startup.")
        return None

    print(f"\n0. Starting llama-server on port {LLAMA_PORT}...")
    
    # Using the exact flags from your .bat file, but port 8080 instead of 8081
    cmd = [
        LLAMA_SERVER_EXE,
        "-m", LLAMA_MODEL_PATH,
        "--port", str(LLAMA_PORT),
        "--host", "127.0.0.1",
        "--ctx-size", "4096",
        "-ngl", "99"
    ]
    
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        errors='replace'
    )
    
    def stream_output():
        for line in iter(process.stdout.readline, ''):
            print(f"[llama-server:{LLAMA_PORT}] {line.rstrip()}")
            
    threading.Thread(target=stream_output, daemon=True).start()

    # Poll the /health endpoint until it's ready
    print("Waiting for LLM to load into memory (this may take a few seconds)...")
    for i in range(45):  # up to 45 seconds
        try:
            resp = requests.get(f"http://127.0.0.1:{LLAMA_PORT}/health", timeout=1)
            if resp.status_code == 200:
                print("✅ llama-server is ready!")
                return process
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        
    print("⚠️ LLM did not report healthy in time. Proceeding anyway...")
    return process

def main():
    print("=" * 60)
    print("Starting Dungeon Journey 2 - Unified Game System")
    print("=" * 60)
    
    processes = []
    
    try:
        # 0. Start Llama Server
        llm_proc = start_llama_server()
        if llm_proc:
            processes.append(llm_proc)

        # 1. Start dungeon server (port 5005)
        print("\n1. Starting dungeon server (port 5005)...")
        dungeon_proc = run_server("dungeon_app.py", 5005)
        processes.append(dungeon_proc)
        time.sleep(3)
        
        # 2. Start world server (port 5000)
        print("\n2. Starting world server (port 5000)...")
        world_proc = run_server("world_app.py", 5000)
        processes.append(world_proc)
        
        print("\n" + "=" * 60)
        print("✅ All systems started successfully!")
        print("=" * 60)
        print("\nAccess Points (clickable in most terminals):")
        print(f"  • World Interface:   http://localhost:5000")
        print(f"  • Dungeon Direct:    http://localhost:5005")
        print(f"  • Game Engine API:   http://localhost:5000/api/engine/status")
        print(f"  • Dungeon Status:    http://localhost:5000/api/dungeon/status")
        print(f"  • LLM API:           http://localhost:{LLAMA_PORT}/health")
        print("\nPress Ctrl+C to stop all servers")
        print("=" * 60)
        
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Shutting down servers...")
        # Reverse order to kill Flask apps before the LLM
        for proc in reversed(processes):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("All servers stopped.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()