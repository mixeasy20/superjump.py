import pygame
import sys
import random
import math
import os

pygame.init()
pygame.mixer.init()

# ── Constants ──────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1024, 600
FPS = 60
TOTAL_LEVELS = 8

# Colors
SKY_TOP      = (20,  20,  60)
SKY_BOT      = (60,  40, 120)
WHITE        = (255, 255, 255)
BLACK        = (0,   0,   0)
GROUND_COL   = (80,  50,  20)
GRASS_COL    = (50, 160,  50)
PLAT_COL     = (100, 70,  30)
PLAT_TOP     = (70, 180,  70)
PLAYER_COL   = (70, 130, 220)
ENEMY_COL    = (200,  50,  50)
ENEMY_EYE    = (255, 255, 100)
COIN_COL     = (255, 215,   0)
SPEED_COL    = (100, 255, 200)
HP_RED       = (200,  30,  30)
HP_GREEN     = (50,  200,  50)
SCORE_COL    = (255, 240, 100)
STAR_COL     = (255, 255, 200)
SPIKE_COL    = (160, 160, 160)
BULLET_COL   = (255, 255,  50)
FIREBALL_COL = (255, 130,  20)
BOSS_COL     = (160,  20, 160)
BURN_COL     = (255,  80,   0)
SHIELD_COL   = ( 80, 200, 255)
BOOTS_COL    = (160, 220, 100)

# Physics
GRAVITY      = 0.55
JUMP_FORCE   = -13.5
WALK_SPEED   = 5
RUN_SPEED    = 9
NORMAL_SPEED = 5
BOOST_SECS   = 8

# ── Utility ────────────────────────────────────────────────────────────────────
GAME_TITLE = "SUPER JUMP"
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption(f"{GAME_TITLE} — นายทำได้เว้ยยย!")
clock = pygame.time.Clock()

def _thai_font(size, bold=False):
    font_file = "Kanit-Bold.ttf" if bold else "Kanit-Medium.ttf"
    if os.path.exists(font_file):
        try: return pygame.font.Font(font_file, size)
        except: pass
    for name in ["leelawadeeui", "leelawadee", "tahoma", "microsoft sans serif"]:
        f = pygame.font.SysFont(name, size, bold=bold)
        if f: return f
    return pygame.font.SysFont(None, size, bold=bold)

font_giant = _thai_font(64, bold=True)
font_big   = _thai_font(48, bold=True)
font_med   = _thai_font(28, bold=True)
font_small = _thai_font(20)
font_tiny  = _thai_font(16)

# ── Audio ──────────────────────────────────────────────────────────────────────
try:
    sfx_jump  = pygame.mixer.Sound("jump.wav")
    sfx_coin  = pygame.mixer.Sound("coin.wav")
    sfx_shoot = pygame.mixer.Sound("shoot.wav")
    sfx_hit   = pygame.mixer.Sound("hit.wav")
    sfx_jump.set_volume(0.4); sfx_coin.set_volume(0.5)
    sfx_shoot.set_volume(0.4); sfx_hit.set_volume(0.6)
except:
    class DummySound:
        def play(self): pass
    sfx_jump = sfx_coin = sfx_shoot = sfx_hit = DummySound()

def play_bgm():
    try:
        pygame.mixer.music.load("bgm.wav")
        pygame.mixer.music.set_volume(0.25)
        pygame.mixer.music.play(-1)
    except: pass

def lerp_color(c1, c2, t):
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))

def draw_text_shadow(surf, text, font, color, x, y, shadow=(0,0,0)):
    surf.blit(font.render(text, True, shadow), (x+2, y+2))
    surf.blit(font.render(text, True, color),  (x,   y))

def draw_panel(surf, x, y, w, h, alpha=180, border=(80,80,160)):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (10,10,30,alpha), s.get_rect(), border_radius=12)
    pygame.draw.rect(s, (*border, 200), s.get_rect(), 2, border_radius=12)
    surf.blit(s, (x, y))

# ── Camera ─────────────────────────────────────────────────────────────────────
class Camera:
    def __init__(self): self.offset_x = 0
    def update(self, tx):
        self.offset_x += (tx - SCREEN_W//3 - self.offset_x) * 0.12
    def apply(self, rect):
        return pygame.Rect(rect.x - self.offset_x, rect.y, rect.width, rect.height)

# ── Particles ──────────────────────────────────────────────────────────────────
particles = []
def emit_particles(x, y, color, n=8, speed=3):
    for _ in range(n):
        a = random.uniform(0, math.tau); sp = random.uniform(1, speed)
        particles.append({'x':x,'y':y,'vx':math.cos(a)*sp,
            'vy':math.sin(a)*sp-random.uniform(1,3),
            'life':random.randint(20,40),'color':color,'r':random.randint(3,7)})

def update_particles(surf, cam):
    for p in particles[:]:
        p['x']+=p['vx']; p['y']+=p['vy']; p['vy']+=0.15; p['life']-=1
        alpha = max(0, p['life']/40)
        col = tuple(int(c*alpha) for c in p['color'][:3])
        sx,sy = int(p['x']-cam.offset_x), int(p['y'])
        if 0<=sx<=SCREEN_W and 0<=sy<=SCREEN_H:
            pygame.draw.circle(surf, col, (sx,sy), p['r'])
        if p['life']<=0: particles.remove(p)

stars = [(random.randint(0,SCREEN_W), random.randint(0,SCREEN_H//2),
          random.uniform(0.5,2.5)) for _ in range(120)]

def draw_sky(surf):
    for y in range(SCREEN_H):
        col = lerp_color(SKY_TOP, SKY_BOT, y/SCREEN_H)
        pygame.draw.line(surf, col, (0,y), (SCREEN_W,y))
    for sx,sy,r in stars:
        twinkle = 0.6+0.4*math.sin(pygame.time.get_ticks()*0.003+sx)
        col = tuple(int(c*twinkle) for c in STAR_COL)
        pygame.draw.circle(surf, col, (sx,sy), int(r))

# ── Weapons ────────────────────────────────────────────────────────────────────
class Bullet:
    DAMAGE = 20
    def __init__(self, x, y, right):
        self.rect = pygame.Rect(x, y-10, 14, 6)
        self.vx = 16 if right else -16
        self.life = 65
    def update(self): self.rect.x += self.vx; self.life -= 1
    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        pygame.draw.rect(surf, BULLET_COL, r, border_radius=3)
        pygame.draw.rect(surf, WHITE, pygame.Rect(r.x+3,r.y+2,r.w-6,r.h-4))

class Fireball:
    DAMAGE = 15; BURN_DMG = 2; BURN_SECS = 5
    def __init__(self, x, y, right):
        self.rect = pygame.Rect(x, y-14, 20, 20)
        self.vx = 10 if right else -10
        self.life = 90; self.anim = 0
    def update(self): self.rect.x += self.vx; self.life -= 1; self.anim += 1
    def draw(self, surf, cam):
        r = cam.apply(self.rect); t = self.anim*0.2
        cx,cy = r.centerx, r.centery
        for rad,a in [(18,60),(14,100)]:
            s = pygame.Surface((rad*2,rad*2), pygame.SRCALPHA)
            pygame.draw.circle(s,(255,80,0,a),(rad,rad),rad)
            surf.blit(s,(cx-rad,cy-rad))
        pygame.draw.circle(surf, FIREBALL_COL,(cx,cy),10)
        pygame.draw.circle(surf,(255,220,50),(cx-2,cy-2),5)
        for i in range(4):
            a = t+i*math.pi/2
            pygame.draw.circle(surf,(255,100,0),(cx+int(math.cos(a)*13),cy+int(math.sin(a)*13)),3)

class Spike:
    def __init__(self, x, y, w=30):
        self.rect = pygame.Rect(x, y, w, 20)
    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        count = max(1, self.rect.w//10); wp = self.rect.w/count
        for i in range(count):
            lx=r.x+i*wp; rx=r.x+(i+1)*wp; mx=(lx+rx)/2
            pygame.draw.polygon(surf, SPIKE_COL,[(lx,r.bottom),(mx,r.top),(rx,r.bottom)])
            pygame.draw.polygon(surf, WHITE,    [(lx+1,r.bottom),(mx,r.top+2),(rx-1,r.bottom)],1)

# ── Player ─────────────────────────────────────────────────────────────────────
class Player:
    W, H = 36, 48
    def __init__(self):
        self.rect       = pygame.Rect(80,100,self.W,self.H)
        self.vx = self.vy = 0
        self.on_ground  = False
        # Persistent stats
        self.hp           = 100
        self.coins        = 0
        self.score        = 0
        self.has_sword    = False
        self.ammo         = 0
        self.fireball_ammo= 0
        self.has_shield   = False         # reflect shield
        self.has_boots    = False         # anti-spike boots
        self.boots_dur    = 0             # durability (max 6)
        # Runtime stats
        self.speed        = NORMAL_SPEED
        self.boost_timer  = 0
        self.invincible   = 0
        self.facing_right = True
        self.anim_frame   = 0; self.anim_timer = 0
        self.dead         = False
        self.jump_count   = 0
        self.slash_timer  = 0; self.slash_rect = None
        self.shield_flash = 0            # frames showing shield pulse

    def reset_for_level(self, x, y):
        self.rect.topleft = (x,y)
        self.vx = self.vy = 0
        self.speed = NORMAL_SPEED
        self.boost_timer = self.invincible = self.slash_timer = 0
        self.slash_rect = None; self.dead = False

    @property
    def boosted(self): return self.boost_timer > 0

    def apply_boost(self):
        self.boost_timer = BOOST_SECS*FPS; self.speed = RUN_SPEED

    def take_damage(self, amount=5):
        if self.invincible > 0: return
        self.hp = max(0, self.hp-amount)
        self.invincible = 60
        sfx_hit.play()
        emit_particles(self.rect.centerx, self.rect.centery, HP_RED, 10, 4)
        if self.hp <= 0: self.dead = True

    def slash(self):
        if not self.has_sword or self.slash_timer > 0: return
        self.slash_timer = 20; sfx_shoot.play()
        sx = self.rect.right if self.facing_right else self.rect.left-40
        self.slash_rect = pygame.Rect(sx, self.rect.y+10, 40, 30)

    def shoot(self, bullets):
        if self.ammo > 0:
            self.ammo -= 1; sfx_shoot.play()
            bx = self.rect.right if self.facing_right else self.rect.left-12
            bullets.append(Bullet(bx, self.rect.centery, self.facing_right))

    def throw_fireball(self, projectiles):
        if self.fireball_ammo > 0:
            self.fireball_ammo -= 1; sfx_shoot.play()
            bx = self.rect.right if self.facing_right else self.rect.left-20
            projectiles.append(Fireball(bx, self.rect.centery, self.facing_right))

    def update(self, platforms, spikes, enemies, boss):
        keys = pygame.key.get_pressed()
        dx = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx=-self.speed; self.facing_right=False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx=+self.speed; self.facing_right=True

        if self.boost_timer > 0:
            self.boost_timer -= 1
            if self.boost_timer == 0: self.speed = NORMAL_SPEED
        if self.invincible > 0: self.invincible -= 1
        if self.shield_flash > 0: self.shield_flash -= 1
        if self.slash_timer > 0:
            self.slash_timer -= 1
            sx = self.rect.right if self.facing_right else self.rect.left-40
            self.slash_rect = pygame.Rect(sx, self.rect.y+10, 40, 30)
            if self.slash_timer == 0: self.slash_rect = None

        self.vy = min(self.vy+GRAVITY, 18)
        self.rect.x += dx
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if dx>0: self.rect.right=p.rect.left
                elif dx<0: self.rect.left=p.rect.right

        self.on_ground = False
        self.rect.y += self.vy
        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.vy>0:
                    self.rect.bottom=p.rect.top; self.vy=0
                    self.on_ground=True; self.jump_count=0
                elif self.vy<0:
                    self.rect.top=p.rect.bottom; self.vy=0

        if self.rect.left<0: self.rect.left=0
        if self.rect.top>SCREEN_H+50: self.hp=0; self.dead=True

        # Spike collision
        for s in spikes:
            if self.rect.colliderect(s.rect):
                if self.has_boots and self.boots_dur > 0:
                    self.boots_dur -= 1
                    if self.boots_dur == 0: self.has_boots = False
                    self.invincible = max(self.invincible, 40)  # brief immune
                    self.vy = -5
                else:
                    self.take_damage(10); self.vy=-8; self.rect.y-=10

        # Sword vs enemies
        if self.slash_rect:
            for e in enemies:
                if e.alive and self.slash_rect.colliderect(e.rect):
                    e.alive=False; self.score+=50; self.coins+=5
                    sfx_hit.play()
                    emit_particles(e.rect.centerx,e.rect.centery,ENEMY_COL,14,5)
            if boss and boss.alive and self.slash_rect.colliderect(boss.rect):
                boss.take_hit(15); sfx_hit.play()
                emit_particles(boss.rect.centerx,boss.rect.centery,BOSS_COL,10,4)

        self.anim_timer += 1
        if self.anim_timer > 8: self.anim_frame=(self.anim_frame+1)%4; self.anim_timer=0

    def jump(self):
        if self.jump_count < 2:
            self.vy = JUMP_FORCE if self.jump_count==0 else JUMP_FORCE*0.8
            self.jump_count += 1; sfx_jump.play()
            emit_particles(self.rect.centerx,self.rect.bottom,(200,200,255),6,2)

    def draw(self, surf, cam):
        r = cam.apply(self.rect)
        if self.invincible>0 and (self.invincible//5)%2: return

        # Shield aura
        if self.has_shield:
            t = pygame.time.get_ticks()*0.004
            pulse = 0.6+0.4*math.sin(t)
            aura = pygame.Surface((r.w+30,r.h+30), pygame.SRCALPHA)
            pygame.draw.ellipse(aura, (*SHIELD_COL, int(80*pulse)), aura.get_rect())
            surf.blit(aura,(r.x-15,r.y-15))
            if self.shield_flash > 0:
                ring = pygame.Surface((r.w+50,r.h+50), pygame.SRCALPHA)
                pygame.draw.ellipse(ring,(255,255,255,int(200*self.shield_flash/20)),ring.get_rect(),4)
                surf.blit(ring,(r.x-25,r.y-25))

        # Body shadow
        pygame.draw.ellipse(surf,(0,0,0,60),pygame.Rect(r.x+3,r.bottom-6,r.w-6,10))

        body_col = (100,240,220) if self.boosted else PLAYER_COL
        leg_offset = int(math.sin(self.anim_frame*math.pi/2)*5) if not self.on_ground else 0
        pygame.draw.rect(surf, body_col, r, border_radius=8)

        # Belt
        pygame.draw.rect(surf,(50,50,180),pygame.Rect(r.x,r.y+r.h*2//3,r.w,8),border_radius=4)

        # Eye
        ex = r.x+(r.w*2//3 if self.facing_right else r.w//3-8)
        pygame.draw.circle(surf,WHITE,(ex+4,r.y+14),7)
        pygame.draw.circle(surf,(30,30,30),(ex+5,r.y+15),4)

        # Legs
        lx,rx2 = r.x+4, r.x+r.w//2+2
        pygame.draw.rect(surf,(40,40,140),pygame.Rect(lx,r.bottom-14+leg_offset,r.w//2-6,14),border_radius=5)
        pygame.draw.rect(surf,(40,40,140),pygame.Rect(rx2,r.bottom-14-leg_offset,r.w//2-6,14),border_radius=5)

        # Boots visual (green-tinted feet)
        if self.has_boots:
            bcol = BOOTS_COL if self.boots_dur>3 else (220,150,50)
            pygame.draw.rect(surf,bcol,pygame.Rect(lx,r.bottom-6,r.w//2-6,6),border_radius=3)
            pygame.draw.rect(surf,bcol,pygame.Rect(rx2,r.bottom-6,r.w//2-6,6),border_radius=3)

        # Boost aura
        if self.boosted:
            t = pygame.time.get_ticks()*0.005
            for i in range(6):
                angle = t+i*math.pi/3
                pygame.draw.circle(surf,SPEED_COL,
                    (r.centerx+int(math.cos(angle)*(r.w//2+8)),
                     r.centery+int(math.sin(angle)*(r.h//2+8))),5)

        # Slash arc
        if self.slash_timer>0 and self.slash_rect:
            sr = cam.apply(self.slash_rect)
            sw = pygame.Surface((sr.w,sr.h),pygame.SRCALPHA)
            pygame.draw.ellipse(sw,(200,220,255,160),(0,0,sr.w,sr.h))
            surf.blit(sw,(sr.x,sr.y))

# ── Boss ───────────────────────────────────────────────────────────────────────
class Boss:
    W,H = 70,80; MAX_HP = 100
    def __init__(self, x, y, platforms):
        self.rect=pygame.Rect(x,y,self.W,self.H)
        self.hp=self.MAX_HP; self.alive=True
        self.vy=0; self.dir=1; self.speed=2.5
        self.platforms=platforms; self.anim=0; self.atk_cd=0
        self.burn_timer=0; self.burn_tick=0

    def take_hit(self, dmg, burn=False):
        self.hp -= dmg
        if burn: self.burn_timer=Fireball.BURN_SECS*FPS
        if self.hp<=0: self.hp=0; self.alive=False

    def update(self, player):
        if not self.alive: return
        self.anim+=1
        if self.atk_cd>0: self.atk_cd-=1
        if self.burn_timer>0:
            self.burn_timer-=1; self.burn_tick+=1
            if self.burn_tick>=FPS:
                self.hp=max(0,self.hp-Fireball.BURN_DMG); self.burn_tick=0
                if self.hp<=0: self.alive=False; return
        self.vy=min(self.vy+GRAVITY,18)
        self.rect.x+=self.dir*self.speed
        for p in self.platforms:
            if self.rect.colliderect(p.rect):
                if self.dir>0: self.rect.right=p.rect.left
                else: self.rect.left=p.rect.right
                self.dir*=-1
        self.rect.y+=self.vy
        for p in self.platforms:
            if self.rect.colliderect(p.rect):
                if self.vy>0: self.rect.bottom=p.rect.top; self.vy=0
                elif self.vy<0: self.rect.top=p.rect.bottom; self.vy=0
        if self.rect.top>SCREEN_H+80: self.alive=False; return
        self.dir = -1 if player.rect.centerx<self.rect.centerx else 1
        if self.rect.colliderect(player.rect) and self.atk_cd==0:
            player.take_damage(10); self.atk_cd=90

    def draw(self, surf, cam):
        if not self.alive: return
        r = cam.apply(self.rect)
        burning = self.burn_timer>0
        if burning:
            gs=pygame.Surface((r.w+20,r.h+20),pygame.SRCALPHA)
            pygame.draw.ellipse(gs,(255,80,0,80),gs.get_rect())
            surf.blit(gs,(r.x-10,r.y-10))
        pygame.draw.rect(surf,BOSS_COL,r,border_radius=10)
        for i in range(7):
            angle=-math.pi/2+(i-3)*0.3
            sx2=r.centerx+int(math.cos(angle)*(r.w//2+10))
            sy2=r.centery+int(math.sin(angle)*(r.h//2+5))-15
            pygame.draw.circle(surf,(200,0,200),(sx2,sy2),7)
        pygame.draw.circle(surf,(255,0,0),(r.centerx-15,r.centery-10),9)
        pygame.draw.circle(surf,(255,0,0),(r.centerx+15,r.centery-10),9)
        pygame.draw.circle(surf,BLACK,(r.centerx-14,r.centery-10),5)
        pygame.draw.circle(surf,BLACK,(r.centerx+16,r.centery-10),5)
        pygame.draw.line(surf,BLACK,(r.centerx-22,r.centery-22),(r.centerx-7,r.centery-16),3)
        pygame.draw.line(surf,BLACK,(r.centerx+8,r.centery-16),(r.centerx+23,r.centery-22),3)
        pts=[(r.centerx-18,r.centery+15),(r.centerx-10,r.centery+22),
             (r.centerx,r.centery+15),(r.centerx+10,r.centery+22),(r.centerx+18,r.centery+15)]
        pygame.draw.lines(surf,BLACK,False,pts,3)
        # HP bar
        bar_w=r.w+20; bx=r.x-10; by=r.y-20
        pygame.draw.rect(surf,(60,0,0),(bx,by,bar_w,12),border_radius=5)
        fill=int(bar_w*max(0,self.hp/self.MAX_HP))
        if fill>0:
            pygame.draw.rect(surf,lerp_color(HP_RED,(200,0,200),1-self.hp/self.MAX_HP),(bx,by,fill,12),border_radius=5)
        lbl=font_tiny.render(f"BOSS HP {self.hp}/{self.MAX_HP}",True,WHITE)
        surf.blit(lbl,(bx,by-16))

# ── Enemy ──────────────────────────────────────────────────────────────────────
class Enemy:
    W,H=36,36
    def __init__(self, x, y, platforms, speed=1.8):
        self.rect=pygame.Rect(x,y,self.W,self.H)
        self.vy=0; self.speed=speed; self.dir=random.choice([-1,1])
        self.platforms=platforms; self.alive=True; self.anim=0; self.stomp_cd=0
        self.burn_timer=0; self.burn_tick=0

    def update(self, player):
        if not self.alive: return
        self.anim+=1
        if self.stomp_cd>0: self.stomp_cd-=1
        if self.burn_timer>0:
            self.burn_timer-=1; self.burn_tick+=1
            if self.burn_tick>=FPS:
                self.burn_tick=0; self.alive=False; return

        self.vy=min(self.vy+GRAVITY,18)
        self.rect.x+=self.dir*self.speed
        for p in self.platforms:
            if self.rect.colliderect(p.rect):
                if self.dir>0: self.rect.right=p.rect.left
                else: self.rect.left=p.rect.right
                self.dir*=-1
        self.rect.y+=self.vy
        for p in self.platforms:
            if self.rect.colliderect(p.rect):
                if self.vy>0: self.rect.bottom=p.rect.top; self.vy=0
                elif self.vy<0: self.rect.top=p.rect.bottom; self.vy=0
        if self.rect.top>SCREEN_H+80: self.alive=False; return

        if self.rect.colliderect(player.rect) and self.stomp_cd==0:
            if player.vy>0 and player.rect.bottom<=self.rect.centery+12:
                # Stomp kill
                self.alive=False; player.vy=JUMP_FORCE*0.7
                player.score+=50; player.coins+=5; sfx_hit.play()
                emit_particles(self.rect.centerx,self.rect.centery,ENEMY_COL,14,5)
            elif player.has_shield:
                # Shield reflect: monster dies, player unharmed
                self.alive=False; sfx_hit.play()
                player.score+=50; player.coins+=5
                player.shield_flash=20
                emit_particles(self.rect.centerx,self.rect.centery,SHIELD_COL,16,6)
            else:
                player.take_damage(5); self.stomp_cd=30

    def draw(self, surf, cam):
        if not self.alive: return
        r = cam.apply(self.rect)
        if r.right<0 or r.left>SCREEN_W: return
        burning = self.burn_timer>0
        col = BURN_COL if burning else ENEMY_COL
        pygame.draw.ellipse(surf,col,r)
        for i in range(5):
            angle=-math.pi/2+(i-2)*0.4
            sx2=r.centerx+int(math.cos(angle)*(r.w//2+6))
            sy2=r.centery+int(math.sin(angle)*(r.h//2+2))-5
            pygame.draw.circle(surf,(160,20,20) if not burning else (255,100,0),(sx2,sy2),5)
        elx,erx,ey=r.centerx-9,r.centerx+9,r.centery-4
        pygame.draw.circle(surf,ENEMY_EYE,(elx,ey),6); pygame.draw.circle(surf,ENEMY_EYE,(erx,ey),6)
        pygame.draw.circle(surf,BLACK,(elx+1,ey+1),3); pygame.draw.circle(surf,BLACK,(erx+1,ey+1),3)
        pygame.draw.line(surf,BLACK,(elx-5,ey-7),(elx+5,ey-3),2)
        pygame.draw.line(surf,BLACK,(erx-5,ey-3),(erx+5,ey-7),2)
        pygame.draw.lines(surf,BLACK,False,[(r.centerx-7,r.centery+8),(r.centerx,r.centery+12),(r.centerx+7,r.centery+8)],2)

# ── Environment ────────────────────────────────────────────────────────────────
class Platform:
    def __init__(self, x, y, w, h=18, moving=False, move_range=100, move_speed=2):
        self.rect=pygame.Rect(x,y,w,h); self.moving=moving; self.origin_x=x
        self.move_range=move_range; self.move_speed=move_speed; self.move_dir=1
    def update(self):
        if self.moving:
            self.rect.x+=self.move_speed*self.move_dir
            if abs(self.rect.x-self.origin_x)>=self.move_range: self.move_dir*=-1
    def draw(self, surf, cam):
        r=cam.apply(self.rect)
        if r.right<0 or r.left>SCREEN_W: return
        pygame.draw.rect(surf,PLAT_COL,r,border_radius=6)
        pygame.draw.rect(surf,PLAT_TOP,pygame.Rect(r.x,r.y,r.w,7),border_radius=6)
        for i in range(1,r.w//30):
            lx2=r.x+i*30; pygame.draw.line(surf,(60,35,10),(lx2,r.y+8),(lx2,r.bottom-2))

class Ground:
    def __init__(self, world_w):
        self.rect=pygame.Rect(0,SCREEN_H-60,world_w,60)
    def update(self): pass
    def draw(self, surf, cam):
        r=cam.apply(self.rect)
        pygame.draw.rect(surf,GROUND_COL,r)
        pygame.draw.rect(surf,GRASS_COL,pygame.Rect(r.x,r.y,r.w,14))
        for gx in range(int(cam.offset_x)%20,SCREEN_W,20):
            gy=SCREEN_H-60
            pygame.draw.line(surf,(40,140,40),(gx,gy),(gx-4,gy-8),2)
            pygame.draw.line(surf,(40,140,40),(gx+4,gy),(gx+8,gy-6),2)

class Coin:
    def __init__(self, x, y):
        self.rect=pygame.Rect(x,y,22,22); self.collected=False; self.anim=random.uniform(0,math.tau)
    def update(self): self.anim+=0.07
    def draw(self, surf, cam):
        if self.collected: return
        r=cam.apply(self.rect)
        if r.right<0 or r.left>SCREEN_W: return
        cx,cy=r.centerx,r.centery+int(math.sin(self.anim)*4)
        for rad,a in [(14,40),(11,80)]:
            s=pygame.Surface((rad*2,rad*2),pygame.SRCALPHA)
            pygame.draw.circle(s,(*COIN_COL,a),(rad,rad),rad)
            surf.blit(s,(cx-rad,cy-rad))
        pygame.draw.circle(surf,COIN_COL,(cx,cy),9)
        pygame.draw.circle(surf,(255,240,120),(cx-2,cy-2),5)
        lbl=font_tiny.render("$",True,(180,130,0))
        surf.blit(lbl,(cx-lbl.get_width()//2,cy-lbl.get_height()//2))

class SpeedItem:
    def __init__(self, x, y):
        self.rect=pygame.Rect(x,y,28,28); self.collected=False; self.anim=random.uniform(0,math.tau)
    def update(self): self.anim+=0.09
    def draw(self, surf, cam):
        if self.collected: return
        r=cam.apply(self.rect)
        if r.right<0 or r.left>SCREEN_W: return
        t=self.anim; cx,cy=r.centerx,r.centery+int(math.sin(t)*5)
        for i in range(6):
            a=t+i*math.pi/3
            pygame.draw.circle(surf,(80,255,180),(cx+int(math.cos(a)*16),cy+int(math.sin(a)*16)),4)
        pygame.draw.circle(surf,SPEED_COL,(cx,cy),12)
        pygame.draw.circle(surf,WHITE,(cx-3,cy-3),5)
        lbl=font_tiny.render("SPD",True,(0,100,60))
        surf.blit(lbl,(cx-lbl.get_width()//2,cy-lbl.get_height()//2))

# ── HUD ────────────────────────────────────────────────────────────────────────
def draw_hud(surf, player, level_num):
    # HP bar
    bw,bh=220,22; bx,by=16,16
    pygame.draw.rect(surf,(40,10,10),(bx-2,by-2,bw+4,bh+4),border_radius=12)
    pygame.draw.rect(surf,(80,20,20),(bx,by,bw,bh),border_radius=10)
    pct=max(0,player.hp/100); fill=int(bw*pct)
    if fill>0: pygame.draw.rect(surf,lerp_color(HP_RED,HP_GREEN,pct),(bx,by,fill,bh),border_radius=10)
    pygame.draw.rect(surf,(255,255,255,60),(bx,by,bw,bh//3),border_radius=10)
    surf.blit(font_small.render(f"HP {int(player.hp)}/100",True,WHITE),(bx+8,by+2))

    by2=by+bh+8
    draw_text_shadow(surf,f"Dan: {level_num}/{TOTAL_LEVELS}",font_small,WHITE,16,by2)
    draw_text_shadow(surf,f"Coin: {player.coins}",font_small,COIN_COL,180,by2)
    draw_text_shadow(surf,f"SCORE {player.score:06d}",font_med,SCORE_COL,
                     SCREEN_W-font_med.size(f"SCORE {player.score:06d}")[0]-16,14)

    by3=by2+26
    items_left = []
    if player.has_sword:     items_left.append(("Sword (F)", (220,220,255)))
    if player.ammo>0:        items_left.append((f"Gun {player.ammo}/10 (G)", BULLET_COL))
    if player.fireball_ammo>0: items_left.append((f"Fire {player.fireball_ammo}/6 (H)", FIREBALL_COL))
    if player.has_shield:    items_left.append(("[SHIELD]", SHIELD_COL))
    if player.has_boots:
        bcol=BOOTS_COL if player.boots_dur>3 else (220,150,50)
        items_left.append((f"Boots {player.boots_dur}/6", bcol))

    for i,(txt,col) in enumerate(items_left):
        draw_text_shadow(surf, txt, font_tiny, col, 16, by3+i*20)

    if player.boosted:
        boost_w=int(bw*(player.boost_timer/(BOOST_SECS*FPS))); by4=by3+len(items_left)*20+4
        pygame.draw.rect(surf,(0,60,50),(bx-2,by4-2,bw+4,18),border_radius=8)
        pygame.draw.rect(surf,(0,120,90),(bx,by4,boost_w,14),border_radius=6)
        surf.blit(font_tiny.render("-- SPEED BOOST --",True,SPEED_COL),(bx+6,by4-1))

# ── Shop ───────────────────────────────────────────────────────────────────────
def draw_shop(surf, player):
    overlay=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
    overlay.fill((0,0,20,120)); surf.blit(overlay,(0,0))

    cx=SCREEN_W//2
    # Add a panel behind the shop content so text is readable
    draw_panel(surf, cx-330, 40, 660, 520, alpha=180)

    # Title
    draw_text_shadow(surf,"=== ร้านค้าระหว่างด่าน ===",font_big,SPEED_COL,cx-275,60)
    draw_text_shadow(surf,f"เหรียญคงเหลือ: {player.coins} เหรียญ",font_med,COIN_COL,cx-145,120)

    def avail(cond): return WHITE if cond else (80,80,80)
    can=[
        player.coins>=20 and player.hp<100,
        player.coins>=50 and not player.has_sword,
        player.coins>=40 and player.ammo<10,
        player.coins>=35 and player.fireball_ammo<6,
        player.coins>=100 and not player.has_shield,
        player.coins>=30 and (not player.has_boots or player.boots_dur<6),
    ]
    items=[
        ("1","ฟื้นฟู HP +50","20 เหรียญ",HP_GREEN,can[0]),
        ("2","ดาบ (ฟัน F)","50 เหรียญ",(220,220,220),can[1]),
        ("3","กระสุนปืน 10 นัด (G)","40 เหรียญ",BULLET_COL,can[2]),
        ("4","ลูกบอลไฟ 6 ลูก (H)","35 เหรียญ",FIREBALL_COL,can[3]),
        ("5","เกราะสะท้อน [SHIELD]","100 เหรียญ",SHIELD_COL,can[4]),
        ("6","รองเท้ากันหนาม Boots","30 เหรียญ",BOOTS_COL,can[5]),
    ]
    for i,(key,name,price,dot_col,c) in enumerate(items):
        iy=185+i*50
        row=i%2; col_x=cx-300 if row==0 else cx+30
        col_y=185+(i//2)*50 if False else iy  # single column, easier read
        pygame.draw.rect(surf,(*dot_col,60),(cx-290,iy-2,580,40),border_radius=8)
        pygame.draw.rect(surf,(*dot_col,120),(cx-290,iy-2,580,40),2,border_radius=8)
        draw_text_shadow(surf,f"{key}. {name}",font_med,avail(c),cx-275,iy+4)
        lbl=font_small.render(price,True,dot_col)
        surf.blit(lbl,(cx+200,iy+8))

    desc=[
        "เกราะสะท้อน: มอนสเตอร์แตะตายทันที + ได้เหรียญ",
        "รองเท้ากันหนาม: กันหนามได้ 6 ครั้ง แล้วพัง ต้องซื้อใหม่",
        "ปืน: 20 dmg  |  ลูกบอลไฟ: 15 dmg + ไหม้ 2/วิ x 5 วิ",
    ]
    for i,d in enumerate(desc):
        surf.blit(font_tiny.render(d,True,(180,180,220)),(cx-290,505+i*18))

    hint=font_med.render("กด ENTER ไปด่านต่อไป ->",True,(100,255,100))
    surf.blit(hint,(cx-hint.get_width()//2,482))

# ── Level Generator ────────────────────────────────────────────────────────────
def build_level(level_num):
    is_boss=(level_num==TOTAL_LEVELS)
    world_w=(4000+level_num*1200) if not is_boss else 3000
    ground=Ground(world_w)
    platforms=[ground]
    coins=[]; speed_items=[]; enemies=[]; spikes=[]

    if is_boss:
        for bpx,bpy,bpw in [(300,400,200),(600,320,160),(900,240,160),(1200,350,200),
                             (1500,280,180),(1800,200,160),(2100,350,200),(2400,300,200),(2600,200,400)]:
            platforms.append(Platform(bpx,bpy,bpw))
            for j in range(random.randint(2,3)):
                cx2=bpx+15+j*35
                if cx2<bpx+bpw-15: coins.append(Coin(cx2,bpy-32))
        boss=Boss(1400,SCREEN_H-60-Boss.H,platforms)
        return platforms,coins,speed_items,enemies,spikes,world_w,boss

    hard=min(level_num,7)
    curr_x=200
    while curr_x<world_w-600:
        w=random.randint(80,180)
        gap=random.randint(60+hard*12,160+hard*22)
        y=random.randint(200,480)
        moving=random.random()<0.08*hard
        p=Platform(curr_x,y,w,moving=moving,move_range=w,move_speed=1+hard*0.45)
        platforms.append(p)
        if hard>=2 and random.random()<0.28:
            spikes.append(Spike(curr_x+w//2-15,p.rect.top-20,30))
        if hard>=3 and random.random()<0.35:
            spikes.append(Spike(curr_x+w+10,SCREEN_H-80,random.randint(30,90)))
        if hard>=6 and random.random()<0.4:
            spikes.append(Spike(curr_x-20,SCREEN_H-80,50))
        for j in range(random.randint(1,4)):
            cx2=p.rect.x+15+j*35
            if cx2<p.rect.right-15: coins.append(Coin(cx2,p.rect.y-32))
        if random.random()<0.12: speed_items.append(SpeedItem(p.rect.centerx,p.rect.y-38))
        if p.rect.w>=90 and random.random()<0.25+hard*0.09:
            ex=p.rect.x+random.randint(10,p.rect.w-50)
            enemies.append(Enemy(ex,p.rect.y-Enemy.H,platforms,
                                 speed=random.uniform(1.2+hard*0.28,2.5+hard*0.3)))
        curr_x+=w+gap

    platforms.append(Platform(world_w-400,300,400))
    for gx in range(400,world_w-500,max(200,800-hard*90)):
        enemies.append(Enemy(gx,SCREEN_H-60-Enemy.H,platforms,
                             speed=random.uniform(1.5+hard*0.2,3.5+hard*0.2)))
    return platforms,coins,speed_items,enemies,spikes,world_w,None

# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    play_bgm()
    state="start"; level_num=1; player=Player()
    platforms=[]; coins=[]; speed_items=[]
    enemies=[]; spikes=[]; bullets=[]; projectiles=[]
    world_w=6000; cam=Camera(); boss=None

    def start_level():
        nonlocal platforms,coins,speed_items,enemies,spikes,bullets,projectiles,world_w,cam,boss
        particles.clear(); bullets.clear(); projectiles.clear()
        platforms,coins,speed_items,enemies,spikes,world_w,boss = build_level(level_num)
        player.reset_for_level(80,SCREEN_H-150)
        cam=Camera()

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type==pygame.QUIT: sys.exit()
            if event.type==pygame.KEYDOWN:
                if state=="start":
                    if event.key in (pygame.K_RETURN,pygame.K_SPACE):
                        player=Player(); level_num=1; start_level(); state="play"
                elif state=="play":
                    if event.key in (pygame.K_SPACE,pygame.K_UP,pygame.K_w): player.jump()
                    if event.key==pygame.K_f: player.slash()
                    if event.key==pygame.K_g: player.shoot(bullets)
                    if event.key==pygame.K_h: player.throw_fireball(projectiles)
                    if event.key==pygame.K_ESCAPE: sys.exit()
                elif state=="shop":
                    if event.key==pygame.K_1 and can1(player):
                        player.coins-=20; player.hp=min(100,player.hp+50)
                    if event.key==pygame.K_2 and player.coins>=50 and not player.has_sword:
                        player.coins-=50; player.has_sword=True
                    if event.key==pygame.K_3 and player.coins>=40 and player.ammo<10:
                        player.coins-=40; player.ammo=10
                    if event.key==pygame.K_4 and player.coins>=35 and player.fireball_ammo<6:
                        player.coins-=35; player.fireball_ammo=6
                    if event.key==pygame.K_5 and player.coins>=100 and not player.has_shield:
                        player.coins-=100; player.has_shield=True
                    if event.key==pygame.K_6 and player.coins>=30 and (not player.has_boots or player.boots_dur<6):
                        player.coins-=30; player.has_boots=True; player.boots_dur=6
                    if event.key==pygame.K_RETURN:
                        level_num+=1
                        if level_num>TOTAL_LEVELS: state="win"
                        else: start_level(); state="play"
                elif state in ("dead","win"):
                    if event.key==pygame.K_r: state="start"
                    if event.key==pygame.K_ESCAPE: sys.exit()

        if state=="play":
            player.update(platforms,spikes,enemies,boss)
            for p in platforms: p.update()
            for c in coins:
                c.update()
                if not c.collected and player.rect.colliderect(c.rect):
                    c.collected=True; sfx_coin.play()
                    player.score+=10; player.coins+=2
                    emit_particles(c.rect.centerx,c.rect.centery,COIN_COL,8,3)
            for si in speed_items:
                si.update()
                if not si.collected and player.rect.colliderect(si.rect):
                    si.collected=True; player.apply_boost()
                    emit_particles(si.rect.centerx,si.rect.centery,SPEED_COL,16,5)
            for e in enemies: e.update(player)

            for b in bullets[:]:
                b.update(); hit=False
                for e in enemies:
                    if e.alive and b.rect.colliderect(e.rect):
                        e.alive=False; sfx_hit.play()
                        player.score+=50; player.coins+=5
                        emit_particles(e.rect.centerx,e.rect.centery,ENEMY_COL,14,5)
                        hit=True; break
                if not hit and boss and boss.alive and b.rect.colliderect(boss.rect):
                    boss.take_hit(Bullet.DAMAGE); sfx_hit.play()
                    emit_particles(boss.rect.centerx,boss.rect.centery,BOSS_COL,8,4); hit=True
                if hit or b.life<=0:
                    try: bullets.remove(b)
                    except ValueError: pass

            for fb in projectiles[:]:
                fb.update(); hit=False
                for e in enemies:
                    if e.alive and fb.rect.colliderect(e.rect):
                        e.burn_timer=Fireball.BURN_SECS*FPS; e.alive=False; sfx_hit.play()
                        player.score+=50; player.coins+=5
                        emit_particles(e.rect.centerx,e.rect.centery,BURN_COL,14,5)
                        hit=True; break
                if not hit and boss and boss.alive and fb.rect.colliderect(boss.rect):
                    boss.take_hit(Fireball.DAMAGE,burn=True); sfx_hit.play()
                    emit_particles(boss.rect.centerx,boss.rect.centery,BURN_COL,10,4); hit=True
                if hit or fb.life<=0:
                    try: projectiles.remove(fb)
                    except ValueError: pass

            if boss: boss.update(player)
            cam.update(player.rect.x)

            is_boss_level=(level_num==TOTAL_LEVELS)
            if is_boss_level:
                if boss and not boss.alive: player.score+=5000; state="win"
            else:
                if player.rect.x>world_w-200: player.score+=1000*level_num; state="shop"
            if player.dead: state="dead"

        # ── Draw ───────────────────────────────────────────────────────────────
        draw_sky(screen)

        if state=="start":
            t=pygame.time.get_ticks()
            for i in range(0,SCREEN_W,60):
                x=(i-t*0.05)%SCREEN_W
                pygame.draw.line(screen,(35,35,70),(x,0),(x,SCREEN_H))
            px,py=SCREEN_W//2-20,100+int(math.sin(t*0.005)*10)
            pygame.draw.rect(screen,(100,240,220),(px,py,40,50),border_radius=8)
            pygame.draw.rect(screen,(50,50,180),(px,py+35,40,8),border_radius=4)
            pygame.draw.circle(screen,WHITE,(px+28,py+15),8)
            pygame.draw.circle(screen,(30,30,30),(px+30,py+16),4)

            title_y=190+int(math.sin(t*0.003)*10)
            title=font_giant.render(f"*  {GAME_TITLE}  *",True,SCORE_COL)
            glow=font_giant.render(f"*  {GAME_TITLE}  *",True,(255,200,0))
            glow.set_alpha(int(128+math.sin(t*0.005)*127))
            draw_text_shadow(screen,f"*  {GAME_TITLE}  *",font_giant,SCORE_COL,
                             SCREEN_W//2-title.get_width()//2,title_y)
            screen.blit(glow,(SCREEN_W//2-title.get_width()//2,title_y))

            draw_panel(screen,SCREEN_W//2-360,295,720,160)
            lines=[
                ("เดิน: ลูกศรซ้ายขวา   กระโดด: SPACE (กด 2 ครั้ง = Double Jump)",WHITE),
                ("ดาบ: F   ปืน: G (20 dmg)   ลูกบอลไฟ: H (15+burn)",  (200,255,200)),
                ("[SHIELD] สะท้อนมอนสเตอร์    [Boots] กันหนาม 6 ครั้ง", SHIELD_COL),
            ]
            for i,(txt,col) in enumerate(lines):
                surf_txt=font_small.render(txt,True,col)
                screen.blit(surf_txt,(SCREEN_W//2-surf_txt.get_width()//2,315+i*38))

            pulse=abs(math.sin(t*0.004))
            msg_col=lerp_color(SPEED_COL,(100,100,255),pulse)
            msg=font_big.render("[ กด ENTER เพื่อเริ่มด่าน 1 ]",True,msg_col)
            screen.blit(msg,(SCREEN_W//2-msg.get_width()//2,485))

        elif state in ("play","shop"):
            for p in platforms: p.draw(screen,cam)
            for s in spikes: s.draw(screen,cam)
            for c in coins: c.draw(screen,cam)
            for si in speed_items: si.draw(screen,cam)
            for e in enemies: e.draw(screen,cam)
            for b in bullets: b.draw(screen,cam)
            for fb in projectiles: fb.draw(screen,cam)
            if boss: boss.draw(screen,cam)
            update_particles(screen,cam)
            player.draw(screen,cam)
            draw_hud(screen,player,level_num)
            if state=="shop": draw_shop(screen,player)

        elif state=="dead":
            draw_panel(screen,SCREEN_W//2-300,SCREEN_H//2-100,600,230)
            lines2=[
                (f"GAME OVER",font_big,HP_RED),
                (f"คะแนน: {player.score:06d}  (ด่าน {level_num}/{TOTAL_LEVELS})",font_med,WHITE),
                ("กด R = เริ่มใหม่  |  ESC = ออก",font_small,(200,200,255)),
            ]
            for i,(txt,fnt,col) in enumerate(lines2):
                lbl=fnt.render(txt,True,col)
                screen.blit(lbl,(SCREEN_W//2-lbl.get_width()//2,SCREEN_H//2-80+i*65))

        elif state=="win":
            draw_panel(screen,SCREEN_W//2-320,SCREEN_H//2-100,640,220)
            lines3=[
                ("*** ยินดีด้วย! คุณเอาชนะ BOSS ได้! ***",font_big,SCORE_COL),
                (f"คะแนนสุดยอด: {player.score:06d}",font_med,WHITE),
                ("กด R = เล่นใหม่  |  ESC = ออก",font_small,SPEED_COL),
            ]
            for i,(txt,fnt,col) in enumerate(lines3):
                lbl=fnt.render(txt,True,col)
                screen.blit(lbl,(SCREEN_W//2-lbl.get_width()//2,SCREEN_H//2-80+i*65))

        pygame.display.flip()

def can1(p): return p.coins>=20 and p.hp<100

if __name__=="__main__":
    main()
