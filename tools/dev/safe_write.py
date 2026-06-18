#!/usr/bin/env python3
"""
safe_write.py - atomic, self-verifying file write for this repo.

Why this exists: Edit/Write tool calls against this repo have a documented
history of silent truncation (see tools/analysis/docs/HISTORY.md) - content
that looks correct in the tool's own echo/Read-back was never actually fully
written to disk. The previously-documented fix was: write via a bash heredoc,
then run a separate `diff` to confirm. This script folds that into one call:
it writes through a temp file + atomic rename (so a crash/truncation mid-write
can never leave a half-written file at the real path), then immediately reads
the result back and byte-compares it against what was sent in, all in a single
process. No content ever touches the Edit/Write file-tool path.

Usage:
    python3 tools/dev/safe_write.py <target_path> << 'EOF'
    <exact file content>
    EOF

Reads the new file content from stdin as raw bytes (no text-mode/encoding
translation), so explicitly write your heredoc content as UTF-8 text and it
will land byte-for-byte.

Exit code 0 + "OK" line on confirmed match. Exit code 1 + "MISMATCH" line
(with the first differing byte offset) if the post-write read-back does not
match what was sent in - in that case, do not trust the file; re-run.
"""
import sys
import os
import hashlib
import tempfile


def main():
    if len(sys.argv) != 2:
        print("usage: safe_write.py <target_path>  (content via stdin)", file=sys.stderr)
        return 2

    target_path = sys.argv[1]
    target_dir = os.path.dirname(os.path.abspath(target_path)) or "."
    content = sys.stdin.buffer.read()

    if not os.path.isdir(target_dir):
        print(f"ERROR: directory does not exist: {target_dir}", file=sys.stderr)
        return 2

    # Write to a temp file in the same directory (so the final os.replace is
    # an atomic rename on the same filesystem), then fsync before rename so
    # the bytes are actually flushed, not just buffered.
    fd, tmp_path = tempfile.mkstemp(dir=target_dir, prefix=os.path.basename(target_path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    # Read back from the real path (not the in-memory content) and compare.
    with open(target_path, "rb") as f:
        on_disk = f.read()

    if on_disk == content:
        print(f"OK {target_path} ({len(content)} bytes, sha256={hashlib.sha256(content).hexdigest()[:12]})")
        return 0
    else:
        first_diff = next((i for i, (a, b) in enumerate(zip(content, on_disk)) if a != b), min(len(content), len(on_disk)))
        print(f"MISMATCH {target_path}: sent {len(content)} bytes, on-disk {len(on_disk)} bytes, "
              f"first differing byte at offset {first_diff}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
