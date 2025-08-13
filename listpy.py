import os
import argparse

def list_python_files(exclude_dirs=None):
#def list_python_files(exclude_dirs=['.git', '.vscode', 'Lib', '__pycache__', 'Scripts', 'include','dg_orig']):

    if exclude_dirs is None:
        exclude_dirs = []
    
    for root, dirs, files in os.walk(os.getcwd()):
        # Filter out excluded directories (modify in-place to prevent traversal)
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.endswith('.py'):
                print(os.path.join(root, file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='List Python files excluding specified directories')
    parser.add_argument('--exclude', nargs='+', default=[],
                        help='Directories to exclude at any level')
    args = parser.parse_args()
    
    list_python_files(exclude_dirs=args.exclude)