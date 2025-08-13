import random
import math
from typing import List, Dict, Any, Tuple, Optional
from dungeon_neo.constants import CELL_FLAGS, DIRECTION_VECTORS, OPPOSITE_DIRECTIONS

class DungeonGeneratorNeo:

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

    @property
    def rooms(self):
        """Alias for room attribute to match test expectations"""
        return self.room

    @property
    def stairs(self):
        """Alias for stairList attribute to match test expectations"""
        return self.stairList

    @property
    def corridors(self):
        """Return list of corridor cells"""
        corridors = []
        for row in self.cell:
            for cell in row:
                if cell & self.CORRIDOR:
                    corridors.append(cell)
        return corridors


    def __init__(self, options=None):
        self.opts = options
        self.n_rows = options['n_rows']
        self.n_cols = options['n_cols']
        self.room = []
        self.doorList = []      
        self.stairList = []

        if options:
            self.opts.update(options)

        print (self.opts['seed'])
            
        if self.opts['seed'] is None:
            self.opts['seed'] = random.randint(1, 100000)
            
        self.rand = random.Random(self.opts['seed'])
        
        # Direction vectors
        self.di = {d: vec[0] for d, vec in DIRECTION_VECTORS.items()}
        self.dj = {d: vec[1] for d, vec in DIRECTION_VECTORS.items()}
        self.dj_dirs = list(self.dj.keys())
        self.opposite = OPPOSITE_DIRECTIONS
        
        # Layout configurations
        self.dungeon_layout = {
            'Box': [[1, 1, 1], [1, 0, 1], [1, 1, 1]],
            'Cross': [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
        }
        
        self.corridor_layout = {
            'Labyrinth': 0,
            'Bent': 50,
            'Straight': 100
        }
        
        # Stair configurations
        self.stair_end = {
            'north': {
                'walled': [[1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1]],
                'corridor': [[0, 0], [1, 0], [2, 0]],
                'stair': [0, 0],
                'next': [1, 0]
            },
            'south': {
                'walled': [[-1, -1], [0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1]],
                'corridor': [[0, 0], [-1, 0], [-2, 0]],
                'stair': [0, 0],
                'next': [-1, 0]
            },
            'west': {
                'walled': [[-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0], [1, 1]],
                'corridor': [[0, 0], [0, 1], [0, 2]],
                'stair': [0, 0],
                'next': [0, 1]
            },
            'east': {
                'walled': [[-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [1, -1]],
                'corridor': [[0, 0], [0, -1], [0, -2]],
                'stair': [0, 0],
                'next': [0, -1]
            }
        }
        
        # Deadend cleaning configurations
        self.close_end = {
            'north': {
                'walled': [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1]],
                'close': [[0, 0]],
                'recurse': [-1, 0]
            },
            'south': {
                'walled': [[0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1]],
                'close': [[0, 0]],
                'recurse': [1, 0]
            },
            'west': {
                'walled': [[-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0]],
                'close': [[0, 0]],
                'recurse': [0, -1]
            },
            'east': {
                'walled': [[-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0]],
                'close': [[0, 0]],
                'recurse': [0, 1]
            }
        }
        
        self._initialize_structures()

        
    def _initialize_structures(self):
        self.cell = None
        self.room = []
        self.doorList = []
        self.stairList = []
        self.n_rooms = 0
        self.last_room_id = 0
        self.n_i = 0
        self.n_j = 0
        self.max_row = 0
        self.max_col = 0
        self.room_base = 0
        self.room_radix = 0
        
    def create_dungeon(self):
        self.init_dungeon_size()
        self.init_cells()
        self.emplace_rooms()
        # Initialize diagnostics collection
        self.room_diagnostics = []
        self.open_rooms()
        self.label_rooms()
        self.corridors()
        
        if self.opts['add_stairs']:
            self.emplace_stairs()
                
        self.clean_dungeon()

        # NEW: Clean stray door flags
        for r in range(len(self.cell)):
            for c in range(len(self.cell[r])):
                if self.cell[r][c] & self.DOORSPACE:
                    # Check if door is registered
                    if not any(d['x'] == c and d['y'] == r for d in self.doorList):
                        #print(f"Cleaning stray door at ({c},{r})")
                        self.cell[r][c] &= ~self.DOORSPACE  # Remove door flags
                        self.cell[r][c] |= self.ENTRANCE  # Keep as regular entrance
        
        # Before returning, ensure all grid values are integers
        for x in range(len(self.cell)):
            for y in range(len(self.cell[x])):
                if not isinstance(self.cell[x][y], int):
                    print(f"Non-int value at ({x},{y}): {self.cell[x][y]} - converting to NOTHING")
                    self.cell[x][y] = self.NOTHING
        
        # Prepare stairs and doors in world coordinates
        stairs = []
        for stair in self.stairList:
            # Convert to standardized coordinate system
            stairs.append({
                'x': stair['x'],  # column = horizontal position
                'y': stair['y'],  # row = vertical position
                'dx': stair['dx'],
                'dy': stair['dy'],
                'key': stair['key'],
                'orientation': stair.get('orientation', 'horizontal')
            })
        
        # Prepare doors in world coordinates
        doors = []
        for door in self.doorList:
            # Convert to standardized coordinate system
            doors.append({
                'x': door['x'],  # column = horizontal position
                'y': door['y'],  # row = vertical position
                'orientation': door.get('orientation', 'horizontal'),
                'key': door.get('key', 'door'),
                'out_id': door.get('out_id')
            })

        # Prepare rooms in world coordinates
        rooms = []
        for room in self.room:
            rooms.append({
                'id': room['id'],
                'x': room['west'],  # horizontal start
                'y': room['north'],  # vertical start
                'width': room['east'] - room['west'] + 1,
                'height': room['south'] - room['north'] + 1,
                'north': room['north'],
                'south': room['south'],
                'west': room['west'],
                'east': room['east']
            })

        self.fill_blocks() # set blocked which cannot be traveled through.
        #print(f"Cell (6,5) flags: {hex(self.cell[5][6])}")  # [row][col]        
        return {
            'grid': self.cell,
            'stairs': stairs,
            'doors': doors,
            'rooms': self.room,
            'n_rows': self.opts['n_rows'],
            'n_cols': self.opts['n_cols'],
            'diagnostics': self.room_diagnostics  # Add diagnostics to output
        }
    
    # Core generation methods
    def init_dungeon_size(self):
        self.n_i = self.opts['n_rows'] // 2
        self.n_j = self.opts['n_cols'] // 2
        self.opts['n_rows'] = self.n_i * 2
        self.opts['n_cols'] = self.n_j * 2
        self.max_row = self.opts['n_rows'] - 1
        self.max_col = self.opts['n_cols'] - 1
        
        max_size = self.opts['room_max']
        min_size = self.opts['room_min']
        self.room_base = (min_size + 1) // 2
        self.room_radix = (max_size - min_size) // 2 + 1

    def init_cells(self):
        # Ensure proper dimensions
        rows = self.opts['n_rows'] + 1
        cols = self.opts['n_cols'] + 1
        
        try:
            # Initialize with NOTHING flag
            self.cell = [
                [self.NOTHING for _ in range(cols)]
                for _ in range(rows)
            ]
        except Exception as e:
            # Fallback to safe initialization
            self.cell = [[self.NOTHING] * cols for _ in range(rows)]
        
        layout = self.dungeon_layout.get(self.opts['dungeon_layout'])
        if layout:
            self.mask_cells(layout)
        elif self.opts['dungeon_layout'] == 'Round':
            self.round_mask()
        
    def mask_cells(self, mask):
        r_scale = len(mask) / (self.opts['n_rows'] + 1)
        c_scale = len(mask[0]) / (self.opts['n_cols'] + 1)
        
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                mask_r = int(r * r_scale)
                mask_c = int(c * c_scale)
                if (0 <= mask_r < len(mask) and (0 <= mask_c < len(mask[0]))):
                    if not mask[mask_r][mask_c]:
                        self.cell[r][c] = self.BLOCKED

    def round_mask(self):
        center_r = self.opts['n_rows'] // 2
        center_c = self.opts['n_cols'] // 2
        radius = center_c
        
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                d = math.sqrt((r - center_r) ** 2 + (c - center_c) ** 2)
                if d > radius:
                    self.cell[r][c] = self.BLOCKED

    def emplace_rooms(self):
        if self.opts.get('room_layout') == 'Packed':
            self.pack_rooms()
        else:
            self.scatter_rooms()

    def pack_rooms(self):
        for i in range(self.n_i):
            r = (i * 2) + 1
            for j in range(self.n_j):
                c = (j * 2) + 1
                if self.cell[r][c] & self.ROOM:
                    continue
                if (i == 0 or j == 0) and self.rand.randint(0, 1):
                    continue
                self.emplace_room({'i': i, 'j': j})

    def scatter_rooms(self):
        n_rooms = self.alloc_rooms()
        for _ in range(n_rooms):
            self.emplace_room()

    def alloc_rooms(self):
        dungeon_area = self.opts['n_cols'] * self.opts['n_rows']
        room_area = self.opts['room_max'] ** 2
        return dungeon_area // room_area

    def emplace_room(self, proto=None):
        if self.n_rooms >= 999:
            return
        
        proto = self.set_room(proto)
        r1 = (proto['i'] * 2) + 1
        c1 = (proto['j'] * 2) + 1
        r2 = ((proto['i'] + proto['height']) * 2) - 1
        c2 = ((proto['j'] + proto['width']) * 2) - 1
        
        if r1 < 1 or r2 > self.max_row or c1 < 1 or c2 > self.max_col:
            return
        
        hit = self.sound_room(r1, c1, r2, c2)
        if hit.get('blocked') or hit:
            return
        
        room_id = self.n_rooms + 1
        self.n_rooms = room_id
        self.last_room_id = room_id
        
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.cell[r][c] & self.ENTRANCE:
                    self.cell[r][c] &= ~self.ESPACE
                elif self.cell[r][c] & self.PERIMETER:
                    self.cell[r][c] &= ~self.PERIMETER
                self.cell[r][c] |= self.ROOM | (room_id << 6)
        
        height = (r2 - r1 + 1) * 10
        width = (c2 - c1 + 1) * 10
        room_data = {
            'id': room_id, 'row': r1, 'col': c1,
            'north': r1, 'south': r2, 'west': c1, 'east': c2,
            'height': height, 'width': width, 'area': height * width,
            'door': {}
        }
        self.room.append(room_data)
        
        # Block corridors from room boundary
        for r in range(r1 - 1, r2 + 2):
            if r <= self.max_row:
                if not (self.cell[r][c1 - 1] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r][c1 - 1] |= (self.BLOCKED | self.PERIMETER)
                if not (self.cell[r][c2 + 1] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r][c2 + 1] |= self.PERIMETER
        
        for c in range(c1 - 1, c2 + 2):
            if c <= self.max_col:
                if not (self.cell[r1 - 1][c] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r1 - 1][c] |= self.PERIMETER
                if not (self.cell[r2 + 1][c] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r2 + 1][c] |= (self.BLOCKED | self.PERIMETER)

    def set_room(self, proto):
        if proto is None:
            proto = {}
        
        if 'height' not in proto:
            proto['height'] = self.room_base + self.rand.randint(0, self.room_radix - 1)
        
        if 'width' not in proto:
            proto['width'] = self.room_base + self.rand.randint(0, self.room_radix - 1)
        
        if 'i' not in proto:
            proto['i'] = self.rand.randint(0, self.n_i - proto['height'])
        
        if 'j' not in proto:
            proto['j'] = self.rand.randint(0, self.n_j - proto['width'])
        
        return proto

    def sound_room(self, r1, c1, r2, c2):
        hit = {}
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.cell[r][c] & self.BLOCKED:
                    return {'blocked': True}
                if self.cell[r][c] & self.ROOM:
                    room_id = (self.cell[r][c] & self.ROOM_ID) >> 6
                    hit[room_id] = hit.get(room_id, 0) + 1
        return hit

    def open_rooms(self):
        for room_id in range(1, self.n_rooms + 1):
            self.open_room(self.room[room_id - 1])
        if hasattr(self, 'connect'):
            del self.connect

    def open_room(self, room):
        # Initialize diagnostic tracking
        room_diag = {
            'room_id': room['id'],
            'initial_sills': 0,
            'allocated_doors': 0,
            'placed_doors': 0,
            'rejected_sills': [],
            'failure_reason': None
        }

        sills = self.door_sills(room)
        room_diag['initial_sills'] = len(sills)

        if not sills:
            # Early exit if no sills found
            room_diag['failure_reason'] = 'no_valid_sills'
            self.room_diagnostics.append(room_diag)
            return
        
        n_opens = self.alloc_opens(room)
        room_diag['allocated_doors'] = n_opens

        if not hasattr(self, 'connect'):
            self.connect = {}
        
        # Initialize master door list if it doesn't exist
        if not hasattr(self, 'all_doors'):
            self.all_doors = []
        
        for _ in range(n_opens):
            if not sills:
                break
            
            idx = self.rand.randint(0, len(sills) - 1)
            sill = sills.pop(idx)
            door_r = sill['door_r']
            door_c = sill['door_c']
            
            # Track rejection reasons
            if self.cell[door_r][door_c] & self.DOORSPACE:
                room_diag['rejected_sills'].append({
                    'position': (door_c, door_r),
                    'reason': 'existing_door'
                })
                continue
            
            if 'out_id' in sill and sill['out_id'] is not None:
                connect_key = ','.join(map(str, sorted([room['id'], sill['out_id']])))
                if connect_key in self.connect:
                    room_diag['rejected_sills'].append({
                        'position': (door_c, door_r),
                        'reason': 'duplicate_connection'
                    })
                    continue
                self.connect[connect_key] = True
            
            open_dir = sill['dir']
            for x in range(3):
                r = sill['sill_r'] + self.di[open_dir] * x
                c = sill['sill_c'] + self.dj[open_dir] * x
                self.cell[r][c] &= ~self.PERIMETER
                self.cell[r][c] |= self.ENTRANCE

            # DETERMINE DOOR ORIENTATION
            orientation = 'vertical' if sill['dir'] in ['east', 'west'] else 'horizontal'
            #print(f"1 generate: {orientation} global_x:{door_c} global_y:{door_r}")
            
            door_type = self.door_type()
            
            # Create door with GLOBAL coordinates
            door = {
                'x': door_c,  # horizontal position (global)
                'y': door_r,  # vertical position (global)
                'orientation': orientation,
                'key': door_type
            }
            
            # Apply door flags
            if door_type == self.ARCH:
                self.cell[door_r][door_c] |= self.ARCH
                door['key'] = 'arch'
            elif door_type == self.DOOR:
                self.cell[door_r][door_c] |= self.DOOR
                door['key'] = 'open'
            elif door_type == self.LOCKED:
                self.cell[door_r][door_c] |= self.LOCKED
                door['key'] = 'lock'
            elif door_type == self.TRAPPED:
                self.cell[door_r][door_c] |= self.TRAPPED
                door['key'] = 'trap'
            elif door_type == self.SECRET:
                self.cell[door_r][door_c] |= self.SECRET
                door['key'] = 'secret'
            elif door_type == self.PORTC:
                self.cell[door_r][door_c] |= self.PORTC
                door['key'] = 'portc'
            
            if 'out_id' in sill:
                door['out_id'] = sill['out_id']
            
            # Add to master list
            self.all_doors.append(door)
            
            # Also add to room's door list
            if open_dir not in room['door']:
                room['door'][open_dir] = []
            room['door'][open_dir].append(door)

            room_diag['placed_doors'] += 1
        
        # Final disconnection analysis
        if not room['door']:  # Room ended up with no doors
            if room_diag['initial_sills'] == 0:
                room_diag['failure_reason'] = 'no_valid_sills'
            elif room_diag['allocated_doors'] == 0:
                room_diag['failure_reason'] = 'zero_door_allocation'
            elif room_diag['placed_doors'] == 0:
                room_diag['failure_reason'] = 'all_sills_rejected'
        
        self.room_diagnostics.append(room_diag)

    def alloc_opens(self, room):
        room_h = ((room['south'] - room['north']) // 2) + 1
        room_w = ((room['east'] - room['west']) // 2) + 1
        flumph = int(math.sqrt(room_w * room_h))
        return flumph + self.rand.randint(0, flumph - 1)

    def door_sills(self, room):
        sills = []
        dirs = ['north', 'south', 'west', 'east']
        
        for dir in dirs:
            if dir == 'north' and room['north'] >= 3:
                for c in range(room['west'], room['east'] + 1, 2):
                    sill = self.check_sill(room, room['north'], c, dir)
                    if sill:
                        sills.append(sill)
            
            elif dir == 'south' and room['south'] <= self.opts['n_rows'] - 3:
                for c in range(room['west'], room['east'] + 1, 2):
                    sill = self.check_sill(room, room['south'], c, dir)
                    if sill:
                        sills.append(sill)
            
            elif dir == 'west' and room['west'] >= 3:
                for r in range(room['north'], room['south'] + 1, 2):
                    sill = self.check_sill(room, r, room['west'], dir)
                    if sill:
                        sills.append(sill)
            
            elif dir == 'east' and room['east'] <= self.opts['n_cols'] - 3:
                for r in range(room['north'], room['south'] + 1, 2):
                    sill = self.check_sill(room, r, room['east'], dir)
                    if sill:
                        sills.append(sill)

        # Add this new section to guarantee at least one sill
        if not sills:
            return self.create_guaranteed_sill(room)
            
        self.shuffle(sills)
        return sills

    def create_guaranteed_sill(self, room):
        """Create at least one guaranteed door position for isolated rooms"""
        # Find the most central wall position
        center_r = (room['north'] + room['south']) // 2
        center_c = (room['west'] + room['east']) // 2
        walls = [
            ('north', room['north'], center_c),
            ('south', room['south'], center_c),
            ('west', center_r, room['west']),
            ('east', center_r, room['east'])
        ]
        
        # Try center positions first (most aesthetic)
        for dir, r, c in walls:
            sill = self.check_sill(room, r, c, dir)
            if sill:
                return [sill]
        
        # Then scan entire walls for any valid position
        # North wall
        if room['north'] >= 3:
            for c in range(room['west'], room['east'] + 1, 2):
                sill = self.check_sill(room, room['north'], c, 'north')
                if sill:
                    return [sill]
        
        # South wall
        if room['south'] <= self.opts['n_rows'] - 3:
            for c in range(room['west'], room['east'] + 1, 2):
                sill = self.check_sill(room, room['south'], c, 'south')
                if sill:
                    return [sill]
        
        # West wall
        if room['west'] >= 3:
            for r in range(room['north'], room['south'] + 1, 2):
                sill = self.check_sill(room, r, room['west'], 'west')
                if sill:
                    return [sill]
        
        # East wall
        if room['east'] <= self.opts['n_cols'] - 3:
            for r in range(room['north'], room['south'] + 1, 2):
                sill = self.check_sill(room, r, room['east'], 'east')
                if sill:
                    return [sill]
        
        # Ultimate fallback - force create a door at east wall center
        return [{
            'sill_r': center_r,
            'sill_c': room['east'],  # Wall position
            'dir': 'east',
            'door_r': center_r,
            'door_c': min(room['east'] + 1, self.opts['n_cols']),  # Ensure within bounds
            'out_id': None
        }]
    
    def check_sill(self, room, sill_r, sill_c, dir):
        door_r = sill_r + self.di[dir]
        door_c = sill_c + self.dj[dir]
        
        if not (self.cell[door_r][door_c] & self.PERIMETER):
            return None
        if self.cell[door_r][door_c] & self.BLOCK_DOOR:
            return None
        
        out_r = door_r + self.di[dir]
        out_c = door_c + self.dj[dir]
        
        if out_r < 0 or out_r > self.opts['n_rows'] or out_c < 0 or out_c > self.opts['n_cols']:
            return None
        if self.cell[out_r][out_c] & self.BLOCKED:
            return None
        
        out_id = None
        if self.cell[out_r][out_c] & self.ROOM:
            out_id = (self.cell[out_r][out_c] & self.ROOM_ID) >> 6
            if out_id == room['id']:
                return None
        
        return {
            'sill_r': sill_r, 'sill_c': sill_c,
            'dir': dir, 'door_r': door_r, 'door_c': door_c,
            'out_id': out_id
        }

    def shuffle(self, arr):
        self.rand.shuffle(arr)

    def door_type(self):
        r = self.rand.randint(0, 109)
        if r < 15:
            return self.ARCH
        elif r < 60:
            return self.DOOR
        elif r < 75:
            return self.LOCKED
        elif r < 90:
            return self.TRAPPED
        elif r < 100:
            return self.SECRET
        else:
            return self.PORTC


    def label_rooms(self):
        for room in self.room:
            label = str(room['id'])
            label_len = len(label)
            label_r = (room['north'] + room['south']) // 2
            label_c = (room['west'] + room['east'] - label_len) // 2 + 1
            
            for i, char in enumerate(label):
                char_code = ord(char)
                self.cell[label_r][label_c + i] |= (char_code << 24)

    def corridors(self):
        for i in range(1, self.n_i):
            r = (i * 2) + 1
            for j in range(1, self.n_j):
                c = (j * 2) + 1
                if self.cell[r][c] & self.CORRIDOR:
                    continue
                self.tunnel(i, j)
        self.block_corridor_walls() # this should create the blocking for corridors

    def block_corridor_walls(self):
        for i in range(1, self.n_i):
            r = (i * 2) + 1
            for j in range(1, self.n_j):
                c = (j * 2) + 1
                if not (self.cell[r][c] & self.CORRIDOR):
                    continue
                
                # Block adjacent cells in all directions
                for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nr, nc = r + dr, c + dc
                    if (0 <= nr <= self.max_row and 0 <= nc <= self.max_col and
                        not (self.cell[nr][nc] & (self.ROOM | self.CORRIDOR | self.ENTRANCE))):
                        self.cell[nr][nc] |= self.BLOCKED | self.PERIMETER


    def tunnel(self, i, j, last_dir=None):
        dirs = self.tunnel_dirs(last_dir)
        for dir in dirs:
            if self.open_tunnel(i, j, dir):
                next_i = i + self.di[dir]
                next_j = j + self.dj[dir]
                self.tunnel(next_i, next_j, dir)

    def tunnel_dirs(self, last_dir):
        dirs = self.dj_dirs[:]
        self.shuffle(dirs)
        
        if last_dir and self.corridor_layout[self.opts['corridor_layout']] is not None:
            p = self.corridor_layout[self.opts['corridor_layout']]
            if self.rand.randint(0, 99) < p:
                dirs.insert(0, last_dir)
        return dirs

    def open_tunnel(self, i, j, dir):
        this_r = (i * 2) + 1
        this_c = (j * 2) + 1
        next_i = i + self.di[dir]
        next_j = j + self.dj[dir]
        next_r = (next_i * 2) + 1
        next_c = (next_j * 2) + 1
        mid_r = (this_r + next_r) // 2
        mid_c = (this_c + next_c) // 2
        
        if self.sound_tunnel(mid_r, mid_c, next_r, next_c):
            return self.delve_tunnel(this_r, this_c, next_r, next_c)
        return False

    def sound_tunnel(self, mid_r, mid_c, next_r, next_c):
        if next_r < 0 or next_r > self.opts['n_rows'] or next_c < 0 or next_c > self.opts['n_cols']:
            return False
        
        r1 = min(mid_r, next_r)
        r2 = max(mid_r, next_r)
        c1 = min(mid_c, next_c)
        c2 = max(mid_c, next_c)
        
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if self.cell[r][c] & self.BLOCK_CORR:
                    return False
        return True

    def delve_tunnel(self, r1, c1, r2, c2):
        min_r = min(r1, r2)
        max_r = max(r1, r2)
        min_c = min(c1, c2)
        max_c = max(c1, c2)
        
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                self.cell[r][c] &= ~self.ENTRANCE
                self.cell[r][c] |= self.CORRIDOR
        return True

    def emplace_stairs(self):
        # Reset stairList at start
        self.stairList = []

        n = self.opts['add_stairs']
        if not n:
            return
        
        ends = self.stair_ends()
        if not ends:
            return

        # Create exactly one up and one down stair when n=2
        if n == 2:
            # First stair: down
            if ends:
                end = ends.pop(0)
                r, c = end['x'], end['y']
                self.cell[r][c] |= self.STAIR_DN
                end['key'] = 'down'
                self.stairs.append(end)
            
            # Second stair: up
            if ends:
                end = ends.pop(0)
                r, c = end['x'], end['y']
                self.cell[r][c] |= self.STAIR_UP
                end['key'] = 'up'
                self.stairs.append(end)
        else:
            for i in range(n):
                if not ends:
                    break
                end = ends.pop(0)
                x, y = end['x'], end['y']
                # Store corridor direction vector
                next_pos = end['next']
                end['corridor_dx'] = next_pos[0]
                end['corridor_dy'] = next_pos[1]
                
                # For n != 2, maintain existing random behavior
                stair_type = i if i < 2 else random.randint(0, 1)
                
                if stair_type == 0:
                    self.cell[y][x] |= self.STAIR_DN
                    end['key'] = 'down'
                else:
                    self.cell[y][x] |= self.STAIR_UP
                    end['key'] = 'up'
                    stair = {
                        'x': end['x'],  # row position
                        'y': end['y'],  # column position
                        'dx': end['dx'],
                        'dy': end['dy'],
                        'orientation': end['orientation'],  # Use calculated orientation
                        'key': 'down' if (i == 0 and n == 2) else 'up'
                    }    
                
                self.stairList.append(stair)
        if False:   # debug output you can turn on for identifying stair position for orientation fix      
            for stair in self.stairList:
                print(f"GENERATOR stair: pos=({stair['x']},{stair['y']}) "
                      f"orientation={stair['orientation']}")

    def stair_ends(self):
        ends = []
        for i in range(self.n_i):
            r = (i * 2) + 1
            for j in range(self.n_j):
                c = (j * 2) + 1
                if self.cell[r][c] != self.CORRIDOR:
                    continue
                if self.cell[r][c] & self.STAIRS:
                    continue
                
                for dir, config in self.stair_end.items():
                    if self.check_tunnel(self.cell, r, c, config):
                        next_vec = config['next']  # This is what matters
                        orientation = 'horizontal' if next_vec[0] != 0 else 'vertical' # orientation of stair                
                        end = {
                            'y': c,  # column = horizontal position
                            'x': r,  # row = vertical position
                            'dx': next_vec[0],  # horizontal direction
                            'dy': next_vec[1],  # vertical direction
                            'orientation': orientation
                        }
                        ends.append(end)
                        break
        return ends

    def clean_dungeon(self):
        if self.opts['remove_deadends']:
            self.remove_deadends()
        self.clean_disconnected_doors()
        self.fix_doors()

    def remove_deadends(self):
        p = self.opts['remove_deadends']
        all = (p == 100)
        
        for i in range(self.n_i):
            r = (i * 2) + 1
            for j in range(self.n_j):
                c = (j * 2) + 1
                if not (self.cell[r][c] & (self.ROOM | self.CORRIDOR)):
                    continue
                if self.cell[r][c] & self.STAIRS:
                    continue
                if not all and self.rand.randint(0, 99) >= p:
                    continue
                if self.is_adjacent_to_door(r, c):
                    continue
                if self.corridor_leads_to_door(r, c):
                    continue
                self.collapse(r, c, self.close_end)

    def clean_disconnected_doors(self):
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & self.DOORSPACE:
                    connected = 0
                    for dr, dc in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']:
                            if self.cell[nr][nc] & ((self.ROOM | self.CORRIDOR) | self.DOORSPACE):
                                connected += 1
                    if connected < 2:
                        self.cell[r][c] &= ~self.DOORSPACE
                        self.cell[r][c] |= self.PERIMETER

    def collapse(self, r, c, xc):
        if not (self.cell[r][c] & (self.ROOM | self.CORRIDOR)):
            return
        
        for dir, config in xc.items():
            if not self.check_tunnel(self.cell, r, c, config):
                continue
            
            for pos in config['close']:
                self.cell[r + pos[0]][c + pos[1]] = self.NOTHING
            
            if 'recurse' in config:
                recurse = config['recurse']
                self.collapse(r + recurse[0], c + recurse[1], xc)

    def is_adjacent_to_door(self, r, c):
        for dr, dc in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']:
                if self.cell[nr][nc] & self.DOORSPACE:
                    return True
        return False

    def corridor_leads_to_door(self, r, c):
        if not (self.cell[r][c] & self.CORRIDOR):
            return False
        
        for dr, dc in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']:
                if self.cell[nr][nc] & self.DOORSPACE:
                    return True
        return False

    def check_tunnel(self, cell, r, c, check):
        if 'corridor' in check:
            for pos in check['corridor']:
                nr, nc = r + pos[0], c + pos[1]
                if not (0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']):
                    return False
                if cell[nr][nc] != self.CORRIDOR:
                    return False
        
        if 'walled' in check:
            for pos in check['walled']:
                nr, nc = r + pos[0], c + pos[1]
                if not (0 <= nr <= self.opts['n_rows'] and 0 <= nc <= self.opts['n_cols']):
                    continue
                if cell[nr][nc] & (self.ROOM | self.CORRIDOR):
                    return False
        return True


    def fix_doors(self):
        fixed = [[False] * (self.opts['n_cols'] + 1) for _ in range(self.opts['n_rows'] + 1)]
        self.doorList = []  # We'll rebuild this from all_doors
        
        # Create a position map for quick lookup
        position_map = {}
        for door in self.all_doors:
            pos = (door['x'], door['y'])
            position_map[pos] = door
        
        for room in self.room:
            for dir, doors in room['door'].items():
                shiny = []
                for door in doors:
                    x, y = door['x'], door['y']
                    
                    if not (0 <= y < len(self.cell) and 0 <= x < len(self.cell[0])):
                        continue
                        
                    if not (self.cell[y][x] & (self.ROOM | self.CORRIDOR)):
                        continue
                    
                    if fixed[y][x]:
                        shiny.append(door)
                        continue
                    
                    fixed[y][x] = True
                    
                    # Get the original door from master list
                    original_door = position_map.get((x, y))
                    if original_door:
                        # Preserve original orientation
                        orientation = original_door.get('orientation', 'horizontal')
                        key = original_door.get('key', 'door')
                    else:
                        # Fallback to door data
                        orientation = door.get('orientation', 'horizontal')
                        key = door.get('key', 'door')
                    
                    # Create new door with preserved orientation
                    new_door = {
                        'x': x,
                        'y': y,
                        'orientation': orientation,
                        'key': key,
                        'out_id': door.get('out_id')
                    }
                    
                    shiny.append(new_door)
                    self.doorList.append(new_door)
                    
                    # Update opposite room if needed
                    if 'out_id' in door and door['out_id'] is not None:
                        out_id = door['out_id']
                        out_room = next((r for r in self.room if r['id'] == out_id), None)
                        if out_room:
                            out_dir = self.opposite[dir]
                            if out_dir not in out_room['door']:
                                out_room['door'][out_dir] = []
                            out_room['door'][out_dir].append(new_door)
                
                room['door'][dir] = shiny

    def get_door_type(self, cell):
        if cell & ARCH:
            return 'arch'
        if cell & DOOR:
            return 'open'
        if cell & LOCKED:
            return 'lock'
        if cell & TRAPPED:
            return 'trap'
        if cell & SECRET:
            return 'secret'
        if cell & PORTC:
            return 'portc'
        return 'open'

    def has_open_space(self, r, c):
        """Check if coordinates contain open space"""
        if not hasattr(self, 'state') or not self.state:
            return False
        if r < 0 or r >= self.state.height or c < 0 or c >= self.state.width:
            return False
        cell = self.state.grid[r][c]
        return cell and (cell.is_room or cell.is_corridor)

    def fill_blocks(self):
        """Post-processing step to fill all empty space with BLOCKED cells"""
        for r in range(len(self.cell)):
            for c in range(len(self.cell[r])):
                # Only fill cells that are truly empty (NOTHING)
                if self.cell[r][c] == self.NOTHING:
                    self.cell[r][c] = self.BLOCKED
                    
                # Also fill perimeter cells that aren't doors/entrances
                elif (self.cell[r][c] & self.PERIMETER and 
                      not (self.cell[r][c] & (self.ENTRANCE | self.DOORSPACE))):
                    self.cell[r][c] = self.BLOCKED        