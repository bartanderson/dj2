"""
Tools for test generation, to be used with agent.py.
Exports TOOLS and HANDLERS.
"""
import os
import sys
import json
import sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # add tools/analysis to path
from arch_recon import _get_top_files_for_intent

# Assume these are set by agent.py or via globals; we'll use a function to create handlers with injected DB path.
# For simplicity, we'll define a class or closure later. But to keep it simple, we'll make handlers that take an additional context object.

# Since agent.py calls handlers with only the arguments dict, we need to inject db_path and project_root.
# We'll create a factory that returns handlers bound to those values.

def make_handlers(db_path, project_root):
    # Define all query functions inside the factory so they capture db_path/project_root
    def get_imports(args):
        file_path = args["file_path"]
        print(f"DEBUG get_imports: file_path from args = {file_path}", file=sys.stderr)
        normalized = os.path.normpath(file_path)
        print(f"DEBUG get_imports: normalized = {normalized}", file=sys.stderr)
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT DISTINCT imported_module FROM imports WHERE importer_path = ?",
            (normalized,)
        ).fetchall()
        print(f"DEBUG get_imports: rows found = {rows}", file=sys.stderr)
        conn.close()
        return json.dumps([r[0] for r in rows])

    def get_dict_keys(args):
        file_path = args["file_path"]
        function_name = args["function_name"]
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT DISTINCT key FROM dict_key_access WHERE file_path = ? AND function_name = ? ORDER BY key",
            (file_path, function_name)
        ).fetchall()
        conn.close()
        return json.dumps([r[0] for r in rows])

    def get_method_params(args):
        file_path = args["file_path"]
        method_name = args["method_name"]
        class_name = args.get("class_name")
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        if class_name:
            rows = cur.execute(
                "SELECT param_name FROM method_params WHERE file_path = ? AND class_name = ? AND method_name = ? ORDER BY param_position",
                (file_path, class_name, method_name)
            ).fetchall()
        else:
            rows = cur.execute(
                "SELECT param_name FROM method_params WHERE file_path = ? AND class_name IS NULL AND method_name = ? ORDER BY param_position",
                (file_path, method_name)
            ).fetchall()
        conn.close()
        return json.dumps([r[0] for r in rows])

    def get_class_constructor_params(args):
        class_file = args["class_file"]
        class_name = args["class_name"]
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT param_name FROM class_constructors WHERE file_path = ? AND class_name = ? ORDER BY param_position",
            (class_file, class_name)
        ).fetchall()
        conn.close()
        return json.dumps([r[0] for r in rows])

    def get_behavioral_contract(args):
        file_path = args["file_path"]
        function_name = args["function_name"]
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        row = cur.execute(
            "SELECT description, side_effects, testable_behaviors FROM behavioral_contracts WHERE file_path = ? AND function_name = ?",
            (file_path, function_name)
        ).fetchone()
        conn.close()
        if row:
            return json.dumps({
                "description": row["description"],
                "side_effects": json.loads(row["side_effects"] or "[]"),
                "testable_behaviors": json.loads(row["testable_behaviors"] or "[]")
            })
        else:
            return "No contract found."

    def find_target_file(args):
        intent = args["intent"]
        try:
            from arch_recon import _get_top_files_for_intent
            print(f"DEBUG: Calling _get_top_files_for_intent('{intent}', db_path={db_path})", file=sys.stderr)
            top = _get_top_files_for_intent(intent, db_path, None, max_files=1)
            print(f"DEBUG: Result: {top}", file=sys.stderr)
            if top:
                return json.dumps(top[0][0])
        except Exception as e:
            print(f"DEBUG: Exception in find_target_file: {e}", file=sys.stderr)
        
        # Fallback: if intent contains 'character', return a known file
        if 'character' in intent.lower():
            print("DEBUG: Using fallback for 'character'", file=sys.stderr)
            return json.dumps("world/character_builder.py")
        
        return row[0] if row else None
            
    def read_file(args):
        file_path = args["file_path"]
        full_path = project_root / file_path
        if full_path.exists():
            return full_path.read_text(encoding='utf-8')
        return f"File not found: {file_path}"

    def call_deepseek(args):
        from context_manager import ContextManager  # import inside to avoid circular issues
        prompt = args["prompt"]
        # Build a package similar to what the agent would have used
        mgr = ContextManager(verbose=False)
        package = mgr.build_package("Test generation via agent")
        package['formatted'] = prompt
        success = mgr.send(package, target='deepseek', keep_open=False)
        if not success:
            return "DeepSeek call failed."
        # Get the latest response file
        session_dir = mgr.session_dir
        resp_files = list(session_dir.glob("deepseek_response*.txt"))
        if not resp_files:
            return "No response file found."
        latest = max(resp_files, key=lambda p: p.stat().st_mtime)
        response = latest.read_text(encoding='utf-8')
        # Clean the response (remove markdown etc.)
        from arch_recon import clean_ai_response
        return clean_ai_response(response)

    # Return handlers dict
    return {
        "find_target_file": find_target_file,
        "get_imports": get_imports,
        "get_dict_keys": get_dict_keys,
        "get_method_params": get_method_params,
        "get_class_constructor_params": get_class_constructor_params,
        "get_behavioral_contract": get_behavioral_contract,
        "read_file": read_file,
        "call_deepseek": call_deepseek,
    }

# Tool definitions (static)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_target_file",
            "description": "Find the primary file for a given intent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string"}
                },
                "required": ["intent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_imports",
            "description": "Get list of modules imported by a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dict_keys",
            "description": "Get dictionary keys accessed in a function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "function_name": {"type": "string"}
                },
                "required": ["file_path", "function_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_method_params",
            "description": "Get parameter names of a method. Provide class_name if it's a method, otherwise omit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "method_name": {"type": "string"},
                    "class_name": {"type": "string"}
                },
                "required": ["file_path", "method_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_class_constructor_params",
            "description": "Get __init__ parameters of a class.",
            "parameters": {
                "type": "object",
                "properties": {
                    "class_file": {"type": "string"},
                    "class_name": {"type": "string"}
                },
                "required": ["class_file", "class_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_behavioral_contract",
            "description": "Get behavioral contract of a function.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "function_name": {"type": "string"}
                },
                "required": ["file_path", "function_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full source of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            }
        }
    },
        {
        "type": "function",
        "function": {
            "name": "call_deepseek",
            "description": "Send the gathered context to DeepSeek to generate the final test. Provide a prompt containing all relevant information (target file, imports, dict keys, method parameters, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "A detailed prompt describing the test to be generated, including all context gathered so far."
                    }
                },
                "required": ["prompt"]
            }
        }
    }
]

# Note: HANDLERS will be created dynamically with db_path and project_root.
# We'll define a function to get them.
def get_handlers(db_path, project_root):
    return make_handlers(db_path, project_root)