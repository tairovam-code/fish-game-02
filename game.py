import math
import os
import random
import sys

import pygame

pygame.init()

# 1. Окно
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Рыбка на pygame")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
big_font = pygame.font.SysFont(None, 48)
SCREEN_RECT = screen.get_rect()

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "images")


def load(name, scale=2):
    """Картинка с прозрачным фоном (convert_alpha), увеличенная без размытия."""
    img = pygame.image.load(os.path.join(IMG, name)).convert_alpha()
    w, h = img.get_size()
    return pygame.transform.scale(img, (w * scale, h * scale))


def hit_rect(surface, center):
    """Прямоугольник именно РЫБКИ (без прозрачных полей вокруг картинки).
    Нужен, чтобы рыбка доплывала точно до края окна и попадания были честными."""
    r = surface.get_rect(center=center)
    return surface.get_bounding_rect().move(r.topleft)


# 2. Картинки Kenney (PNG без фона). Рыбка в файле смотрит ВПРАВО.
COLORS = ["orange", "red", "blue", "green", "pink"]
fishes = [load(f"fish_{c}.png") for c in COLORS]
fishes_flipped = [pygame.transform.flip(f, True, False) for f in fishes]
bubble_imgs = [load(f"bubble_{c}.png", 1) for c in "abc"]
bullet_img = load("bubble_a.png", 2)  # пузырь-снаряд

bubbles = [
    {
        "img": random.choice(bubble_imgs),
        "x": random.randint(0, WIDTH),
        "y": random.randint(0, HEIGHT),
        "v": random.uniform(0.5, 1.8),
    }
    for _ in range(12)
]


# 3. Случайные объекты: рыбки-мишени, которые плавают хаотично
def new_direction(enemy):
    angle = random.uniform(0, 2 * math.pi)
    sp = random.uniform(1.5, 3.5)
    enemy["vx"] = math.cos(angle) * sp
    enemy["vy"] = math.sin(angle) * sp
    enemy["timer"] = random.randint(40, 120)  # через сколько кадров снова сменить курс


def spawn_enemy(avoid=None):
    i = random.randrange(len(fishes))
    while True:
        x = random.randint(80, WIDTH - 80)
        y = random.randint(80, HEIGHT - 80)
        # не появляемся прямо на игроке
        if avoid is None or math.hypot(x - avoid[0], y - avoid[1]) > 200:
            break
    enemy = {"i": i, "x": x, "y": y, "vx": 0, "vy": 0, "timer": 0}
    new_direction(enemy)
    # картинка и хитбокс нужны сразу, иначе при появлении новой рыбки будет KeyError
    enemy["img"] = fishes[i] if enemy["vx"] >= 0 else fishes_flipped[i]
    enemy["hb"] = hit_rect(enemy["img"], (x, y))
    return enemy


# 4. Состояние игры
x, y = WIDTH / 2, HEIGHT / 2
speed = 5
facing_right = True
tilt_target = 0.0
tilt = 0.0
t = 0.0
fish_index = 0
score = 0
shoot_cooldown = 0
bullets = []
enemies = [spawn_enemy((x, y)) for _ in range(6)]

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_c:  # C - сменить цвет рыбки
                fish_index = (fish_index + 1) % len(fishes)

    keys = pygame.key.get_pressed()
    dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
    dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])

    moving = bool(dx or dy)
    if moving:
        length = math.hypot(dx, dy)
        x += dx / length * speed
        y += dy / length * speed
        t += 0.35  # "плавание": рыбка покачивается
        if dx:
            facing_right = dx > 0
        tilt_target = -dy * 15  # вверх - нос кверху, вниз - нос книзу
    else:
        t += 0.08
        tilt_target = 0

    tilt += (tilt_target - tilt) * 0.2
    wobble = math.sin(t) * (6 if moving else 2)

    fish = fishes[fish_index]
    if not facing_right:
        fish = fishes_flipped[fish_index]
    angle = tilt + wobble
    if not facing_right:
        angle = -angle
    fish = pygame.transform.rotate(fish, angle)

    # --- ОГРАНИЧЕНИЕ ПО РАМКЕ ЭКРАНА ---
    # берём прямоугольник самой рыбки и не даём ему выйти за окно
    player_hb = hit_rect(fish, (x, y))
    fixed = player_hb.clamp(SCREEN_RECT)
    x += fixed.x - player_hb.x
    y += fixed.y - player_hb.y
    player_hb = fixed

    # --- СТРЕЛЬБА ПО ПРОБЕЛУ ---
    if shoot_cooldown > 0:
        shoot_cooldown -= 1
    if keys[pygame.K_SPACE] and shoot_cooldown == 0:
        direction = 1 if facing_right else -1
        mouth_x = player_hb.right if facing_right else player_hb.left
        bullets.append({"x": mouth_x, "y": player_hb.centery, "vx": 12 * direction})
        shoot_cooldown = 15  # не чаще 4 выстрелов в секунду

    # --- ДВИЖЕНИЕ СНАРЯДОВ ---
    for b in bullets:
        b["x"] += b["vx"]
    bullets = [b for b in bullets if -40 < b["x"] < WIDTH + 40]

    # --- ХАОТИЧНОЕ ДВИЖЕНИЕ РЫБОК-МИШЕНЕЙ ---
    for e in enemies:
        e["timer"] -= 1
        if e["timer"] <= 0:
            new_direction(e)           # время от времени резко меняем курс
        e["vy"] += random.uniform(-0.3, 0.3)       # и постоянно чуть "виляем"
        e["vy"] = max(-3.5, min(3.5, e["vy"]))
        e["x"] += e["vx"]
        e["y"] += e["vy"]

        img = fishes[e["i"]] if e["vx"] >= 0 else fishes_flipped[e["i"]]
        hb = hit_rect(img, (e["x"], e["y"]))
        # отскок от краёв окна
        if hb.left < 0:
            e["x"] -= hb.left
            e["vx"] = abs(e["vx"])
        if hb.right > WIDTH:
            e["x"] -= hb.right - WIDTH
            e["vx"] = -abs(e["vx"])
        if hb.top < 0:
            e["y"] -= hb.top
            e["vy"] = abs(e["vy"])
        if hb.bottom > HEIGHT:
            e["y"] -= hb.bottom - HEIGHT
            e["vy"] = -abs(e["vy"])
        e["img"] = fishes[e["i"]] if e["vx"] >= 0 else fishes_flipped[e["i"]]
        e["hb"] = hit_rect(e["img"], (e["x"], e["y"]))

    # --- ПОПАДАНИЯ ---
    alive_bullets = []
    for b in bullets:
        brect = bullet_img.get_rect(center=(b["x"], b["y"]))
        hit = False
        for k, e in enumerate(enemies):
            if brect.colliderect(e["hb"]):
                score += 1
                enemies[k] = spawn_enemy((x, y))  # подбитая рыбка появляется заново
                hit = True
                break
        if not hit:
            alive_bullets.append(b)
    bullets = alive_bullets

    # --- РИСУЕМ ---
    screen.fill((51, 153, 220))
    for b in bubbles:
        b["y"] -= b["v"]
        if b["y"] < -20:
            b["y"] = HEIGHT + 20
            b["x"] = random.randint(0, WIDTH)
        screen.blit(b["img"], (b["x"], b["y"]))

    for e in enemies:
        screen.blit(e["img"], e["img"].get_rect(center=(e["x"], e["y"])))
    for b in bullets:
        screen.blit(bullet_img, bullet_img.get_rect(center=(b["x"], b["y"])))
    screen.blit(fish, fish.get_rect(center=(x, y)))

    hint = font.render(
        "Стрелки/WASD - плыть, Пробел - стрелять, C - цвет, Esc - выход",
        True, (255, 255, 255),
    )
    screen.blit(hint, (10, 10))
    score_text = big_font.render(f"Счёт: {score}", True, (255, 255, 255))
    screen.blit(score_text, (WIDTH - score_text.get_width() - 15, 40))
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
