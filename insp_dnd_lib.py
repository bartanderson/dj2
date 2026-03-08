import pkgutil
import importlib
import dnd_character

def list_modules(package):
    """Recursively list all submodules in a package."""
    modules = []
    for importer, modname, ispkg in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
        modules.append(modname)
        if ispkg:
            try:
                submod = importlib.import_module(modname)
                modules.extend(list_modules(submod))
            except:
                pass
    return modules

print("Top-level attributes in dnd_character:")
for attr in dir(dnd_character):
    if not attr.startswith('_'):
        print(f"  {attr}")

print("\nAll submodules:")
all_mods = list_modules(dnd_character)
for mod in all_mods:
    print(f"  {mod}")

# Try to find race-related modules
race_modules = [m for m in all_mods if 'race' in m.lower()]
print("\nRace-related modules:")
for m in race_modules:
    print(f"  {m}")
    try:
        mod = importlib.import_module(m)
        attrs = [a for a in dir(mod) if not a.startswith('_')]
        print(f"    Attributes: {attrs}")
    except:
        pass