import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from .models import FileArchitecture

class BaseParser:
    def parse(self, path: Path, content: str) -> FileArchitecture:
        raise NotImplementedError

class PythonParser(BaseParser):
    def parse(self, path: Path, content: str) -> FileArchitecture:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._fallback_parse(path, content)
            
        imports = []
        exports = []
        interfaces = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend([f"{module}.{alias.name}" for alias in node.names])
            elif isinstance(node, ast.ClassDef):
                exports.append(node.name)
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                interfaces.append({"type": "class", "name": node.name, "methods": methods[:5]})
            elif isinstance(node, ast.FunctionDef):
                exports.append(node.name)
                interfaces.append({
                    "type": "function", 
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args][:4]  # Limit args
                })
        
        return FileArchitecture(
            path=str(path),
            file_type="python",
            lines_of_code=len(content.splitlines()),
            imports=list(set(imports)),  # Deduplicate
            exports=exports,
            dependencies=[],
            dependents=[],
            purpose_summary=self._extract_docstring(tree),
            complexity_score=self._calc_complexity(tree),
            interfaces=interfaces,
            key_patterns=self._detect_patterns(tree)
        )
    
    def _extract_docstring(self, tree) -> str:
        doc = ast.get_docstring(tree)
        return doc[:200] if doc else ""
    
    def _calc_complexity(self, tree) -> int:
        """Simple cyclomatic complexity approximation"""
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        return complexity
    
    def _detect_patterns(self, tree) -> List[str]:
        patterns = []
        has_classes = any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        has_decorators = any(isinstance(n, ast.FunctionDef) and n.decorator_list for n in ast.walk(tree))
        
        if has_classes:
            patterns.append("oop")
        if has_decorators:
            patterns.append("decorators")
        # Add more pattern detection as needed
        return patterns
    
    def _fallback_parse(self, path: Path, content: str) -> FileArchitecture:
        """Handle syntax errors gracefully"""
        return FileArchitecture(
            path=str(path),
            file_type="python",
            lines_of_code=len(content.splitlines()),
            purpose_summary="[Syntax error - could not parse]"
        )

class JavaScriptParser(BaseParser):
    def parse(self, path: Path, content: str) -> FileArchitecture:
        # Regex-based parsing for JS (no runtime dependency on JS parser)
        imports = re.findall(r'import\s+.*?from\s+["\']([^"\']+)["\']', content)
        imports += re.findall(r'require\(["\']([^"\']+)["\']\)', content)
        
        exports = re.findall(r'export\s+(?:default\s+)?(?:class|function|const|let|var)?\s*(\w+)', content)
        exports += re.findall(r'module\.exports\s*=\s*(\w+)', content)
        
        # Detect functions
        functions = re.findall(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\()', content)
        func_names = [f[0] or f[1] for f in functions if f[0] or f[1]]
        
        interfaces = [{"type": "function", "name": name} for name in func_names[:5]]
        
        return FileArchitecture(
            path=str(path),
            file_type="javascript",
            lines_of_code=len(content.splitlines()),
            imports=list(set(imports)),
            exports=list(set(exports)),
            dependencies=[],
            dependents=[],
            purpose_summary=self._extract_jsdoc(content),
            complexity_score=len(re.findall(r'if|while|for|switch|catch', content)),
            interfaces=interfaces
        )
    
    def _extract_jsdoc(self, content: str) -> str:
        """Extract JSDoc or header comment"""
        jsdoc = re.search(r'/\*\*(.*?)\*/', content, re.DOTALL)
        if jsdoc:
            return jsdoc.group(1)[:200].replace('*', '').strip()
        # Fallback to first line comment
        line_comment = re.search(r'//\s*(.+)', content)
        return line_comment.group(1)[:100] if line_comment else ""

class HTMLParser(BaseParser):
    def parse(self, path: Path, content: str) -> FileArchitecture:
        # Extract script tags, links, templates
        scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', content)
        links = re.findall(r'<link[^>]*href=["\']([^"\']+)["\']', content)
        templates = re.findall(r'<template[^>]*id=["\']([^"\']+)["\']', content)
        
        return FileArchitecture(
            path=str(path),
            file_type="html",
            lines_of_code=len(content.splitlines()),
            imports=scripts + links,
            exports=templates,  # Template IDs as exports
            dependencies=[],
            dependents=[],
            purpose_summary=f"HTML with {len(scripts)} scripts, {len(links)} stylesheets",
            interfaces=[{"type": "template", "name": t} for t in templates[:5]]
        )

class CSSParser(BaseParser):
    def parse(self, path: Path, content: str) -> FileArchitecture:
        # Extract classes, IDs, and imports
        classes = re.findall(r'\.([a-zA-Z_-][\w-]*)\s*[{,]', content)
        ids = re.findall(r'#([a-zA-Z_-][\w-]*)\s*[{,]', content)
        imports = re.findall(r'@import\s+["\']([^"\']+)["\']', content)
        
        return FileArchitecture(
            path=str(path),
            file_type="css",
            lines_of_code=len(content.splitlines()),
            imports=imports,
            exports=list(set(classes + ids)),
            dependencies=[],
            dependents=[],
            purpose_summary=f"CSS with {len(set(classes))} classes, {len(set(ids))} IDs",
            interfaces=[{"type": "class", "name": c} for c in list(set(classes))[:5]]
        )

def get_parser(file_suffix: str) -> Optional[BaseParser]:
    parsers = {
        '.py': PythonParser(),
        '.js': JavaScriptParser(),
        '.html': HTMLParser(),
        '.css': CSSParser(),
        '.jsx': JavaScriptParser(),
        '.ts': JavaScriptParser(),  # TS is close enough for basic analysis
    }
    return parsers.get(file_suffix)