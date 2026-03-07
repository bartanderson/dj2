#!/usr/bin/env python
# coding=utf-8
"""Single script to run the entire Dungeon Journey 2 game"""
import subprocess
import sys
import time
import os
import threading
import requests

def run_server(script_name, port):
    """Run a Flask server and capture its output, handling encoding errors."""
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    # Use binary mode (no text=True) to avoid automatic decoding
    process = subprocess.Popen(
        [sys.executable, script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env
    )
    
    def stream_output():
        """Read output line by line, decoding with fallback."""
        for line in iter(process.stdout.readline, b''):
            # Try UTF-8 first, fall back to system encoding with replacement
            try:
                decoded = line.decode('utf-8', errors='replace').rstrip()
            except:
                decoded = line.decode(sys.getdefaultencoding(), errors='replace').rstrip()
            print(f"[{script_name}:{port}] {decoded}")
    
    threading.Thread(target=stream_output, daemon=True).start()
    return process

def main():
    print("=" * 60)
    print("Starting Dungeon Journey 2 - Unified Game System")
    print("=" * 60)
    
    processes = []
    
    try:
        # Start dungeon server (port 5005)
        print("\n1. Starting dungeon server (port 5005)...")
        dungeon_proc = run_server("dungeon_app.py", 5005)
        processes.append(dungeon_proc)
        time.sleep(3)
        
        # Start world server (port 5000)
        print("\n2. Starting world server (port 5000)...")
        world_proc = run_server("world_app.py", 5000)
        processes.append(world_proc)
        
        print("\n" + "=" * 60)
        print("✅ Both servers started successfully!")
        print("=" * 60)
        print("\nAccess Points (clickable in most terminals):")
        print(f"  • World Interface:   http://localhost:5000")
        print(f"  • Dungeon Direct:    http://localhost:5005")
        print(f"  • Game Engine API:   http://localhost:5000/api/engine/status")
        print(f"  • Dungeon Status:    http://localhost:5000/api/dungeon/status")
        print("\nPress Ctrl+C to stop both servers")
        print("=" * 60)
        
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Shutting down servers...")
        for proc in processes:
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