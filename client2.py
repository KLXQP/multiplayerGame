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

PlayerId = None
OwnerId = None
GameId = None
BulletSpeed = None
MaxHealth = None
print("modules initialized")

# ✅ Replace asyncio.Queue with thread-safe queue.Queue
q = queue.Queue()
dataLock = threading.Lock()
delay = 0.3

dataQ = queue.Queue()
print("queue created")

def startLoop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

# ---------------------------------------------------------------------------------

# Websocket code
global loop
loop = asyncio.new_event_loop()

t = Thread(target=startLoop, args=(loop,), daemon=True)

async def recieve(websocket):
    global data
    while True:
        Recieved = await websocket.recv()
        data = json.loads(Recieved)
        print(data)
        if data['type'] == "update":
            print(data)
            if data['message'] == "game started":
                pygameT = Thread(target=Rungame, daemon=False)
                pygameT.start()
        dataQ.put(data)

# ✅ run_in_executor for thread-safe q.get()
async def sendPos(websocket):
    loop_in_thread = asyncio.get_running_loop()
    while True:
        message = await loop_in_thread.run_in_executor(None, q.get)
        await websocket.send(message)

async def client():
    async with connect("ws://192.168.0.90:3000/game/play") as websocket:
        await asyncio.gather(sendPos(websocket), recieve(websocket))

# ----------------------------------------------------------------------------------
# Pygame code

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
    global data
    screen = pygame.display.set_mode(dim)
    class GameObj:
        def __init__(self, x, y, type, speed, width=None, height=None):
            self.type = type
            self.x = x
            self.y = y
            self.speed = speed
            self.width = width
            self.height = height
        def update(self):
            pass
        def draw(self):
            pass
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
            color = "Green" if self.type == "same" else "red"
            pygame.draw.rect(screen, color, pygame.Rect(self.CTP()[0], self.CTP()[1], self.CTP()[2], self.CTP()[3]))
        def update(self):
            self.x += self.speed * dt if self.type == "same" else -self.speed * dt
            self.position = (self.x, self.y)

    class Healthbar:
        def __init__(self, Parent):
            self.Parent = Parent
        def draw(self):
            Parentx = self.Parent.CTP()[0]
            Parenty = self.Parent.CTP()[1]
            color = "green" if self.Parent.type == "same" else "red"
            offset = 0 if self.Parent.type == "same" else -32
            pygame.draw.rect(screen, color, pygame.Rect(Parentx + offset, Parenty - 10, self.Parent.health / 100 * PlayerWidth, 10))

    class Player(GameObj):
        def __init__(self, sprite, x, y, type, speed, strength, width, height, health=100):
            super().__init__(x, y, type, speed, width, height)
            self.health = health
            self.strength = strength
            self.position = (self.x, self.y)
            self.sprite = sprite
        def move(self, direction):
            if direction == "Left":
                self.y -= self.speed * dt
                if self.type == "same":
                    MoveDataDict = {'type': 'action', 'action_type': 'MOVE_UP', 'gameId': GameId, 'playerId': PlayerId}
                    MoveData = json.dumps(MoveDataDict)
                    q.put(MoveData)
            elif direction == "Right":
                self.y += self.speed * dt
                if self.type == "same":
                    MoveDataDict = {'type': 'action', 'action_type': 'MOVE_DOWN', 'gameId': GameId, 'playerId': PlayerId}
                    MoveData = json.dumps(MoveDataDict)
                    q.put(MoveData)
            self.position = (self.x, self.y)
        def draw(self):
            screen.blit(self.sprite, (self.CTP()[0], self.CTP()[1]))

    GoatSprite = pygame.transform.rotate(pygame.image.load('you.png').convert_alpha(), -90)
    TrashSprite = pygame.transform.rotate(pygame.image.load('enemy.png').convert_alpha(), 90)
    MySprite = pygame.transform.scale(GoatSprite, (PlayerWidth * dim[0] // worldCoords[0], PlayerHeight * dim[1] // worldCoords[1]))
    OtherSprite = pygame.transform.scale(TrashSprite, (PlayerWidth * dim[0] // worldCoords[0], PlayerHeight * dim[1] // worldCoords[1]))
    Player1 = Player(MySprite, PlayerDistance, int(midY), "same", PlayerSpeed, 20, PlayerWidth, PlayerHeight, MaxHealth)
    Player2 = Player(OtherSprite, worldCoords[0]-(PlayerDistance + PlayerWidth), midY, "other", PlayerSpeed, 20, PlayerWidth, PlayerHeight, MaxHealth)

    players = [Player1, Player2]
    healthbars = [Healthbar(player) for player in players]
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
        if keys[pygame.K_LEFT]:
            Player1.move("Left")
        if keys[pygame.K_RIGHT]:
            Player1.move("Right")
        if keys[pygame.K_SPACE] and time.time() - lastFire >= delay:
            bullets.append(Bullet(Player1.x + PlayerWidth, Player1.y + PlayerHeight/2, Bulletwidth, BulletHeight, BulletSpeed, "same"))
            FireDataDict = {'type': 'action', 'action_type': 'FIRE', 'gameId': GameId, 'playerId': PlayerId}
            FireData = json.dumps(FireDataDict)
            q.put(FireData)
            lastFire = time.time()

        screen.fill("WHITE")

        while not dataQ.empty():
            Message = dataQ.get()
            if Message["type"] == "action":
                if Message["action"]["action_type"] == "MOVE_UP":
                    Player2.move("Left")
                elif Message["action"]["action_type"] == "MOVE_DOWN":
                    Player2.move("Right")
                elif Message["action"]["action_type"] == "FIRE":
                    bullets.append(Bullet(Player2.x, Player2.y + PlayerHeight/2, Bulletwidth, BulletHeight, BulletSpeed, "other"))

        objects = players + bullets
        playerect = pygame.Rect(Player1.CTP()[0], Player1.CTP()[1], Player1.CTP()[2], Player1.CTP()[3])
        Opponentrect = pygame.Rect(Player2.CTP()[0], Player2.CTP()[1], Player2.CTP()[2], Player2.CTP()[3])
        for obj in objects:
            obj.draw()

        BTR = []
        for bullet in bullets:
            bullet.update()
            bulletRect = pygame.Rect(bullet.CTP()[0], bullet.CTP()[1], bullet.CTP()[2], bullet.CTP()[3])
            if bullet.type == "other" and playerect.colliderect(bulletRect):
                Player1.health -= Player2.strength
                BTR.append(bullet)
            elif bullet.type == "same" and Opponentrect.colliderect(bulletRect):
                Player2.health -= Player1.strength
                BTR.append(bullet)
            if bullet.x < 0 or bullet.x > worldCoords[0]:
                BTR.append(bullet)
        for bullet in BTR:
            bullets.remove(bullet)

        if Player1.health == 0:
            print('\nYou lose')
            pygame.quit()
            sys.exit()
        if Player2.health == 0:
            running = False
            pygame.quit()
            print("\nYOU WIN")
            continue

        for healthbar in healthbars:
            healthbar.draw()

        pygame.display.flip()

# ----------------------------------------
# Requests and Menu code — unchanged
# (since this part was fine)

# same as your existing CreateGame, joinGame, and StartMenu functions

# ----------------------------------------

StartMenu()
