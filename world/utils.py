# world\utils.py
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