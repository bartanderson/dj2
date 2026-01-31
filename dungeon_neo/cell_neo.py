from dungeon_neo.constants import CELL_FLAGS
class DungeonCellNeo:
    NOTHING = CELL_FLAGS['NOTHING']
    BLOCKED = CELL_FLAGS['BLOCKED']
    ROOM = CELL_FLAGS['ROOM']
    CORRIDOR = CELL_FLAGS['CORRIDOR']
    PERIMETER = CELL_FLAGS['PERIMETER']
    ENTRANCE = CELL_FLAGS['ENTRANCE']
    ROOM_ID = CELL_FLAGS['ROOM_ID']
    ARCH = CELL_FLAGS['ARCH']
    DOOR = CELL_FLAGS['DOOR']
    LOCKED = CELL_FLAGS['LOCKED']
    TRAPPED = CELL_FLAGS['TRAPPED']
    SECRET = CELL_FLAGS['SECRET']
    PORTC = CELL_FLAGS['PORTC']
    STAIR_DN = CELL_FLAGS['STAIR_DN']
    STAIR_UP = CELL_FLAGS['STAIR_UP']
    LABEL = CELL_FLAGS['LABEL']

    # Composite flags
    DOORSPACE = CELL_FLAGS['DOORSPACE']
    ESPACE = CELL_FLAGS['ESPACE']
    STAIRS = CELL_FLAGS['STAIRS']
    BLOCK_ROOM = CELL_FLAGS['BLOCK_ROOM']
    BLOCK_CORR = CELL_FLAGS['BLOCK_CORR']
    BLOCK_DOOR = CELL_FLAGS['BLOCK_DOOR']

    def __init__(self, base_type, x, y):
        # Convert to integer with comprehensive fallback
        self.base_type = self._ensure_int(base_type)
        self.x = x
        self.y = y
        self.features = []
        self.objects = []
        self.npcs = []
        self.items = []
        self.modifications = []
        self.temporary_effects = []
        self.entities = []       # List of Entity objects
        self.overlays = []       # List of Overlay objects
        self.description = ""    # Text description of the cell
        self.properties = {}

    @property
    def position(self):
        return (self.x, self.y)

    # Add this helper method for all properties
    def _safe_property_check(self, flag):
        """Safe property check with type validation"""
        try:
            # Ensure we're working with integers
            return isinstance(self.base_type, int) and bool(self.base_type & flag)
        except Exception:
            return False

    def _ensure_int(self, value):
        """Convert any value to a valid integer flag"""
        try:
            # Handle string representations of integers
            if isinstance(value, str):
                # Try to parse hex string (e.g., '0x1000')
                if value.startswith('0x'):
                    return int(value, 16)
                # Parse decimal string
                return int(value)
            # Handle float values
            if isinstance(value, float):
                return int(value)
            # Handle None and other types
            if value is None:
                return self.NOTHING
            # Return integer as-is
            return int(value)
        except (TypeError, ValueError):
            return self.NOTHING

    def is_passable(self, secret_revealed=False):
        if self.is_blocked: 
            return False
        if self.is_secret and not secret_revealed:
            return False
        if self.is_perimeter and not self.is_door:
            return False
        if self.is_door and not self.is_arch:
            return False
        return True
        
    def reveal_secret(self):
        if self.base_type == self.SECRET:
            self.discovered = True
            return True
        return False

    @property
    def door_orientation(self):
        """Get door orientation from state if available"""
        if hasattr(self, '_state') and self._state:
            return self._state.get_door_orientation(self.x, self.y)
        return 'horizontal'

    @property
    def stair_orientation(self):
        """Get stair orientation from state if available"""
        if hasattr(self, '_state') and self._state:
            return self._state.get_stair_orientation(self.x, self.y)
        return 'horizontal'
    
    @property
    def is_room(self):
        return self._safe_property_check(self.ROOM)
    
    @property
    def is_corridor(self):
        return self._safe_property_check(self.CORRIDOR)
    
    @property
    def is_blocked(self):
        return self._safe_property_check(self.BLOCKED)

    @property
    def is_perimeter(self):
        return self._safe_property_check(self.PERIMETER)

    @property
    def is_door(self):
        return self._safe_property_check(self.DOORSPACE)

    @property
    def is_arch(self):
        return self._safe_property_check(self.ARCH)
    
    @property
    def is_door_unlocked(self):
        return self._safe_property_check(self.DOOR)
    
    @property
    def is_locked(self):
        return self._safe_property_check(self.LOCKED)
    
    @property
    def is_trapped(self):
        return self._safe_property_check(self.TRAPPED)
    
    @property
    def is_secret(self):
        return self._safe_property_check(self.SECRET)
    
    @property
    def is_portc(self):
        return self._safe_property_check(self.PORTC)
    
    @property
    def is_stair_up(self):
        return self._safe_property_check(self.STAIR_UP)
    
    @property
    def is_stair_down(self):
        return self._safe_property_check(self.STAIR_DN)
    
    @property
    def is_stairs(self):
        return self._safe_property_check(self.STAIRS)
    
    @property
    def has_label(self):
        return self._safe_property_check(self.LABEL)