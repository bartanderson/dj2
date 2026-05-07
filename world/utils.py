# world\utils.py
import json
from world.models.dialog import DialogResponse

def truncate(obj, max_len=200):
    """Return a string representation of obj, truncated to max_len."""
    try:
        s = json.dumps(obj)
    except:
        s = str(obj)
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return s

# convex_hull and cross are for use in dungeon rendering
def convex_hull(points):
    """Compute convex hull of a set of points"""
    if len(points) <= 3:
        return points
        
    # Sort points by x-coordinate
    points = sorted(points, key=lambda p: p[0])
    
    # Build lower hull
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    
    # Build upper hull
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    
    return lower[:-1] + upper[:-1]

def cross(o, a, b):
    """Cross product for vectors OA and OB"""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

from typing import Any, List

def normalize_responses(raw: Any) -> List[DialogResponse]:
    if raw is None:
        return []

    # already correct format
    if isinstance(raw, list) and all(isinstance(r, DialogResponse) for r in raw):
        return raw

    normalized = []

    for r in raw if isinstance(raw, list) else [raw]:

        # Case 1: DialogResponse object
        if isinstance(r, DialogResponse):
            normalized.append(r)

        # Case 2: dict (legacy escape hatch)
        elif isinstance(r, dict):
            normalized.append(DialogResponse(
                speaker=r.get("speaker", "DM"),
                content=r.get("content", ""),
                dialog_type=r.get("dialog_type") or r.get("type", "narration")
            ))

        else:
            # unknown type fallback (prevents crashes)
            normalized.append(DialogResponse(
                speaker="DM",
                content=str(r),
                dialog_type="narration"
            ))

    return normalized