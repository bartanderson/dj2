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
        
        self.OPENSPACE = self.ROOM | self.CORRIDOR | self.ENTRANCE
        self.DOORSPACE = self.ARCH | self.DOOR | self.LOCKED | self.TRAPPED | self.SECRET | self.PORTC
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
            for c in range(self.opts['n_cols'] + 1):
                mask_row = int(r * r_x)
                mask_col = int(c * c_x)
                if mask_row < len(mask) and mask_col < len(mask[0]) and not mask[mask_row][mask_col]:
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
        
        # Mark perimeter as blocked to prevent adjacent rooms
        for r in range(r1 - 1, r2 + 2):
            if r < 0 or r > self.opts['n_rows']:
                continue
            for c in [c1 - 1, c2 + 1]:
                if 0 <= c <= self.opts['n_cols']:
                    self.cell[r][c] |= self.BLOCKED | self.PERIMETER 
        
        for c in range(c1 - 1, c2 + 2):
            if c < 0 or c > self.opts['n_cols']:
                continue
            for r in [r1 - 1, r2 + 1]:
                if 0 <= r <= self.opts['n_rows']:
                    self.cell[r][c] |= self.BLOCKED | self.PERIMETER 
    
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
            
            if self.cell[door_r][door_c] & self.DOORSPACE:
                continue
            
            if sill['out_id']:
                connect_key = ','.join(map(str, sorted([room['id'], sill['out_id']])))
                if connect_key in self.connect:
                    continue
                self.connect[connect_key] = True
            
            open_dir = sill['dir']
            for x in range(3):
                r = sill['sill_r'] + (self.di[open_dir] * x)
                c = sill['sill_c'] + (self.dj[open_dir] * x)
                self.cell[r][c] &= ~(self.PERIMETER | self.BLOCKED)
                self.cell[r][c] |= self.ENTRANCE
            
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
            
            self.cell[door_r][door_c] |= door_bits
            
            if sill['out_id']:
                door['out_id'] = sill['out_id']
            
            if open_dir not in room['door']:
                room['door'][open_dir] = []
            room['door'][open_dir].append(door)
    
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
        if self.cell[door_r][door_c] & self.DOORSPACE:
            return None
        
        out_r = door_r + self.di[dir]
        out_c = door_c + self.dj[dir]
        
        if out_r < 0 or out_r > self.opts['n_rows'] or out_c < 0 or out_c > self.opts['n_cols']:
            return None
        # if self.cell[out_r][out_c] & self.BLOCKED:
        #     return None
        
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
    
    def tunnel(self, i, j, last_dir=None):
        dirs = self.tunnel_dirs(last_dir)
        for dir in dirs:
            if self.open_tunnel(i, j, dir):
                next_i = i + self.di[dir]
                next_j = j + self.dj[dir]
                self.tunnel(next_i, next_j, dir)
    
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
                if self.cell[r][c] & self.BLOCK_CORR:
                    return False
        return True
    
    def delve_tunnel(self, r1, c1, r2, c2):
        min_r = min(r1, r2)
        max_r = max(r1, r2)
        min_c = min(c1, c2)
        max_c = max(c1, c2)
        
        for r in range(int(min_r), int(max_r) + 1):
            for c in range(int(min_c), int(max_c) + 1):
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
        width = (self.opts['n_cols'] + 1) * cell_size
        height = (self.opts['n_rows'] + 1) * cell_size
        
        # Create image with dark background
        img = Image.new('RGB', (width, height), color='#1a1f25')
        draw = ImageDraw.Draw(img)
        
        # Draw corridors
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & self.CORRIDOR:
                    x = c * cell_size
                    y = r * cell_size
                    draw.rectangle([x, y, x+cell_size, y+cell_size], fill='#3498db')
        
        # Draw rooms
        for room_id in range(1, self.n_rooms + 1):
            room = self.room[room_id]
            if room:
                x1 = room['west'] * cell_size
                y1 = room['north'] * cell_size
                x2 = (room['east'] + 1) * cell_size
                y2 = (room['south'] + 1) * cell_size
                
                # Room background
                draw.rectangle([x1, y1, x2, y2], fill='#f1c40f')
                
                # Room border
                draw.rectangle([x1, y1, x2, y2], outline='#e67e22', width=2)
                
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
        
        # Draw doors
        for door in self.doorList:
            r, c = door['row'], door['col']
            door_type = door.get('key', 'open')
            x = c * cell_size
            y = r * cell_size
            center_x = x + cell_size // 2
            center_y = y + cell_size // 2
            
            color = '#ffffff' #'#8B4513'
            # Determine orientation
            horizontal = self._is_horizontal_door(r, c)
            
            draw.rectangle([x, y, x+cell_size, y+cell_size], fill=color)

            # Draw door base
            if horizontal:
                draw.line([(x, center_y), (x + cell_size, center_y)], fill=color, width=3)
            else:
                draw.line([(center_x, y), (center_x, y + cell_size)], fill=color, width=3)
            
            # Draw door symbol
            symbols = {'lock': '🔒', 'trap': '⚠️', 'secret': '❓'}
            if door_type in symbols:
                try:
                    symbol = symbols[door_type]
                    symbol_font = ImageFont.truetype("seguiemj.ttf", int(cell_size * 0.8))
                    draw.text((center_x, center_y), symbol, fill='white', font=symbol_font, anchor='mm')
                except:
                    pass
        
        # Draw stairs
        for stair in self.stairs:
            r, c = stair['row'], stair['col']
            stair_type = stair.get('key', 'down')
            x = c * cell_size
            y = r * cell_size
            center_x = x + cell_size // 2
            center_y = y + cell_size // 2
            
            # Stair background
            color = '#9b59b6' if stair_type == 'up' else '#8e44ad'
            draw.rectangle([x, y, x+cell_size, y+cell_size], fill=color)
            
            # Stair symbol
            symbol = '▲' if stair_type == 'up' else '▼'
            try:
                font = ImageFont.truetype("arial.ttf", int(cell_size * 0.8))
                draw.text((center_x, center_y), symbol, fill='white', font=font, anchor='mm')
            except:
                pass
        
        # Draw grid # squeezed the cell size to get rigth and bottom edges drawn.. another way?
        for r in range(0, self.opts['n_rows'] + 2):
            y = r * (cell_size - .001)
            draw.line([(0, y), (width, y)], fill='rgb(255,255,255)', width=1)
        for c in range(0, self.opts['n_cols'] + 2):
            x = c * (cell_size - .001)
            draw.line([(x, 0), (x, height)], fill='rgb(255,255,255)', width=1)
        
        # Save to BytesIO
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io.getvalue()