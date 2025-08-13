import random
import math
from PIL import Image, ImageDraw

class DungeonGenerator:
    # Cell bit flags
    NOTHING     = 0x00000000
    BLOCKED     = 0x00000001
    ROOM        = 0x00000002
    CORRIDOR    = 0x00000004
    PERIMETER   = 0x00000010
    ENTRANCE    = 0x00000020
    ROOM_ID     = 0x0000FFC0
    ARCH        = 0x00010000
    DOOR        = 0x00020000
    LOCKED      = 0x00040000
    TRAPPED     = 0x00080000
    SECRET      = 0x00100000
    PORTC       = 0x00200000
    STAIR_DN    = 0x00400000
    STAIR_UP    = 0x00800000
    LABEL       = 0xFF000000

    OPENSPACE   = ROOM | CORRIDOR
    DOORSPACE   = ARCH | DOOR | LOCKED | TRAPPED | SECRET | PORTC
    ESPACE      = ENTRANCE | DOORSPACE | 0xFF000000
    STAIRS      = STAIR_DN | STAIR_UP
    BLOCK_ROOM  = BLOCKED | ROOM
    BLOCK_CORR  = BLOCKED | PERIMETER | CORRIDOR
    BLOCK_DOOR  = BLOCKED | DOORSPACE

    def __init__(self, options=None):
        self.opts = {
            'seed': 'None',
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
            'grid': 'Square'
        }
        
        if options:
            self.opts.update(options)

        print (self.opts['seed'])
            
        if self.opts['seed'] is None:
            self.opts['seed'] = random.randint(1, 100000)
            
        self.rand = random.Random(self.opts['seed'])
        
        # Direction vectors
        self.di = {'north': -1, 'south': 1, 'west': 0, 'east': 0}
        self.dj = {'north': 0, 'south': 0, 'west': -1, 'east': 1}
        self.dj_dirs = list(self.dj.keys())
        self.opposite = {
            'north': 'south', 'south': 'north',
            'west': 'east', 'east': 'west'
        }
        
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
        
        # Initialize dungeon structures
        self.cell = None
        self.room = []
        self.doorList = []
        self.stairs = []
        self.n_rooms = 0
        self.last_room_id = 0

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
        
        max_size = self.opts['room_max']
        min_size = self.opts['room_min']
        self.room_base = (min_size + 1) // 2
        self.room_radix = (max_size - min_size) // 2 + 1

    def init_cells(self):
        self.cell = [
            [self.NOTHING] * (self.opts['n_cols'] + 1)
            for _ in range(self.opts['n_rows'] + 1)
        ]
        
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
                    self.cell[r][c1 - 1] |= self.PERIMETER
                if not (self.cell[r][c2 + 1] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r][c2 + 1] |= self.PERIMETER
        
        for c in range(c1 - 1, c2 + 2):
            if c <= self.max_col:
                if not (self.cell[r1 - 1][c] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r1 - 1][c] |= self.PERIMETER
                if not (self.cell[r2 + 1][c] & (self.ROOM | self.ENTRANCE)):
                    self.cell[r2 + 1][c] |= self.PERIMETER

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
        sills = self.door_sills(room)
        if not sills:
            return
        
        n_opens = self.alloc_opens(room)
        if not hasattr(self, 'connect'):
            self.connect = {}
        
        for _ in range(n_opens):
            if not sills:
                break
            
            idx = self.rand.randint(0, len(sills) - 1)
            sill = sills.pop(idx)
            door_r = sill['door_r']
            door_c = sill['door_c']
            
            if self.cell[door_r][door_c] & self.DOORSPACE:
                continue
            
            if 'out_id' in sill and sill['out_id'] is not None:
                connect_key = ','.join(map(str, sorted([room['id'], sill['out_id']])))
                if connect_key in self.connect:
                    continue
                self.connect[connect_key] = True
            
            open_dir = sill['dir']
            for x in range(3):
                r = sill['sill_r'] + self.di[open_dir] * x
                c = sill['sill_c'] + self.dj[open_dir] * x
                self.cell[r][c] &= ~self.PERIMETER
                self.cell[r][c] |= self.ENTRANCE
            
            door_type = self.door_type()
            door = {'row': door_r, 'col': door_c}
            
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
            
            if open_dir not in room['door']:
                room['door'][open_dir] = []
            room['door'][open_dir].append(door)

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
        
        self.shuffle(sills)
        return sills

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
                r, c = end['row'], end['col']
                self.cell[r][c] |= self.STAIR_DN
                end['key'] = 'down'
                self.stairs.append(end)
            
            # Second stair: up
            if ends:
                end = ends.pop(0)
                r, c = end['row'], end['col']
                self.cell[r][c] |= self.STAIR_UP
                end['key'] = 'up'
                self.stairs.append(end)
        else:
            for i in range(n):
                if not ends:
                    break
                end = ends.pop(0)
                r, c = end['row'], end['col']
                
                # For n != 2, maintain existing random behavior
                stair_type = i if i < 2 else random.randint(0, 1)
                
                if stair_type == 0:
                    self.cell[r][c] |= self.STAIR_DN
                    end['key'] = 'down'
                else:
                    self.cell[r][c] |= self.STAIR_UP
                    end['key'] = 'up'
                
                self.stairs.append(end)
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
                        next_pos = config['next']
                        end = {
                            'row': r, 'col': c,
                            'next_row': r + next_pos[0],
                            'next_col': c + next_pos[1]
                        }
                        ends.append(end)
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
        all = (p == 100)
        
        for i in range(self.n_i):
            r = (i * 2) + 1
            for j in range(self.n_j):
                c = (j * 2) + 1
                if not (self.cell[r][c] & self.OPENSPACE):
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
                            if self.cell[nr][nc] & (self.OPENSPACE | self.DOORSPACE):
                                connected += 1
                    if connected < 2:
                        self.cell[r][c] &= ~self.DOORSPACE
                        self.cell[r][c] |= self.PERIMETER

    def collapse(self, r, c, xc):
        if not (self.cell[r][c] & self.OPENSPACE):
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
                if cell[nr][nc] & self.OPENSPACE:
                    return False
        return True

    def fix_doors(self):
        fixed = [[False] * (self.opts['n_cols'] + 1) for _ in range(self.opts['n_rows'] + 1)]
        self.doorList = []
        
        for room in self.room:
            for dir, doors in room['door'].items():
                shiny = []
                for door in doors:
                    r, c = door['row'], door['col']
                    if not (self.cell[r][c] & self.OPENSPACE):
                        continue
                    
                    if fixed[r][c]:
                        shiny.append(door)
                        continue
                    
                    fixed[r][c] = True
                    if 'out_id' in door and door['out_id'] is not None:
                        out_dir = self.opposite[dir]
                        out_room = self.room[door['out_id'] - 1]
                        if out_dir not in out_room['door']:
                            out_room['door'][out_dir] = []
                        out_room['door'][out_dir].append(door)
                    
                    shiny.append(door)
                    self.doorList.append(door)
                
                room['door'][dir] = shiny

    def empty_blocks(self):
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                if self.cell[r][c] & self.BLOCKED:
                    self.cell[r][c] = self.NOTHING

    def get_door_orientation(self, r, c):
        horizontal = (self.has_open_space(r, c - 1) and 
                     self.has_open_space(r, c + 1))
        vertical = (self.has_open_space(r - 1, c) and 
                   self.has_open_space(r + 1, c))
        
        if horizontal and not vertical:
            return 'horizontal'
        if vertical and not horizontal:
            return 'vertical'
        return 'horizontal'

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

    def has_open_space(self, r, c):
        if r < 0 or r > self.opts['n_rows'] or c < 0 or c > self.opts['n_cols']:
            return False
        return bool(self.cell[r][c] & self.OPENSPACE)

    def render_to_image(self):
        cell_size = self.opts['cell_size']
        width = (self.opts['n_cols'] + 1) * cell_size
        height = (self.opts['n_rows'] + 1) * cell_size
        
        img = Image.new('RGB', (width, height), color=(52, 73, 94))
        draw = ImageDraw.Draw(img)
        
        # Colors
        colors = {
            'WALL': (52, 73, 94),
            'OPEN': (255, 255, 255),
            'DOOR': (0, 0, 0),
            'STAIR': (0,0,0),
            'GRID': (200, 200, 200)
        }
        
        # Draw open spaces
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                cell = self.cell[r][c]
                x1 = c * cell_size
                y1 = r * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                
                if cell & (self.OPENSPACE | self.DOORSPACE):
                    draw.rectangle([x1, y1, x2, y2], fill=colors['OPEN'])
        
        # Draw grid
        for r in range(0, self.opts['n_rows'] + 2):
            y = r * cell_size
            draw.line([0, y, width, y], fill=colors['GRID'], width=1)
        for c in range(0, self.opts['n_cols'] + 2):
            x = c * cell_size
            draw.line([x, 0, x, height], fill=colors['GRID'], width=1)
        
        # Draw doors
        for r in range(self.opts['n_rows'] + 1):
            for c in range(self.opts['n_cols'] + 1):
                cell = self.cell[r][c]
                x = c * cell_size
                y = r * cell_size
                
                if cell & self.DOORSPACE:
                    door_type = self.get_door_type(cell)
                    orientation = self.get_door_orientation(r, c)
                    self.draw_door(draw, x, y, cell_size, door_type, orientation)
                
                if cell & self.STAIRS:
                    stair = next((s for s in self.stairs if s['row'] == r and s['col'] == c), None)
                    if stair:
                        self.draw_stairs(draw, x, y, cell_size, stair)
                
                if cell & self.LABEL:
                    char = chr((cell >> 24) & 0xFF)
                    if char.isdigit():
                        draw.text(
                            (x + cell_size // 2, y + cell_size // 2),
                            char, fill=(0, 0, 0), anchor='mm'
                        )
        
        return img


    def draw_stairs(self, draw, x, y, cell_size, stair):
        step_count = 5
        max_length = cell_size * 0.8
        dx = stair['next_col'] - stair['col'] or 0
        dy = stair['next_row'] - stair['row'] or 0
        is_down = (stair['key'] == 'down')

        # Determine direction vector
        if abs(dx) > abs(dy):  # Horizontal
            center_y = y + cell_size // 2
            spacing = cell_size / (step_count + 1)
            
            for i in range(1, step_count + 1):
                if is_down:
                    # Down stairs: arrow pattern (tapered)
                    if dx > 0:  # Right-pointing
                        length = max_length * (i / step_count)
                    else:  # Left-pointing
                        length = max_length * ((step_count - i + 1) / step_count)
                else:
                    # Up stairs: parallel lines (equal length)
                    length = max_length 
                    
                x_pos = x + i * spacing
                draw.line([x_pos, center_y - length//2, x_pos, center_y + length//2], 
                         fill=(0,0,0), width=1)
        else:  # Vertical
            center_x = x + cell_size // 2
            spacing = cell_size / (step_count + 1)
            
            for i in range(1, step_count + 1):
                if is_down:
                    # Down stairs: arrow pattern (tapered)
                    if dy > 0:  # Down-pointing
                        length = max_length * (i / step_count)
                    else:  # Up-pointing
                        length = max_length * ((step_count - i + 1) / step_count)
                else:
                    # Up stairs: parallel lines (equal length)
                    length = max_length 
                    
                y_pos = y + i * spacing
                draw.line([center_x - length//2, y_pos, center_x + length//2, y_pos], 
                         fill=(0,0,0), width=1)

    def draw_door(self, draw, x, y, cell_size, door_type, orientation):
        is_horizontal = (orientation == 'horizontal')
        center_x = x + cell_size // 2
        center_y = y + cell_size // 2
        door_width = cell_size // 3
        arch_width = cell_size // 6
        symbol_size = cell_size // 6

        # Draw arch (common to several door types)
        if door_type in ['arch', 'open', 'lock', 'trap', 'portc']:
            if is_horizontal:
                draw.rectangle([center_x - door_width//2, y, center_x + door_width//2, y + arch_width], outline='black')
                draw.rectangle([center_x - door_width//2, y + cell_size - arch_width, center_x + door_width//2, y + cell_size], outline='black')
            else:
                draw.rectangle([x, center_y - door_width//2, x + arch_width, center_y + door_width//2], outline='black')
                draw.rectangle([x + cell_size - arch_width, center_y - door_width//2, x + cell_size, center_y + door_width//2], outline='black')

        if door_type in ['open', 'lock', 'trap']:
            # Draw door slab
            if is_horizontal:
                draw.rectangle([center_x - door_width//2, y + arch_width, center_x + door_width//2, y + cell_size - arch_width], outline='black')
            else:
                draw.rectangle([x + arch_width, center_y - door_width//2, x + cell_size - arch_width, center_y + door_width//2], outline='black')


        # Draw specific door features
        if door_type == 'arch':
            # Nothing more to draw for arch
            pass
            
        elif door_type == 'open': # note open refers to regular unlocked door
            pass
        
        elif door_type == 'lock':
            # Draw diamond (square rotated 45°) for locked door
            half_size = symbol_size // 2
            diamond = [
                (center_x, center_y - half_size),  # Top
                (center_x + half_size, center_y),  # Right
                (center_x, center_y + half_size),  # Bottom
                (center_x - half_size, center_y)   # Left
            ]
            draw.polygon(diamond, outline='black')

        
        elif door_type == 'trap':
            pass
        
        elif door_type == 'secret':
            # Draw as wall (invisible)
            wall_color = (52, 73, 94)
            # draw.rectangle([x, y, x+cell_size, y+cell_size], fill=wall_color)
            # this is just to see, just remove whole thing if it works
            half_size = door_width
            diamond = [
                (center_x, center_y - half_size),  # Top
                (center_x + half_size, center_y),  # Right
                (center_x, center_y + half_size),  # Bottom
                (center_x - half_size, center_y)   # Left
            ]
            draw.rectangle([x+1, y+1, x+cell_size-1, y+cell_size-1], fill=wall_color)
            #draw.polygon(diamond, outline='green', fill='green') # this was to see where they were

        elif door_type == 'portc':
            # Draw portcullis as dots (3 dots centered)
            dot_radius = .5
            dot_count = 3
            dot_spacing = cell_size / (dot_count + 1)
            
            if is_horizontal:
                # Vertical line of dots
                for i in range(1, dot_count + 1):
                    dot_y = y + i * dot_spacing
                    draw.ellipse([
                        center_x - dot_radius, dot_y - dot_radius,
                        center_x + dot_radius, dot_y + dot_radius
                    ], fill='black')
            else:
                # Horizontal line of dots
                for i in range(1, dot_count + 1):
                    dot_x = x + i * dot_spacing
                    draw.ellipse([
                        dot_x - dot_radius, center_y - dot_radius,
                        dot_x + dot_radius, center_y + dot_radius
                    ], fill='black')

# Example usage
if __name__ == "__main__":
    options = {
        'seed': 12345,
        'n_rows': 39,
        'n_cols': 39,
        'room_min': 3,
        'room_max': 9,
        'corridor_layout': 'Bent',
        'remove_deadends': 50,
        'add_stairs': 2
    }
    
    generator = DungeonGenerator(options)
    generator.create_dungeon()
    image = generator.render_to_image()
    image.save('dungeon.png')