import math
import asyncio
import pygame
import websockets
from websockets import connect
import json
import time
import threading
from threading import Thread
import requests
import sys
import queue

# Global variables
PlayerId = None
OwnerId = None
GameId = None
BulletSpeed = None
MaxHealth = None
delay = 0.3

print("modules initialized")

# Thread-safe queues
q = queue.Queue()
dataQ = queue.Queue()
dataLock = threading.Lock()

print("queue created")

# Start asyncio loop in a new thread
loop = asyncio.new_event_loop()
def startLoop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

t = Thread(target=startLoop, args=(loop,), daemon=True)

# WebSocket handlers
async def recieve(websocket):
    while True:
        Recieved = await websocket.recv()
        data = json.loads(Recieved)
        print(data)
        if data['type'] == "update" and data['message'] == "game started":
            pygameT = Thread(target=Rungame, daemon=False)
            pygameT.start()
        dataQ.put(data)

async def sendPos(websocket):
    loop_in_thread = asyncio.get_running_loop()
    while True:
        message = await loop_in_thread.run_in_executor(None, q.get)
        await websocket.send(message)

async def client():
    async with connect("ws://192.168.0.90:3000/game/play") as websocket:
        await asyncio.gather(sendPos(websocket), recieve(websocket))

# Pygame & Game Logic
worldCoords = (1000, 700)
dim = (500, 350)

PlayerDim = [64, 64, 30]
PlayerWidth, PlayerHeight, PlayerDistance = PlayerDim
PlayerSpeed = 100

Bulletwidth = 10
BulletHeight = 2

midY = int(worldCoords[1] // 2)
clock = pygame.time.Clock()

def Rungame():
    screen = pygame.display.set_mode(dim)

    class GameObj:
        def __init__(self, x, y, type, speed, width=None, height=None):
            self.type = type
            self.x = x
            self.y = y
            self.speed = speed
            self.width = width
            self.height = height
        def CTP(self):
            Px = int(self.x * dim[0] / worldCoords[0])
            Py = int(self.y * dim[1] / worldCoords[1])
            if self.width and self.height:
                Pwidth = int(self.width * dim[0] / worldCoords[0])
                Pheight = int(self.height * dim[1] / worldCoords[1])
                return (Px, Py, Pwidth, Pheight)
            return (Px, Py)

    class Bullet(GameObj):
        def __init__(self, x, y, width, height, speed, type):
            super().__init__(x, y, type, speed, width, height)
        def draw(self):
            color = "Green" if self.type == "same" else "Red"
            pygame.draw.rect(screen, color, pygame.Rect(*self.CTP()))
        def update(self):
            self.x += self.speed * dt if self.type == "same" else -self.speed * dt

    class Healthbar:
        def __init__(self, Parent):
            self.Parent = Parent
        def draw(self):
            Parentx, Parenty = self.Parent.CTP()[:2]
            color = "green" if self.Parent.type == "same" else "red"
            offset = 0 if self.Parent.type == "same" else -32
            pygame.draw.rect(screen, color, pygame.Rect(Parentx + offset, Parenty - 10, self.Parent.health / 100 * PlayerWidth, 10))

    class Player(GameObj):
        def __init__(self, sprite, x, y, type, speed, strength, width, height, health=100):
            super().__init__(x, y, type, speed, width, height)
            self.health = health
            self.strength = strength
            self.sprite = sprite
        def move(self, direction):
            if direction == "Left":
                self.y -= self.speed * dt
                if self.type == "same":
                    q.put(json.dumps({'type': 'action', 'action_type': 'MOVE_UP', 'gameId': GameId, 'playerId': PlayerId}))
            elif direction == "Right":
                self.y += self.speed * dt
                if self.type == "same":
                    q.put(json.dumps({'type': 'action', 'action_type': 'MOVE_DOWN', 'gameId': GameId, 'playerId': PlayerId}))
        def draw(self):
            screen.blit(self.sprite, self.CTP()[:2])

    # Load sprites
    GoatSprite = pygame.transform.rotate(pygame.image.load('you.png').convert_alpha(), -90)
    TrashSprite = pygame.transform.rotate(pygame.image.load('enemy.png').convert_alpha(), 90)
    MySprite = pygame.transform.scale(GoatSprite, (PlayerWidth * dim[0] // worldCoords[0], PlayerHeight * dim[1] // worldCoords[1]))
    OtherSprite = pygame.transform.scale(TrashSprite, (PlayerWidth * dim[0] // worldCoords[0], PlayerHeight * dim[1] // worldCoords[1]))

    Player1 = Player(MySprite, PlayerDistance, midY, "same", PlayerSpeed, 20, PlayerWidth, PlayerHeight, MaxHealth)
    Player2 = Player(OtherSprite, worldCoords[0]-(PlayerDistance + PlayerWidth), midY, "other", PlayerSpeed, 20, PlayerWidth, PlayerHeight, MaxHealth)

    players = [Player1, Player2]
    healthbars = [Healthbar(p) for p in players]
    bullets = []
    lastFire = 0
    running = True

    while running:
        global dt
        dt = clock.tick(60) / 1000

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: Player1.move("Left")
        if keys[pygame.K_RIGHT]: Player1.move("Right")
        if keys[pygame.K_SPACE] and time.time() - lastFire >= delay:
            bullets.append(Bullet(Player1.x + PlayerWidth, Player1.y + PlayerHeight/2, Bulletwidth, BulletHeight, BulletSpeed, "same"))
            q.put(json.dumps({'type': 'action', 'action_type': 'FIRE', 'gameId': GameId, 'playerId': PlayerId}))
            lastFire = time.time()

        screen.fill("WHITE")

        while not dataQ.empty():
            Message = dataQ.get()
            if Message["type"] == "action":
                if Message["action"]["action_type"] == "MOVE_UP": Player2.move("Left")
                elif Message["action"]["action_type"] == "MOVE_DOWN": Player2.move("Right")
                elif Message["action"]["action_type"] == "FIRE":
                    bullets.append(Bullet(Player2.x, Player2.y + PlayerHeight/2, Bulletwidth, BulletHeight, BulletSpeed, "other"))

        for obj in players + bullets: obj.draw()

        playerect = pygame.Rect(*Player1.CTP())
        opponentrect = pygame.Rect(*Player2.CTP())
        BTR = []

        for bullet in bullets:
            bullet.update()
            bulletrect = pygame.Rect(*bullet.CTP())
            if bullet.type == "other" and playerect.colliderect(bulletrect):
                Player1.health -= Player2.strength
                Player1.health = max(0, Player1.health)  # clamp to zero
                BTR.append(bullet)
                if Player1.health <= 0:
                    print('\nYou lose')
                    pygame.quit()
                    sys.exit()
            elif bullet.type == "same" and opponentrect.colliderect(bulletrect):
                Player2.health -= Player1.strength
                Player2.health = max(0, Player2.health)  # clamp to zero
                BTR.append(bullet)
                if Player2.health <= 0:
                    print("\nYOU WIN")
                    pygame.quit()
                    sys.exit()
            if bullet.x < 0 or bullet.x > worldCoords[0]:
                BTR.append(bullet)

        for bullet in BTR:
            bullets.remove(bullet)

        for hb in healthbars:
            hb.draw()

        pygame.display.flip()

# REST API helpers
def joinGame(id=None):
    global GameId, BulletSpeed, PlayerId, MaxHealth
    if id is None:
        GameId = input('Input the gameID: ')
    else:
        GameId = id
    data = {"name": input("Your name: "), "gameId": GameId}
    response = requests.post("http://192.168.0.90:3000/game/join", json=data)
    rdata = response.json()
    if rdata.get('success'):
        BulletSpeed = rdata['game']['bulletSpeed']
        PlayerId = rdata['player']['id']
        MaxHealth = rdata['player']['health']
        print(f"Game Joined: BulletSpeed={BulletSpeed}, PlayerId={PlayerId}, Health={MaxHealth}")

def CreateGame():
    global GameId, BulletSpeed, PlayerId, MaxHealth
    BulletSpeed = int(input("Bullet speed: "))
    data = {"name": input("Your name: "), "bulletSpeed": BulletSpeed}
    response = requests.post("http://192.168.0.90:3000/game/create", json=data)
    rdata = response.json()
    if rdata.get('success'):
        GameId = rdata['game']['id']
        PlayerId = rdata['player']['id']
        MaxHealth = rdata['player']['health']
        print(f"Game Created: GameId={GameId}, PlayerId={PlayerId}, Health={MaxHealth}")

# Game Menu
def StartMenu():
    ready = False
    while True:
        if not ready:
            action = input("What do you wanna do? (join/create): ").strip()
            if action == 'join':
                joinGame()
                t.start()
                asyncio.run_coroutine_threadsafe(client(), loop)
                input("Press enter when ready")
                initData = json.dumps({"type": "action", "action_type": "INIT", "gameId": GameId, "playerId": PlayerId})
                q.put(initData)
                ready = True
            elif action == 'create':
                CreateGame()
                t.start()
                asyncio.run_coroutine_threadsafe(client(), loop)
                initData = json.dumps({"type": "action", "action_type": "INIT", "gameId": GameId, "playerId": PlayerId})
                q.put(initData)
                ready = True
            else:
                print("invalid action")
        elif ready and action == "create":
            input("Press enter to start the game")
            startData = json.dumps({"type": "action", "action_type": "START_GAME", "gameId": GameId, "playerId": PlayerId})
            q.put(startData)
            time.sleep(1)
        elif ready and action == "join":
            continue

# Start program
StartMenu()
