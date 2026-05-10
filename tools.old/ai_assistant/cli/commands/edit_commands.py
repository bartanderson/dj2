"""
Edit-related commands for AI Assistant CLI
These commands directly modify files - use with caution!
"""
import os
import json
import re
from pathlib import Path

# Import registry
from . import register_command

def delete_command(args):
    """Delete lines from file directly"""
    try:
        if args.dry_run:
            print(f"DRY RUN: Would delete lines {args.start}-{args.end} from {args.file}")
            # Show what would be deleted
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if args.start <= len(lines) and args.end <= len(lines):
                    print("Lines that would be deleted:")
                    for i in range(args.start-1, min(args.end, len(lines))):
                        print(f"  {i+1}: {lines[i].rstrip()}")
                else:
                    print(f"Warning: Line numbers out of range (file has {len(lines)} lines)")
            except Exception as e:
                print(f"Error reading file: {e}")
            return 0
        
        # Ask for confirmation
        print(f"Delete lines {args.start}-{args.end} from {args.file}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Perform deletion
        with open(args.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if args.start < 1 or args.end > len(lines) or args.start > args.end:
            print(f"Error: Invalid line range (1-{len(lines)})")
            return 1
        
        # Delete lines
        del lines[args.start-1:args.end]
        
        # Write back
        with open(args.file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"[OK] Deleted lines {args.start}-{args.end} from {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def insert_command(args):
    """Insert lines into file directly"""
    try:
        # Handle newlines in text
        text_lines = args.text.replace('\\n', '\n').split('\n')
        
        if args.dry_run:
            print(f"DRY RUN: Would insert {len(text_lines)} lines at line {args.line} in {args.file}")
            print("Content that would be inserted:")
            for i, line in enumerate(text_lines):
                print(f"  [{i+1}] {line}")
            return 0
        
        # Ask for confirmation
        print(f"Insert {len(text_lines)} lines at line {args.line} in {args.file}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Read file
        with open(args.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if args.line < 1 or args.line > len(lines) + 1:
            print(f"Error: Invalid line position (1-{len(lines)+1})")
            return 1
        
        # Prepare new lines with newline characters
        new_lines = []
        for line in text_lines:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
        
        # Insert lines
        lines[args.line-1:args.line-1] = new_lines
        
        # Write back
        with open(args.file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"[OK] Inserted {len(new_lines)} lines at line {args.line} in {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def replace_command(args):
    """Replace lines in file directly"""
    try:
        # Handle newlines in text
        text_lines = args.text.replace('\\n', '\n').split('\n')
        
        if args.dry_run:
            print(f"DRY RUN: Would replace lines {args.start}-{args.end} in {args.file}")
            print(f"  With {len(text_lines)} lines of new content")
            print("New content:")
            for i, line in enumerate(text_lines):
                print(f"  [{i+1}] {line}")
            return 0
        
        # Ask for confirmation
        print(f"Replace lines {args.start}-{args.end} in {args.file} with {len(text_lines)} new lines?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Read file
        with open(args.file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if args.start < 1 or args.end > len(lines) or args.start > args.end:
            print(f"Error: Invalid line range (1-{len(lines)})")
            return 1
        
        # Prepare new lines with newline characters
        new_lines = []
        for line in text_lines:
            if not line.endswith('\n'):
                line += '\n'
            new_lines.append(line)
        
        # Replace lines
        lines[args.start-1:args.end] = new_lines
        
        # Write back
        with open(args.file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"[OK] Replaced lines {args.start}-{args.end} in {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def write_command(args):
    """Write or overwrite file directly"""
    try:
        # Handle newlines in text
        content = args.text.replace('\\n', '\n')
        
        if args.dry_run:
            print(f"DRY RUN: Would write {len(content)} characters to {args.file}")
            print("First 500 characters of content:")
            print(content[:500])
            if len(content) > 500:
                print("...")
            return 0
        
        # Check if file exists
        if os.path.exists(args.file):
            print(f"[WARN]  File {args.file} already exists. Overwrite?")
            response = input("Confirm (y/n): ").lower().strip()
        else:
            print(f"Create new file {args.file}?")
            response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Ensure content ends with newline if it has content
        if content and not content.endswith('\n'):
            content += '\n'
        
        # Write file
        with open(args.file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        action = "Overwrote" if os.path.exists(args.file) else "Created"
        print(f"[OK] {action} file {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def replace_text_command(args):
    """Replace text in file directly"""
    try:
        if args.dry_run:
            print(f"DRY RUN: Would replace '{args.search}' with '{args.replace}' in {args.file}")
            # Count occurrences
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    content = f.read()
                count = content.count(args.search)
                print(f"  Found {count} occurrence(s) of '{args.search}'")
                if count > 0:
                    # Show context
                    idx = content.find(args.search)
                    if idx >= 0:
                        start = max(0, idx - 50)
                        end = min(len(content), idx + len(args.search) + 50)
                        context = content[start:end].replace('\n', ' ')
                        print(f"  First occurrence context: ...{context}...")
            except Exception as e:
                print(f"  Error reading file: {e}")
            return 0
        
        # Ask for confirmation
        print(f"Replace all occurrences of '{args.search}' with '{args.replace}' in {args.file}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Read file
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if args.search not in content:
            print(f"[WARN]  Text '{args.search}' not found in {args.file}")
            return 0
        
        # Replace text
        new_content = content.replace(args.search, args.replace)
        
        # Write back
        with open(args.file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        count = content.count(args.search)
        print(f"[OK] Replaced {count} occurrence(s) of '{args.search}' in {args.file}")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def extract_class_command(args):
    """Extract class to new file directly"""
    try:
        if args.dry_run:
            print(f"DRY RUN: Would extract class {args.class_name} from {args.source}")
            if args.target:
                print(f"  Target file: {args.target}")
            return 0
        
        # Ask for confirmation
        action = f"Extract class {args.class_name} from {args.source}"
        if args.target:
            action += f" to {args.target}"
        print(f"{action}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Use EditingCommands to perform extraction
        result = extract_class_direct(
            source_file=args.source,
            class_name=args.class_name,
            target_file=args.target
        )
        
        if result.get('success'):
            print(f"[OK] {result['message']}")
            return 0
        else:
            print(f"[ERROR] {result.get('error', 'Extraction failed')}")
            return 1
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def extract_class_direct(source_file: str, class_name: str, target_file: str = None):
    """Extract a class to a new file - implementation"""
    try:
        from ...editing_commands import EditingCommands
        
        result = EditingCommands.extract_class_direct(
            source_file=source_file,
            class_name=class_name,
            target_file=target_file
        )
        
        return result
        
    except ImportError:
        # Fallback implementation
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find class definition
            class_start = -1
            class_end = -1
            indent_level = 0
            
            for i, line in enumerate(lines):
                # Look for class definition
                if class_start == -1 and f"class {class_name}" in line:
                    class_start = i
                    # Get indentation of class definition
                    indent_level = len(line) - len(line.lstrip())
                    continue
                
                # Find end of class (next line at same or less indentation that's not empty/comment)
                if class_start != -1 and class_end == -1 and i > class_start:
                    if line.strip() and not line.strip().startswith('#'):
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent <= indent_level:
                            class_end = i - 1
                            break
            
            # If we reached end of file
            if class_start != -1 and class_end == -1:
                class_end = len(lines) - 1
            
            if class_start == -1:
                return {'success': False, 'error': f'Class {class_name} not found in {source_file}'}
            
            # Extract class lines
            class_lines = lines[class_start:class_end+1]
            
            # Determine target filename
            if not target_file:
                target_file = f"{class_name.lower()}.py"
            
            # Write to target
            with open(target_file, 'w', encoding='utf-8') as f:
                f.writelines(class_lines)
            
            # Remove from source
            del lines[class_start:class_end+1]
            with open(source_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return {
                'success': True,
                'message': f'Extracted class {class_name} to {target_file}',
                'source_file': source_file,
                'target_file': target_file,
                'lines_extracted': len(class_lines)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

def extract_lines_command(args):
    """Extract lines to new file directly"""
    try:
        if args.dry_run:
            print(f"DRY RUN: Would extract lines {args.start}-{args.end} from {args.source} to {args.target}")
            return 0
        
        # Ask for confirmation
        print(f"Extract lines {args.start}-{args.end} from {args.source} to {args.target}?")
        response = input("Confirm (y/n): ").lower().strip()
        
        if response != 'y':
            print("Cancelled")
            return 0
        
        # Use EditingCommands to perform extraction
        result = extract_lines_direct(
            source_file=args.source,
            start_line=args.start,
            end_line=args.end,
            target_file=args.target
        )
        
        if result.get('success'):
            print(f"[OK] {result['message']}")
            return 0
        else:
            print(f"[ERROR] {result.get('error', 'Extraction failed')}")
            return 1
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

def extract_lines_direct(source_file: str, start_line: int, end_line: int, target_file: str):
    """Extract lines to a new file - implementation"""
    try:
        from ...editing_commands import EditingCommands
        
        result = EditingCommands.extract_lines_direct(
            source_file=source_file,
            start_line=start_line,
            end_line=end_line,
            target_file=target_file
        )
        
        return result
        
    except ImportError:
        # Fallback implementation
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if start_line < 1 or end_line > len(lines) or start_line > end_line:
                return {'success': False, 'error': f'Invalid line range (1-{len(lines)})'}
            
            # Extract lines (adjusting for 1-indexed input)
            extracted_lines = lines[start_line-1:end_line]
            
            # Write to target
            with open(target_file, 'w', encoding='utf-8') as f:
                f.writelines(extracted_lines)
            
            # Remove from source
            del lines[start_line-1:end_line]
            with open(source_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return {
                'success': True,
                'message': f'Extracted lines {start_line}-{end_line} from {source_file} to {target_file}',
                'lines_extracted': len(extracted_lines)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

def extract_command(args):
    """Extract specific components for refactoring analysis"""
    try:
        from ..indexer import CodebaseIndexer
    except ImportError:
        from tools.ai_assistant.cli.indexer import CodebaseIndexer
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    
    component = args.component
    print(f"\nExtracting analysis for: {component}")
    print("=" * 80)
    
    # Search for component
    results = indexer.search(component, limit=20)
    
    # We need to get full documents to check for class definitions
    definition_files = []
    usage_files = []
    
    # Open index searcher to access full documents
    from whoosh.qparser import QueryParser
    if not indexer.index:
        from whoosh import index as idx
        indexer.index = idx.open_dir(str(args.index_dir))
    
    with indexer.index.searcher() as searcher:
        for result in results:
            path = result['path']
            # Get the full document from the index
            doc = searcher.document(path=path)
            if doc:
                content = doc.get('content', '')
                
                # Use regex to find class definition (more robust)
                import re
                regex_pattern = re.compile(r'class\s+' + re.escape(component) + r'\s*[:\(]')
                is_definition = bool(regex_pattern.search(content))
                
                if is_definition:
                    definition_files.append((path, result))
                    print(f"  [] Definition found in: {path}")
                    
                    if args.verbose:
                        # Show the class definition context
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if regex_pattern.search(line):
                                start = max(0, i - 2)
                                end = min(len(lines), i + 5)
                                print("    " + "\n    ".join(lines[start:end]))
                                break
                elif component in content:
                    usage_files.append((path, result))
    
    print(f"\nSummary:")
    print(f"  Definition files: {len(definition_files)}")
    print(f"  Usage files: {len(usage_files)}")
    if not args.output:
        print(f"  Tip: Use --output file.json to save full analysis")
    
    if definition_files:
        print(f"\nDefinition files:")
        for path, _ in definition_files:
            print(f"    - {path}")

    if usage_files:
        print(f"\nUsage files (first 10 of {len(usage_files)}):")
        for path, _ in usage_files[:10]:
            print(f"    - {path}")
        if len(usage_files) > 10:
            print(f"    ... and {len(usage_files) - 10} more")
    
    # Save to file if requested
    if args.output:
        extraction_data = {
            'component': component,
            'definition_files': [p for p, _ in definition_files],
            'usage_files': [p for p, _ in usage_files],
            'total_references': len(results)
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(extraction_data, f, indent=2)
        
        print(f"\n[] Extraction data saved to: {args.output}")
    
    return 0

def find_class_command(args):
    """Find class definition lines"""
    try:
        from ...editing_commands import EditingCommands
        
        result = EditingCommands.find_class_lines(args.file, args.class_name)
        
        if result:
            start, end = result
            print(f"Class '{args.class_name}' found in {args.file}:")
            print(f"  Start line: {start}")
            print(f"  End line: {end}")
            print(f"  Total lines: {end - start + 1}")
            
            # Show snippet
            with open(args.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                start_idx = max(0, start - 3)
                end_idx = min(len(lines), start + 7)
                print(f"\nContext (lines {start_idx+1}-{end_idx}):")
                for i in range(start_idx, end_idx):
                    print(f"{i+1:4}: {lines[i].rstrip()}")
        else:
            print(f"Class '{args.class_name}' not found in {args.file}")
        
        return 0
        
    except ImportError:
        # Fallback implementation
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start = -1
            end = -1
            indent_level = 0
            
            for i, line in enumerate(lines):
                # Look for class definition
                if start == -1 and f"class {args.class_name}" in line:
                    start = i + 1  # Convert to 1-indexed
                    # Get indentation of class definition
                    indent_level = len(line) - len(line.lstrip())
                    continue
                
                # Find end of class
                if start != -1 and end == -1 and i > (start - 1):
                    if line.strip():
                        current_indent = len(line) - len(line.lstrip())
                        if current_indent <= indent_level:
                            end = i  # Current line is outside class
                            break
            
            # If we reached end of file
            if start != -1 and end == -1:
                end = len(lines)
            
            if start != -1:
                print(f"Class '{args.class_name}' found in {args.file}:")
                print(f"  Start line: {start}")
                print(f"  End line: {end}")
                print(f"  Total lines: {end - start + 1}")
                
                # Show snippet
                start_idx = max(0, start - 4)
                end_idx = min(len(lines), start + 6)
                print(f"\nContext (lines {start_idx+1}-{end_idx}):")
                for i in range(start_idx, end_idx):
                    print(f"{i+1:4}: {lines[i].rstrip()}")
            else:
                print(f"Class '{args.class_name}' not found in {args.file}")
            
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1

# Register all edit commands
register_command('delete', delete_command, "Delete lines from file (direct)")
register_command('insert', insert_command, "Insert lines into file (direct)")
register_command('replace', replace_command, "Replace lines in file (direct)")
register_command('write', write_command, "Write or overwrite file (direct)")
register_command('replace-text', replace_text_command, "Replace text in file (direct)")
register_command('extract-class', extract_class_command, "Extract class to new file (direct)")
register_command('extract-lines', extract_lines_command, "Extract lines to new file (direct)")
register_command('extract', extract_command, "Extract component for refactoring analysis")
register_command('find-class', find_class_command, "Find class definition lines")