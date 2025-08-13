import ollama
import json

# Simulated tool definitions (same as your real system)
TOOLS_SPEC = [
    {
        "name": "create_door",
        "description": "CREATE a new door at specified position",
        "parameters": {
            "x": "X coordinate (number)",
            "y": "Y coordinate (number)",
            "orientation": "horizontal or vertical",
            "door_type": "arch, normal, locked, trapped, secret, portc"
        }
    },
    {
        "name": "move_party",
        "description": "Move player party in direction",
        "parameters": {
            "direction": "north, south, east, west, northeast, northwest, southeast, southwest",
            "steps": "Number of steps (default=1)"
        }
    }
]

# Full system prompt simulation
SYSTEM_PROMPT = f"""
You are a Dungeon Master assistant. Follow these rules:
1. ALWAYS respond with VALID JSON containing "thoughts", "tool", and "arguments"
2. Use this exact JSON format: 
   {{
        "thoughts": "Brief reasoning",
        "tool": "tool_name",
        "arguments": {{"arg1": value, "arg2": value}}
   }}
3. Only use these tools:
{json.dumps(TOOLS_SPEC, indent=2)}
4. Critical workflows:
   - Doors: Use 'create_door' (NOT 'set_cell_type')
   - Movement: 'move_party direction steps'
   - Coordinates: Always use numbers (e.g., (5,7))
"""

def test_ollama(prompt):
    print(f"\n=== SENDING PROMPT ===\n{'-'*50}")
    print(f"System Prompt:\n{SYSTEM_PROMPT[:500]}... [truncated]")
    print(f"\nUser Command: {prompt}")
    print("-"*50)
    
    try:
        response = ollama.generate(
            model="llama3.1:8b",
            system=SYSTEM_PROMPT,
            prompt=prompt,
            format="json",
            options={"temperature": 0.1}
        )
        
        print("\n=== RAW RESPONSE ===")
        print(response)
        
        if 'response' in response:
            try:
                json_response = json.loads(response['response'])
                print("\n=== PARSED JSON ===")
                print(json.dumps(json_response, indent=2))
                
                # Validate response structure
                required_keys = {"thoughts", "tool", "arguments"}
                if not all(key in json_response for key in required_keys):
                    print("\n❌ ERROR: Missing required keys in response")
                else:
                    print("\n✅ Valid response structure")
                    
            except json.JSONDecodeError:
                print("\n❌ ERROR: Response is not valid JSON")
                print(f"Response content: {response['response']}")
        else:
            print("\n❌ ERROR: No 'response' in Ollama output")
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")

if __name__ == "__main__":
    # Test with different commands
    test_commands = [
        "Create a trapped door at position (5,7) facing vertically",
        "Move the party 3 steps northwest",
        "Add a secret door at location (3,4) on the east wall",
        "Set cell type to corridor at (8,12)"  # Should trigger tool selection error
    ]
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n{'#'*50}")
        print(f"TEST {i}: {cmd}")
        print(f"{'#'*50}")
        test_ollama(cmd)