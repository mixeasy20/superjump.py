import pygame
import sys
import random
import math

pygame.init()
pygame.mixer.init()

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1024, 600
FPS = 60

# Colors
SKY_TOP       = (20,  20,  60)
SKY_BOT       = (60,  40, 120)
WHITE         = (255, 255, 255)
BLACK         = (0,   0,   0)
GROUND_COL    = (80,  50,  20)
GRASS_COL     = (50, 160,  50)
PLAT_COL      = (100, 70,  30)
PLAT_TOP      = (70, 180,  70)
PLAYER_COL    = (70, 130, 220)
ENEMY_COL     = (200,  50,  50)
ENEMY_EYE     = (255, 255, 100)
COIN_COL      = (255, 215,   0)
SPEED_COL     = (100, 255, 200)
HP_RED        = (200,  30,  30)
HP_GREEN      = (50,  200,  50)
SCORE_COL     = (255, 240, 100)
STAR_COL      = (255, 255, 200)
SPIKE_COL     = (160, 160, 160)
BULLET_COL    = (255, 255, 50)

# Physics
GRAVITY      = 0.55
JUMP_FORCE   = -13.5
WALK_SPEED   = 5
RUN_SPEED    = 9
NORMAL_SPEED = 5
BOOST_SECS   = 8

# ── Utility ────────────────────────────────────────────────────────────────────
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("🌟 SuperPlatformer  —  นายทำได้เว้ยยย!")
clock = pygame.time.Clock()

# Thai-compatible fonts
_TH_FONTS = ["leelawadeeui", "leelawadee", "tahoma", "microsoft sans serif"]
def _thai_font(size, bold=False):
    for name in _TH_FONTS:
        f = pygame.font.SysFont(name, size, bold=bold)
        if f is not None:
            return f
    return pygame.font.SysFont(None, size, bold=bold)

font_big   = _thai_font(48, bold=True)
font_med   = _thai_font(28, bold=True)
font_small = _thai_font(20)
font_tiny  = _thai_font(16)

def draw_text_shadow(surf, text, font, color, x, y, shadow=(0,0,0)):
    s = font.render(text, True, shadow)
    surf.blit(s, (x+2, y+2))
    t = font.render(text, True, color)
    surf.blit(t, (x, y))

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))

# ── World Camera ───────────────────────────────────────────────────────────────
class Camera:
    def __init__(self):
        self.offset_x = 0
    def update(self, target_x):
        ideal = target_x - SCREEN_W // 3
        self.offset_x += (ideal - self.offset_x) * 0.12
    def apply(self, rect):
        return pygame.Rect(rect.x - self.offset_x, rect.y, rect.width, rect.height)

# ── Particles ──────────────────────────────────────────────────────────────────
particles = []
def emit_particles(x, y, color, n=8, speed=3):
    for _ in range(n):
        angle = random.uniform(0, math.tau)
        spd   = random.uniform(1, speed)
        particles.append({
            'x': x, 'y': y,
            'vx': math.cos(angle)*spd,
            'vy': math.sin(angle)*spd - random.uniform(1,3),
            'life': random.randint(20,40),
            'color': color,
            'r': random.randint(3,7)
        })

def update_particles(surf, cam):
    for p in particles[:]:
        p['x'] += p['vx']
        p['y'] += p['vy']
        p['vy'] += 0.15
        p['life'] -= 1
        alpha = max(0, p['life'] / 40)
        col = tuple(int(c*alpha) for c in p['color'][:3])
        sx = int(p['x'] - cam.offset_x)
        sy = int(p['y'])
        if 0 <= sx <= SCREEN_W and 0 <= sy <= SCREEN_H:
            pygame.draw.circle(surf, col, (sx, sy), p['r'])
        if p['life'] <= 0:
            particles.remove(p)

stars = [(random.randint(0, SCREEN_W), random.randint(0, SCREEN_H//2),
          random.uniform(0.5, 2.5)) for _ in range(120)]

def draw_sky(surf):
    for y in range(SCREEN_H):
        t = y / SCREEN_H
        col = lerp_color(SKY_TOP, SKY_BOT, t)
        pygame.draw.line(surf, col, (0, y), (SCREEN_W, y))
    for sx, sy, r in stars:
        twinkle = 0.6 + 0.4*math.sin(pygame.time.get_ticks()*0.003 + sx)
        col = tuple(int(c*twinkle) for c in STAR_COL)
        pygame.draw.circle(surf, col, (sx, sy), int(r))

# ── Weapons ────────────────────────────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, facing_right):
        self.rect = pygame.Rect(x, y - 10, 12, 6)
        self.vx = 15 if facing_right else -15
        self.life = 60

    def update(self):
        self.rect.x += self.vx
        self.life -= 1

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        pygame.draw.rect(surf, BULLET_COL, r, border_radius=3)
        pygame.draw.rect(surf, WHITE, pygame.Rect(r.x+2, r.y+2, r.w-4, r.h-4))

class Spike:
    def __init__(self, x, y, w=30):
        self.rect = pygame.Rect(x, y, w, 20)
        self.pts = []

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        self.pts = []
        spikes_count = max(1, self.rect.w // 10)
        w_per_spike = self.rect.w / spikes_count
        for i in range(spikes_count):
            lx = r.x + i*w_per_spike
            rx = r.x + (i+1)*w_per_spike
            mx = (lx + rx) / 2
            pygame.draw.polygon(surf, SPIKE_COL, [(lx, r.bottom), (mx, r.top), (rx, r.bottom)])
            pygame.draw.polygon(surf, WHITE, [(lx+1, r.bottom), (mx, r.top+2), (rx-1, r.bottom)], 1)

# ── Player ─────────────────────────────────────────────────────────────────────
class Player:
    W, H = 36, 48

    def __init__(self):
        self.rect   = pygame.Rect(80, 100, self.W, self.H)
        self.vx     = 0
        self.vy     = 0
        self.on_ground = False
        
        # Persistent stats (keep between levels)
        self.hp         = 100
        self.coins      = 0
        self.score      = 0
        self.has_sword  = False
        self.ammo       = 0
        
        # State stats
        self.speed  = NORMAL_SPEED
        self.boost_timer = 0
        self.invincible  = 0
        self.facing_right = True
        self.anim_frame = 0
        self.anim_timer = 0
        self.dead = False
        self.jump_count = 0
        self.slash_timer = 0
        self.slash_rect = None

    def reset_for_level(self, x, y):
        self.rect.x = x
        self.rect.y = y
        self.vx = 0
        self.vy = 0
        self.speed = NORMAL_SPEED
        self.boost_timer = 0
        self.invincible = 0
        self.slash_timer = 0
        self.dead = False

    @property
    def boosted(self): return self.boost_timer > 0

    def apply_boost(self):
        self.boost_timer = BOOST_SECS * FPS
        self.speed = RUN_SPEED

    def take_damage(self, amount=5):
        if self.invincible > 0: return
        self.hp -= amount
        self.invincible = 60
        emit_particles(self.rect.centerx, self.rect.centery, HP_RED, 10, 4)
        if self.hp <= 0:
            self.hp = 0
            self.dead = True

    def slash(self):
        if not self.has_sword or self.slash_timer > 0: return
        self.slash_timer = 20
        # Create hitbox
        sx = self.rect.right if self.facing_right else self.rect.left - 40
        self.slash_rect = pygame.Rect(sx, self.rect.y+10, 40, 30)

    def shoot(self, bullets):
        if self.ammo > 0:
            self.ammo -= 1
            bx = self.rect.right if self.facing_right else self.rect.left - 12
            bullets.append(Bullet(bx, self.rect.centery, self.facing_right))

    def update(self, platforms, spikes, enemies):
        keys = pygame.key.get_pressed()

        # Horizontal
        dx = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            dx = -self.speed
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = +self.speed
            self.facing_right = True

        # Timers
        if self.boost_timer > 0:
            self.boost_timer -= 1
            if self.boost_timer == 0: self.speed = NORMAL_SPEED
        if self.invincible > 0: self.invincible -= 1
        
        if self.slash_timer > 0:
            self.slash_timer -= 1
            sx = self.rect.right if self.facing_right else self.rect.left - 40
            self.slash_rect = pygame.Rect(sx, self.rect.y+10, 40, 30)
            if self.slash_timer == 0:
                self.slash_rect = None

        # Gravity
        self.vy += GRAVITY
        if self.vy > 18: self.vy = 18

        # Move X
        self.rect.x += dx
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if dx > 0: self.rect.right = p.rect.left
                elif dx < 0: self.rect.left = p.rect.right

        # Move Y
        self.on_ground = False
        self.rect.y += self.vy
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vy > 0:
                    self.rect.bottom = p.rect.top
                    self.vy = 0
                    self.on_ground = True
                    self.jump_count = 0
                elif self.vy < 0:
                    self.rect.top = p.rect.bottom
                    self.vy = 0

        # Boundary checks
        if self.rect.left < 0: self.rect.left = 0
        if self.rect.top > SCREEN_H + 50:
            self.hp = 0
            self.dead = True

        # Spike Collisions
        for s in spikes:
            if self.rect.colliderect(s.rect):
                self.take_damage(10) # 10 dmg from spikes
                self.vy = -8 # bounce
                self.rect.y -= 10

        # Sword hits
        if self.slash_rect:
            for e in enemies:
                if e.alive and self.slash_rect.colliderect(e.rect):
                    e.alive = False
                    self.score += 50
                    self.coins += 5 # Bonus coin for sword kill
                    emit_particles(e.rect.centerx, e.rect.centery, ENEMY_COL, 14, 5)

        # Anim
        self.anim_timer += 1
        if self.anim_timer > 8:
            self.anim_frame = (self.anim_frame + 1) % 4
            self.anim_timer = 0

    def jump(self):
        if self.jump_count < 2:
            self.vy = JUMP_FORCE if self.jump_count == 0 else JUMP_FORCE * 0.8
            self.jump_count += 1
            emit_particles(self.rect.centerx, self.rect.bottom, (200,200,255), 6, 2)

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        if self.invincible > 0 and (self.invincible // 5) % 2: return

        # Shadow
        pygame.draw.ellipse(surf, (0,0,0,60), pygame.Rect(r.x+3, r.bottom-6, r.w-6, 10))

        # Body
        body_col = (100, 240, 220) if self.boosted else PLAYER_COL
        leg_offset = int(math.sin(self.anim_frame * math.pi / 2) * 5) if not self.on_ground else 0
        pygame.draw.rect(surf, body_col, r, border_radius=8)

        # Belt
        belt_y = r.y + r.h*2//3
        pygame.draw.rect(surf, (50,50,180), pygame.Rect(r.x, belt_y, r.w, 8), border_radius=4)

        # Eyes
        eye_x = r.x + (r.w*2//3 if self.facing_right else r.w//3 - 8)
        pygame.draw.circle(surf, WHITE, (eye_x+4, r.y+14), 7)
        pygame.draw.circle(surf, (30,30,30),(eye_x+5, r.y+15), 4)

        # Legs
        lx = r.x + 4
        rx = r.x + r.w//2 + 2
        foot_y = r.bottom - 2
        pygame.draw.rect(surf, (40,40,140), pygame.Rect(lx, foot_y-12+leg_offset, r.w//2-6, 14), border_radius=5)
        pygame.draw.rect(surf, (40,40,140), pygame.Rect(rx, foot_y-12-leg_offset, r.w//2-6, 14), border_radius=5)

        # Boost aura
        if self.boosted:
            t = pygame.time.get_ticks() * 0.005
            for i in range(6):
                angle = t + i * math.pi / 3
                ax = r.centerx + int(math.cos(angle) * (r.w//2 + 8))
                ay = r.centery + int(math.sin(angle) * (r.h//2 + 8))
                pygame.draw.circle(surf, SPEED_COL, (ax, ay), 5)
        
        # Sword slash
        if self.slash_timer > 0 and self.slash_rect:
            sr = cam.apply(self.slash_rect)
            sw_color = (200, 200, 200, 150)
            sw_surf = pygame.Surface((sr.w, sr.h), pygame.SRCALPHA)
            pygame.draw.ellipse(sw_surf, sw_color, (0,0, sr.w, sr.h))
            surf.blit(sw_surf, (sr.x, sr.y))

# ── Environment ────────────────────────────────────────────────────────────────
class Platform:
    def __init__(self, x, y, w, h=18, moving=False, move_range=100, move_speed=2):
        self.rect   = pygame.Rect(x, y, w, h)
        self.moving = moving
        self.origin_x = x
        self.move_range = move_range
        self.move_speed = move_speed
        self.move_dir   = 1

    def update(self):
        if self.moving:
            self.rect.x += self.move_speed * self.move_dir
            if abs(self.rect.x - self.origin_x) >= self.move_range:
                self.move_dir *= -1

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        if r.right < 0 or r.left > SCREEN_W: return # Frustum cull

        pygame.draw.rect(surf, PLAT_COL, r, border_radius=6)
        top = pygame.Rect(r.x, r.y, r.w, 7)
        pygame.draw.rect(surf, PLAT_TOP, top, border_radius=6)
        for i in range(1, r.w//30):
            lx = r.x + i*30
            pygame.draw.line(surf, (60,35,10), (lx, r.y+8), (lx, r.bottom-2))

class Ground:
    def __init__(self, world_w):
        self.rect = pygame.Rect(0, SCREEN_H-60, world_w, 60)
    def update(self): pass
    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        pygame.draw.rect(surf, GROUND_COL, r)
        grass = pygame.Rect(r.x, r.y, r.w, 14)
        pygame.draw.rect(surf, GRASS_COL, grass)
        for gx in range(int(cam.offset_x) % 20, SCREEN_W, 20):
            gy = SCREEN_H - 60
            pygame.draw.line(surf, (40,140,40), (gx, gy), (gx-4, gy-8), 2)
            pygame.draw.line(surf, (40,140,40), (gx+4, gy), (gx+8, gy-6), 2)

class Coin:
    def __init__(self, x, y):
        self.rect      = pygame.Rect(x, y, 22, 22)
        self.collected = False
        self.anim      = random.uniform(0, math.tau)
    def update(self): self.anim += 0.07
    def draw(self, surf, cam):
        if self.collected: return
        r = cam.apply(self.rect)
        if r.right < 0 or r.left > SCREEN_W: return
        bob_y = int(math.sin(self.anim) * 4)
        cx, cy = r.centerx, r.centery + bob_y
        for radius, alpha in [(14, 40), (11, 80)]:
            s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*COIN_COL, alpha), (radius, radius), radius)
            surf.blit(s, (cx-radius, cy-radius))
        pygame.draw.circle(surf, COIN_COL, (cx, cy), 9)
        pygame.draw.circle(surf, (255,240,120), (cx-2, cy-2), 5)
        lbl = font_tiny.render("$", True, (180,130,0))
        surf.blit(lbl, (cx - lbl.get_width()//2, cy - lbl.get_height()//2))

class SpeedItem:
    def __init__(self, x, y):
        self.rect      = pygame.Rect(x, y, 28, 28)
        self.collected = False
        self.anim      = random.uniform(0, math.tau)
    def update(self): self.anim += 0.09
    def draw(self, surf, cam):
        if self.collected: return
        r  = cam.apply(self.rect)
        if r.right < 0 or r.left > SCREEN_W: return
        t  = self.anim
        cx, cy = r.centerx, r.centery + int(math.sin(t)*5)
        for i in range(6):
            angle = t + i * math.pi / 3
            gx = cx + int(math.cos(angle) * 16)
            gy = cy + int(math.sin(angle) * 16)
            pygame.draw.circle(surf, (80, 255, 180), (gx, gy), 4)
        pygame.draw.circle(surf, SPEED_COL, (cx, cy), 12)
        pygame.draw.circle(surf, WHITE,     (cx-3, cy-3), 5)
        lbl = font_tiny.render("⚡", True, (0, 100, 60))
        surf.blit(lbl, (cx - lbl.get_width()//2, cy - lbl.get_height()//2))

class Enemy:
    W, H = 36, 36
    def __init__(self, x, y, platforms, speed=1.8):
        self.rect      = pygame.Rect(x, y, self.W, self.H)
        self.vy        = 0
        self.on_ground = False
        self.speed     = speed
        self.dir       = random.choice([-1, 1])
        self.platforms = platforms
        self.alive     = True
        self.anim      = 0
        self.stomp_cooldown = 0

    def update(self, player):
        if not self.alive: return
        self.anim += 1
        if self.stomp_cooldown > 0: self.stomp_cooldown -= 1

        self.vy += GRAVITY
        if self.vy > 18: self.vy = 18

        self.rect.x += self.dir * self.speed
        for p in self.platforms:
            if self.rect.colliderect(p.rect):
                if self.dir > 0: self.rect.right = p.rect.left
                else: self.rect.left = p.rect.right
                self.dir *= -1

        self.on_ground = False
        self.rect.y += self.vy
        for p in self.platforms:
            if self.rect.colliderect(p.rect):
                if self.vy > 0:
                    self.rect.bottom = p.rect.top
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = p.rect.bottom
                    self.vy = 0

        if self.rect.top > SCREEN_H + 80:
            self.alive = False
            return

        # Player col
        if self.rect.colliderect(player.rect) and self.stomp_cooldown == 0:
            if player.vy > 0 and player.rect.bottom <= self.rect.centery + 12:
                self.alive = False
                player.vy  = JUMP_FORCE * 0.7
                player.score += 50
                player.coins += 2
                emit_particles(self.rect.centerx, self.rect.centery, ENEMY_COL, 14, 5)
            else:
                player.take_damage(5)
                self.stomp_cooldown = 30

    def draw(self, surf, cam):
        if not self.alive: return
        r  = cam.apply(self.rect)
        if r.right < 0 or r.left > SCREEN_W: return

        pygame.draw.ellipse(surf, ENEMY_COL, r)
        for i in range(5):
            angle = -math.pi/2 + (i - 2) * 0.4
            sx = r.centerx + int(math.cos(angle) * (r.w//2 + 6))
            sy = r.centery + int(math.sin(angle) * (r.h//2 + 2)) - 5
            pygame.draw.circle(surf, (160, 20, 20), (sx, sy), 5)
        eye_lx = r.centerx - 9
        eye_rx = r.centerx + 9
        eye_y  = r.centery - 4
        pygame.draw.circle(surf, ENEMY_EYE, (eye_lx, eye_y), 6)
        pygame.draw.circle(surf, ENEMY_EYE, (eye_rx, eye_y), 6)
        pygame.draw.circle(surf, BLACK, (eye_lx+1, eye_y+1), 3)
        pygame.draw.circle(surf, BLACK, (eye_rx+1, eye_y+1), 3)
        pygame.draw.line(surf, BLACK, (eye_lx-5, eye_y-7), (eye_lx+5, eye_y-3), 2)
        pygame.draw.line(surf, BLACK, (eye_rx-5, eye_y-3), (eye_rx+5, eye_y-7), 2)
        mouth_pts = [(r.centerx-7, r.centery+8), (r.centerx, r.centery+12), (r.centerx+7, r.centery+8)]
        pygame.draw.lines(surf, BLACK, False, mouth_pts, 2)

# ── HUD & Screens ──────────────────────────────────────────────────────────────
def draw_hud(surf, player, level_num):
    # HP Bar
    bar_w, bar_h = 220, 22
    bx, by = 16, 16
    pygame.draw.rect(surf, (40,10,10), (bx-2, by-2, bar_w+4, bar_h+4), border_radius=12)
    pygame.draw.rect(surf, (80,20,20), (bx, by, bar_w, bar_h), border_radius=10)
    pct = max(0, player.hp / 100)
    fill = int(bar_w * pct)
    if fill > 0:
        hcol = lerp_color(HP_RED, HP_GREEN, pct)
        pygame.draw.rect(surf, hcol, (bx, by, fill, bar_h), border_radius=10)
    pygame.draw.rect(surf, (255,255,255,60), (bx, by, bar_w, bar_h//3), border_radius=10)
    
    surf.blit(font_small.render(f"HP  {int(player.hp)}/100", True, WHITE), (bx+8, by+2))

    by2 = by + bar_h + 10
    # Level & Coins & Score
    draw_text_shadow(surf, f"ด่านที่: {level_num}/5", font_med, WHITE, 16, by2)
    draw_text_shadow(surf, f"💰 เหรียญ: {player.coins}", font_med, COIN_COL, 180, by2)
    
    score_lbl = font_med.render(f"SCORE  {player.score:06d}", True, SCORE_COL)
    sx = SCREEN_W - score_lbl.get_width() - 16
    draw_text_shadow(surf, f"SCORE  {player.score:06d}", font_med, SCORE_COL, sx, 16)

    by3 = by2 + 35
    # Weapons status
    if player.has_sword:
        draw_text_shadow(surf, "🗡️ มีดาบ (กด Z)", font_small, (220,220,220), 20, by3)
    if player.ammo > 0:
        draw_text_shadow(surf, f"🔫 ปืน ({player.ammo}/10 นัด) (กด X)", font_small, BULLET_COL, 180, by3)

    # Boost timer
    if player.boosted:
        boost_w = int(bar_w * (player.boost_timer / (BOOST_SECS*FPS)))
        by4 = by3 + 30
        pygame.draw.rect(surf, (0,60,50), (bx-2, by4-2, bar_w+4, 18), border_radius=8)
        pygame.draw.rect(surf, (0,120,90),(bx, by4, boost_w, 14), border_radius=6)
        surf.blit(font_tiny.render("⚡ SPEED BOOST", True, SPEED_COL), (bx+6, by4-1))


def draw_shop_menu(surf, player):
    s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    s.fill((0, 0, 0, 200))
    surf.blit(s, (0,0))

    cx = SCREEN_W // 2
    draw_text_shadow(surf, "🛒 ร้านค้าลับหลังฉาก 🛒", font_big, SPEED_COL, cx - 210, 100)
    draw_text_shadow(surf, f"เก็บเหรียญมาได้: {player.coins} 💰", font_med, COIN_COL, cx - 120, 180)

    # Calculate status colors
    c1 = WHITE if player.coins >= 20 and player.hp < 100 else (100,100,100)
    c2 = WHITE if player.coins >= 50 and not player.has_sword else (100,100,100)
    c3 = WHITE if player.coins >= 40 and player.ammo < 10 else (100,100,100)

    items = [
        ("1. เลือด 50 HP (ราคา 20)", HP_GREEN, c1),
        ("2. ดาบปราบทรชน (ราคา 50)" if not player.has_sword else "2. มีดาบแล้ว", (200,200,200), c2),
        (f"3. กระสุน 10 นัด (ราคา 40)" if player.ammo < 10 else "3. กระสุนเต็มแล้ว", BULLET_COL, c3),
    ]

    for i, (txt, icon_col, text_col) in enumerate(items):
        pygame.draw.circle(surf, icon_col, (cx - 180, 275 + i*50), 8)
        lbl = font_med.render(txt, True, text_col)
        surf.blit(lbl, (cx - 150, 260 + i*50))

    hint1 = font_small.render("กดแป้นเลข 1, 2, 3 เพื่อเปย์ของให้ตัวเอง", True, WHITE)
    hint2 = font_med.render("พร้อมแล้ว กด ENTER เพื่อสู้ต่อในด่านถัดไป ➔", True, (100,255,100))
    surf.blit(hint1, (cx - hint1.get_width()//2, 450))
    surf.blit(hint2, (cx - hint2.get_width()//2, 500))

# ── Level Generator ────────────────────────────────────────────────────────────
def build_level(level_num):
    # Scale width and difficulty based on level
    world_w = 4000 + (level_num * 1000)
    ground = Ground(world_w)
    platforms = [ground]
    coins = []
    speed_items = []
    enemies = []
    spikes = []

    # Procedural gen
    curr_x = 200
    while curr_x < world_w - 500:
        w = random.randint(80, 180)
        
        # Difficulty scales gap and moving chance
        gap_min = 60 + level_num*10
        gap_max = 160 + level_num*20
        gap = random.randint(gap_min, gap_max)
        
        moving = random.random() < (0.1 * level_num)
        y = random.randint(200, 480)
        p = Platform(curr_x, y, w, moving=moving, move_range=w, move_speed=1+level_num*0.5)
        platforms.append(p)

        # Spikes (on ground below gap or on platform)
        if level_num >= 2 and random.random() < 0.3:
            spikes.append(Spike(curr_x + w//2 - 15, p.rect.top - 20, 30))
        if level_num >= 3 and random.random() < 0.4:
            sw = random.randint(30, 90)
            spikes.append(Spike(curr_x + w + 10, SCREEN_H - 80, sw)) # Spikes on ground

        # Coins
        for j in range(random.randint(1, 4)):
            cx = p.rect.x + 15 + j * 35
            if cx < p.rect.right - 15:
                coins.append(Coin(cx, p.rect.y - 32))

        # Speed item
        if random.random() < 0.15:
            speed_items.append(SpeedItem(p.rect.centerx, p.rect.y - 38))

        # Enemies (scale with level)
        enemy_chance = 0.3 + (level_num * 0.1)
        if p.rect.w >= 100 and random.random() < enemy_chance:
            ex = p.rect.x + random.randint(10, p.rect.w - 50)
            enemies.append(Enemy(ex, p.rect.y - Enemy.H, platforms, speed=random.uniform(1.0 + level_num*0.3, 2.5 + level_num*0.3)))
        
        curr_x += w + gap

    # End platform (safe zone)
    platforms.append(Platform(world_w - 400, 300, 400, moving=False))
    
    # Ground enemies
    for gx in range(400, world_w - 500, max(250, 800 - level_num*100)):
        enemies.append(Enemy(gx, SCREEN_H - 60 - Enemy.H, platforms, speed=random.uniform(1.5, 3.5)))

    return platforms, coins, speed_items, enemies, spikes, world_w

# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    state = "start"
    level_num = 1
    player = Player()
    
    platforms = []
    coins = []
    speed_items = []
    enemies = []
    spikes = []
    bullets = []
    world_w = 6000
    cam = Camera()

    def start_level():
        nonlocal platforms, coins, speed_items, enemies, spikes, bullets, world_w, cam
        particles.clear()
        platforms, coins, speed_items, enemies, spikes, world_w = build_level(level_num)
        bullets.clear()
        player.reset_for_level(80, SCREEN_H - 150)
        cam = Camera()

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if state == "start":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        player = Player() # Reset overall stats
                        level_num = 1
                        start_level()
                        state = "play"

                elif state == "play":
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        player.jump()
                    if event.key == pygame.K_z:
                        player.slash()
                    if event.key == pygame.K_x:
                        player.shoot(bullets)
                    if event.key == pygame.K_ESCAPE:
                        sys.exit()

                elif state == "shop":
                    if event.key == pygame.K_1:
                        if player.coins >= 20 and player.hp < 100:
                            player.coins -= 20
                            player.hp = min(100, player.hp + 50)
                    if event.key == pygame.K_2:
                        if player.coins >= 50 and not player.has_sword:
                            player.coins -= 50
                            player.has_sword = True
                    if event.key == pygame.K_3:
                        if player.coins >= 40 and player.ammo < 10:
                            player.coins -= 40
                            player.ammo = 10
                    if event.key == pygame.K_RETURN:
                        level_num += 1
                        if level_num > 5:
                            state = "win"
                        else:
                            start_level()
                            state = "play"

                elif state in ("dead", "win"):
                    if event.key == pygame.K_r:
                        state = "start"
                    if event.key == pygame.K_ESCAPE:
                        sys.exit()

        # Update
        if state == "play":
            player.update(platforms, spikes, enemies)
            for p in platforms: p.update()
            
            for c in coins:
                c.update()
                if not c.collected and player.rect.colliderect(c.rect):
                    c.collected = True
                    player.score += 10
                    player.coins += 2
                    emit_particles(c.rect.centerx, c.rect.centery, COIN_COL, 8, 3)

            for si in speed_items:
                si.update()
                if not si.collected and player.rect.colliderect(si.rect):
                    si.collected = True
                    player.apply_boost()
                    emit_particles(si.rect.centerx, si.rect.centery, SPEED_COL, 16, 5)

            for e in enemies: e.update(player)

            for b in bullets[:]:
                b.update()
                hit = False
                # Ground / Platform check for bullet (optional, but good for feel)
                for e in enemies:
                    if e.alive and b.rect.colliderect(e.rect):
                        e.alive = False
                        player.score += 50
                        player.coins += 5 # bonus coin
                        emit_particles(e.rect.centerx, e.rect.centery, ENEMY_COL, 14, 5)
                        hit = True
                        break
                if hit or b.life <= 0:
                    try: bullets.remove(b)
                    except ValueError: pass

            cam.update(player.rect.x)

            # Reached end
            if player.rect.x > world_w - 200:
                player.score += 1000 * level_num
                state = "shop"

            if player.dead:
                state = "dead"

        # Draw
        draw_sky(screen)

        if state == "start":
            title = font_big.render("🌟 SUPER PLATFORMER", True, SCORE_COL)
            ctrl = font_med.render("เดิน: วิ่งซ้ายขวา | กระโดด: SPACE | ดาบ: F | ปืน: G", True, WHITE)
            msg = font_med.render("กด ENTER เพื่อลุยด่าน 1!", True, SPEED_COL)
            screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 150))
            screen.blit(ctrl, (SCREEN_W//2 - ctrl.get_width()//2, 280))
            screen.blit(msg, (SCREEN_W//2 - msg.get_width()//2, 400))

        elif state in ["play", "shop"]:
            for p in platforms: p.draw(screen, cam)
            for s in spikes: s.draw(screen, cam)
            for c in coins: c.draw(screen, cam)
            for si in speed_items: si.draw(screen, cam)
            for e in enemies: e.draw(screen, cam)
            for b in bullets: b.draw(screen, cam)
            
            update_particles(screen, cam)
            player.draw(screen, cam)
            draw_hud(screen, player, level_num)

            if state == "shop":
                draw_shop_menu(screen, player)

        elif state == "dead":
            msg = font_big.render("💀 Game Over ว้ายยยแพ้", True, HP_RED)
            sc = font_med.render(f"คะแนน: {player.score:06d} (มาถึงด่าน {level_num})", True, WHITE)
            rst = font_med.render("กด R เพื่อเริ่มเกมใหม่หมด", True, (200,200,255))
            for i, lbl in enumerate([msg, sc, rst]):
                screen.blit(lbl, (SCREEN_W//2 - lbl.get_width()//2, SCREEN_H//2 - 60 + i*60))
                
        elif state == "win":
            msg = font_big.render("🎉 ยินดีด้วย คุณเคลียร์ทั้ง 5 ด่าน!", True, SCORE_COL)
            sc = font_med.render(f"คะแนนสุดยอด: {player.score:06d}", True, WHITE)
            rst = font_med.render("กด R เพื่อเล่นอีกครั้ง", True, SPEED_COL)
            for i, lbl in enumerate([msg, sc, rst]):
                screen.blit(lbl, (SCREEN_W//2 - lbl.get_width()//2, SCREEN_H//2 - 60 + i*60))

        pygame.display.flip()

if __name__ == "__main__":
    main()
