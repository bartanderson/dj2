#tools/utils/format_ai_markdown.py
"""
format_ai_markdown.py - Fix AI's broken markdown output
Simplified version
"""

import re
import sys
from typing import List

class AIMarkdownFormatter:
    """Fixes common AI markdown issues in one pass"""
    
    def __init__(self):
        self.rules = [
            self._fix_unclosed_code_blocks,
            self._normalize_headers,
            self._normalize_lists,
            self._fix_emphasis,
            self._ensure_blank_lines,
            self._remove_trailing_spaces,
        ]
    
    def format(self, text: str) -> str:
        """Apply all formatting rules"""
        for rule in self.rules:
            text = rule(text)
        return text
    
    def _fix_unclosed_code_blocks(self, text: str) -> str:
        """Ensure all code blocks are properly closed"""
        lines = text.split('\n')
        in_code_block = False
        result = []
        
        for line in lines:
            stripped = line.strip()
            
            # Check for code block start/end
            if stripped.startswith('```'):
                in_code_block = not in_code_block
            
            result.append(line)
        
        # If we're still in a code block at the end, close it
        if in_code_block:
            result.append('```')
        
        return '\n'.join(result)
    
    def _normalize_headers(self, text: str) -> str:
        """Fix header formatting"""
        # Remove bold/italic from headers: ###**text** -> ### text
        text = re.sub(r'(#{1,6})\s*[\*\*_]+(.*?)[\*\*_]+\s*$', r'\1 \2', text, flags=re.MULTILINE)
        
        # Ensure exactly one space after #
        text = re.sub(r'(#{1,6})\s+', r'\1 ', text)
        
        return text
    
    def _normalize_lists(self, text: str) -> str:
        """Normalize list markers to -"""
        lines = text.split('\n')
        result = []
        
        for line in lines:
            # Match list items (starting with *, -, •, or numbers)
            match = re.match(r'^(\s*)(?:[\*\•\-]|\d+\.)\s+(.*)$', line)
            if match:
                indent = match.group(1)
                content = match.group(2)
                # Convert to - with proper indentation
                line = f"{indent}- {content}"
            
            result.append(line)
        
        return '\n'.join(result)
    
    def _fix_emphasis(self, text: str) -> str:
        """Normalize bold/italic formatting"""
        # Convert __bold__ to **bold**
        text = re.sub(r'__(.+?)__', r'**\1**', text)
        
        # Convert _italic_ to *italic*
        text = re.sub(r'\b_(.+?)_\b', r'*\1*', text)
        
        return text
    
    def _ensure_blank_lines(self, text: str) -> str:
        """Ensure proper spacing around headers and code blocks"""
        lines = text.split('\n')
        result = []
        
        for i, line in enumerate(lines):
            result.append(line)
            
            # Add blank line after headers (unless at end or next line is blank)
            if re.match(r'^#{1,6} .+$', line.strip()):
                if i + 1 < len(lines) and lines[i + 1].strip():
                    result.append('')
        
        return '\n'.join(result)
    
    def _remove_trailing_spaces(self, text: str) -> str:
        """Remove trailing whitespace from lines"""
        lines = text.split('\n')
        return '\n'.join(line.rstrip() for line in lines)

def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Format AI markdown output')
    parser.add_argument('input', nargs='?', help='Input file (or stdin)')
    parser.add_argument('-o', '--output', help='Output file (or stdout)')
    parser.add_argument('--inplace', action='store_true', help='Format file in place')
    
    args = parser.parse_args()
    
    # Read input
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    
    # Format
    formatter = AIMarkdownFormatter()
    formatted = formatter.format(text)
    
    # Write output
    if args.inplace and args.input:
        with open(args.input, 'w', encoding='utf-8') as f:
            f.write(formatted)
        print(f"Formatted {args.input}")
    elif args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(formatted)
    else:
        sys.stdout.write(formatted)

if __name__ == '__main__':
    main()