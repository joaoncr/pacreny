import pygame
import sys
import os
import random
import math

WIDTH, HEIGHT = 0, 0
FPS = 60
TILE_SIZE = 40

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
PINK = (255, 192, 203)
RED = (255, 0, 0)
BLUE_WALL = (60, 60, 200)

PLAYER_START_POS = (1, 1)
lives = 3

pygame.init()
pygame.mixer.init()

LABIRINTO_PACMAN_CLASSICO = [
    "11111111111",
    "1P220022221",
    "11101110111",
    "1G002020G01",
    "11101110111",
    "12224222221",
    "11111111111"
]

CURRENT_LABYRINTH = LABIRINTO_PACMAN_CLASSICO
GRID_WIDTH = len(CURRENT_LABYRINTH[0])
GRID_HEIGHT = len(CURRENT_LABYRINTH)
WIDTH = GRID_WIDTH * TILE_SIZE + 500
HEIGHT = (GRID_HEIGHT * TILE_SIZE) + 500

OFFSET_X = 500 // 2
OFFSET_Y = 500 // 2

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Nosso Joguinho de Amor!")
clock = pygame.time.Clock()

FONT_DEFAULT = pygame.font.Font(None, 74)
FONT_SMALL = pygame.font.Font(None, 48)

def load_asset_image(path, scale_to_tile=True, custom_size=None):
    full_path = os.path.join('assets', path)
    try:
        image = pygame.image.load(full_path).convert_alpha()
        if custom_size:
            return pygame.transform.scale(image, custom_size)
        elif scale_to_tile:
            return pygame.transform.scale(image, (TILE_SIZE-4, TILE_SIZE-4))
        return image
    except pygame.error as e:
        print(f"Erro ao carregar asset '{full_path}': {e}")
        fallback_surface = pygame.Surface((TILE_SIZE, TILE_SIZE) if scale_to_tile else (50, 50))
        fallback_surface.fill(RED)
        return fallback_surface

ASSETS = {
    'player_img': load_asset_image('player.png', custom_size=(TILE_SIZE-4, TILE_SIZE-4)),
    'heart_img': load_asset_image('heart.png', custom_size=(TILE_SIZE//2, TILE_SIZE//2)),
    'ghost_img': load_asset_image('ghost.png', custom_size=(TILE_SIZE-4, TILE_SIZE-4)),
    'power_pellet_img': load_asset_image('power_pellet.png', custom_size=(TILE_SIZE//1.5, TILE_SIZE//1.5)),
    'music': os.path.join('assets', 'music.mp3'),
    'collect_sound': os.path.join('assets', 'collect_sound.wav'),
    'game_over_sound': os.path.join('assets', 'game_over_sound.wav'),
    'win_sound': os.path.join('assets', 'win_sound.wav')
}

try:
    pygame.mixer.music.load(ASSETS['music'])
    pygame.mixer.music.play(-1)
except pygame.error as e:
    print(f"Erro ao carregar ou tocar música: {e}")
    print("Certifique-se de que o arquivo 'music.mp3' está na pasta 'assets' e não está corrompido.")

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = ASSETS['player_img']
        self.rect = self.image.get_rect(topleft=(x+2, y+2))
        self.speed = 4
        self.dx = 0
        self.dy = 0
        self.score = 0

    def update(self, *args, **kwargs):
        self.rect.x += self.dx
        self.rect.y += self.dy
        if self.rect.right < 0:
            self.rect.left = WIDTH
        elif self.rect.left > WIDTH:
            self.rect.right = 0
        if self.rect.bottom < 0:
            self.rect.top = HEIGHT
        elif self.rect.top > HEIGHT:
            self.rect.bottom = 0

    def set_direction(self, dx, dy):
        self.dx = dx * self.speed
        self.dy = dy * self.speed

    def stop_direction(self):
        self.dx = 0
        self.dy = 0

class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([TILE_SIZE, TILE_SIZE])
        self.image.fill(BLUE_WALL)
        pygame.draw.rect(self.image, BLACK, (0, 0, TILE_SIZE, TILE_SIZE), 2)
        self.rect = self.image.get_rect(topleft=(x, y))

class Heart(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = ASSETS['heart_img']
        self.rect = self.image.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2))

class PowerPellet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = ASSETS['power_pellet_img']
        self.rect = self.image.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2)) # ESTA LINHA É CRÍTICA!

class Ghost(pygame.sprite.Sprite):
    def __init__(self, x, y, player_ref):
        super().__init__()
        self.original_image = ASSETS['ghost_img']
        self.vulnerable_image = pygame.Surface([TILE_SIZE-4, TILE_SIZE-4])
        self.vulnerable_image.fill((0, 0, 255))
        self.image = self.original_image
        self.rect = self.image.get_rect(topleft=(x+2, y+2))
        self.speed = 2
        self.direction = (random.choice([1, -1, 0]), random.choice([1, -1, 0]))
        while self.direction == (0,0):
            self.direction = (random.choice([1, -1, 0]), random.choice([1, -1, 0]))
        self.player_ref = player_ref
        self.vulnerable = False
        self.vulnerable_timer = 0
        self.last_grid_x = x // TILE_SIZE
        self.last_grid_y = y // TILE_SIZE
        self.path_decision_cooldown = 0
        self.ghost_start_pos = (x,y)

    def update(self, walls):
        if self.vulnerable:
            self.vulnerable_timer -= 1
            if self.vulnerable_timer <= 0:
                self.vulnerable = False
                self.image = self.original_image
            else:
                self.image = self.vulnerable_image
                self._move_away_from_player(walls)
                return
        self._chase_player(walls)

    def _chase_player(self, walls):
        current_grid_x = round(self.rect.x / TILE_SIZE)
        current_grid_y = round(self.rect.y / TILE_SIZE)
        if (current_grid_x != self.last_grid_x or current_grid_y != self.last_grid_y) and self.path_decision_cooldown <= 0:
            self.last_grid_x = current_grid_x
            self.last_grid_y = current_grid_y
            dx_to_player = self.player_ref.rect.centerx - self.rect.centerx
            dy_to_player = self.player_ref.rect.centery - self.rect.centery
            possible_moves = []
            if abs(dx_to_player) > abs(dy_to_player):
                if dx_to_player > 0: possible_moves.append((1, 0))
                else: possible_moves.append((-1, 0))
                possible_moves.append((0, 1))
                possible_moves.append((0, -1))
            else:
                if dy_to_player > 0: possible_moves.append((0, 1))
                else: possible_moves.append((0, -1))
                possible_moves.append((1, 0))
                possible_moves.append((-1, 0))
            if self.direction not in possible_moves:
                possible_moves.append(self.direction)
            best_dir = self.direction
            random.shuffle(possible_moves)
            for d in possible_moves:
                temp_rect = self.rect.copy()
                temp_rect.x += d[0] * self.speed
                temp_rect.y += d[1] * self.speed
                if not any(temp_rect.colliderect(wall.rect) for wall in walls):
                    best_dir = d
                    break
            self.direction = best_dir
            self.path_decision_cooldown = 15
        self.rect.x += self.direction[0] * self.speed
        self.rect.y += self.direction[1] * self.speed
        collided_walls = pygame.sprite.spritecollide(self, walls, False)
        for wall in collided_walls:
            if self.direction[0] > 0: self.rect.right = wall.rect.left
            if self.direction[0] < 0: self.rect.left = wall.rect.right
            if self.direction[1] > 0: self.rect.bottom = wall.rect.top
            if self.direction[1] < 0: self.rect.top = wall.rect.bottom
            self._change_direction_on_collision()

    def _change_direction_on_collision(self):
        possible_directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        op_dir = (-self.direction[0], -self.direction[1])
        if op_dir in possible_directions:
            possible_directions.remove(op_dir)
        if possible_directions:
            self.direction = random.choice(possible_directions)
        else:
            self.direction = op_dir

    def _move_away_from_player(self, walls):
        dx_to_player = self.player_ref.rect.centerx - self.rect.centerx
        dy_to_player = self.player_ref.rect.centery - self.rect.centery
        target_dx = -1 if dx_to_player > 0 else (1 if dx_to_player < 0 else 0)
        target_dy = -1 if dy_to_player > 0 else (1 if dy_to_player < 0 else 0)
        new_x = self.rect.x + target_dx * (self.speed // 2)
        new_y = self.rect.y + target_dy * (self.speed // 2)
        test_rect = self.rect.copy()
        test_rect.x = new_x
        test_rect.y = new_y
        if not any(test_rect.colliderect(wall.rect) for wall in walls):
            self.rect.x = new_x
            self.rect.y = new_y
        else:
            self._change_direction_on_collision()

    def set_vulnerable(self, duration_frames):
        self.vulnerable = True
        self.vulnerable_timer = duration_frames
        self.image = self.vulnerable_image

    def reset_position(self):
        self.rect.topleft = self.ghost_start_pos
        self.vulnerable = False
        self.vulnerable_timer = 0
        self.image = self.original_image
        self.direction = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])

all_sprites = pygame.sprite.Group()
walls = pygame.sprite.Group()
hearts = pygame.sprite.Group()
power_pellets = pygame.sprite.Group()
ghosts = pygame.sprite.Group()
player = None

def setup_game():
    global player, lives, PLAYER_START_POS
    all_sprites.empty()
    walls.empty()
    hearts.empty()
    power_pellets.empty()
    ghosts.empty()
    player_found = False
    player_found_in_map = False
    for row_idx, row in enumerate(CURRENT_LABYRINTH):
        for col_idx, char in enumerate(row):
            if char == 'P':
                PLAYER_START_POS = (col_idx, row_idx)
                player = Player(col_idx * TILE_SIZE + OFFSET_X, row_idx * TILE_SIZE + OFFSET_Y)
                all_sprites.add(player)
                player_found_in_map = True
                break
        if player_found_in_map:
            break

    if player is None:
        player = Player(PLAYER_START_POS[0] * TILE_SIZE + OFFSET_X, PLAYER_START_POS[1] * TILE_SIZE + OFFSET_Y)
        all_sprites.add(player)
        print("Aviso: 'P' não encontrado no labirinto. Player criado em posição padrão.")

    for row_idx, row in enumerate(CURRENT_LABYRINTH):
        for col_idx, char in enumerate(row):
            x = col_idx * TILE_SIZE + OFFSET_X
            y = row_idx * TILE_SIZE + OFFSET_Y 

            if char == '1':
                wall = Wall(x, y)
                walls.add(wall)
                all_sprites.add(wall)
            elif char == '2':
                heart = Heart(x, y)
                hearts.add(heart)
                all_sprites.add(heart)
            elif char == '4':
                pellet = PowerPellet(x, y)
                power_pellets.add(pellet)
                all_sprites.add(pellet)
            elif char == 'G':
                ghost = Ghost(x, y, player)
                ghosts.add(ghost)
                all_sprites.add(ghost)
    player.score = 0
    global lives
    lives = 3

setup_game()

running = True
game_over = False
win_message = False
power_pellet_active = False
power_pellet_timer = 0

GAME_STATE_PLAYING = 0
GAME_STATE_GAME_OVER = 1
GAME_STATE_WIN = 2
current_game_state = GAME_STATE_PLAYING

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if current_game_state == GAME_STATE_PLAYING:
                if event.key == pygame.K_LEFT:
                    player.set_direction(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    player.set_direction(1, 0)
                elif event.key == pygame.K_UP:
                    player.set_direction(0, -1)
                elif event.key == pygame.K_DOWN:
                    player.set_direction(0, 1)
            if event.key == pygame.K_r and (current_game_state == GAME_STATE_GAME_OVER or current_game_state == GAME_STATE_WIN):
                game_over = False
                win_message = False
                current_game_state = GAME_STATE_PLAYING
                setup_game()
        elif event.type == pygame.KEYUP:
            if current_game_state == GAME_STATE_PLAYING:
                if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
                    player.stop_direction()
    if current_game_state == GAME_STATE_PLAYING:
        all_sprites.update(walls)
        player.rect.x += player.dx
        collided_walls_x = pygame.sprite.spritecollide(player, walls, False)
        for wall in collided_walls_x:
            if player.dx > 0:
                player.rect.right = wall.rect.left
            elif player.dx < 0:
                player.rect.left = wall.rect.right
            player.dx = 0
        player.rect.y += player.dy
        collided_walls_y = pygame.sprite.spritecollide(player, walls, False)
        for wall in collided_walls_y:
            if player.dy > 0:
                player.rect.bottom = wall.rect.top
            elif player.dy < 0:
                player.rect.top = wall.rect.bottom
            player.dy = 0
        collected_hearts = pygame.sprite.spritecollide(player, hearts, True)
        for _ in collected_hearts:
            player.score += 10
        collected_pellets = pygame.sprite.spritecollide(player, power_pellets, True)
        if collected_pellets:
            player.score += 50
            power_pellet_active = True
            power_pellet_timer = FPS * 8
            for ghost in ghosts:
                ghost.set_vulnerable(power_pellet_timer)
        if power_pellet_active:
            power_pellet_timer -= 1
            if power_pellet_timer <= 0:
                power_pellet_active = False
                for ghost in ghosts:
                    ghost.vulnerable = False
        for ghost in ghosts:
                if pygame.sprite.collide_rect(player, ghost):
                    if ghost.vulnerable:
                        player.score += 200
                        ghost.reset_position()
                        print("Fantasma comido!")
                    else:
                        lives -= 1
                        # CORREÇÃO AQUI: ADICIONAR OFFSET_X E OFFSET_Y
                        player.rect.topleft = (
                            PLAYER_START_POS[0] * TILE_SIZE + OFFSET_X + 2, # Adiciona OFFSET_X
                            PLAYER_START_POS[1] * TILE_SIZE + OFFSET_Y + 2  # Adiciona OFFSET_Y
                        )
                        player.stop_direction()
                        if lives <= 0:
                            current_game_state = GAME_STATE_GAME_OVER
                        break

        if len(hearts) == 0 or len(power_pellets) == 0:
            win_message = True
            current_game_state = GAME_STATE_WIN
    screen.fill(BLACK)
    all_sprites.draw(screen)
    score_text = FONT_SMALL.render(f"Pontos: {player.score}", True, WHITE)
    lives_text = FONT_SMALL.render(f"Vidas: {lives}", True, WHITE)
    screen.blit(score_text, (10, 10))
    screen.blit(lives_text, (WIDTH - lives_text.get_width() - 10, 10))
    if current_game_state == GAME_STATE_GAME_OVER or current_game_state == GAME_STATE_WIN:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            center_y_start = HEIGHT // 2 - 80

            if current_game_state == GAME_STATE_WIN:
                text = FONT_DEFAULT.render("Parabéns, meu amor!", True, PINK)
                message = FONT_SMALL.render(
                    "Você é o tesouro que eu sempre quis encontrar! Feliz Dia dos Namorados!",
                    True, WHITE
                )
                message2 = FONT_SMALL.render(
                    "Cada coração representa um momento nosso. Amo você! <3",
                    True, WHITE
                )
                restart_message_text = "Pressione 'R' para jogar de novo."

            else:
                text = FONT_DEFAULT.render("Ah não! Tente de novo, meu amor!", True, RED)
                message = FONT_SMALL.render(
                    "Os fantasmas do esquecimento não podem te pegar!",
                    True, WHITE
                )
                message2 = FONT_SMALL.render(
                    "Pressione 'R' para jogar de novo.", 
                    True, WHITE
                )
                restart_message_text = "Pressione 'R' para jogar de novo."

            text_rect = text.get_rect(center=(WIDTH // 2, center_y_start))
            screen.blit(text, text_rect)

            message_rect = message.get_rect(center=(WIDTH // 2, center_y_start + 60))
            screen.blit(message, message_rect)

            message2_rect = message2.get_rect(center=(WIDTH // 2, center_y_start + 110))
            screen.blit(message2, message2_rect)

            restart_message = FONT_SMALL.render(restart_message_text, True, WHITE)
            restart_rect = restart_message.get_rect(center=(WIDTH // 2, center_y_start + 180))
            screen.blit(restart_message, restart_rect)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()