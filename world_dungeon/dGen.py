import math
import random
import time
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import io

class DungeonGenerator:
    def __init__(self, options=None):
        if options is None:
            options = {}
        self.opts = {
            'seed': int(time.time() * 1000),
            'n_rows': 39,
            'n_cols': 39,
            'dungeon_layout': 'None',
            'room_min': 3,
            'room_max': 9,
            'room_layout': 'Scattered',
            'corridor_layout': 'Bent',
            'remove_deadends': 50,
            'add_stairs': 2,
            'map_style': 'Standard',
            'cell_size': 18,
            'grid': 'Square',
        }
        self.opts.update(options)
        
        # Bit flags
        self.NOTHING = 0x00000000
        self.BLOCKED = 0x00000001
        self.ROOM = 0x00000002
        self.CORRIDOR = 0x00000004
        self.PERIMETER = 0x00000010
        self.ENTRANCE = 0x00000020
        self.ROOM_ID = 0x0000FFC0
        self.ARCH = 0x00010000
        self.DOOR = 0x00020000
        self.LOCKED = 0x00040000
        self.TRAPPED = 0x00080000
        self.SECRET = 0x00100000
        self.PORTC = 0x00200000
        self.STAIR_DN = 0x00400000
        self.STAIR_UP = 0x00800000
        self.LABEL = 0xFF000000

        self.DOOR_OPEN = 0x01000000
        self.DOOR_BROKEN = 0x02000000
        self.PORTC_OPEN = 0x04000000
        self.PORTC_BROKEN = 0x08000000
        
        self.OPENSPACE = self.ROOM | self.CORRIDOR | self.ENTRANCE
        self.DOORSPACE = (self.ARCH | self.DOOR | self.LOCKED | self.TRAPPED | 
                          self.SECRET | self.PORTC | self.DOOR_OPEN | 
                          self.DOOR_BROKEN | self.PORTC_OPEN | self.PORTC_BROKEN)
        self.ESPACE = self.ENTRANCE | self.DOORSPACE | 0xFF000000
        self.STAIRS = self.STAIR_DN | self.STAIR_UP
        self.BLOCK_ROOM = self.BLOCKED | self.ROOM
        self.BLOCK_CORR = self.BLOCKED | self.PERIMETER | self.CORRIDOR
        self.BLOCK_DOOR = self.BLOCKED | self.DOORSPACE
        
        # Directions
        self.di = {'north': -1, 'south': 1, 'west': 0, 'east': 0}
        self.dj = {'north': 0, 'south': 0, 'west': -1, 'east': 1}
        self.dj_dirs = ['north', 'south', 'west', 'east']
        self.opposite = {'north': 'south', 'south': 'north', 'west': 'east', 'east': 'west'}
        
        # Layouts
        self.dungeon_layout = {
            'Box': [[1, 1, 1], [1, 0, 1], [1, 1, 1]],
            'Cross': [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
        }
        
        self.corridor_layout = {
            'Labyrinth': 0,
            'Bent': 50,
            'Straight': 100
        }
        
        # Stairs
        self.stair_end = {
            'north': {'walled': [[1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1]], 
                     'corridor': [[0, 0], [1, 0], [2, 0]], 
                     'stair': [0, 0], 
                     'next': [1, 0]},
            'south': {'walled': [[-1, -1], [0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1]], 
                     'corridor': [[0, 0], [-1, 0], [-2, 0]], 
                     'stair': [0, 0], 
                     'next': [-1, 0]},
            'west': {'walled': [[-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0], [1, 1]], 
                    'corridor': [[0, 0], [0, 1], [0, 2]], 
                    'stair': [0, 0], 
                    'next': [0, 1]},
            'east': {'walled': [[-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [1, -1]], 
                    'corridor': [[0, 0], [0, -1], [0, -2]], 
                    'stair': [0, 0], 
                    'next': [0, -1]}
        }
        
        # Dead ends
        self.close_end = {
            'north': {'walled': [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1]], 
                     'close': [[0, 0]], 
                     'recurse': [-1, 0]},
            'south': {'walled': [[0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1]], 
                     'close': [[0, 0]], 
                     'recurse': [1, 0]},
            'west': {'walled': [[-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0]], 
                    'close': [[0, 0]], 
                    'recurse': [0, -1]},
            'east': {'walled': [[-1, 0], [-1, -1], [0, -1], [1, -1], [1, 0]], 
                    'close': [[0, 0]], 
                    'recurse': [0, 1]}
        }
        
        # Colors
        self.color_chain = {
            'door': 'fill', 
            'label': 'fill', 
            'stair': 'wall', 
            'wall': 'fill', 
            'fill': 'black'
        }
        
        # Styles
        self.map_style = {
            'Standard': {'fill': '000000', 'open': 'FFFFFF', 'open_grid': 'CCCCCC'}
        }
        
        # Initialize PRNG
        self._prng_seed = self.opts['seed']
        self.rand = self.seeded_random(self._prng_seed)
        self.cell = None
        self.room = []
        self.stairs = []
        self.doorList = []
        self.n_rooms = 0
        self.last_room_id = 0
        self.connect = None
        self.n_i = 0
        self.n_j = 0
        self.max_row = 0
        self.max_col = 0
        self.room_base = 0
        self.room_radix = 0
    
    def seeded_random(self, seed):
        def prng():
            nonlocal seed
            current = seed
            seed += 1
            value = math.sin(current) * 10000
            return value - math.floor(value)
        return prng
    
    def rand_int(self, max_val):
        return int(self.rand() * max_val)
    
    def shuffle(self, array):
        for i in range(len(array) - 1, 0, -1):
            j = self.rand_int(i + 1)
            array[i], array[j] = array[j], array[i]
        return array
    
    def create_dungeon(self):
        self.init_dungeon_size()
        self.init_cells()
        self.emplace_rooms()
        self.open_rooms()
        self.label_rooms()
        self.corridors()
        if self.opts['add_stairs']:
            self.emplace_stairs()
        self.clean_dungeon()
        
        # Debug output
        print(f"Generated dungeon with {self.n_rooms} rooms")
        print(f"Doors placed: {len(self.doorList)}")
        print(f"Corridor cells: {sum(1 for row in self.cell for cell in row if cell & self.CORRIDOR)}")
        
        return self
    
    def init_dungeon_size(self):
        self.n_i = self.opts['n_rows'] // 2
        self.n_j = self.opts['n_cols'] // 2
        self.opts['n_rows'] = self.n_i * 2
        self.opts['n_cols'] = self.n_j * 2
        self.max_row = self.opts['n_rows'] - 1
        self.max_col = self.opts['n_cols'] - 1
        self.n_rooms = 0
        
        max_val = self.opts['room_max']
        min_val = self.opts['room_min']
        self.room_base = (min_val + 1) // 2
        self.room_radix = ((max_val - min_val) // 2) + 1
    
    def init_cells(self):
        self.cell = [
            [self.NOTHING] * (self.opts['n_cols'] + 1) 
            for _ in range(self.opts['n_rows'] + 1)
        ]
        
        layout = self.opts['dungeon_layout']
        if layout in self.dungeon_layout:
            self.mask_cells(self.dungeon_layout[layout])
        elif layout == 'Round':
            self.round_mask()
    
    def mask_cells(self, mask):
        r_x = len(mask) / (self.opts['n_rows'] + 1)
        c_x = len(mask[0]) / (self.opts['n_cols'] + 1)
        
        for r in range(self.opts['n_rows'] + 1):
            mask_row = min(int(r * r_x), len(mask) - 1)  # Ensure within bounds
            for c in range(self.opts['n_cols'] + 1):
                mask_col = min(int(c * c_x), len(mask[0]) - 1)  # Ensure within bounds
                if not mask[mask_row][mask_col]:
                    self.cell[r][c] = self.BLOCKED
    
    def round_mask(self):
        center_r = self.opts['n_rows'] // 2
        center_c = self.opts['n_cols'] // 2
        radius = min(center_r, center_c) - 2
        
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                d = math.sqrt((r - center_r) ** 2 + (c - center_c) ** 2)
                if d > radius:
                    self.cell[r][c] = self.BLOCKED
    
    def emplace_rooms(self):
        if self.opts['room_layout'] == 'Packed':
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
                if (i == 0 or j == 0) and self.rand_int(2):
                    continue
                
                proto = {'i': i, 'j': j}
                self.emplace_room(proto)
    
    def scatter_rooms(self):
        n_rooms = self.alloc_rooms()
        for _ in range(n_rooms):
            self.emplace_room()
    
    def alloc_rooms(self):
        dungeon_area = self.opts['n_cols'] * self.opts['n_rows']
        room_area = self.opts['room_max'] * self.opts['room_max']
        return dungeon_area // room_area
    
    def emplace_room(self, proto=None):
        if proto is None:
            proto = {}
        if self.n_rooms >= 999:
            return
        
        proto = self.set_room(proto)
        r1 = (proto['i'] * 2) + 1
        c1 = (proto['j'] * 2) + 1
        r2 = ((proto['i'] + proto['height']) * 2) - 1
        c2 = ((proto['j'] + proto['width']) * 2) - 1
        
        # Ensure room is within bounds with additional perimeter
        if (r1 < 2 or r2 > self.max_row - 1 or 
            c1 < 2 or c2 > self.max_col - 1):
            return
        
        # Check for collisions with existing rooms (including perimeter)
        hit = self.sound_room(r1, c1, r2, c2)
        if hit.get('blocked'):
            return
        if hit:
            return
        
        room_id = self.n_rooms + 1
        self.n_rooms = room_id
        self.last_room_id = room_id
        
        # Ensure room list is large enough
        while len(self.room) <= room_id:
            self.room.append(None)
        
        # Create room with proper dimensions
        height = (r2 - r1 + 1)
        width = (c2 - c1 + 1)
        
        self.room[room_id] = {
            'id': room_id, 'row': r1, 'col': c1,
            'north': r1, 'south': r2, 'west': c1, 'east': c2,
            'height': height, 'width': width, 'area': height * width,
            'door': {}
        }
        
        # Mark room cells
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                self.cell[r][c] |= self.ROOM | (room_id << 6)
        
        # Mark perimeter as soft blocks only (FIXED)
        for r in range(r1 - 1, r2 + 2):
            if r < 0 or r > self.opts['n_rows']:
                continue
            for c in [c1 - 1, c2 + 1]:
                if 0 <= c <= self.opts['n_cols']:
                    self.cell[r][c] |= self.PERIMETER  # Soft block only
        
        for c in range(c1 - 1, c2 + 2):
            if c < 0 or c > self.opts['n_cols']:
                continue
            for r in [r1 - 1, r2 + 1]:
                if 0 <= r <= self.opts['n_rows']:
                    self.cell[r][c] |= self.PERIMETER  # Soft block only
    
    def set_room(self, proto):
        if 'height' not in proto:
            if 'i' in proto:
                a = self.n_i - self.room_base - proto['i']
                a = max(0, a)
                r = min(a, self.room_radix)
                proto['height'] = self.room_base + self.rand_int(r)
            else:
                proto['height'] = self.room_base + self.rand_int(self.room_radix)
        
        if 'width' not in proto:
            if 'j' in proto:
                a = self.n_j - self.room_base - proto['j']
                a = max(0, a)
                r = min(a, self.room_radix)
                proto['width'] = self.room_base + self.rand_int(r)
            else:
                proto['width'] = self.room_base + self.rand_int(self.room_radix)
        
        if 'i' not in proto:
            proto['i'] = self.rand_int(self.n_i - proto['height'])
        
        if 'j' not in proto:
            proto['j'] = self.rand_int(self.n_j - proto['width'])
        
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
        self.connect = {}
        for room_id in range(1, self.n_rooms + 1):
            self.open_room(self.room[room_id])
        self.connect = None
    
    def open_room(self, room):
        sills = self.door_sills(room)
        if not sills:
            return
        
        n_opens = self.alloc_opens(room)
        if not hasattr(self, 'connect'):
            self.connect = {}
        
        for _ in range(n_opens):
            if not sills:
                break
            
            idx = self.rand_int(len(sills))
            sill = sills.pop(idx)
            door_r = sill['door_r']
            door_c = sill['door_c']
            
            # Skip if door space already occupied
            if self.cell[door_r][door_c] & self.DOORSPACE:
                continue
            
            open_dir = sill['dir']
            # Open the passage (FIXED: clear perimeter only)
            for x in range(3):
                r = sill['sill_r'] + (self.di[open_dir] * x)
                c = sill['sill_c'] + (self.dj[open_dir] * x)
                self.cell[r][c] &= ~self.PERIMETER
                self.cell[r][c] |= self.ENTRANCE
            
            # Create door (FIXED: full door creation preserved)
            door_type = self.door_type()
            door = {'row': door_r, 'col': door_c}
            door_bits = 0
            
            if door_type == self.ARCH:
                door_bits = self.ARCH
                door['key'] = 'arch'
                door['type'] = 'Archway'
            elif door_type == self.DOOR:
                door_bits = self.DOOR
                door['key'] = 'open'
                door['type'] = 'Unlocked Door'
            elif door_type == self.LOCKED:
                door_bits = self.LOCKED
                door['key'] = 'lock'
                door['type'] = 'Locked Door'
            elif door_type == self.TRAPPED:
                door_bits = self.TRAPPED
                door['key'] = 'trap'
                door['type'] = 'Trapped Door'
            elif door_type == self.SECRET:
                door_bits = self.SECRET
                door['key'] = 'secret'
                door['type'] = 'Secret Door'
            elif door_type == self.PORTC:
                door_bits = self.PORTC
                door['key'] = 'portc'
                door['type'] = 'Portcullis'
            elif door_type == self.DOOR_OPEN:
                door_bits = self.DOOR_OPEN
                door['key'] = 'door_open'
                door['type'] = 'Open Door'
            elif door_type == self.DOOR_BROKEN:
                door_bits = self.DOOR_BROKEN
                door['key'] = 'door_broken'
                door['type'] = 'Broken Door'
            elif door_type == self.PORTC_OPEN:
                door_bits = self.PORTC_OPEN
                door['key'] = 'portc_open'
                door['type'] = 'Open Portcullis'
            elif door_type == self.PORTC_BROKEN:
                door_bits = self.PORTC_BROKEN
                door['key'] = 'portc_broken'
                door['type'] = 'Broken Portcullis'
            
            self.cell[door_r][door_c] |= door_bits
            
            if sill['out_id']:
                door['out_id'] = sill['out_id']
            
            if open_dir not in room['door']:
                room['door'][open_dir] = []
            room['door'][open_dir].append(door)
            self.doorList.append(door)
    
    def alloc_opens(self, room):
        room_h = ((room['south'] - room['north']) // 2) + 1
        room_w = ((room['east'] - room['west']) // 2) + 1
        flumph = int(math.sqrt(room_w * room_h))
        return flumph + self.rand_int(flumph)
    
    def door_sills(self, room):
        sills = []
        
        if room['north'] >= 3:
            for c in range(room['west'], room['east'] + 1, 2):
                sill = self.check_sill(room, room['north'], c, 'north')
                if sill:
                    sills.append(sill)
        
        if room['south'] <= self.opts['n_rows'] - 3:
            for c in range(room['west'], room['east'] + 1, 2):
                sill = self.check_sill(room, room['south'], c, 'south')
                if sill:
                    sills.append(sill)
        
        if room['west'] >= 3:
            for r in range(room['north'], room['south'] + 1, 2):
                sill = self.check_sill(room, r, room['west'], 'west')
                if sill:
                    sills.append(sill)
        
        if room['east'] <= self.opts['n_cols'] - 3:
            for r in range(room['north'], room['south'] + 1, 2):
                sill = self.check_sill(room, r, room['east'], 'east')
                if sill:
                    sills.append(sill)

        return self.shuffle(sills)
    
    def check_sill(self, room, sill_r, sill_c, dir):
        door_r = sill_r + self.di[dir]
        door_c = sill_c + self.dj[dir]
        
        if door_r < 0 or door_r > self.opts['n_rows'] or door_c < 0 or door_c > self.opts['n_cols']:
            return None
        if not (self.cell[door_r][door_c] & self.PERIMETER):
            return None

        # NEW: Check if door is at the edge of round layout
        center_r = self.opts['n_rows'] // 2
        center_c = self.opts['n_cols'] // 2
        radius = min(center_r, center_c) - 2
        door_dist = math.sqrt((door_r - center_r) ** 2 + (door_c - center_c) ** 2)
        
        # Reject doors too close to edge
        if door_dist > radius * 0.95:
            return None
        
        out_r = door_r + self.di[dir]
        out_c = door_c + self.dj[dir]
        
        if out_r < 0 or out_r > self.opts['n_rows'] or out_c < 0 or out_c > self.opts['n_cols']:
            return None

        # NEW: Reject if cell beyond door is blocked
        if self.cell[out_r][out_c] & self.BLOCKED:
            return None
            
        out_id = None
        if self.cell[out_r][out_c] & self.ROOM:
            out_id = (self.cell[out_r][out_c] & self.ROOM_ID) >> 6
            if out_id == room['id']:
                return None
        
        return {
            'sill_r': sill_r,
            'sill_c': sill_c,
            'dir': dir,
            'door_r': door_r,
            'door_c': door_c,
            'out_id': out_id
        }
    
    def door_type(self):
        r = self.rand_int(110)
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
        for room_id in range(1, self.n_rooms + 1):
            room = self.room[room_id]
            label = str(room_id)
            length = len(label)
            label_r = (room['north'] + room['south']) // 2
            label_c = (room['west'] + room['east'] - length) // 2 + 1
            
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
    
    def tunnel(self, i, j, last_dir=None, depth=0):
        if depth > 1000:  # Prevent infinite recursion
            return
        
        dirs = self.tunnel_dirs(last_dir)
        for dir in dirs:
            if self.open_tunnel(i, j, dir):
                next_i = i + self.di[dir]
                next_j = j + self.dj[dir]
                self.tunnel(next_i, next_j, dir, depth+1)
    
    def tunnel_dirs(self, last_dir):
        dirs = self.dj_dirs.copy()
        self.shuffle(dirs)
        p = self.corridor_layout.get(self.opts['corridor_layout'], 0)
        
        if last_dir and p and self.rand_int(100) < p:
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
        if (next_r < 0 or next_r > self.opts['n_rows'] or 
            next_c < 0 or next_c > self.opts['n_cols']):
            return False
        
        r1 = min(mid_r, next_r)
        r2 = max(mid_r, next_r)
        c1 = min(mid_c, next_c)
        c2 = max(mid_c, next_c)
        
        for r in range(int(r1), int(r2) + 1):
            for c in range(int(c1), int(c2) + 1):
                # FIXED: Check for permanent blocks and existing corridors
                if self.cell[r][c] & (self.BLOCKED | self.CORRIDOR):
                    return False
        return True
    
    def delve_tunnel(self, r1, c1, r2, c2):
        min_r = min(r1, r2)
        max_r = max(r1, r2)
        min_c = min(c1, c2)
        max_c = max(c1, c2)
        
        for r in range(int(min_r), int(max_r) + 1):
            for c in range(int(min_c), int(max_c) + 1):
                # FIXED: Preserve existing doors
                if not (self.cell[r][c] & self.DOORSPACE):
                    self.cell[r][c] &= ~self.ENTRANCE
                    self.cell[r][c] |= self.CORRIDOR
        return True
    
    def emplace_stairs(self):
        n = self.opts['add_stairs']
        if not n:
            return
        
        ends = self.stair_ends()
        if not ends:
            return
        
        for i in range(n):
            if not ends:
                break
            
            idx = self.rand_int(len(ends))
            end = ends.pop(idx)
            r = end['row']
            c = end['col']
            stair = {**end}
            
            if i < 2:
                stair_type = i
            else:
                stair_type = self.rand_int(2)
            
            if stair_type == 0:
                self.cell[r][c] |= self.STAIR_DN
                stair['key'] = 'down'
            else:
                self.cell[r][c] |= self.STAIR_UP
                stair['key'] = 'up'
            
            self.stairs.append(stair)
    
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
                        next = config['next']
                        ends.append({
                            'row': r, 
                            'col': c,
                            'next_row': r + next[0],
                            'next_col': c + next[1]
                        })
                        break
        return ends
    
    def clean_dungeon(self):
        if self.opts['remove_deadends']:
            self.remove_deadends()
        self.clean_disconnected_doors()
        self.fix_doors()
        self.empty_blocks()
    
    def remove_deadends(self):
        p = self.opts['remove_deadends']
        if not p:
            return
        all = p == 100
        
        for i in range(self.n_i):
            r = (i * 2) + 1
            for j in range(self.n_j):
                c = (j * 2) + 1
                if not (self.cell[r][c] & self.OPENSPACE):
                    continue
                if self.cell[r][c] & self.STAIRS:
                    continue
                if not all and self.rand_int(100) >= p:
                    continue
                if self.is_adjacent_to_door(r, c):
                    continue
                if self.corridor_leads_to_door(r, c):
                    continue
                
                self.collapse(r, c, self.close_end)
    
    def corridor_leads_to_door(self, r, c):
        if not (self.cell[r][c] & self.CORRIDOR):
            return False
        
        neighbors = [
            (0, -1), (0, 1), (-1, 0), (1, 0)  # west, east, north, south
        ]
        
        for dr, dc in neighbors:
            nr = r + dr
            nc = c + dc
            if (0 <= nr <= self.opts['n_rows'] and 
                0 <= nc <= self.opts['n_cols'] and
                self.cell[nr][nc] & self.DOORSPACE):
                return True
        return False
    
    def clean_disconnected_doors(self):
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & self.DOORSPACE:
                    connected_spaces = 0
                    neighbors = [
                        (0, -1), (0, 1), (-1, 0), (1, 0)  # west, east, north, south
                    ]
                    
                    for dr, dc in neighbors:
                        nr = r + dr
                        nc = c + dc
                        if (0 <= nr <= self.opts['n_rows'] and 
                            0 <= nc <= self.opts['n_cols'] and
                            self.cell[nr][nc] & (self.OPENSPACE | self.DOORSPACE)):
                            connected_spaces += 1
                    
                    if connected_spaces < 2:
                        self.cell[r][c] &= ~self.DOORSPACE
                        self.cell[r][c] |= self.PERIMETER
    
    def collapse(self, r, c, xc):
        if not (self.cell[r][c] & self.OPENSPACE):
            return
        
        for dir, check in xc.items():
            if not self.check_tunnel(self.cell, r, c, check):
                continue
            
            for p in check['close']:
                self.cell[r + p[0]][c + p[1]] = self.NOTHING
            
            if 'recurse' in check:
                recurse = check['recurse']
                self.collapse(r + recurse[0], c + recurse[1], xc)
    
    def check_tunnel(self, cell, r, c, check):
        if 'corridor' in check:
            for p in check['corridor']:
                nr = r + p[0]
                nc = c + p[1]
                if cell[nr][nc] != self.CORRIDOR:
                    return False
        
        if 'walled' in check:
            for p in check['walled']:
                nr = r + p[0]
                nc = c + p[1]
                if cell[nr][nc] & self.OPENSPACE:
                    return False
        
        return True
    
    def fix_doors(self):
        fixed = [
            [False] * (self.opts['n_cols'] + 1) 
            for _ in range(self.opts['n_rows'] + 1)
        ]
        self.doorList = []
        
        for room_id in range(1, self.n_rooms + 1):
            room = self.room[room_id]
            for dir, doors in list(room['door'].items()):
                shiny = []
                for door in doors:
                    r = door['row']
                    c = door['col']
                    if not (self.cell[r][c] & self.OPENSPACE):
                        continue
                    if fixed[r][c]:
                        shiny.append(door)
                        continue
                    
                    fixed[r][c] = True
                    if 'out_id' in door:
                        out_dir = self.opposite[dir]
                        out_room = self.room[door['out_id']]
                        if out_dir not in out_room['door']:
                            out_room['door'][out_dir] = []
                        out_room['door'][out_dir].append(door)
                    shiny.append(door)
                    self.doorList.append(door)
                
                if shiny:
                    room['door'][dir] = shiny
                else:
                    del room['door'][dir]
    
    def empty_blocks(self):
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & self.BLOCKED:
                    self.cell[r][c] = self.NOTHING
    
    def is_adjacent_to_door(self, r, c):
        neighbors = [
            (0, -1), (0, 1), (-1, 0), (1, 0)  # west, east, north, south
        ]
        
        for dr, dc in neighbors:
            nr = r + dr
            nc = c + dc
            if (0 <= nr <= self.opts['n_rows'] and 
                0 <= nc <= self.opts['n_cols'] and
                self.cell[nr][nc] & self.DOORSPACE):
                return True
        return False
    
    def has_open_space(self, r, c):
        if r < 0 or r > self.opts['n_rows'] or c < 0 or c > self.opts['n_cols']:
            return False
        return bool(self.cell[r][c] & self.OPENSPACE)
    
    def get_door_orientation(self, r, c):
        horizontal = self._is_horizontal_door(r, c)
        vertical = self._is_vertical_door(r, c)
        
        if horizontal and not vertical:
            return 'horizontal'
        if vertical and not horizontal:
            return 'vertical'
        return 'horizontal'
    
    def _is_horizontal_door(self, r, c):
        return (self.has_open_space(r, c-1) and 
                self.has_open_space(r, c+1))
    
    def _is_vertical_door(self, r, c):
        return (self.has_open_space(r-1, c) and 
                self.has_open_space(r+1, c))
    
    def get_door_type(self, cell):
        if cell & self.ARCH:
            return 'arch'
        if cell & self.DOOR:
            return 'open'
        if cell & self.LOCKED:
            return 'lock'
        if cell & self.TRAPPED:
            return 'trap'
        if cell & self.SECRET:
            return 'secret'
        if cell & self.PORTC:
            return 'portc'
        return 'open'

    def get_stats(self):
        rooms = 0
        doors = 0
        corridors = 0
        
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                cell = self.cell[r][c]
                if cell & self.ROOM: rooms += 1
                if cell & self.DOORSPACE: doors += 1
                if cell & self.CORRIDOR: corridors += 1
        
        return {
            'rooms': self.n_rooms,
            'doors': doors,
            'corridors': corridors,
            'size': f"{self.opts['n_rows']}x{self.opts['n_cols']}"
        }

    def generate_png(self):
        cell_size = self.opts['cell_size']
        width = (self.opts['n_cols'] + 1) * cell_size + 1
        height = (self.opts['n_rows'] + 1) * cell_size + 1

        ROOM_COLOR = '#ffffff'  # Eggshell
        CORRIDOR_COLOR = '#d3d3d3'  # Light gray
        DOOR_COLOR = '#8B4513'
        ARCH_COLOR = '#A07828'
        STAIR_COLOR = '#111111'
        
        # Create image with dark background
        img = Image.new('RGB', (width, height), color='#5f5e67')
        draw = ImageDraw.Draw(img)
        
        # Draw corridors
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & self.CORRIDOR:
                    x = c * cell_size
                    y = r * cell_size
                    draw.rectangle([x, y, x+cell_size, y+cell_size], fill=CORRIDOR_COLOR)
                elif self.cell[r][c] & self.ENTRANCE:
                    x = c * cell_size
                    y = r * cell_size
                    draw.rectangle([x, y, x+cell_size, y+cell_size], fill=CORRIDOR_COLOR)
        
        # Draw rooms
        for room_id in range(1, self.n_rooms + 1):
            room = self.room[room_id]
            if room:
                x1 = room['west'] * cell_size
                y1 = room['north'] * cell_size
                x2 = (room['east'] + 1) * cell_size
                y2 = (room['south'] + 1) * cell_size
                
                draw.rectangle([x1, y1, x2, y2], fill=ROOM_COLOR)
                
                # Room label
                try:
                    font = ImageFont.truetype("arial.ttf", int(cell_size * 0.8))
                except:
                    font = ImageFont.load_default()
                text = str(room_id)

                bbox = font.getbbox(text)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                tx = x1 + (x2 - x1 - text_width) // 2
                ty = y1 + (y2 - y1 - text_height) // 2
                draw.text((tx, ty), text, fill='#2c3e50', font=font)

        # Unified door drawing function
        def draw_door(draw, x, y, cell_size, door_type, orientation, is_legend=False):
            door_color = '#8B4513'
            arch_color = '#A07828'
            door_width = cell_size // 3
            arch_height = cell_size // 6
            
            if is_legend:
                bg_color = CORRIDOR_COLOR
                draw.rectangle([x, y, x+cell_size, y+cell_size], fill=bg_color)
            
            if door_type != 'arch':
                if orientation == 'horizontal':
                    draw.rectangle([
                        x + (cell_size - door_width)//2, y,
                        x + (cell_size + door_width)//2, y + arch_height
                    ], fill=arch_color)
                    draw.rectangle([
                        x + (cell_size - door_width)//2, y + cell_size - arch_height,
                        x + (cell_size + door_width)//2, y + cell_size
                    ], fill=arch_color)
                else:
                    draw.rectangle([
                        x, y + (cell_size - door_width)//2,
                        x + arch_height, y + (cell_size + door_width)//2
                    ], fill=arch_color)
                    draw.rectangle([
                        x + cell_size - arch_height, y + (cell_size - door_width)//2,
                        x + cell_size, y + (cell_size + door_width)//2
                    ], fill=arch_color)
            
            if door_type in ['door', 'lock', 'trap']:
                if orientation == 'horizontal':
                    draw.rectangle([
                        x + (cell_size - door_width)//2, y + arch_height,
                        x + (cell_size + door_width)//2, y + cell_size - arch_height
                    ], fill=door_color)
                else:
                    draw.rectangle([
                        x + arch_height, y + (cell_size - door_width)//2,
                        x + cell_size - arch_height, y + (cell_size + door_width)//2
                    ], fill=door_color)
                
                if door_type == 'lock':
                    lock_size = cell_size // 6
                    center_x = x + cell_size // 2
                    center_y = y + cell_size // 2
                    diamond = [
                        (center_x, center_y - lock_size//2),
                        (center_x + lock_size//2, center_y),
                        (center_x, center_y + lock_size//2),
                        (center_x - lock_size//2, center_y)
                    ]
                    draw.polygon(diamond, fill='#ffffff')
            
            elif door_type == 'arch':
                pass
            
            elif door_type == 'secret':
                pass

            elif door_type == 'door_open':
                door_width = cell_size // 3
                door_length = cell_size * 2 // 3
                sin60 = 0.866
                cos60 = 0.5
                
                if orientation == 'horizontal':
                    hinge_x = x + cell_size // 2
                    hinge_y = y + arch_height
                    unrotated = [
                        (hinge_x - door_width//2, hinge_y),
                        (hinge_x + door_width//2, hinge_y),
                        (hinge_x + door_width//2, hinge_y + door_length),
                        (hinge_x - door_width//2, hinge_y + door_length)
                    ]
                    rotated = []
                    for px, py in unrotated:
                        tx = px - hinge_x
                        ty = py - hinge_y
                        rx = tx * cos60 + ty * sin60
                        ry = -tx * sin60 + ty * cos60
                        rotated.append((int(hinge_x + rx), int(hinge_y + ry)))
                    draw.polygon(rotated, fill=door_color)
                else:
                    hinge_x = x + arch_height
                    hinge_y = y + cell_size // 2
                    unrotated = [
                        (hinge_x, hinge_y - door_width//2),
                        (hinge_x, hinge_y + door_width//2),
                        (hinge_x + door_length, hinge_y + door_width//2),
                        (hinge_x + door_length, hinge_y - door_width//2)
                    ]
                    rotated = []
                    for px, py in unrotated:
                        tx = px - hinge_x
                        ty = py - hinge_y
                        rx = tx * cos60 + ty * sin60
                        ry = -tx * sin60 + ty * cos60
                        rotated.append((int(hinge_x + rx), int(hinge_y + ry)))
                    draw.polygon(rotated, fill=door_color)
            
            elif door_type == 'door_broken':
                plank_width = max(1, cell_size // 6)
                offset = cell_size // 4
                offset2 = cell_size // 6
                draw.line([
                    (x + offset, y + offset2),
                    (x + cell_size//2 - offset2, y + cell_size - offset2)
                ], fill=door_color, width=plank_width)
                draw.line([
                    (x + cell_size - offset2, y + offset),
                    (x + offset2, y + cell_size - offset)
                ], fill=door_color, width=plank_width)
                    
            elif door_type == 'portc':
                bar_count = 5
                bar_radius = max(1, cell_size // 20)
                bar_spacing = cell_size / (bar_count + 1)
                if orientation == 'horizontal':
                    for i in range(1, bar_count + 1):
                        bar_y = y + i * bar_spacing
                        draw.ellipse([
                            x + cell_size//2 - bar_radius, bar_y - bar_radius,
                            x + cell_size//2 + bar_radius, bar_y + bar_radius
                        ], fill=door_color)
                else:
                    for i in range(1, bar_count + 1):
                        bar_x = x + i * bar_spacing
                        draw.ellipse([
                            bar_x - bar_radius, y + cell_size//2 - bar_radius,
                            bar_x + bar_radius, y + cell_size//2 + bar_radius
                        ], fill=door_color)

            elif door_type == 'portc_open':
                bar_radius = max(1, cell_size // 20)
                if orientation == 'horizontal':
                    for i in range(1, 4):
                        bar_x = x + i * cell_size // 4
                        draw.ellipse([
                            bar_x - bar_radius, y + bar_radius,
                            bar_x + bar_radius, y + 3 * bar_radius
                        ], fill=door_color)
                        draw.ellipse([
                            bar_x - bar_radius, y + cell_size - 3 * bar_radius,
                            bar_x + bar_radius, y + cell_size - bar_radius
                        ], fill=door_color)
                else:
                    for i in range(1, 4):
                        bar_y = y + i * cell_size // 4
                        draw.ellipse([
                            x + bar_radius, bar_y - bar_radius,
                            x + 3 * bar_radius, bar_y + bar_radius
                        ], fill=door_color)
                        draw.ellipse([
                            x + cell_size - 3 * bar_radius, bar_y - bar_radius,
                            x + cell_size - bar_radius, bar_y + bar_radius
                        ], fill=door_color)

            elif door_type == 'portc_broken':
                bar_count = 3
                bar_radius = max(1, cell_size // 20)
                bar_spacing = cell_size / (bar_count + 1)
                if orientation == 'horizontal':
                    for i in range(1, bar_count + 1):
                        bar_y = y + i * bar_spacing
                        draw.ellipse([
                            x + cell_size//2 - bar_radius, bar_y - bar_radius,
                            x + cell_size//2 + bar_radius, bar_y + bar_radius
                        ], fill=door_color)
                else:
                    for i in range(1, bar_count + 1):
                        bar_x = x + i * bar_spacing
                        draw.ellipse([
                            bar_x - bar_radius, y + cell_size//2 - bar_radius,
                            bar_x + bar_radius, y + cell_size//2 + bar_radius
                        ], fill=door_color)

        # Draw doors AFTER rooms (FIXED rendering order)
        for door in self.doorList:
            r, c = door['row'], door['col']
            x = c * cell_size
            y = r * cell_size
            orientation = 'horizontal' if self._is_horizontal_door(r, c) else 'vertical'
            draw_door(draw, x, y, cell_size, door['key'], orientation)

        # Draw stairs (improved with tapering for down stairs)
        def draw_stairs(draw, x, y, cell_size, stair_type, orientation):
            step_count = 4
            spacing = cell_size / (step_count + 1)
            max_length = cell_size * 0.8
            min_length = cell_size * 0.2
            center_x = x + cell_size // 2
            center_y = y + cell_size // 2
            
            if orientation == 'horizontal':
                for i in range(1, step_count + 1):
                    length = max_length
                    if stair_type == 'down':
                        length = max_length - (max_length - min_length) * (i-1) / (step_count-1)
                    x_pos = x + i * spacing
                    draw.line([
                        x_pos, center_y - length//2,
                        x_pos, center_y + length//2
                    ], fill=STAIR_COLOR, width=1)
            else:
                for i in range(1, step_count + 1):
                    length = max_length
                    if stair_type == 'down':
                        length = max_length - (max_length - min_length) * (i-1) / (step_count-1)
                    y_pos = y + i * spacing
                    draw.line([
                        center_x - length//2, y_pos,
                        center_x + length//2, y_pos
                    ], fill=STAIR_COLOR, width=1)
        
        # Draw stairs in dungeon
        for stair in self.stairs:
            r, c = stair['row'], stair['col']
            x = c * cell_size
            y = r * cell_size
            dr = stair['next_row'] - r
            orientation = 'vertical' if dr != 0 else 'horizontal'
            draw_stairs(draw, x, y, cell_size, stair['key'], orientation)

        # Draw grid
        GRID_COLOR = '#000000'
        for r in range(0, self.opts['n_rows'] + 1):
            y = r * cell_size
            if y <= height:
                draw.line([(0, y), (width, y)], fill=GRID_COLOR, width=1)
        for c in range(0, self.opts['n_cols'] + 1):
            x = c * cell_size
            if x <= width:
                draw.line([(x, 0), (x, height)], fill=GRID_COLOR, width=1)
        
        # Generate legend
        legend_width = 200
        total_width = width + legend_width
        total_height = max(height, 600)
        composite = Image.new('RGB', (total_width, total_height), color='#3a3a3a')
        composite.paste(img, (0, 0))
        legend_draw = ImageDraw.Draw(composite)
        legend_x = width + 10
        legend_y = 10
        icon_size = 20
        spacing = 10
        font = ImageFont.load_default()
        legend_draw.text((legend_x, legend_y), "Dungeon Features Legend", fill='white', font=font)
        legend_y += 25
        
        items = [
            {'name': 'Room', 'draw': lambda d, x, y: d.rectangle([x, y, x+icon_size, y+icon_size], fill=ROOM_COLOR)},
            {'name': 'Corridor', 'draw': lambda d, x, y: d.rectangle([x, y, x+icon_size, y+icon_size], fill=CORRIDOR_COLOR)},
            {'name': 'Closed Door', 'draw': lambda d, x, y: draw_door(d, x, y, icon_size, 'door', 'horizontal', True)},
            {'name': 'Open Door', 'draw': lambda d, x, y: draw_door(d, x, y, icon_size, 'door_open', 'horizontal', True)},
            {'name': 'Broken Door', 'draw': lambda d, x, y: draw_door(d, x, y, icon_size, 'door_broken', 'horizontal', True)},
            {'name': 'Locked Door', 'draw': lambda d, x, y: draw_door(d, x, y, icon_size, 'lock', 'horizontal', True)},
            {'name': 'Trapped Door', 'draw': lambda d, x, y: draw_door(d, x, y, icon_size, 'trap', 'horizontal', True)},
            {'name': 'Portcullis', 'draw': lambda d, x, y: draw_door(d, x, y, icon_size, 'portc', 'horizontal', True)},
            {'name': 'Open Portcullis', 'draw': lambda d, x, y: draw_door(d, x, y, icon_size, 'portc_open', 'horizontal', True)},
            {'name': 'Broken Portcullis', 'draw': lambda d, x, y: draw_door(d, x, y, icon_size, 'portc_broken', 'horizontal', True)},
            {'name': 'Stairs Up', 'draw': lambda d, x, y: 
                (d.rectangle([x, y, x+icon_size, y+icon_size], fill=CORRIDOR_COLOR),
                 draw_stairs(d, x, y, icon_size, 'up', 'vertical'))},
            {'name': 'Stairs Down', 'draw': lambda d, x, y: 
                (d.rectangle([x, y, x+icon_size, y+icon_size], fill=CORRIDOR_COLOR),
                 draw_stairs(d, x, y, icon_size, 'down', 'vertical'))}
        ]
        
        for i, item in enumerate(items):
            y_pos = legend_y + i * (icon_size + spacing)
            item['draw'](legend_draw, legend_x, y_pos)
            legend_draw.text((legend_x + icon_size + 10, y_pos + icon_size//2), 
                           item['name'], fill='white', anchor='lm', font=font)
        
        # Save to BytesIO
        img_io = io.BytesIO()
        composite.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io.getvalue()
