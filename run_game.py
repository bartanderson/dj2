#!/usr/bin/env python
# coding=utf-8
"""Single script to run the entire Dungeon Journey 2 game"""
import subprocess
import sys
import time
import os
import signal
import threading
import webbrowser

def run_server(script_name, port):
    """Run a Flask server and capture its output"""
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    process = subprocess.Popen(
        [sys.executable, script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env
    )
    
    # Thread to stream output
    def stream_output():
        for line in iter(process.stdout.readline, ''):
            print(f"[{script_name}:{port}] {line.rstrip()}")
    
    threading.Thread(target=stream_output, daemon=True).start()
    return process

def main():
    """Main function to run both game servers"""
    print("=" * 60)
    print("Starting Dungeon Journey 2 - Unified Game System")
    print("=" * 60)
    
    processes = []
    
    try:
        # Start dungeon server (port 5005)
        print("\n1. Starting dungeon server (port 5005)...")
        dungeon_proc = run_server("dungeon_app.py", 5005)
        processes.append(dungeon_proc)
        time.sleep(3)  # Give dungeon server time to start
        
        # Start world server (port 5000)
        print("\n2. Starting world server (port 5000)...")
        world_proc = run_server("world_app.py", 5000)
        processes.append(world_proc)
        time.sleep(3)  # Give world server time to start
        
        print("\n" + "=" * 60)
        print("✅ Both servers started successfully!")
        print("=" * 60)
        print("\nAccess Points:")
        print(f"  • World Interface:   http://localhost:5000")
        print(f"  • Dungeon Direct:    http://localhost:5005")
        print(f"  • Game Engine API:   http://localhost:5000/api/engine/status")
        print(f"  • Dungeon Status:    http://localhost:5000/api/dungeon/status")
        print("\nPress Ctrl+C to stop both servers")
        print("=" * 60)
        
        # Optional: Open browser
        open_browser = input("\nOpen browser to world interface? (y/n): ").lower().strip()
        if open_browser == 'y':
            webbrowser.open("http://localhost:5000")
        
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Shutting down servers...")
        
        # Terminate all processes
        for proc in processes:
            if proc.poll() is None:  # Still running
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