# dungeon_neo/constants.py

# Cell bit flags - SINGLE SOURCE OF TRUTH
CELL_FLAGS = {
    'NOTHING': 0x00000000,
    'BLOCKED': 0x00000001,
    'ROOM': 0x00000002,
    'CORRIDOR': 0x00000004,
    'PERIMETER': 0x00000010,
    'ENTRANCE': 0x00000020,
    'ROOM_ID': 0x0000FFC0,
    'ARCH': 0x00010000,
    'DOOR': 0x00020000,
    'LOCKED': 0x00040000,
    'TRAPPED': 0x00080000,
    'SECRET': 0x00100000,
    'PORTC': 0x00200000,
    'STAIR_DN': 0x00400000,
    'STAIR_UP': 0x00800000,
    'LABEL': 0xFF000000
}

#OPENSPACE   = ROOM | CORRIDOR # note that any use of self.OPENSPACE was replaced by (ROOM | CORRIDOR)
# it is a handy concept but created a slight issue in its use as it is a logical construct and the individual
# items need to be treated individually and seperated by logic and am doing that, historical fyi since new encoding methods used

# COMPOSITE FLAGS - CRITICAL FOR GENERATION LOGIC
CELL_FLAGS['DOORSPACE'] = (
    CELL_FLAGS['ARCH'] |
    CELL_FLAGS['DOOR'] |
    CELL_FLAGS['LOCKED'] |
    CELL_FLAGS['TRAPPED'] |
    CELL_FLAGS['SECRET'] |
    CELL_FLAGS['PORTC']
)

CELL_FLAGS['ESPACE'] = (
    CELL_FLAGS['ENTRANCE'] |
    CELL_FLAGS['DOORSPACE'] |
    CELL_FLAGS['LABEL']
)

CELL_FLAGS['STAIRS'] = (
    CELL_FLAGS['STAIR_DN'] |
    CELL_FLAGS['STAIR_UP']
)

CELL_FLAGS['BLOCK_ROOM'] = (
    CELL_FLAGS['BLOCKED'] |
    CELL_FLAGS['ROOM']
)

CELL_FLAGS['BLOCK_CORR'] = (
    CELL_FLAGS['BLOCKED'] |
    CELL_FLAGS['PERIMETER'] |
    CELL_FLAGS['CORRIDOR']
)

CELL_FLAGS['BLOCK_DOOR'] = (
    CELL_FLAGS['BLOCKED'] |
    CELL_FLAGS['DOORSPACE']
)


# Direction vectors - CONSISTENT ACROSS COMPONENTS
swap = True
if swap:
    DIRECTION_VECTORS = {
        'north': (0, -1),    # Now moves right (original west)
        'south': (0, 1),   # Now moves left (original east)
        'east': (1, 0),     
        'west': (-1, 0),    
    }

    DIRECTION_VECTORS_8 = {
        'north': (0, -1),    # Now moves right (original west)
        'south': (0, 1),   # Now moves left (original east)
        'east': (1, 0),     
        'west': (-1, 0),    
        'northeast': (1, -1),
        'northwest': (-1, -1),
        'southeast': (1, 1),
        'southwest': (-1, 1)
    }
else:
    DIRECTION_VECTORS = {
        'north': (-1, 0),
        'south': (1, 0),
        'east': (0, 1),
        'west': (0, -1)
    }
    DIRECTION_VECTORS_8 = {
        'north': (-1, 0),
        'south': (1, 0),
        'east': (0, 1),
        'west': (0, -1),
        'northeast': (-1, 1),
        'northwest': (-1, -1),
        'southeast': (1, 1),
        'southwest': (1, -1)
    }

OPPOSITE_DIRECTIONS = {
    'north': 'south',
    'south': 'north',
    'east': 'west',
    'west': 'east'
}