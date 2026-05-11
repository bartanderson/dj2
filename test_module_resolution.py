from tools.analysis.graph.module_resolution import (
    normalize_file_path,
    module_name_from_file_path,
    file_path_from_module_name,
)

PROJECT_ROOT = r"C:\Users\bartl\dev\dj2"

TEST_FILE = (
    r"C:\Users\bartl\dev\dj2"
    r"\tools\analysis\query\query_file_analysis.py"
)

print("\nNORMALIZED PATH:")
print(normalize_file_path(TEST_FILE))

print("\nMODULE NAME:")
module_name = module_name_from_file_path(
    TEST_FILE,
    PROJECT_ROOT,
)
print(module_name)

print("\nRESOLVED FILE:")
resolved = file_path_from_module_name(
    module_name,
    PROJECT_ROOT,
)
print(resolved)