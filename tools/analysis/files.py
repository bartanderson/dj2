import os
import sys

directories = sys.argv[1:]  # pass directories as arguments
excluded_dirs = {'__pycache__', 'Lib'}

for root in directories:
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories
        if any(part in excluded_dirs for part in dirpath.split(os.sep)):
            continue
        for f in filenames:
            if f.endswith('.py') and not f.startswith('test'):
                print(os.path.join(dirpath, f))