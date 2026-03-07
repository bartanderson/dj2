#!/usr/bin/env python
"""
Inspect the dnd_character library – dump all attributes.
"""
import inspect
from dnd_character import CLASSES
from dnd_character.spellcasting import SPELLS

def dump_obj(obj, name, indent=0, max_depth=3, current_depth=0):
    """Recursively dump object attributes up to max_depth."""
    if current_depth > max_depth:
        print(" " * indent + f"{name}: (max depth reached)")
        return
    
    prefix = " " * indent
    if isinstance(obj, (str, int, float, bool, type(None))):
        print(f"{prefix}{name}: {repr(obj)}")
    elif isinstance(obj, (list, tuple)):
        print(f"{prefix}{name}: [{type(obj).__name__} of length {len(obj)}]")
        for i, item in enumerate(obj[:3]):  # show first 3 items
            dump_obj(item, f"[{i}]", indent+2, max_depth, current_depth+1)
        if len(obj) > 3:
            print(" " * (indent+2) + f"... and {len(obj)-3} more")
    elif isinstance(obj, dict):
        print(f"{prefix}{name}: dict with keys: {list(obj.keys())[:5]}")
        for k, v in list(obj.items())[:5]:
            dump_obj(v, f"['{k}']", indent+2, max_depth, current_depth+1)
    else:
        # It's an object
        print(f"{prefix}{name}: {type(obj).__name__}")
        # Get all non-private attributes
        attrs = [a for a in dir(obj) if not a.startswith('_')]
        for attr in attrs[:10]:  # limit to first 10 attrs
            try:
                val = getattr(obj, attr)
                dump_obj(val, f".{attr}", indent+2, max_depth, current_depth+1)
            except Exception as e:
                print(" " * (indent+2) + f".{attr}: <error: {e}>")

def main():
    print("=" * 60)
    print("CLASSES")
    print("=" * 60)
    for class_name, class_obj in CLASSES.items():
        print(f"\n--- {class_name} ---")
        dump_obj(class_obj, class_name, max_depth=2)
    
    print("\n" + "=" * 60)
    print("SPELLS (first 3)")
    print("=" * 60)
    for i, (spell_name, spell_obj) in enumerate(SPELLS.items()):
        if i >= 3:
            break
        print(f"\n--- {spell_name} ---")
        dump_obj(spell_obj, spell_name, max_depth=2)

if __name__ == "__main__":
    main()