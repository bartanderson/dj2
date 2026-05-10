#tools/ai_assistant/editing_commands.py
"""
Flexible editing commands - Direct operations only (no backup)
Simplified version without backup functionality
"""

from pathlib import Path
from typing import List, Optional, Dict, Union, Tuple
import ast
import re

class EditingCommands:
    """Direct editing commands with confirmation only (no backup)"""
    
    @staticmethod
    def delete_lines_direct(file_path: str, start_line: int, end_line: int) -> Dict:
        """Delete lines from a file directly"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if start_line < 1 or end_line > len(lines) or start_line > end_line:
                return {
                    'success': False,
                    'error': f'Invalid line range (1-{len(lines)})'
                }
            
            # Delete lines
            del lines[start_line-1:end_line]
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return {
                'success': True,
                'message': f'Deleted lines {start_line}-{end_line} from {file_path}',
                'lines_deleted': end_line - start_line + 1
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def insert_lines_direct(file_path: str, line_number: int, new_lines: List[str]) -> Dict:
        """Insert lines at position directly"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_number < 1 or line_number > len(lines) + 1:
                return {
                    'success': False,
                    'error': f'Invalid line position (1-{len(lines)+1})'
                }
            
            # Ensure new lines end with newline
            formatted_lines = []
            for line in new_lines:
                if not line.endswith('\n'):
                    line += '\n'
                formatted_lines.append(line)
            
            # Insert lines
            lines[line_number-1:line_number-1] = formatted_lines
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return {
                'success': True,
                'message': f'Inserted {len(formatted_lines)} lines at line {line_number} in {file_path}',
                'lines_inserted': len(formatted_lines)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def replace_lines_direct(file_path: str, start_line: int, end_line: int, 
                           new_lines: List[str]) -> Dict:
        """Replace lines with new content directly"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if start_line < 1 or end_line > len(lines) or start_line > end_line:
                return {
                    'success': False,
                    'error': f'Invalid line range (1-{len(lines)})'
                }
            
            # Ensure new lines end with newline
            formatted_lines = []
            for line in new_lines:
                if not line.endswith('\n'):
                    line += '\n'
                formatted_lines.append(line)
            
            # Replace lines
            lines[start_line-1:end_line] = formatted_lines
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return {
                'success': True,
                'message': f'Replaced lines {start_line}-{end_line} in {file_path}',
                'old_lines_replaced': end_line - start_line + 1,
                'new_lines_inserted': len(formatted_lines)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def write_file_direct(file_path: str, content: str) -> Dict:
        """Write or overwrite a file directly"""
        try:
            # Ensure content ends with newline if it has content
            if content and not content.endswith('\n'):
                content += '\n'
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'success': True,
                'message': f'Wrote {len(content)} characters to {file_path}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def replace_in_file_direct(file_path: str, search: str, replace: str) -> Dict:
        """Replace text in file directly"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if search not in content:
                return {
                    'success': False,
                    'error': f"Text '{search}' not found in {file_path}",
                    'occurrences': 0
                }
            
            # Count occurrences
            count = content.count(search)
            
            # Replace text
            new_content = content.replace(search, replace)
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                'success': True,
                'message': f'Replaced {count} occurrence(s) of text in {file_path}',
                'occurrences': count
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def extract_class_direct(source_file: str, class_name: str, 
                           target_file: Optional[str] = None) -> Dict:
        """
        Extract a class to a new file directly
        Returns status dict
        """
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            start_line = None
            end_line = None
            
            # Find the class definition
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    start_line = node.lineno
                    # For end line, we need to find the next node at same indentation
                    # This is a simplified approach
                    break
            
            if not start_line:
                return {
                    'success': False,
                    'error': f"Class {class_name} not found in {source_file}"
                }
            
            # Parse lines to find end of class
            lines = content.splitlines(keepends=True)
            class_line = lines[start_line - 1]
            class_indent = len(class_line) - len(class_line.lstrip())
            
            # Find end of class (next line with equal or less indentation that's not empty)
            end_line = start_line
            for i in range(start_line, len(lines)):
                if i == start_line - 1:  # Skip the class definition line itself
                    continue
                    
                line = lines[i]
                if not line.strip():  # Skip empty lines
                    continue
                    
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= class_indent:
                    # Found something at same or less indentation
                    end_line = i - 1
                    break
            
            # If we didn't find a boundary, use the end of file
            if end_line == start_line:
                end_line = len(lines)
            
            # Create target file name if not provided
            if not target_file:
                target_file = f"{class_name.lower()}.py"
            
            # Extract class content
            class_content = ''.join(lines[start_line-1:end_line])
            
            # Write class to new file
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(class_content)
            
            return {
                'success': True,
                'message': f'Extracted class {class_name} from {source_file} to {target_file}',
                'source_file': source_file,
                'target_file': target_file,
                'start_line': start_line,
                'end_line': end_line,
                'lines_extracted': end_line - start_line + 1
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def extract_lines_direct(source_file: str, start_line: int, end_line: int, 
                           target_file: str) -> Dict:
        """Extract lines to a new file directly"""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if start_line < 1 or end_line > len(lines) or start_line > end_line:
                return {
                    'success': False,
                    'error': f'Invalid line range (1-{len(lines)})'
                }
            
            # Extract lines
            extracted_lines = lines[start_line-1:end_line]
            
            # Write to target file
            with open(target_file, 'w', encoding='utf-8') as f:
                f.writelines(extracted_lines)
            
            return {
                'success': True,
                'message': f'Extracted lines {start_line}-{end_line} from {source_file} to {target_file}',
                'lines_extracted': len(extracted_lines)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def find_class_lines(file_path: str, class_name: str) -> Optional[Tuple[int, int]]:
        """Find start and end lines of a class definition"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            return None
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                start_line = node.lineno
                
                # Get end line - look for next class/function at same indentation
                lines = content.split('\n')
                class_line = lines[start_line - 1]
                class_indent = len(class_line) - len(class_line.lstrip())
                
                end_line = start_line
                for i in range(start_line, len(lines)):
                    if i == start_line - 1:  # Skip the class definition line itself
                        continue
                        
                    line = lines[i]
                    if not line.strip():  # Skip empty lines
                        continue
                        
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= class_indent:
                        # Found something at same or less indentation
                        end_line = i - 1
                        break
                
                # If we didn't find a boundary, use the end of file
                if end_line == start_line:
                    end_line = len(lines)
                    
                return (start_line, end_line)
        
        return None
    
    @staticmethod
    def preview_changes(file_path: str, operation: str, **kwargs) -> str:
        """Preview changes without applying them"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines(keepends=True)
            preview = []
            
            if operation == 'delete':
                start = kwargs.get('start_line', 1)
                end = kwargs.get('end_line', 1)
                if start <= len(lines) and end <= len(lines):
                    preview.append(f"Would delete lines {start}-{end}:")
                    for i in range(start-1, min(end, len(lines))):
                        preview.append(f"  {i+1}: {lines[i].rstrip()}")
                else:
                    preview.append(f"Invalid line range (file has {len(lines)} lines)")
            
            elif operation == 'insert':
                line_num = kwargs.get('line_number', 1)
                new_lines = kwargs.get('new_lines', [])
                preview.append(f"Would insert at line {line_num}:")
                for i, line in enumerate(new_lines):
                    preview.append(f"  [{i+1}] {line}")
            
            elif operation == 'replace':
                start = kwargs.get('start_line', 1)
                end = kwargs.get('end_line', 1)
                new_lines = kwargs.get('new_lines', [])
                preview.append(f"Would replace lines {start}-{end} with:")
                for i, line in enumerate(new_lines):
                    preview.append(f"  [{i+1}] {line}")
            
            return '\n'.join(preview)
            
        except Exception as e:
            return f"Error generating preview: {e}"