import inspect
from tools import agent_tools
from tools.agent_tools import read_file

print(f"Function location: {inspect.getfile(read_file)}")
print(f"Function signature: {inspect.signature(read_file)}")
print(f"PROJECT_ROOT in agent_tools: {agent_tools.PROJECT_ROOT}")

# Create test file
with open("test_read.txt", "w") as f:
    f.write("Hello, world!")
print("Test file created.")

try:
    content = read_file("test_read.txt")
    print(f"Content: {content} (type: {type(content)})")
    assert content == "Hello, world!"
    print("✅ read_file works")
except Exception as e:
    print(f"❌ read_file failed: {e}")
finally:
    import os
    os.remove("test_read.txt")
    print("Test file cleaned up.")