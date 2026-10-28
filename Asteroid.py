import pygame, random, os, json

# -------------------- Configuration --------------------

pygame.init()
pygame.mixer.pre_init(44100, -16, 1, 60)
pygame.mixer.init()
background_music = pygame.mixer.music.load("audio/backgroundMusic.wav")
pygame.mixer.music.set_volume(0.8)
pygame.mixer.music.play(-1)

WIDTH, HEIGHT = 1280, 720
FPS = 60
difficulyMul = 1
PLAYER_SPEED = 300       # Pixels per second
BULLET_SPEED = 360       # Pixels per second
ASTEROID_SPEED = 30      # Pixels per second

SPAWN_INTERVAL = 3       # Seconds between asteroid waves
ASTEROIDS_PER_WAVE = 6

TIME_SCORE = 50
ASTEROID_SCORE = 100

BACKGROUND_COLOR = "dark grey"

options = ["Play", "Leaderboard", "Quit"]
play_again = ["Yes", "No"]
continueMenu = False
difficulties = ["Easy" ,"Medium", "Hard"]
difficultyMenu = False
selected = 0

paused = False

initials = ""
saved = False
leaderboard = False
played = False
mode = ""

window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Asteroid Shooter")

clock = pygame.time.Clock()
font = pygame.font.Font(None, 48)
titleFont = pygame.font.Font(None, 72)

# -------------------- Asset Loading --------------------

def load_image(path, size=None):
    """Load an image once and optionally resize it."""
    image = pygame.image.load(path).convert_alpha()

    if size:
        image = pygame.transform.scale(image, size)

    return image


ship_image = load_image("img/ship.png", (100, 100))
bullet_image = load_image("img/beam.png", (25, 25))
asteroid_image = load_image("img/astroid.png", (200, 200))
space_image = load_image("img/space.png", (WIDTH, HEIGHT))
impact_image = load_image("img/impact.png", (400, 400))
laser_wav = pygame.mixer.Sound("audio/laser.wav")
boom_wav = pygame.mixer.Sound("audio/boom.wav")
choose_wav = pygame.mixer.Sound("audio/choose.wav")
select_wav = pygame.mixer.Sound("audio/select.wav")

ship_images = {
    "up": ship_image,
    "down": pygame.transform.rotate(ship_image, 180),
    "left": pygame.transform.rotate(ship_image, 90),
    "right": pygame.transform.rotate(ship_image, 270),
}

# -------------------- Game Objects --------------------

class Bullet:
    def __init__(self, position, direction):
        self.image = bullet_image
        self.rect = self.image.get_rect(center=position)
        self.direction = direction

        #This sets up an object and chooses the proper value based on the value of direction. Eg. if direction is "up" then velocity = the value of "up"
        self.velocity = {
            "up": (0, -BULLET_SPEED),
            "down": (0, BULLET_SPEED),
            "left": (-BULLET_SPEED, 0),
            "right": (BULLET_SPEED, 0),
        }[direction]

    def update(self, dt):
        self.rect.x += round(self.velocity[0] * dt)
        self.rect.y += round(self.velocity[1] * dt)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def off_screen(self):
        return not window.get_rect().colliderect(self.rect)


class Player:
    def __init__(self):
        #Using the // operator it rounds down to the nearest integer
        self.rect = ship_image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.direction = "up"
        self.alive = True

    def update(self, keys, dt):
        if not self.alive:
            return

        #keys[pygame.K_*] returns a 0 for pressed and 1 for pressed.
        #This means dx can return either -1,0,1 -1 to a, 0 for none, 1 to d
        dx = keys[pygame.K_d] - keys[pygame.K_a]
        dy = keys[pygame.K_s] - keys[pygame.K_w]

        # Normalize diagonal movement so it isn't faster.
        #vector allows simultanious direction inputs to be handled under one comman.
        movement = pygame.Vector2(dx, dy)

        #using length squared it checks to see if movement is seen
        if movement.length_squared() > 0:
            #if movement is one direction normalize does nothing,
            #if movement is a diagonal direction it basically treats it as a single direction
            movement = movement.normalize() * PLAYER_SPEED * dt
            self.rect.x += round(movement.x)
            self.rect.y += round(movement.y)

        #clamp_ip (clamp in place) when used in this way keeps the rect from crossing the boundaries of another rect.
        self.rect.clamp_ip(window.get_rect())

        if keys[pygame.K_w]:
            self.direction = "up"
        elif keys[pygame.K_s]:
            self.direction = "down"
        elif keys[pygame.K_a]:
            self.direction = "left"
        elif keys[pygame.K_d]:
            self.direction = "right"

    def shoot(self):
        # Place the bullet at the edge of the ship.
        offsets = {
            "up": (0, -self.rect.height // 2),
            "down": (0, self.rect.height // 2),
            "left": (-self.rect.width // 2, 0),
            "right": (self.rect.width // 2, 0),
        }

        offset = offsets[self.direction]
        position = (self.rect.centerx + offset[0],self.rect.centery + offset[1])

        return Bullet(position, self.direction)

    def draw(self, surface):
        if self.alive:
            surface.blit(ship_images[self.direction],self.rect)

    def reset(self):
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        self.direction = "up"
        self.alive = True


class Asteroid:
    # Movement direction for each edge and target.
    VELOCITIES = {
        "upLeft": (-1, 1),
        "upMiddle": (0, 1),
        "upRight": (1, 1),
        "leftUp": (1, -1),
        "leftMiddle": (1, 0),
        "leftDown": (1, 1),
        "downLeft": (-1, -1),
        "downMiddle": (0, -1),
        "downRight": (1, -1),
        "rightUp": (-1, -1),
        "rightMiddle": (-1, 0),
        "rightDown": (-1, 1),
    }

    def __init__(self):
        self.image = asteroid_image
        self.rect = self.image.get_rect()
        self.speed = ASTEROID_SPEED

        side = random.choice(("top", "bottom", "left", "right"))

        if side in ("top", "bottom"):
            self.rect.centerx = random.randint(-200, WIDTH + 200)
            self.rect.centery = -200 if side == "top" else HEIGHT + 200

            if self.rect.centerx < WIDTH * 0.4:
                target = "Right"
            elif self.rect.centerx > WIDTH * 0.6:
                target = "Left"
            else:
                target = random.choice(("Left", "Middle", "Right"))

            self.path = ("up" if side == "top" else "down") + target

        else:
            self.rect.centery = random.randint(-100, HEIGHT + 100)
            self.rect.centerx = -200 if side == "left" else WIDTH + 200

            if self.rect.centery < HEIGHT * 0.4:
                target = "Down"
            elif self.rect.centery > HEIGHT * 0.6:
                target = "Up"
            else:
                target = random.choice(("Up", "Middle", "Down"))

            self.path = ("left" if side == "left" else "right") + target

        # The normalized vector gives diagonal movement a consistent speed.
        self.velocity = pygame.Vector2(self.VELOCITIES[self.path]).normalize() if self.VELOCITIES[self.path] != (0, 0) else pygame.Vector2()

    def update(self, dt):
        self.rect.x += round(self.velocity.x * self.speed * dt)
        self.rect.y += round(self.velocity.y * self.speed * dt)

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def off_screen(self):
        bounds = window.get_rect().inflate(400, 400)
        return not bounds.colliderect(self.rect)


#-----------------Save and Load Logic-----------------

class HighScoreManager:
    def __init__(self, filename="high_scores.json", max_scores=10):
        self.filename = filename
        self.max_scores = max_scores
        self.scores = []
        self.load_scores()

    def load_scores(self):
        self.scores = []
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as file:
                    data = json.load(file)
                for entry in data:
                    initials = str(entry["initials"])[:3].upper()
                    score = int(entry["score"])
                    mode = str(entry["mode"])
                    self.scores.append({
                        "initials": initials,
                        "score": score,
                        "mode": mode
                    })
            except(OSError, ValueError, TypeError, KeyError):
                print("Could not load high scores.")
                self.scores = []
        self.scores.sort(key=lambda entry: entry["score"], reverse=True)
        self.scores = self.scores[:self.max_scores]

    def save_scores(self):
        try:
            with open(self.filename, "w") as file:
                json.dump(self.scores, file, indent=4)
        except OSError:
            print("could not save high score")

    def qualifies(self, score):
        return (len(self.scores) < self.max_scores or score > self.scores[-1]["score"])

    def add_score(self, initials, score, mode):
        if not self.qualifies(score):
            return False
        initials = "".join(c for c in initials.upper() if c.isalnum())[:3]

        if not initials:
            initials = "???"

        self.scores.append({
            "initials": initials,
            "score": int(score),
            "mode": mode
        })

        self.scores.sort(key=lambda entry: entry["score"], reverse=True)
        self.scores = self.scores[:self.max_scores]
        self.save_scores()
        return True

    def get_scores(self):
        return [entry.copy() for entry in self.scores]

scoreManager = HighScoreManager()

# -------------------- Game Setup --------------------

player = Player()
bullets = []
asteroids = []
impacts = []

score = 0
asteroid_speed = ASTEROID_SPEED
spawn_timer = 0
impact_life = 200
game_state = "title"

# -------------------- Game Functions --------------------

def reset_game():
    global score, spawn_timer, asteroid_speed, TIME_SCORE, ASTEROID_SCORE, SPAWN_INTERVAL, ASTEROIDS_PER_WAVE, ASTEROID_SPEED, mode

    player.reset()
    bullets.clear()
    asteroids.clear()

    score = 0
    spawn_timer = 0
    if not played and difficulyMul == 1:
        SPAWN_INTERVAL = 4
        ASTEROIDS_PER_WAVE = 4
        ASTEROID_SPEED = 60
        asteroid_speed = 60
        mode = 'EASY'
        print(mode + " " + str(SPAWN_INTERVAL) + " " + str(ASTEROIDS_PER_WAVE) + " " + str(ASTEROID_SPEED))
    elif not played and difficulyMul == 3:
        SPAWN_INTERVAL = 2
        ASTEROIDS_PER_WAVE = 8
        ASTEROID_SPEED = 100
        asteroid_speed = 100
        mode = "HARD"
        print(mode + " " + str(SPAWN_INTERVAL) + " " + str(ASTEROIDS_PER_WAVE) + " " + str(ASTEROID_SPEED))
    else:
        SPAWN_INTERVAL = 3
        ASTEROIDS_PER_WAVE = 6
        ASTEROID_SPEED = 80
        asteroid_speed = 80
        mode = "Medium"
        print(mode + " " + str(SPAWN_INTERVAL) + " " + str(ASTEROIDS_PER_WAVE) + " " + str(ASTEROID_SPEED))

def handle_events():
    global game_state, running, selected, paused, initials, saved, leaderboard, difficultyMenu, difficulyMul, played, continueMenu

    for event in pygame.event.get():
        if saved and not player.alive or not scoreManager.qualifies(score) and not player.alive:
            continueMenu = True
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_w:
                if game_state == "title":
                    select_wav.play()
                    if not difficultyMenu:
                        selected = (selected - 1) % len(options)
                    elif difficultyMenu:
                        selected = (selected - 1) % len(difficulties)
            if event.key == pygame.K_s:
                if game_state == "title":
                    select_wav.play()
                    if not difficultyMenu:
                        selected = (selected + 1) % len(options)
                    elif difficultyMenu:
                        selected = (selected +1 ) % len(difficulties)
            if event.key == pygame.K_a:
                if saved and not player.alive or not scoreManager.qualifies(score) and not player.alive:
                    select_wav.play()
                    selected = (selected - 1) % len(play_again)
            if event.key == pygame.K_d:
                if saved and not player.alive or not scoreManager.qualifies(score) and not player.alive:
                    select_wav.play()
                    selected = (selected + 1) % len(play_again)
            if event.key == pygame.K_RETURN:
                choose_wav.play()
                if game_state == "title":
                    if leaderboard:
                        leaderboard = False
                        break
                    elif difficultyMenu:
                        difficultyMenu = False
                        difficulyMul = selected + 1
                        reset_game()
                        selected = 0
                        played = True
                        game_state = "game"
                    elif selected == 0 and not leaderboard:
                        difficultyMenu = True
                    elif selected == 1 and not leaderboard:
                        selected = 0
                        leaderboard = True
                    elif selected == 2 and not leaderboard:
                        running = False
                if game_state == "game":
                    if scoreManager.qualifies(score) and not player.alive and not saved:
                        if initials:
                            saved = True
                            scoreManager.add_score(initials, score, mode)
                    if saved and not player.alive or not scoreManager.qualifies(score) and not player.alive:
                        if selected == 0 and continueMenu:
                            saved = False
                            continueMenu = False
                            reset_game()
                        if selected == 1 and continueMenu:
                            print("this should be taking me back to title")
                            saved = False
                            difficulyMul = 1
                            selected = 0
                            played = False
                            continueMenu = False
                            reset_game()
                            game_state = "title"
            if scoreManager.qualifies(score) and not player.alive and not saved:
                if event.unicode.isalnum() and len(initials) < 3:
                    select_wav.play()
                    initials += event.unicode.upper()
            if event.key == pygame.K_BACKSPACE:
                select_wav.play()
                if difficultyMenu:
                    difficultyMenu = False
                    selected = 0
                elif scoreManager.qualifies(score) and not player.alive and not saved:
                    initials = initials[:-1]
            if event.key == pygame.K_SPACE:
                if game_state == "game":
                    if player.alive and not paused:
                        laser_wav.play()
                        bullets.append(player.shoot())
            if event.key == pygame.K_p:
                choose_wav.play()
                if game_state == "game":
                    if paused:
                        paused = False
                    else:
                        paused = True

def update_game(dt):
    global score, spawn_timer, asteroid_speed, played, continueMenu

    if not player.alive:
        return

    player.update(pygame.key.get_pressed(), dt)

    # Spawn an asteroid wave every five seconds.
    spawn_timer += dt

    if spawn_timer >= SPAWN_INTERVAL:
        spawn_timer -= SPAWN_INTERVAL
        score += TIME_SCORE
        asteroid_speed += 6

        for _ in range(ASTEROIDS_PER_WAVE):
            asteroids.append(Asteroid())

    # Update and remove bullets.
    for bullet in bullets:
        bullet.update(dt)

    bullets[:] = [
        bullet for bullet in bullets
        if not bullet.off_screen()
    ]

    # Update and remove asteroids.
    for asteroid in asteroids:
        asteroid.speed = asteroid_speed
        asteroid.update(dt)

    asteroids[:] = [
        asteroid for asteroid in asteroids
        if not asteroid.off_screen()
    ]

    # Check collisions.
    player_hitbox = player.rect.inflate(-60, -60)

    for asteroid in asteroids:
        asteroid_hitbox = asteroid.rect.inflate(-110, -110)

        if player_hitbox.colliderect(asteroid_hitbox):
            player.alive = False
            played = False
            break

    # Remove each asteroid and bullet at most once.
    destroyed_asteroids = set()
    spent_bullets = set()

    for bullet in bullets:
        for asteroid in asteroids:
            if asteroid in destroyed_asteroids:
                continue

            hitbox = asteroid.rect.inflate(-110, -110)

            if bullet.rect.colliderect(hitbox):
                boom_wav.play()
                destroyed_asteroids.add(asteroid)
                spent_bullets.add(bullet)
                center = asteroid.rect
                impacts.append({
                    "position": center,
                    "start_time": pygame.time.get_ticks()
                })
                score += ASTEROID_SCORE
                break

    asteroids[:] = [
        asteroid for asteroid in asteroids
        if asteroid not in destroyed_asteroids
    ]

    bullets[:] = [
        bullet for bullet in bullets
        if bullet not in spent_bullets
    ]


def draw_game():
    window.fill(BACKGROUND_COLOR)

    window.blit(space_image, space_image.get_rect(center=(WIDTH // 2,HEIGHT // 2)))

    player.draw(window)

    for bullet in bullets:
        bullet.draw(window)

    for asteroid in asteroids:
        asteroid.draw(window)

        current_time = pygame.time.get_ticks()
        for impact in impacts[:]:
            elapsed = current_time - impact["start_time"]
            if elapsed < impact_life:
                window.blit(impact_image, (impact["position"].x - 100, impact["position"].y - 100))
            else:
                impacts.remove(impact)

    score_surface = font.render(
        f"Score: {score}", True, "white"
    )
    window.blit(score_surface, (20, 10))
    
    if not player.alive:
        xPos = -50
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        window.blit(overlay, (0, 0))
        title = font.render("Game Over", True, "white")
        final_score = font.render(f"Score: {score}", True, "white")
        window.blit(title,title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 70)))
        window.blit(final_score,final_score.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        if scoreManager.qualifies(score) and not saved:
            prompt = font.render("Enter your initials: ", True, "white")
            entry = font.render(initials + ("_" * (3 - len(initials))), True, "white")
            window.blit(prompt, prompt.get_rect(center = (WIDTH // 2 -150, HEIGHT // 2 + 140)))
            window.blit(entry, entry.get_rect(center = (WIDTH // 2 + 50, HEIGHT // 2 + 140)))
        if not scoreManager.qualifies(score) or saved:
            for i, option in enumerate(play_again):
                if i > 0:
                    xPos += 100
                if i == selected:
                    color = "yellow"
                    label = "> " + option
                else:
                    color = "white"
                    label = option
                option_text = font.render(label, True, color)
                window.blit(option_text, option_text.get_rect(center=(WIDTH // 2 + xPos, HEIGHT //2 + 100)))
            text = titleFont.render("Play again?", True, "white")
            window.blit(text, text.get_rect(center=(WIDTH //2, HEIGHT // 2 + 50)))

def draw_title():
    global option

    window.blit(space_image, space_image.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    if leaderboard:
        scoreOffset = 40
        currentOffset = 25
        boardTitle = titleFont.render("High Scores", True, "white")
        window.blit(boardTitle, boardTitle.get_rect(center=(WIDTH // 2,75)))
        highScores = scoreManager.get_scores()
        count = len(highScores)
        for entry in highScores:
            count -= 1
            if count < len(highScores)-1:
                currentOffset += scoreOffset
            entryText = font.render(entry["initials"] + ": " + str(entry["score"]) + " " + entry["mode"], True, "white")
            window.blit(entryText, entryText.get_rect(center=(WIDTH // 2, (125 + currentOffset))))

    if difficultyMenu:
        difTitle = titleFont.render("Select Difficulty", True, "white")
        window.blit(difTitle, difTitle.get_rect(center=(WIDTH // 2, 100)))
        selectOffset = 40
        newOffset = 0
        for i, diff in enumerate(difficulties):
            newOffset += selectOffset

            if i == selected:
                color = "yellow"
                label = "> " + diff
            else:
                color = "white"
                label = diff
            selectedDif = font.render(label, True, color)
            window.blit(selectedDif, selectedDif.get_rect(center=(WIDTH // 2, 120+newOffset)))

    title = titleFont.render("Asteroid Shooter", True, "white")

    yPos = 0
    if not leaderboard and not difficultyMenu:
        for i, option in enumerate(options):
            yPos += 200
            if i == selected:
                color = "yellow"
                label = "> " + option
            else:
                color = "white"
                label = option
            text = font.render(label, True, color)
            window.blit(text, text.get_rect(center = (WIDTH // 2, yPos)))

        window.blit(title,title.get_rect(center=(WIDTH // 2, 100)))

# -------------------- Main Loop --------------------

running = True

while running:
    dt = min(clock.tick(FPS) / 1000, 0.05)

    handle_events()

    if game_state == "title":
        draw_title()
    else:
        if not paused:
            update_game(dt)
            draw_game()

    pygame.display.flip()

pygame.mixer.quit()
pygame.quit()