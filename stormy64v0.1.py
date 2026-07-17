#!/usr/bin/env python3
"""
Stormy64 B3313 — pygame-ce 3D Engine
SM64-inspired Peach's Castle courtyard with software 3D rendering.
Fully rewritten for Python 3.14 + pygame-ce.
"""

import pygame
import math
import sys
import traceback
from array import array
from random import uniform
from dataclasses import dataclass

WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480
RENDER_W = 320
RENDER_H = 240
FPS = 60
FOV = 75.0
NEAR = 0.5
FAR = 100.0
FOG_START = 16.0
FOG_END = 38.0
RENDER_TRI_LIMIT = 8000

SPAWN_POS = (0.0, 1.5, 4.0)
MAX_HEALTH = 8
TARGET_RED_COINS = 8
ENEMY_HIT_RADIUS = 1.05
HIT_DAMAGE = 2
INVULN_SEC = 1.6
SPAWN_GRACE_SEC = 2.5

WALK_MAX = 8.5
RUN_MAX = 15.0
GROUND_ACCEL = 46.0
GROUND_DECEL = 58.0
AIR_ACCEL = 14.0
AIR_DECEL = 10.0
GRAVITY = 30.0
GRAVITY_HOLD_MULT = 0.52
MAX_FALL = 42.0
JUMP_V = (8.0, 9.2, 10.4)
LONG_JUMP_H = 14.0
LONG_JUMP_V = 7.8
TRIPLE_JUMP_WINDOW = 0.36
DIVE_SPEED = 16.0
BACKFLIP_V = 12.0
SIDEFLIP_V = 9.5
SIDEFLIP_H = 8.0
GROUND_POUND_V = 20.0
CROUCH_MAX = 3.5
COURTYARD_HALF = 14

C_MARIO_RED = (255, 40, 40)
C_MARIO_BLUE = (40, 60, 220)
C_MARIO_SKIN = (255, 190, 150)
C_MARIO_HAIR = (120, 70, 20)
C_BRICK = (130, 95, 75)
C_PAVEMENT = (215, 215, 225)
C_GRASS = (65, 145, 55)
C_DIRT = (110, 85, 55)
C_TREE = (45, 120, 40)
C_CASTLE = (235, 200, 215)
C_CASTLE_TRIM = (255, 170, 190)
C_CASTLE_STONE = (248, 228, 238)
C_CASTLE_ROOF = (215, 55, 95)
C_CASTLE_WINDOW = (90, 170, 255)
C_FOUNTAIN = (170, 175, 185)
C_WATER = (80, 160, 240)
C_RED_COIN = (255, 45, 45)
C_STAR = (255, 220, 60)
C_BOO = (230, 230, 255)
C_SKY = (100, 150, 220)
C_MENU_BG = (20, 13, 30, 209)
C_MENU_TITLE = (255, 220, 100)
C_MENU_TEXT = (255, 240, 250)
C_MENU_SEL = (255, 255, 120)
C_MENU_DIM = (180, 150, 170)
C_HUD_BG = (0, 0, 0, 100)
C_HP = (255, 60, 60)

pygame.init()
pygame.display.set_caption("Stormy64 B3313 — Peach's Castle (SM64 DS)")
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
clock = pygame.time.Clock()
font_small = None
font_large = None
font_title = None

def _init_fonts():
    global font_small, font_large, font_title
    font_small = pygame.font.Font(None, 20)
    font_large = pygame.font.Font(None, 36)
    font_title = pygame.font.Font(None, 52)

_init_fonts()

class Vec3:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x=0, y=0, z=0):
        self.x = float(x); self.y = float(y); self.z = float(z)
    def __add__(self, o): return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)
    def __sub__(self, o): return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)
    def __mul__(self, s): return Vec3(self.x * s, self.y * s, self.z * s)
    def __truediv__(self, s): return Vec3(self.x / s, self.y / s, self.z / s)
    def __neg__(self): return Vec3(-self.x, -self.y, -self.z)
    def __iter__(self): yield self.x; yield self.y; yield self.z
    def __repr__(self): return f"({self.x:.2f},{self.y:.2f},{self.z:.2f})"
    def dot(self, o): return self.x * o.x + self.y * o.y + self.z * o.z
    def cross(self, o): return Vec3(self.y * o.z - self.z * o.y, self.z * o.x - self.x * o.z, self.x * o.y - self.y * o.x)
    def length(self): return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    def normalize(self):
        l = self.length()
        if l < 1e-8: return Vec3(0, 1, 0)
        return self / l
    def __getitem__(self, i):
        if i == 0: return self.x
        if i == 1: return self.y
        return self.z
    def __setitem__(self, i, v):
        if i == 0: self.x = v
        elif i == 1: self.y = v
        else: self.z = v
    def to_tuple(self): return (self.x, self.y, self.z)

def vec3(*a):
    if len(a) == 1: a = a[0]
    if isinstance(a, (list, tuple)): return Vec3(a[0], a[1], a[2])
    return Vec3(a[0], a[1], a[2])

def lerp_v3(a, b, t): return a + (b - a) * t

_M = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

class Mat4:
    __slots__ = ('m',)
    def __init__(self, data=None):
        if data:
            self.m = data if isinstance(data, list) and len(data) == 16 else [v for r in data for v in r]
        else:
            self.m = _M[:]

    def __mul__(self, o):
        if isinstance(o, Mat4):
            a, b = self.m, o.m
            return Mat4([
                a[0]*b[0]+a[1]*b[4]+a[2]*b[8]+a[3]*b[12],
                a[0]*b[1]+a[1]*b[5]+a[2]*b[9]+a[3]*b[13],
                a[0]*b[2]+a[1]*b[6]+a[2]*b[10]+a[3]*b[14],
                a[0]*b[3]+a[1]*b[7]+a[2]*b[11]+a[3]*b[15],

                a[4]*b[0]+a[5]*b[4]+a[6]*b[8]+a[7]*b[12],
                a[4]*b[1]+a[5]*b[5]+a[6]*b[9]+a[7]*b[13],
                a[4]*b[2]+a[5]*b[6]+a[6]*b[10]+a[7]*b[14],
                a[4]*b[3]+a[5]*b[7]+a[6]*b[11]+a[7]*b[15],

                a[8]*b[0]+a[9]*b[4]+a[10]*b[8]+a[11]*b[12],
                a[8]*b[1]+a[9]*b[5]+a[10]*b[9]+a[11]*b[13],
                a[8]*b[2]+a[9]*b[6]+a[10]*b[10]+a[11]*b[14],
                a[8]*b[3]+a[9]*b[7]+a[10]*b[11]+a[11]*b[15],

                a[12]*b[0]+a[13]*b[4]+a[14]*b[8]+a[15]*b[12],
                a[12]*b[1]+a[13]*b[5]+a[14]*b[9]+a[15]*b[13],
                a[12]*b[2]+a[13]*b[6]+a[14]*b[10]+a[15]*b[14],
                a[12]*b[3]+a[13]*b[7]+a[14]*b[11]+a[15]*b[15],
            ])
        vx, vy, vz = o.x, o.y, o.z
        m = self.m
        x = m[0]*vx + m[1]*vy + m[2]*vz + m[3]
        y = m[4]*vx + m[5]*vy + m[6]*vz + m[7]
        z = m[8]*vx + m[9]*vy + m[10]*vz + m[11]
        w = m[12]*vx + m[13]*vy + m[14]*vz + m[15]
        if abs(w) > 1e-10:
            return Vec3(x/w, y/w, z/w)
        return Vec3(x, y, z)

    def transform_batch(self, verts, out):
        m = self.m
        for i, v in enumerate(verts):
            vx, vy, vz = v.x, v.y, v.z
            x = m[0]*vx + m[1]*vy + m[2]*vz + m[3]
            y = m[4]*vx + m[5]*vy + m[6]*vz + m[7]
            z = m[8]*vx + m[9]*vy + m[10]*vz + m[11]
            w = m[12]*vx + m[13]*vy + m[14]*vz + m[15]
            o = out[i]
            if abs(w) > 1e-10:
                o.x = x/w; o.y = y/w; o.z = z/w
            else:
                o.x = x; o.y = y; o.z = z
        return out

def identity():
    return Mat4()

def translate(tx, ty, tz):
    m = _M[:]
    m[3], m[7], m[11] = tx, ty, tz
    return Mat4(m)

def scale_mat(sx, sy, sz):
    m = _M[:]
    m[0], m[5], m[10] = sx, sy, sz
    return Mat4(m)

def rotate_x(a):
    c = math.cos(a); s = math.sin(a)
    m = _M[:]
    m[5], m[6], m[9], m[10] = c, -s, s, c
    return Mat4(m)

def rotate_y(a):
    c = math.cos(a); s = math.sin(a)
    m = _M[:]
    m[0], m[2], m[8], m[10] = c, s, -s, c
    return Mat4(m)

def rotate_z(a):
    c = math.cos(a); s = math.sin(a)
    m = _M[:]
    m[0], m[1], m[4], m[5] = c, -s, s, c
    return Mat4(m)

def look_at(eye, target, up):
    f = (target - eye).normalize()
    s = f.cross(up).normalize()
    u = s.cross(f)
    sx, sy, sz = s.x, s.y, s.z
    ux, uy, uz = u.x, u.y, u.z
    fx, fy, fz = f.x, f.y, f.z
    m = _M[:]
    m[0], m[1], m[2] = sx, sy, sz
    m[4], m[5], m[6] = ux, uy, uz
    m[8], m[9], m[10] = -fx, -fy, -fz
    m[3] = -(sx*eye.x + sy*eye.y + sz*eye.z)
    m[7] = -(ux*eye.x + uy*eye.y + uz*eye.z)
    m[11] = fx*eye.x + fy*eye.y + fz*eye.z
    return Mat4(m)

def perspective(fov_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    nf = 1.0 / (near - far)
    m = [0.0]*16
    m[0] = f / aspect
    m[5] = f
    m[10] = (far + near) * nf
    m[11] = 2.0 * far * near * nf
    m[14] = -1.0
    return Mat4(m)

@dataclass
class Tri:
    a: Vec3
    b: Vec3
    c: Vec3
    color: tuple

@dataclass
class MeshData:
    verts: list
    tris: list

    def transformed(self, model_mat):
        mats = model_mat
        out_verts = [Vec3() for _ in self.verts]
        mats.transform_batch(self.verts, out_verts)
        out_tris = []
        for i, j, k, color in self.tris:
            out_tris.append(Tri(out_verts[i], out_verts[j], out_verts[k], color))
        return out_tris

def tri_normal(t):
    return (t.b - t.a).cross(t.c - t.a).normalize()

def _cube_mesh(scale, color):
    w, h, d = scale.x / 2, scale.y / 2, scale.z / 2
    verts = [
        Vec3(-w, -h, -d), Vec3(w, -h, -d), Vec3(w, h, -d), Vec3(-w, h, -d),
        Vec3(-w, -h, d), Vec3(w, -h, d), Vec3(w, h, d), Vec3(-w, h, d),
    ]
    faces = [
        (0,1,2,3), (4,5,6,7), (1,5,6,2),
        (0,4,7,3), (3,2,6,7), (0,1,5,4),
    ]
    tris = []
    for a,b,c,d in faces:
        tris.append((a,b,c,color))
        tris.append((a,c,d,color))
    return MeshData(verts, tris)

def _plane_mesh(w, d, color, double_sided=False):
    hw, hd = w / 2, d / 2
    verts = [
        Vec3(-hw, 0, -hd),
        Vec3( hw, 0, -hd),
        Vec3( hw, 0,  hd),
        Vec3(-hw, 0,  hd),
    ]
    if double_sided:
        tris = [(0,1,2,color),(0,2,3,color),(0,2,1,color),(0,3,2,color)]
    else:
        tris = [(0,1,2,color),(0,2,3,color)]
    return MeshData(verts, tris)

def _cylinder_mesh(radius, height, color, segs=12):
    verts = []
    y0, y1 = -height/2, height/2
    for i in range(segs):
        a = 2 * math.pi * i / segs
        x = radius * math.cos(a)
        z = radius * math.sin(a)
        verts.append(Vec3(x, y1, z))
    for i in range(segs):
        a = 2 * math.pi * i / segs
        x = radius * math.cos(a)
        z = radius * math.sin(a)
        verts.append(Vec3(x, y0, z))
    tris = []
    for i in range(segs):
        ni = (i + 1) % segs
        tris.append((i, ni, i+segs, color))
        tris.append((ni, ni+segs, i+segs, color))
    for i in range(2, segs):
        tris.append((0, i-1, i, color))
    for i in range(2, segs):
        tris.append((segs, segs+i, segs+i-1, color))
    return MeshData(verts, tris)

def _sphere_mesh(radius, color, rings=8, sectors=8):
    verts = []
    tris = []
    for r in range(rings + 1):
        theta = math.pi * r / rings
        for s in range(sectors + 1):
            phi = 2 * math.pi * s / sectors
            verts.append(Vec3(
                radius * math.sin(theta) * math.cos(phi),
                radius * math.cos(theta),
                radius * math.sin(theta) * math.sin(phi),
            ))
    for r in range(rings):
        for s in range(sectors):
            i0 = r * (sectors + 1) + s
            i1 = i0 + 1
            i2 = (r + 1) * (sectors + 1) + s
            i3 = i2 + 1
            tris.append((i0, i1, i2, color))
            tris.append((i1, i3, i2, color))
    return MeshData(verts, tris)

def _merge_meshes(*mesh_list):
    verts = []
    tris = []
    offset = 0
    for md in mesh_list:
        verts.extend(md.verts)
        for idx in md.tris:
            tris.append((idx[0]+offset, idx[1]+offset, idx[2]+offset, idx[3]))
        offset += len(md.verts)
    return MeshData(verts, tris)

_merge = _merge_meshes

def _cube_tris(pos, scale, color):
    return _cube_mesh(scale, color).transformed(translate(pos.x, pos.y, pos.z))

def _plane_tris(pos, w, d, color, double_sided=False):
    return _plane_mesh(w, d, color, double_sided).transformed(translate(pos.x, pos.y, pos.z))

def _cylinder_tris(pos, radius, height, color, segs=12):
    return _cylinder_mesh(radius, height, color, segs).transformed(translate(pos.x, pos.y, pos.z))

def _sphere_tris(pos, radius, color, rings=8, sectors=8):
    return _sphere_mesh(radius, color, rings, sectors).transformed(translate(pos.x, pos.y, pos.z))

class Camera:
    def __init__(self):
        self.target = Vec3(0, 2, 0)
        self.position = Vec3(0, 6, 12)
        self.yaw = 180.0
        self.pitch = 18.0
        self.dist = 7.5
        self.height = 2.8
        self.zoom_delta = 0.0
        self.aspect = RENDER_W / RENDER_H

    def update(self, dt):
        self.dist = max(4.5, min(14, self.dist + self.zoom_delta * 0.45))
        self.zoom_delta = 0.0
        target_p = self.target + Vec3(0, self.height, 0)
        yr = math.radians(self.yaw)
        pr = math.radians(self.pitch)
        offset = Vec3(
            math.sin(yr) * math.cos(pr) * self.dist,
            math.sin(pr) * self.dist,
            math.cos(yr) * math.cos(pr) * self.dist,
        )
        self.position = target_p - offset

    def get_view_matrix(self):
        return look_at(self.position, self.target + Vec3(0, 0.4, 0), Vec3(0, 1, 0))

    def get_proj_matrix(self):
        return perspective(FOV, self.aspect, NEAR, FAR)

class Renderer3D:
    __slots__ = ('fb', 'zbuf', 'fb_w', 'fb_h', '_sx', '_sy', '_scratch', '_temp_verts')
    def __init__(self):
        self.fb = pygame.Surface((RENDER_W, RENDER_H))
        self.fb_w = RENDER_W
        self.fb_h = RENDER_H
        self._sx = RENDER_W / 2
        self._sy = RENDER_H / 2
        size = RENDER_W * RENDER_H
        self.zbuf = array('f', [float('inf')]) * size
        self._scratch = []
        self._temp_verts = []

    def clear(self, bg_color):
        self.fb.fill(bg_color)
        self.zbuf = array('f', [float('inf')]) * (self.fb_w * self.fb_h)

    def render_meshes(self, meshes, camera):
        view = camera.get_view_matrix()
        proj = camera.get_proj_matrix()
        vp = proj * view
        sx, sy = self._sx, self._sy

        scratch = self._scratch
        scratch.clear()

        for mesh_data in meshes:
            if len(mesh_data) == 2:
                pos, item = mesh_data
                rot = None
            elif len(mesh_data) == 3:
                pos, item, rot = mesh_data
            else:
                continue

            if isinstance(item, list):
                # item is already in world space (pre-transformed by get_tris)
                mvp = vp
                for tri in item:
                    va = mvp * tri.a
                    vb = mvp * tri.b
                    vc = mvp * tri.c
                    ax, ay = va.x, va.y
                    bx, by = vb.x, vb.y
                    cx, cy = vc.x, vc.y
                    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
                    if area <= 0:
                        continue
                    sa = (int((va.x + 1.0) * sx), int((1.0 - va.y) * sy), va.z)
                    sb = (int((vb.x + 1.0) * sx), int((1.0 - vb.y) * sy), vb.z)
                    sc = (int((vc.x + 1.0) * sx), int((1.0 - vc.y) * sy), vc.z)
                    avg_z = (sa[2] + sb[2] + sc[2]) / 3.0
                    scratch.append((avg_z, (sa[:2], sb[:2], sc[:2]), tri.color))
            elif hasattr(item, 'verts'):
                md = item
                if not md.tris:
                    continue
                model = translate(pos.x, pos.y, pos.z)
                if rot:
                    rx, ry, rz = rot
                    if rx: model = model * rotate_x(math.radians(rx))
                    if ry: model = model * rotate_y(math.radians(ry))
                    if rz: model = model * rotate_z(math.radians(rz))
                mvp = vp * model
                nv = len(md.verts)
                temp = self._temp_verts
                while len(temp) < nv:
                    temp.append(Vec3())
                i = 0
                mm = mvp.m
                m0, m1, m2, m3 = mm[0], mm[1], mm[2], mm[3]
                m4, m5, m6, m7 = mm[4], mm[5], mm[6], mm[7]
                m8, m9, m10, m11 = mm[8], mm[9], mm[10], mm[11]
                m12, m13, m14, m15 = mm[12], mm[13], mm[14], mm[15]
                for v in md.verts:
                    vx, vy, vz = v.x, v.y, v.z
                    x = m0*vx + m1*vy + m2*vz + m3
                    y = m4*vx + m5*vy + m6*vz + m7
                    z = m8*vx + m9*vy + m10*vz + m11
                    w = m12*vx + m13*vy + m14*vz + m15
                    o = temp[i]; i += 1
                    if abs(w) > 1e-10:
                        o.x = x/w; o.y = y/w; o.z = z/w
                    else:
                        o.x = x; o.y = y; o.z = z
                for i, j, k, color in md.tris:
                    va, vb, vc = temp[i], temp[j], temp[k]
                    ax, ay = va.x, va.y
                    bx, by = vb.x, vb.y
                    cx, cy = vc.x, vc.y
                    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
                    if area <= 0:
                        continue
                    sa = (int((va.x + 1.0) * sx), int((1.0 - va.y) * sy), va.z)
                    sb = (int((vb.x + 1.0) * sx), int((1.0 - vb.y) * sy), vb.z)
                    sc = (int((vc.x + 1.0) * sx), int((1.0 - vc.y) * sy), vc.z)
                    avg_z = (sa[2] + sb[2] + sc[2]) / 3.0
                    scratch.append((avg_z, (sa[:2], sb[:2], sc[:2]), color))

        scratch.sort(key=lambda x: x[0])
        if len(scratch) > RENDER_TRI_LIMIT:
            del scratch[RENDER_TRI_LIMIT:]
        scratch.reverse()
        fb = self.fb
        for _, pts, color in scratch:
            try:
                pygame.draw.polygon(fb, color, pts)
            except Exception:
                pass

    def render_mesh(self, mesh_pos, mesh_tris, camera, mesh_rot=None):
        self.render_meshes([(mesh_pos, mesh_tris, mesh_rot)], camera)

    def present(self):
        scaled = pygame.transform.scale(self.fb, (WINDOW_WIDTH, WINDOW_HEIGHT))
        screen.blit(scaled, (0, 0))

class Player:
    def __init__(self):
        self.pos = Vec3(*SPAWN_POS)
        self.vel_h = Vec3(0, 0, 0)
        self.vel_y = 0.0
        self.grounded = False
        self.face_yaw = 0.0
        self.jump_chain = 0
        self.time_since_jump = 99.0
        self.jump_held = False
        self.long_jump_timer = 0.0
        self.invuln_timer = 0.0
        self.dive_used = False
        self.crouching = False
        self.punch_timer = 0.0
        self.ground_pounding = False
        self.sideflip_timer = 0.0
        self.backflip_timer = 0.0
        self.punch_cooldown = 0.0
        self.collected = 0
        self.alive = True
        self.health = MAX_HEALTH
        self.height = 1.35
        self.visible = True

    def running(self):
        return True

    def stick(self, cam_yaw):
        keys = pygame.key.get_pressed()
        x = float(keys[pygame.K_d]) - float(keys[pygame.K_a])
        z = float(keys[pygame.K_w]) - float(keys[pygame.K_s])
        if abs(x) < 0.01 and abs(z) < 0.01:
            return Vec3(0, 0, 0)
        yr = math.radians(cam_yaw)
        fwd = Vec3(math.sin(yr), 0, math.cos(yr))
        right = Vec3(fwd.z, 0, -fwd.x)
        move = fwd * z + right * x
        if move.length() > 0:
            return move.normalize()
        return Vec3(0, 0, 0)

    def try_dive(self, cam_yaw):
        if not self.alive or self.grounded or self.dive_used:
            return
        self.dive_used = True
        yr = math.radians(cam_yaw)
        fwd = Vec3(math.sin(yr), 0, math.cos(yr))
        self.vel_h = fwd * DIVE_SPEED
        self.vel_y = min(self.vel_y, -5.0)

    def ground_pound(self):
        if not self.alive or self.grounded or self.ground_pounding:
            return False
        self.ground_pounding = True
        self.vel_y = -GROUND_POUND_V
        self.vel_h = Vec3(0, 0, 0)
        return True

    def punch(self):
        if not self.alive or not self.grounded or self.punch_cooldown > 0:
            return False
        self.punch_timer = 0.2
        self.punch_cooldown = 0.4
        return True

    def jump(self, cam_yaw):
        if not self.alive:
            return
        keys = pygame.key.get_pressed()
        stick = self.stick(cam_yaw)
        crouch = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        move_fwd = keys[pygame.K_w]
        move_bwd = keys[pygame.K_s]
        move_side = keys[pygame.K_a] or keys[pygame.K_d]

        if self.grounded:
            # Backflip: crouching + stationary
            if crouch and not move_fwd and not move_bwd and not move_side:
                self.backflip_timer = 0.5
                self.vel_y = BACKFLIP_V
                self.grounded = False
                self.jump_chain = 0
                return

            # Long jump: crouching + forward/backward
            if crouch and (move_fwd or move_bwd) and not move_side:
                self.long_jump_timer = 0.35
                self.vel_y = LONG_JUMP_V
                self.grounded = False
                self.vel_h = Vec3(stick.x * LONG_JUMP_H, 0, stick.z * LONG_JUMP_H)
                self.face_yaw = math.degrees(math.atan2(stick.x, stick.z))
                self.jump_chain = 0
                return

            # Sideflip: crouching + sideways
            if crouch and move_side:
                self.sideflip_timer = 0.4
                self.vel_y = SIDEFLIP_V
                self.grounded = False
                self.vel_h = Vec3(stick.x * SIDEFLIP_H, 0, stick.z * SIDEFLIP_H)
                self.face_yaw = math.degrees(math.atan2(stick.x, stick.z))
                self.jump_chain = 0
                return

            if self.time_since_jump < TRIPLE_JUMP_WINDOW:
                self.jump_chain = min(3, self.jump_chain + 1)
            else:
                self.jump_chain = 1
            idx = self.jump_chain - 1
            self.vel_y = JUMP_V[idx]
            self.grounded = False
            self.time_since_jump = 0.0
        elif self.jump_chain < 3 and self.time_since_jump < TRIPLE_JUMP_WINDOW:
            self.jump_chain += 1
            idx = min(2, self.jump_chain - 1)
            self.vel_y = max(self.vel_y, JUMP_V[idx] * 0.92)

    def apply_horizontal(self, wish, dt):
        max_spd = RUN_MAX if self.running() else WALK_MAX
        if self.crouching:
            max_spd = CROUCH_MAX
        if self.long_jump_timer > 0:
            max_spd = LONG_JUMP_H
        target = wish * max_spd if wish.length() > 0 else Vec3(0, 0, 0)
        accel = GROUND_ACCEL if self.grounded else AIR_ACCEL
        decel = GROUND_DECEL if self.grounded else AIR_DECEL
        for i in (0, 2):
            cur = self.vel_h[i]; tgt = target[i]
            if abs(tgt) > 0.01:
                if cur < tgt:
                    cur = min(tgt, cur + accel * dt)
                else:
                    cur = max(tgt, cur - accel * dt)
            else:
                if cur > 0:
                    cur = max(0, cur - decel * dt)
                elif cur < 0:
                    cur = min(0, cur + decel * dt)
            self.vel_h[i] = cur
        if wish.length() > 0 and self.long_jump_timer <= 0 and not self.crouching:
            self.face_yaw = math.degrees(math.atan2(self.vel_h.x, self.vel_h.z))

    def apply_gravity(self, dt, solid_boxes):
        grav = GRAVITY
        if self.ground_pounding:
            grav *= 2.5
        elif self.vel_y > 0 and self.jump_held and not pygame.key.get_pressed()[pygame.K_SPACE]:
            self.jump_held = False
        if self.vel_y > 0 and self.jump_held:
            grav *= GRAVITY_HOLD_MULT
        self.vel_y = max(self.vel_y - grav * dt, -MAX_FALL)
        move_y = self.vel_y * dt
        new_pos = self.pos + Vec3(0, move_y, 0)
        if move_y <= 0:
            landed = False
            for box in solid_boxes:
                cx, cy, cz = box.center
                hx, hy, hz = box.half
                dx = abs(new_pos.x - cx)
                dz = abs(new_pos.z - cz)
                if dx <= hx + 0.4 and dz <= hz + 0.4:
                    top = cy + hy
                    if self.pos.y >= top and new_pos.y <= top:
                        new_pos.y = top
                        self.vel_y = 0
                        self.grounded = True
                        self.dive_used = False
                        self.ground_pounding = False
                        if self.long_jump_timer <= 0:
                            self.vel_h *= 0.82
                        landed = True
                        break
            if not landed and new_pos.y <= 0:
                new_pos.y = 0
                self.vel_y = 0
                self.grounded = True
                self.dive_used = False
                self.ground_pounding = False
                if self.long_jump_timer <= 0:
                    self.vel_h *= 0.82
                self.pos = new_pos
                return
            if landed:
                self.pos = new_pos
                return
        self.pos = new_pos
        self.grounded = False

    def update(self, dt, cam_yaw, solid_boxes):
        if not self.alive:
            return
        self.time_since_jump += dt
        if self.long_jump_timer > 0:
            self.long_jump_timer = max(0, self.long_jump_timer - dt)
        if self.invuln_timer > 0:
            self.invuln_timer = max(0, self.invuln_timer - dt)
        if self.punch_timer > 0:
            self.punch_timer = max(0, self.punch_timer - dt)
        if self.punch_cooldown > 0:
            self.punch_cooldown = max(0, self.punch_cooldown - dt)
        if self.sideflip_timer > 0:
            self.sideflip_timer = max(0, self.sideflip_timer - dt)
        if self.backflip_timer > 0:
            self.backflip_timer = max(0, self.backflip_timer - dt)

        keys = pygame.key.get_pressed()
        self.crouching = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and self.grounded

        wish = self.stick(cam_yaw)
        self.apply_horizontal(wish, dt)
        self.pos.x += self.vel_h.x * dt
        self.pos.z += self.vel_h.z * dt
        self.apply_gravity(dt, solid_boxes)
        for box in solid_boxes:
            self._push_out_of_box(box)

    def _push_out_of_box(self, box):
        # pos is at the feet. Horizontal pad ~0.4; body height for vertical tests.
        cx, cy, cz = box.center
        hx, hy, hz = box.half
        top = cy + hy
        dx = self.pos.x - cx
        dz = self.pos.z - cz
        if abs(dx) > hx + 0.4 or abs(dz) > hz + 0.4:
            return
        # Prefer standing on the top face instead of lateral shove / y-padding jitter.
        if self.vel_y <= 0.5 and self.pos.y >= top - 0.12 and self.pos.y <= top + 0.55:
            self.pos.y = top
            if self.vel_y < 0:
                self.vel_y = 0
            self.grounded = True
            self.dive_used = False
            return
        # Fully above or below the volume — no wall collision.
        if self.pos.y >= top or self.pos.y + self.height <= cy - hy:
            return
        dy = (self.pos.y + self.height * 0.5) - cy
        if abs(dy) > hy + self.height * 0.5:
            return
        overlap = [
            (hx + 0.4 - abs(dx), 0),
            (hy + self.height * 0.5 - abs(dy), 1),
            (hz + 0.4 - abs(dz), 2),
        ]
        overlap.sort(key=lambda x: x[0])
        amo, axis = overlap[0]
        if amo > 0:
            if axis == 0:
                self.pos.x = cx + (hx + 0.41) * (1 if dx > 0 else -1)
                self.vel_h.x = 0
            elif axis == 2:
                self.pos.z = cz + (hz + 0.41) * (1 if dz > 0 else -1)
                self.vel_h.z = 0
            elif axis == 1:
                if dy > 0:
                    self.pos.y = top
                    self.vel_y = 0
                    self.grounded = True
                    self.dive_used = False
                else:
                    self.pos.y = cy - hy - self.height
                    self.vel_y = min(self.vel_y, 0)

    def take_damage(self, amount):
        if self.invuln_timer > 0 or not self.alive:
            return False
        self.health = max(0, self.health - amount)
        self.invuln_timer = INVULN_SEC
        if self.health <= 0:
            self.alive = False
            return True
        return False

    def respawn(self):
        self.pos = Vec3(*SPAWN_POS)
        self.vel_h = Vec3(0, 0, 0)
        self.vel_y = 0
        self.alive = True
        self.health = MAX_HEALTH
        self.grounded = False
        self.invuln_timer = INVULN_SEC
        self.dive_used = False

    def get_tris(self):
        parts = [
            (Vec3(0, 0.28, -0.02), Vec3(0.42, 0.5, 0.32), C_MARIO_BLUE),
            (Vec3(0, 0.72, 0), Vec3(0.48, 0.45, 0.38), C_MARIO_RED),
            (Vec3(0, 1.08, 0), Vec3(0.38, 0.38, 0.38), C_MARIO_SKIN),
            (Vec3(0, 1.38, 0), Vec3(0.46, 0.18, 0.46), C_MARIO_RED),
            (Vec3(0, 1.48, 0.2), Vec3(0.12, 0.08, 0.12), C_MARIO_HAIR),
        ]
        pos = self.pos
        tris = []
        for offset, scale, color in parts:
            p = pos + offset
            tris.extend(_cube_mesh(scale, color).transformed(translate(p.x, p.y, p.z)))
        return tris

@dataclass
class SolidBox:
    center: Vec3
    half: Vec3

_RED_COIN_MESH = _merge_meshes(
    _cube_mesh(Vec3(0.35, 0.08, 0.35), (255, 45, 45)),
    _cube_mesh(Vec3(0.08, 0.35, 0.35), (255, 45, 45)),
    _cube_mesh(Vec3(0.35, 0.35, 0.08), (255, 45, 45)),
)

class RedCoin:
    def __init__(self, pos):
        self.pos = Vec3(*pos) if isinstance(pos, tuple) else pos
        self.collected = False
        self.angle = uniform(0, math.pi * 2)
        self.base_y = self.pos.y

    def update(self, dt):
        self.angle += dt * 2.0
        self.pos.y = self.base_y + math.sin(self.angle) * 0.3

    def get_tris(self):
        m = translate(self.pos.x, self.pos.y, self.pos.z) * rotate_y(self.angle * 1.5)
        return _RED_COIN_MESH.transformed(m)

_BOO_BODY_MESH = _sphere_mesh(0.45, C_BOO, 8, 8)
_BOO_EYE_MESH = _cube_mesh(Vec3(0.12, 0.16, 0.08), (0, 0, 0))

class Boo:
    def __init__(self, p0, p1, speed=1.5):
        self.p0 = Vec3(*p0) if isinstance(p0, tuple) else p0
        self.p1 = Vec3(*p1) if isinstance(p1, tuple) else p1
        self.u = 0.0
        self.dir = 1
        self.speed = speed
        self.pos = self.p0
        self.time = uniform(0, math.pi * 2)
        self.alive = True

    def update(self, dt):
        if not self.alive:
            return
        self.u += self.dir * self.speed * dt * 0.16
        if self.u > 1:
            self.u, self.dir = 1, -1
        if self.u < 0:
            self.u, self.dir = 0, 1
        self.pos = lerp_v3(self.p0, self.p1, self.u)
        self.pos.y = self.p0.y + math.sin(self.time + self.u * 4) * 0.35
        self.time += dt * 2.2

    def get_tris(self):
        m = translate(self.pos.x, self.pos.y, self.pos.z) * rotate_y(self.time * 40)
        m_eyes1 = translate(self.pos.x - 0.18, self.pos.y + 0.12, self.pos.z + 0.35) * rotate_y(self.time * 40)
        m_eyes2 = translate(self.pos.x + 0.18, self.pos.y + 0.12, self.pos.z + 0.35) * rotate_y(self.time * 40)
        out = _BOO_BODY_MESH.transformed(m)
        out.extend(_BOO_EYE_MESH.transformed(m_eyes1))
        out.extend(_BOO_EYE_MESH.transformed(m_eyes2))
        return out

@dataclass
class Portal:
    """Interactable door/painting that warps to another map when E is pressed."""
    pos: Vec3
    label: str
    target_map: str
    spawn: Vec3
    spawn_yaw: float = 0.0
    radius: float = 3.0


# Map graph: courtyard door → lobby → course paintings / exit door
MAP_COURTYARD = "courtyard"
MAP_LOBBY = "castle_lobby"
MAP_BOB = "bobomb_battlefield"
MAP_WF = "whomps_fortress"
MAP_JRB = "jolly_roger_bay"
MAP_CCM = "cool_cool_mountain"

COURSE_SKY = {
    MAP_COURTYARD: C_SKY,
    MAP_LOBBY: (40, 35, 55),
    MAP_BOB: (110, 165, 230),
    MAP_WF: (120, 150, 200),
    MAP_JRB: (70, 120, 190),
    MAP_CCM: (160, 200, 240),
}


class Level:
    def __init__(self, map_id=MAP_COURTYARD):
        self.map_id = map_id
        self.meshes = []
        self.solid_boxes = []
        self.coins = []
        self.boos = []
        self.star_mesh = None
        self.star_pos = Vec3(0, 5.8, -5.5)
        self.star_active = False
        self.portals = []  # list[Portal]
        self.name = "Peach's Castle Courtyard"
        self.sky = COURSE_SKY.get(map_id, C_SKY)
        self._build(map_id)

    def _add_mesh(self, pos, item, rot=None):
        self.meshes.append((pos, item, rot))

    def _add_portal(self, pos, label, target_map, spawn, spawn_yaw=0.0, radius=3.0):
        self.portals.append(Portal(pos, label, target_map, spawn, spawn_yaw, radius))

    def _add_door_mesh(self, pos, size=None):
        size = size or Vec3(2.0, 3.2, 0.12)
        self._add_mesh(pos, _cube_mesh(size, (139, 90, 43)))

    def _floor_and_walls(self, half, wall_h=4.8, thick=1.35, floor_color=C_PAVEMENT, wall_color=C_BRICK, grass=True):
        if grass:
            self._add_mesh(Vec3(0, -0.01, 0), _plane_mesh(half * 3, half * 3, C_GRASS))
        self._add_mesh(Vec3(0, 0.02, 0), _plane_mesh(half * 2, half * 2, floor_color, True))
        w2 = half * 2 + thick * 2
        self._add_mesh(Vec3(0, wall_h / 2, half), _cube_mesh(Vec3(w2, wall_h, thick), wall_color))
        self._add_mesh(Vec3(0, wall_h / 2, -half), _cube_mesh(Vec3(w2, wall_h, thick), wall_color))
        self._add_mesh(Vec3(half, wall_h / 2, 0), _cube_mesh(Vec3(thick, wall_h, half * 2), wall_color))
        self._add_mesh(Vec3(-half, wall_h / 2, 0), _cube_mesh(Vec3(thick, wall_h, half * 2), wall_color))
        half_long = half + thick
        for oz in (half, -half):
            self.solid_boxes.append(SolidBox(Vec3(0, wall_h / 2, oz), Vec3(half_long, wall_h / 2, thick / 2)))
        for ox in (half, -half):
            self.solid_boxes.append(SolidBox(Vec3(ox, wall_h / 2, 0), Vec3(thick / 2, wall_h / 2, half)))
        self.solid_boxes.append(SolidBox(Vec3(0, -0.5, 0), Vec3(half + 2, 0.5, half + 2)))

    def _build(self, map_id):
        if map_id == MAP_COURTYARD:
            self._build_courtyard()
        elif map_id == MAP_LOBBY:
            self._build_lobby()
        elif map_id == MAP_BOB:
            self._build_course("Bob-omb Battlefield", (90, 160, 70), (140, 100, 70))
        elif map_id == MAP_WF:
            self._build_course("Whomp's Fortress", (100, 120, 90), (160, 150, 140))
        elif map_id == MAP_JRB:
            self._build_course("Jolly Roger Bay", (40, 90, 140), (70, 130, 180))
        elif map_id == MAP_CCM:
            self._build_course("Cool, Cool Mountain", (200, 220, 240), (180, 200, 220))
        else:
            self._build_courtyard()

    def _build_courtyard(self):
        self.name = "Peach's Castle Courtyard"
        h = COURTYARD_HALF
        wall_h, thick = 4.8, 1.35
        self._add_mesh(Vec3(0, -0.01, 0), _plane_mesh(40, 40, C_GRASS))
        self._add_mesh(Vec3(0, 0.02, 0), _plane_mesh(18, 18, C_PAVEMENT, True))
        w2 = h * 2 + thick * 2
        self._add_mesh(Vec3(0, wall_h / 2, h), _cube_mesh(Vec3(w2, wall_h, thick), C_BRICK))
        self._add_mesh(Vec3(0, wall_h / 2, -h), _cube_mesh(Vec3(w2, wall_h, thick), C_BRICK))
        self._add_mesh(Vec3(h, wall_h / 2, 0), _cube_mesh(Vec3(thick, wall_h, h * 2), C_BRICK))
        self._add_mesh(Vec3(-h, wall_h / 2, 0), _cube_mesh(Vec3(thick, wall_h, h * 2), C_BRICK))
        # Front/back walls run along X; side walls run along Z (half extents must match).
        half_long = h + thick
        for oz in (h, -h):
            self.solid_boxes.append(SolidBox(Vec3(0, wall_h / 2, oz), Vec3(half_long, wall_h / 2, thick / 2)))
        for ox in (h, -h):
            self.solid_boxes.append(SolidBox(Vec3(ox, wall_h / 2, 0), Vec3(thick / 2, wall_h / 2, h)))
        cap_w = h * 2 + 3
        self._add_mesh(Vec3(0, wall_h + 0.3, h), _cube_mesh(Vec3(cap_w, 0.45, 1.4), (100, 75, 58)))
        self._add_mesh(Vec3(0, wall_h + 0.3, -h), _cube_mesh(Vec3(cap_w, 0.45, 1.4), (100, 75, 58)))
        self._add_mesh(Vec3(h, wall_h + 0.3, 0), _cube_mesh(Vec3(1.4, 0.45, h * 2), (100, 75, 58)))
        self._add_mesh(Vec3(-h, wall_h + 0.3, 0), _cube_mesh(Vec3(1.4, 0.45, h * 2), (100, 75, 58)))

        z_castle = -h + 0.65
        door_gap = 1.35  # half-width of walkable/trigger gap in castle face
        # Castle facade split so the door opening is not a solid wall
        self._add_mesh(Vec3(-6.0, 4.2, z_castle), _cube_mesh(Vec3(8.0, 8.5, 2.6), C_CASTLE))
        self._add_mesh(Vec3(6.0, 4.2, z_castle), _cube_mesh(Vec3(8.0, 8.5, 2.6), C_CASTLE))
        self._add_mesh(Vec3(0, 6.6, z_castle), _cube_mesh(Vec3(2.8, 3.5, 2.6), C_CASTLE))  # lintel
        self._add_mesh(Vec3(-6.5, 4.8, z_castle + 0.4), _cube_mesh(Vec3(6, 1.2, 2), C_CASTLE_TRIM))
        self._add_mesh(Vec3(6.5, 4.8, z_castle + 0.4), _cube_mesh(Vec3(6, 1.2, 2), C_CASTLE_TRIM))
        self._add_mesh(Vec3(-3.2, 2.8, z_castle + 0.9), _cube_mesh(Vec3(1.4, 5.6, 1.6), C_CASTLE_TRIM))
        self._add_mesh(Vec3(3.2, 2.8, z_castle + 0.9), _cube_mesh(Vec3(1.4, 5.6, 1.6), C_CASTLE_TRIM))
        # Solids: left wing, right wing, lintel above door (gap open for approach)
        self.solid_boxes.append(SolidBox(Vec3(-(door_gap + 4.0), 4.2, z_castle), Vec3(4.0, 4.25, 1.3)))
        self.solid_boxes.append(SolidBox(Vec3(door_gap + 4.0, 4.2, z_castle), Vec3(4.0, 4.25, 1.3)))
        self.solid_boxes.append(SolidBox(Vec3(0, 6.6, z_castle), Vec3(door_gap + 0.2, 1.75, 1.3)))
        self.solid_boxes.append(SolidBox(Vec3(-3.2, 2.8, z_castle + 0.9), Vec3(0.7, 2.8, 0.8)))
        self.solid_boxes.append(SolidBox(Vec3(3.2, 2.8, z_castle + 0.9), Vec3(0.7, 2.8, 0.8)))

        bx = h - 3.5
        for dz, dy in ((0, 0), (2.2, 0.6), (-2.2, 0.6)):
            self._add_mesh(Vec3(bx, 1.0 + dy, dz), _cube_mesh(Vec3(2.8, 2.0 + dy * 2, 2.8), C_BRICK))
        for tx, tz in [(-5.5, -5.5), (5.5, -5.5), (-5.5, 5.5), (5.5, 5.5)]:
            self._add_tree(tx, tz)
        self._add_fountain()
        gate_z = h - 0.5
        self._add_mesh(Vec3(-5.5, 2.6, gate_z), _cube_mesh(Vec3(1.6, 5.2, 1.6), C_CASTLE_TRIM))
        self._add_mesh(Vec3(5.5, 2.6, gate_z), _cube_mesh(Vec3(1.6, 5.2, 1.6), C_CASTLE_TRIM))
        coin_spots = [
            (-5.5, 1.4, -5.5), (5.5, 1.4, -5.5), (-5.5, 1.4, 5.5), (5.5, 1.4, 5.5),
            (3.2, 1.5, 0.5), (-3.2, 1.5, -0.5), (0, 1.6, 9), (-11, 1.3, 0),
        ]
        for p in coin_spots[:TARGET_RED_COINS]:
            self.coins.append(RedCoin(Vec3(*p)))
        routes = [
            (Vec3(-h + 2.5, 1.4, -h + 1), Vec3(-h + 2.5, 1.4, h - 3)),
            (Vec3(h - 2.5, 1.4, -h + 1), Vec3(h - 2.5, 1.4, h - 3)),
            (Vec3(-h + 3, 1.4, -h + 2), Vec3(h - 3, 1.4, -h + 2)),
        ]
        for i, (p0, p1) in enumerate(routes):
            self.boos.append(Boo(p0, p1, speed=1.35 + i * 0.2))
        self.solid_boxes.append(SolidBox(Vec3(0, -0.5, 0), Vec3(15, 0.5, 15)))

        # Castle main door → lobby
        door_vis = Vec3(0, 1.7, z_castle + 0.9)
        door_trig = Vec3(0, 0.0, z_castle + 1.8)
        self._add_door_mesh(door_vis)
        self._add_portal(
            door_trig, "Castle Door", MAP_LOBBY,
            spawn=Vec3(0, 0.0, 6.0), spawn_yaw=180.0, radius=3.2,
        )

    def _build_lobby(self):
        """Castle interior hub with exit door and course paintings."""
        self.name = "Castle Lobby"
        half = 10.0
        wall_h, thick = 6.0, 1.2
        self._add_mesh(Vec3(0, -0.01, 0), _plane_mesh(30, 30, C_CASTLE_STONE))
        self._add_mesh(Vec3(0, 0.02, 0), _plane_mesh(half * 2 - 0.5, half * 2 - 0.5, C_PAVEMENT, True))
        # Ceiling
        self._add_mesh(Vec3(0, wall_h, 0), _plane_mesh(half * 2, half * 2, C_CASTLE))
        w2 = half * 2 + thick * 2
        for oz in (half, -half):
            self._add_mesh(Vec3(0, wall_h / 2, oz), _cube_mesh(Vec3(w2, wall_h, thick), C_CASTLE))
            self.solid_boxes.append(SolidBox(Vec3(0, wall_h / 2, oz), Vec3(half + thick, wall_h / 2, thick / 2)))
        for ox in (half, -half):
            self._add_mesh(Vec3(ox, wall_h / 2, 0), _cube_mesh(Vec3(thick, wall_h, half * 2), C_CASTLE))
            self.solid_boxes.append(SolidBox(Vec3(ox, wall_h / 2, 0), Vec3(thick / 2, wall_h / 2, half)))
        self.solid_boxes.append(SolidBox(Vec3(0, -0.5, 0), Vec3(half + 2, 0.5, half + 2)))

        # Pillars
        for px, pz in ((-4, -4), (4, -4), (-4, 4), (4, 4)):
            self._add_mesh(Vec3(px, 2.5, pz), _cube_mesh(Vec3(1.0, 5.0, 1.0), C_CASTLE_TRIM))
            self.solid_boxes.append(SolidBox(Vec3(px, 2.5, pz), Vec3(0.5, 2.5, 0.5)))

        # Exit door (south) → courtyard, spawn in front of castle
        exit_z = half - 0.6
        self._add_door_mesh(Vec3(0, 1.7, exit_z - 0.2))
        self._add_portal(
            Vec3(0, 0.0, exit_z - 1.2), "Exit to Courtyard", MAP_COURTYARD,
            spawn=Vec3(0, 0.0, -COURTYARD_HALF + 3.5), spawn_yaw=180.0, radius=3.0,
        )

        # Paintings on walls → courses
        inner = half - thick / 2 - 0.05
        painting_data = [
            (Vec3(-inner, 2.4, -4.5), Vec3(0.08, 2.2, 1.6), "Bob-omb Battlefield", MAP_BOB, (90, 140, 60)),
            (Vec3(-inner, 2.4, 4.5), Vec3(0.08, 2.2, 1.6), "Whomp's Fortress", MAP_WF, (150, 150, 130)),
            (Vec3(inner, 2.4, -4.5), Vec3(0.08, 2.2, 1.6), "Jolly Roger Bay", MAP_JRB, (50, 100, 180)),
            (Vec3(inner, 2.4, 4.5), Vec3(0.08, 2.2, 1.6), "Cool, Cool Mountain", MAP_CCM, (180, 210, 240)),
            (Vec3(0, 2.4, -inner), Vec3(1.6, 2.2, 0.08), "Back Door", MAP_COURTYARD, (139, 90, 43)),
        ]
        for ppos, psize, pname, tmap, color in painting_data:
            self._add_mesh(ppos, _cube_mesh(psize, color))
            # Trigger slightly toward room center
            if abs(ppos.x) > abs(ppos.z):
                tpos = Vec3(ppos.x * 0.85, 0.0, ppos.z)
            else:
                tpos = Vec3(ppos.x, 0.0, ppos.z * 0.85)
            spawn = Vec3(0, 0.0, 5.0) if tmap != MAP_COURTYARD else Vec3(0, 0.0, -COURTYARD_HALF + 3.5)
            yaw = 180.0
            self._add_portal(tpos, pname, tmap, spawn=spawn, spawn_yaw=yaw, radius=3.2)

        # A few lobby coins
        for p in ((-3, 1.2, 0), (3, 1.2, 0), (0, 1.2, -3), (0, 1.2, 3)):
            self.coins.append(RedCoin(Vec3(*p)))

    def _build_course(self, name, ground_color, wall_color):
        """Simple open course arena with exit door back to lobby."""
        self.name = name
        half = 12.0
        self._floor_and_walls(half, wall_h=5.0, thick=1.2, floor_color=ground_color, wall_color=wall_color, grass=True)
        # Center platform / hill
        self._add_mesh(Vec3(0, 0.8, -2), _cube_mesh(Vec3(5.0, 1.6, 5.0), wall_color))
        self.solid_boxes.append(SolidBox(Vec3(0, 0.8, -2), Vec3(2.5, 0.8, 2.5)))
        self._add_mesh(Vec3(0, 2.0, -2), _cube_mesh(Vec3(2.4, 1.0, 2.4), (wall_color[0] + 20, wall_color[1] + 20, wall_color[2] + 20)))
        self.solid_boxes.append(SolidBox(Vec3(0, 2.0, -2), Vec3(1.2, 0.5, 1.2)))

        # Trees / decoration
        for tx, tz in ((-7, -7), (7, -7), (-7, 7), (7, 7), (0, 8)):
            self._add_tree(tx, tz)

        coin_spots = [
            (-6, 1.3, -6), (6, 1.3, -6), (-6, 1.3, 6), (6, 1.3, 6),
            (0, 2.8, -2), (3, 1.3, 0), (-3, 1.3, 0), (0, 1.3, 7),
        ]
        for p in coin_spots[:TARGET_RED_COINS]:
            self.coins.append(RedCoin(Vec3(*p)))
        self.boos.append(Boo(Vec3(-8, 1.4, -4), Vec3(8, 1.4, -4), speed=1.5))
        self.boos.append(Boo(Vec3(-5, 1.4, 5), Vec3(5, 1.4, 5), speed=1.7))
        self.star_pos = Vec3(0, 4.0, -2)

        # Exit door → lobby
        exit_z = half - 0.7
        self._add_door_mesh(Vec3(0, 1.7, exit_z - 0.15))
        self._add_portal(
            Vec3(0, 0.0, exit_z - 1.4), "Exit to Lobby", MAP_LOBBY,
            spawn=Vec3(0, 0.0, 0.0), spawn_yaw=0.0, radius=3.2,
        )

    def nearest_portal(self, player_pos, max_dist=None):
        """Closest portal by horizontal distance (ignores Y so feet-level works)."""
        best = None
        best_d = max_dist if max_dist is not None else 999.0
        for p in self.portals:
            dx = player_pos.x - p.pos.x
            dz = player_pos.z - p.pos.z
            d = math.sqrt(dx * dx + dz * dz)
            limit = p.radius if max_dist is None else max_dist
            if d < limit and d < best_d:
                best_d = d
                best = p
        return best

    def _add_tree(self, x, z):
        self._add_mesh(Vec3(x, 0.06, z), _cylinder_mesh(1.2, 0.12, C_DIRT, 8))
        self._add_mesh(Vec3(x, 0.75, z), _cylinder_mesh(0.2, 1.3, (85, 55, 30), 6))
        self._add_mesh(Vec3(x, 2.35, z), _sphere_mesh(1.0, C_TREE, 6, 6))

    def _add_fountain(self):
        self._add_mesh(Vec3(0, 0.22, 0), _cube_mesh(Vec3(6.2, 0.45, 6.2), C_FOUNTAIN))
        self.solid_boxes.append(SolidBox(Vec3(0, 0.22, 0), Vec3(3.1, 0.225, 3.1)))
        self._add_mesh(Vec3(0, 0.55, 0), _cylinder_mesh(1.9, 0.55, C_WATER, 12))
        self._add_mesh(Vec3(0, 1.35, 0), _cylinder_mesh(0.45, 2.2, C_FOUNTAIN, 10))
        self.solid_boxes.append(SolidBox(Vec3(0, 1.35, 0), Vec3(0.45, 1.1, 0.45)))
        self._add_mesh(Vec3(0, 2.85, 0), _sphere_mesh(0.55, C_STAR, 8, 8))
        self._add_mesh(Vec3(0, 2.85, 0), _sphere_mesh(0.9, (255, 220, 60, 55), 6, 6))

    def spawn_star(self):
        self.star_active = True
        self.star_mesh = _merge_meshes(
            _sphere_mesh(0.6, C_STAR, 8, 8),
            _sphere_mesh(0.85, (255, 220, 60, 40), 6, 6),
        )

    def get_star_tris(self):
        if not self.star_active or not self.star_mesh:
            return []
        m = translate(self.star_pos.x, self.star_pos.y, self.star_pos.z) * rotate_y(pygame.time.get_ticks() / 200.0)
        return self.star_mesh.transformed(m)

def _blit_text(text, font, color, x, y, center=True):
    surf = font.render(text, True, color[:3] if len(color) == 4 else color)
    if center:
        rect = surf.get_rect(center=(x, y))
    else:
        rect = surf.get_rect(topleft=(x, y))
    screen.blit(surf, rect)

def _draw_hud(coins, health, game_active):
    if not game_active:
        return
    bg = pygame.Surface((WINDOW_WIDTH, 60))
    bg.set_alpha(80)
    screen.blit(bg, (0, 0))
    _blit_text(f"Red Coins {coins}/{TARGET_RED_COINS}", font_small, (255, 255, 255), 80, 20, False)
    pip_size = 16
    for i in range(MAX_HEALTH):
        x = 80 + i * (pip_size + 4)
        color = (255, 60, 60) if i < health else (60, 30, 30)
        pygame.draw.rect(screen, color, (x, 32, pip_size, pip_size // 2))
        pygame.draw.rect(screen, (200, 200, 200), (x, 32, pip_size, pip_size // 2), 1)

def _draw_menu(selected):
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(210)
    overlay.fill((20, 13, 30))
    screen.blit(overlay, (0, 0))
    _blit_text("STORMY64", font_title, (255, 220, 100), WINDOW_WIDTH // 2, 120)
    _blit_text("B3313 — Peach's Castle", font_large, (180, 150, 170), WINDOW_WIDTH // 2, 170)
    items = ["Play Game", "Exit Game"]
    for i, item in enumerate(items):
        y = 260 + i * 60
        color = (255, 255, 120) if i == selected else (255, 240, 250)
        prefix = "> " if i == selected else "  "
        _blit_text(f"{prefix}{item}", font_large, color, WINDOW_WIDTH // 2, y)
    _blit_text("UP/DOWN  select  ENTER  confirm", font_small, (180, 150, 170), WINDOW_WIDTH // 2, 420)

def _draw_pause(selected):
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(160)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    _blit_text("PAUSED", font_title, (255, 220, 100), WINDOW_WIDTH // 2, 140)
    items = ["Resume", "Return to Menu"]
    for i, item in enumerate(items):
        y = 250 + i * 60
        color = (255, 255, 120) if i == selected else (255, 240, 250)
        prefix = "> " if i == selected else "  "
        _blit_text(f"{prefix}{item}", font_large, color, WINDOW_WIDTH // 2, y)
    _blit_text("UP/DOWN  select  ENTER  confirm", font_small, (180, 150, 170), WINDOW_WIDTH // 2, 400)

def _draw_game_over():
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(160)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    _blit_text("GAME OVER", font_title, (255, 60, 60), WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20)
    _blit_text("Press R to restart", font_large, (0, 255, 255), WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)

def _draw_course_clear(coins):
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(140)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    _blit_text("COURSE CLEAR!", font_title, (255, 220, 60), WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30)
    _blit_text(f"You got a Power Star! ({coins} red coins)", font_large, (255, 255, 255), WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20)
    _blit_text("Press R to play again", font_small, (0, 255, 255), WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60)

class Game:
    def __init__(self):
        self.state = "menu"
        self.menu_index = 0
        self.player = None
        self.level = None
        self.renderer = Renderer3D()
        self.camera = Camera()
        self.coin_count = 0
        self.health = MAX_HEALTH
        self.game_over = False
        self.course_clear = False
        self.spawn_grace = 0.0
        self.mouse_down = False
        self.last_mouse_pos = (0, 0)
        self.pause_menu_index = 0
        self.near_portal = None
        self.entering = None
        self.enter_timer = 0.0
        self.pending_portal = None
        self.map_coins = {}

    def start_game(self):
        self.state = "playing"
        self.player = Player()
        self.map_coins = {}
        self.coin_count = 0
        self.health = MAX_HEALTH
        self.game_over = False
        self.course_clear = False
        self.near_portal = None
        self.entering = None
        self.enter_timer = 0.0
        self.pending_portal = None
        self.load_map(MAP_COURTYARD, Vec3(*SPAWN_POS), 180.0)
        pygame.mouse.set_visible(True)

    def load_map(self, map_id, spawn_pos, spawn_yaw=0.0):
        """Warp into a map and place the player at spawn."""
        if self.level is not None:
            self.map_coins[self.level.map_id] = sum(1 for c in self.level.coins if c.collected)
        self.level = Level(map_id)
        saved = self.map_coins.get(map_id, 0)
        for i, coin in enumerate(self.level.coins):
            if i < saved:
                coin.collected = True
        others = sum(v for k, v in self.map_coins.items() if k != map_id)
        self.coin_count = others + sum(1 for c in self.level.coins if c.collected)
        if self.player:
            self.player.pos = Vec3(spawn_pos.x, spawn_pos.y, spawn_pos.z)
            self.player.vel_h = Vec3(0, 0, 0)
            self.player.vel_y = 0.0
            self.player.grounded = False
            self.player.face_yaw = spawn_yaw
            self.player.dive_used = False
            self.player.ground_pounding = False
        self.spawn_grace = SPAWN_GRACE_SEC
        self.course_clear = False
        self.near_portal = None
        self.entering = None
        self.enter_timer = 0.0
        self.pending_portal = None
        self.camera.target = Vec3(spawn_pos.x, spawn_pos.y, spawn_pos.z)
        self.camera.yaw = spawn_yaw
        self.camera.pitch = 18.0
        self.camera.dist = 7.5
        if sum(1 for c in self.level.coins if c.collected) >= TARGET_RED_COINS:
            self.level.spawn_star()

    def try_enter_portal(self):
        """Start enter sequence for nearest portal (called on E)."""
        if not self.player or not self.level or self.pending_portal:
            return False
        portal = self.level.nearest_portal(self.player.pos)
        if not portal:
            return False
        self.near_portal = portal
        self.pending_portal = portal
        self.entering = f"Entering {portal.label}..."
        self.enter_timer = 0.85
        return True

    def restart(self):
        self.start_game()

    def return_to_menu(self):
        self.state = "menu"
        self.player = None
        self.level = None
        pygame.mouse.set_visible(True)

    def handle_event(self, event):
        if self.state == "menu":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.menu_index = (self.menu_index - 1) % 2
                elif event.key == pygame.K_DOWN:
                    self.menu_index = (self.menu_index + 1) % 2
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.menu_index == 0:
                        self.start_game()
                    elif self.menu_index == 1:
                        return "quit"
            return
        if self.state == "pause":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    self.state = "playing"
                elif event.key == pygame.K_UP:
                    self.pause_menu_index = (self.pause_menu_index - 1) % 2
                elif event.key == pygame.K_DOWN:
                    self.pause_menu_index = (self.pause_menu_index + 1) % 2
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.pause_menu_index == 0:
                        self.state = "playing"
                    elif self.pause_menu_index == 1:
                        self.return_to_menu()
            return
        if self.state == "playing":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    self.state = "pause"
                    self.pause_menu_index = 0
                    return
                if event.key == pygame.K_SPACE:
                    if self.player and self.player.alive:
                        self.player.jump_held = True
                        self.player.jump(self.camera.yaw)
                if event.key in (pygame.K_x, pygame.K_LCTRL, pygame.K_RCTRL):
                    if self.player:
                        if self.player.grounded:
                            self.player.punch()
                        elif self.player.alive:
                            self.player.try_dive(self.camera.yaw)
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    if self.player and not self.player.grounded and self.player.alive:
                        self.player.ground_pound()
                if event.key == pygame.K_r:
                    if self.game_over or self.course_clear:
                        self.start_game()
                    elif self.player:
                        self.camera.yaw = self.player.face_yaw
                # C-stick camera (arrows)
                if event.key == pygame.K_UP:
                    self.camera.pitch = max(-45, self.camera.pitch - 2)
                if event.key == pygame.K_DOWN:
                    self.camera.pitch = min(85, self.camera.pitch + 2)
                if event.key == pygame.K_LEFT:
                    self.camera.yaw += 3
                if event.key == pygame.K_RIGHT:
                    self.camera.yaw -= 3
                # Q/E camera rotate (E also enters doors/paintings → next map)
                if event.key == pygame.K_q:
                    self.camera.yaw += 3
                if event.key == pygame.K_e:
                    if not self.try_enter_portal():
                        self.camera.yaw -= 3
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE and self.player:
                    self.player.jump_held = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:
                    self.mouse_down = True
                    self.last_mouse_pos = pygame.mouse.get_pos()
                    pygame.mouse.set_visible(False)
                elif event.button == 4:
                    self.camera.zoom_delta += 1.0
                elif event.button == 5:
                    self.camera.zoom_delta -= 1.0
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    self.mouse_down = False
                    pygame.mouse.set_visible(True)
            if event.type == pygame.MOUSEMOTION and self.mouse_down:
                dx = event.rel[0]
                self.camera.yaw -= dx * 0.5

    def update(self, dt):
        if self.state == "pause":
            return
        if self.state != "playing" or not self.player or not self.level:
            return
        if self.game_over or self.course_clear:
            return

        # Finish portal warp after short enter message
        if self.pending_portal is not None:
            if self.enter_timer > 0:
                self.enter_timer = max(0.0, self.enter_timer - dt)
            if self.enter_timer <= 0:
                p = self.pending_portal
                self.load_map(p.target_map, p.spawn, p.spawn_yaw)
                return
            # Freeze movement while the enter message is on screen
            self.camera.target = lerp_v3(self.camera.target, self.player.pos, dt * 8)
            self.camera.update(dt)
            return

        if self.spawn_grace > 0:
            self.spawn_grace = max(0.0, self.spawn_grace - dt)

        self.player.update(dt, self.camera.yaw, self.level.solid_boxes)
        self.camera.target = lerp_v3(self.camera.target, self.player.pos, dt * 8)
        self.camera.update(dt)
        for coin in self.level.coins:
            coin.update(dt)
        for boo in self.level.boos:
            boo.update(dt)
        for coin in self.level.coins:
            if not coin.collected:
                d = (coin.pos - self.player.pos).length()
                if d < 1.25:
                    coin.collected = True
                    self.coin_count += 1
                    if sum(1 for c in self.level.coins if c.collected) >= TARGET_RED_COINS:
                        self.level.spawn_star()
        if self.level.star_active and self.player.alive:
            d = (self.level.star_pos - self.player.pos).length()
            if d < 2.2:
                self.course_clear = True
        for boo in self.level.boos:
            if boo.alive and self.player.alive and self.player.invuln_timer <= 0:
                d = (boo.pos - self.player.pos).length()
                if d < ENEMY_HIT_RADIUS:
                    push = (self.player.pos - boo.pos).normalize() * 4.5
                    self.player.pos += Vec3(push.x, 0, push.z)
                    if self.player.take_damage(HIT_DAMAGE):
                        self.game_over = True

        self.near_portal = self.level.nearest_portal(self.player.pos) if self.player else None

    def render(self):
        if self.state == "menu":
            screen.fill((30, 20, 50))
            _draw_menu(self.menu_index)
            return
        sky = self.level.sky if self.level else C_SKY
        if self.state == "pause":
            self.renderer.clear(sky)
            self._render_world()
            self.renderer.present()
            _draw_hud(self.coin_count, self.player.health if self.player else 0, True)
            _draw_pause(self.pause_menu_index)
            return
        if self.state != "playing":
            return
        self.renderer.clear(sky)
        self._render_world()
        self.renderer.present()
        _draw_hud(self.coin_count, self.player.health if self.player else 0, True)
        if self.level:
            _blit_text(self.level.name, font_small, (220, 220, 255), WINDOW_WIDTH // 2, 52)
        if self.entering:
            _blit_text(self.entering, font_large, (255, 220, 60), WINDOW_WIDTH // 2, WINDOW_HEIGHT - 80)
        elif self.near_portal:
            _blit_text(
                f"{self.near_portal.label} — Press E to enter",
                font_small, (255, 255, 255), WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40,
            )
        if self.game_over:
            _draw_game_over()
        if self.course_clear:
            _draw_course_clear(self.coin_count)

    def _render_world(self):
        meshes = list(self.level.meshes)
        for coin in self.level.coins:
            if not coin.collected:
                meshes.append((coin.pos, coin.get_tris(), None))
        for boo in self.level.boos:
            if boo.alive:
                meshes.append((boo.pos, boo.get_tris(), None))
        if self.level.star_active:
            meshes.append((self.level.star_pos, self.level.get_star_tris(), None))
        if self.player and self.player.alive:
            meshes.append((Vec3(0, 0, 0), self.player.get_tris(), None))
        self.renderer.render_meshes(meshes, self.camera)

def main():
    game = Game()
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            result = game.handle_event(event)
            if result == "quit":
                running = False
        game.update(min(dt, 0.05))
        game.render()
        fps = clock.get_fps()
        _blit_text(f"{fps:.0f} FPS", font_small, (100, 100, 100), WINDOW_WIDTH - 50, 10, True)
        pygame.display.flip()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("Press Enter to close...")
