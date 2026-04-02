"""
Space Runner — a Pygame Zero endless runner game.
Controls: SPACE/UP to jump, ESC to pause.
"""

import math
import random
from sys import exit
import os

DEBUG = os.environ.get("DEBUG") == "1"

WIDTH, HEIGHT = 800, 400
GROUND_Y = 310
GRAVITY = 0.55
SCROLL_SPEED_INIT = 4.0
MAX_JUMPS = 2
WIN_SCORE = 20
MAX_LIVES = 3
INVINCIBLE_TIME = 1.0
FPS = 60

STATE_MENU, STATE_PLAYING, STATE_WIN, STATE_LOSE = "menu", "playing", "win", "lose"
state = STATE_MENU
sound_enabled = True


def play_sound(name):
    if sound_enabled:
        sounds.load(name).play()


def start_music():
    if sound_enabled:
        music.play("theme")


def stop_music():
    music.stop()


class Actor(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, anchor=("left", "bottom"))

    def draw(self, screen):
        if self.sprite:
            self.sprite.draw(screen, self.topleft)
        else:
            Actor.draw(self, screen)


class AnimatedSprite:
    def __init__(self, sheets: dict, default_sheet="", fps=10):
        self.sheets = sheets
        for sh in self.sheets.values():  # The individual spritesheets {name: , count:}
            sheet = getattr(
                images, sh["name"]
            )  # ex: equiv. to sheet = images.hero_idle
            self.width = sheet.get_width() // sh["count"]
            self.height = sheet.get_height()
            sh["frames"] = []
            for i in range(sh["count"]):
                rect = Rect(i * self.width, 0, self.width, self.height)
                sh["frames"].append(sheet.subsurface(rect).copy())
        self.fps = fps
        self.timer = 0.0
        self.frame_index = 0
        self.current_key = (
            list(sheets.keys())[0] if not default_sheet else default_sheet
        )

    def update(self, dt):
        # slows down update time
        self.timer += dt
        if self.timer >= 1.0 / self.fps:
            self.timer -= 1.0 / self.fps
            sh = self.sheets[self.current_key]
            self.frame_index = (self.frame_index + 1) % len(sh["frames"])

    def draw(self, screen, pos):
        sh = self.sheets[self.current_key]
        if sh["frames"] and self.frame_index < len(sh["frames"]):
            screen.blit(
                sh["frames"][self.frame_index],
                pos,
            )


class Hero(Actor):
    def __init__(self):
        super().__init__("hero_idle", (30, GROUND_Y))
        self.vy = 0.0
        self.jumps_left = MAX_JUMPS
        self.on_ground = True
        self.sprite = AnimatedSprite(
            {
                "idle": {"name": "hero_idle", "count": 4},
                "run": {"name": "hero_run", "count": 8},
            },
        )
        # Using the builtin _rect of the Actor class and have it construct the rect
        self._rect.width = self.sprite.width
        self._rect.height = self.sprite.height

    def jump(self):
        if self.jumps_left > 0:
            self.vy = -12.0
            self.jumps_left -= 1
            self.on_ground = False
            play_sound("jump")

    def update(self, dt, platforms):
        self.vy += GRAVITY
        self.y += self.vy

        # for bounds clipping and reset jumps
        if self.bottom >= GROUND_Y:
            self.bottom = GROUND_Y
            self.vy = 0.0
            self.jumps_left = MAX_JUMPS
            self.on_ground = True
        if self.right >= WIDTH:
            self.right = WIDTH
        if self.left <= 0:
            self.left = 0

        # basically if falling check if plat below
        if self.vy > 0:
            for plat in platforms:
                if self.colliderect(plat) and self.bottom < plat.top + 20:
                    self.bottom = plat.top
                    self.vy = 0.0
                    self.jumps_left = MAX_JUMPS
                    self.on_ground = True
                    break

        self.sprite.current_key = "idle" if self.on_ground else "run"
        self.sprite.update(dt)


class CrabEnemy(Actor):
    def __init__(self, x):
        super().__init__("crab_idle", (x, GROUND_Y))
        self.speed = 1.5
        self.sprite = AnimatedSprite(
            {
                "idle": {"name": "crab_idle", "count": 4},
                "run": {"name": "crab_run", "count": 6},
            },
            default_sheet="run",
        )
        self._rect.width = self.sprite.width
        self._rect.height = self.sprite.height

    def update(self, dt, scroll_speed):
        self.x -= scroll_speed * dt * FPS * self.speed
        self.sprite.update(dt)


class DroneEnemy(Actor):
    def __init__(self, x, base_y=160.0):
        super().__init__("drone_idle", (x, base_y))
        self.base_y = base_y
        self.speed = 5
        self.flight_range = 30
        self.bob_phase = random.uniform(0, math.pi * 2)
        self.sprite = AnimatedSprite(
            {
                "idle": {"name": "drone_idle", "count": 4},
                "run": {"name": "drone_run", "count": 6},
            },
            default_sheet="run",
        )
        self._rect.width = self.sprite.width
        self._rect.height = self.sprite.height

    def update(self, dt, scroll_speed):
        self.x -= scroll_speed * dt * FPS
        self.bob_phase += self.speed * dt
        self.y = self.base_y + math.sin(self.bob_phase) * self.flight_range
        self.sprite.update(dt)


class Coin(Actor):
    def __init__(self, x, y):
        super().__init__("coin", (x, y))
        self.collected = False
        self.sprite = AnimatedSprite(
            {"idle": {"name": "coin", "count": 6}},
            default_sheet="idle",
        )
        self._rect.width = self.sprite.width
        self._rect.height = self.sprite.height

    def update(self, dt, scroll_speed):
        self.x -= scroll_speed * dt * FPS
        self.sprite.update(dt)


class PlatformStrip:
    TILE_W, TILE_H = 64, 24

    def __init__(self, x, y, tile_count):
        self.x, self.y = float(x), float(y)
        self.width = tile_count * self.TILE_W
        self.rect = Rect(self.x, self.y, self.width, self.TILE_H)

    def update(self, dt, scroll_speed):
        self.x -= scroll_speed * dt * FPS
        self.rect.x = self.x

    def draw(self, screen):
        for i in range(int(self.width // self.TILE_W)):
            screen.blit("platform", (int(self.x + i * self.TILE_W), int(self.y)))


class World:
    def __init__(self):
        self.hero = Hero()
        self.enemies, self.coins, self.platforms = [], [], []
        self.scroll_speed = SCROLL_SPEED_INIT
        self.distance, self.score = 0.0, 0
        self.lives = MAX_LIVES
        self.invincible = 0.0
        self.spawn_timer, self.spawn_interval = 0.0, 2.2
        self.bg_x, self.mid_x = 0.0, 0.0
        self.ground_tiles = list(range(0, WIDTH + 64, 64))

    def _spawn_obstacle(self):
        roll = random.random()
        if roll < 0.25:
            y = random.randint(180, 240)
            plat = PlatformStrip(WIDTH, y, random.randint(3, 5))
            self.platforms.append(plat)
            self.coins.append(Coin(WIDTH - 16 + plat.width // 2, y - 10))
        elif roll < 0.55:
            self.enemies.append(CrabEnemy(WIDTH + random.randint(20, 80)))
        elif roll < 0.80:
            self.enemies.append(
                DroneEnemy(WIDTH + random.randint(20, 80), random.randint(120, 200))
            )
        else:
            for i in range(random.randint(2, 4)):
                self.coins.append(Coin(WIDTH + 40 + i * 40, GROUND_Y - 20))

    def update(self, dt):
        self.scroll_speed = SCROLL_SPEED_INIT + self.distance * 0.0003
        self.bg_x -= self.scroll_speed * 0.2 * dt * FPS
        self.mid_x -= self.scroll_speed * 0.5 * dt * FPS
        if self.bg_x <= -WIDTH:
            self.bg_x += WIDTH
        if self.mid_x <= -WIDTH:
            self.mid_x += WIDTH

        self.ground_tiles = [
            t - self.scroll_speed * dt * FPS for t in self.ground_tiles
        ]
        while self.ground_tiles[0] < -64:
            self.ground_tiles.pop(0)
            self.ground_tiles.append(self.ground_tiles[-1] + 64)

        self.distance += self.scroll_speed * dt * FPS

        for p in self.platforms:
            p.update(dt, self.scroll_speed)
        self.platforms = [p for p in self.platforms if p.x + p.width > -10]

        platform_rects = [p.rect for p in self.platforms]
        self.hero.update(dt, platform_rects)

        for e in self.enemies:
            e.update(dt, self.scroll_speed)
        self.enemies = [e for e in self.enemies if e.x > -80]

        for c in self.coins:
            c.update(dt, self.scroll_speed)
        self.coins = [c for c in self.coins if c.x > -40 and not c.collected]

        if self.invincible > 0:
            self.invincible -= dt

        if self.invincible <= 0:
            for e in self.enemies:
                if self.hero.colliderect(e):
                    self.lives -= 1
                    self.invincible = INVINCIBLE_TIME
                    play_sound("hit")
                    break

        for c in self.coins:
            if not c.collected and self.hero.colliderect(c):
                c.collected = True
                self.score += 1
                play_sound("coin")

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_interval = max(1.0, 2.2 - self.distance * 0.0002)
            self._spawn_obstacle()

    def draw(self, screen):
        screen.blit("bg_far", (int(self.bg_x), 0))
        screen.blit("bg_far", (int(self.bg_x) + WIDTH, 0))
        screen.blit("bg_mid", (int(self.mid_x), 0))
        screen.blit("bg_mid", (int(self.mid_x) + WIDTH, 0))

        for tx in self.ground_tiles:
            screen.blit("ground", (int(tx), GROUND_Y))
            screen.blit("ground", (int(tx), GROUND_Y + 32))
            screen.blit("ground", (int(tx), GROUND_Y + 64))
        for p in self.platforms:
            p.draw(screen)
        for c in self.coins:
            c.draw(screen)
        for e in self.enemies:
            e.draw(screen)
        for i in range(self.lives):
            screen.blit("heart", (10 + i * 36, 10))

        if self.invincible <= 0 or int(self.invincible * 10) % 2 == 0:
            self.hero.draw(screen)

        if DEBUG:
            for e in self.enemies:
                screen.draw.rect(e._rect, (255, 0, 0))
            for c in self.coins:
                screen.draw.rect(c._rect, (255, 255, 0))
            screen.draw.rect(self.hero._rect, (0, 255, 0))
            for p in self.platforms:
                screen.draw.rect(p.rect, (0, 0, 255))

        screen.draw.text(
            f"Coins: {self.score}/{WIN_SCORE}",
            topright=(WIDTH - 10, 10),
            fontsize=24,
            color=(255, 220, 80),
        )
        screen.draw.text(
            f"Distance: {int(self.distance)}",
            topright=(WIDTH - 10, 38),
            fontsize=20,
            color=(180, 200, 220),
        )


class Button:
    def __init__(self, label, cx, cy, w=220, h=48):
        self.label = label
        self.cx, self.cy = cx, cy
        self.rect = Rect(cx - w // 2, cy - h // 2, w, h)
        self.hovered = False

    def check_hover(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

    def clicked(self, mx, my):
        return self.rect.collidepoint(mx, my)

    def draw(self, screen):
        col = (90, 180, 120) if self.hovered else (50, 120, 80)
        screen.draw.filled_rect(self.rect, col)
        screen.draw.text(
            self.label, center=(self.cx, self.cy), fontsize=26, color=(230, 255, 240)
        )


world = World()
menu_buttons = [
    Button("Start Game", WIDTH // 2, 190),
    Button("Sound: ON", WIDTH // 2, 250),
    Button("Exit", WIDTH // 2, 310),
]


def update_sound_label():
    menu_buttons[1].label = "Sound: ON" if sound_enabled else "Sound: OFF"


def draw():
    screen.clear()

    if state == STATE_MENU:
        screen.blit("bg_far", (0, 0))
        screen.draw.text(
            "SPACE RUNNER", center=(WIDTH // 2, 100), fontsize=60, color=(100, 220, 180)
        )
        screen.draw.text(
            "Collect coins to win!",
            center=(WIDTH // 2, 148),
            fontsize=22,
            color=(160, 220, 200),
        )
        for btn in menu_buttons:
            btn.draw(screen)

    elif state == STATE_PLAYING:
        world.draw(screen)

    elif state == STATE_WIN:
        screen.fill((10, 30, 50))
        screen.draw.text(
            "YOU WIN!", center=(WIDTH // 2, 150), fontsize=70, color=(100, 255, 160)
        )
        screen.draw.text(
            f"Coins collected: {world.score}",
            center=(WIDTH // 2, 230),
            fontsize=30,
            color=(200, 255, 220),
        )
        screen.draw.text(
            "Press SPACE to play again",
            center=(WIDTH // 2, 330),
            fontsize=22,
            color=(140, 200, 180),
        )

    elif state == STATE_LOSE:
        screen.fill((30, 10, 10))
        screen.draw.text(
            "GAME OVER", center=(WIDTH // 2, 150), fontsize=70, color=(255, 80, 80)
        )
        screen.draw.text(
            f"Coins: {world.score}/{WIN_SCORE}",
            center=(WIDTH // 2, 240),
            fontsize=28,
            color=(220, 160, 160),
        )
        screen.draw.text(
            "Press SPACE to try again",
            center=(WIDTH // 2, 320),
            fontsize=22,
            color=(200, 140, 140),
        )


def update(dt):
    global state, world

    if state == STATE_PLAYING:
        if keyboard.h or keyboard.left:
            world.hero.x -= 2 + world.scroll_speed * dt * FPS
        elif keyboard.l or keyboard.right:
            world.hero.x += 3
        world.update(dt)
        if world.lives <= 0:
            state = STATE_LOSE
            stop_music()
            play_sound("gameover")
        elif world.score >= WIN_SCORE:
            state = STATE_WIN
            stop_music()
            play_sound("win")


def on_mouse_move(pos):
    if state == STATE_MENU:
        for btn in menu_buttons:
            btn.check_hover(*pos)


def on_mouse_down(pos):
    global state, world, sound_enabled
    if state == STATE_MENU:
        mx, my = pos
        if menu_buttons[0].clicked(mx, my):
            world = World()
            state = STATE_PLAYING
        elif menu_buttons[1].clicked(mx, my):
            sound_enabled = not sound_enabled
            update_sound_label()
            start_music() if sound_enabled else stop_music()
        elif menu_buttons[2].clicked(mx, my):
            exit()


def on_key_down(key):
    global state, world, sound_enabled
    if state == STATE_PLAYING:
        if key in (keys.SPACE, keys.UP, keys.K):
            world.hero.jump()
        elif key == keys.ESCAPE:
            state = STATE_MENU
            stop_music()
    elif key in (keys.SPACE, keys.RETURN):
        start_music() if sound_enabled else stop_music()
        world = World()
        state = STATE_PLAYING
    if key == keys.M:
        sound_enabled = not sound_enabled
        update_sound_label()
        start_music() if sound_enabled else stop_music()


start_music()
