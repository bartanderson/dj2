from tools.agent_tools import deepseek_consult

print("Testing deepseek_consult with simple prompt (no file)...")
result = deepseek_consult(prompt="Say hello")
print("Result:", result)

print("\nTesting deepseek_consult with a file...")
# Create a temporary file
with open("test.txt", "w") as f:
    f.write("This is a test file content.")
result = deepseek_consult(prompt="Summarize this file", file="test.txt")
print("Result:", result)