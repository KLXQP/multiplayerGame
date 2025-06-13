import math
import asyncio
import pygame
import websockets
from websockets import connect
import json
import time
from threading import Thread

global q
q = asyncio.Queue()
delay = 0.3


def startLoop(loop):
	asyncio.set_event_loop(loop)
	loop.run_forever()





#-----------------------------------------------------------------------------------
#websocket code
global loop
loop = asyncio.new_event_loop()
data = None

t = Thread(target=startLoop, args=(loop,), daemon=True)
t.start()

async def recieve(websocket):
	global data
	while True:
		data = await websocket.recv()
		print(data)

async def sendPos(websocket):
	while True:
		position = await q.get()
		await websocket.send(str(position))


async def client():
	async with connect("ws://localhost:3000") as websocket:
		await websocket.send("hello")
		await asyncio.gather(sendPos(websocket), recieve(websocket))

asyncio.run_coroutine_threadsafe(client(), loop)



#--------------------------------------------------------------------------------------------------#
#pygame code



worldCoords = (1000, 700)
dim = (1000,700)
screen = pygame.display.set_mode(dim)

GoatSprite = pygame.transform.rotate(pygame.image.load('you.png').convert_alpha(), -90)
TrashSprite = pygame.transform.rotate(pygame.image.load('enemy.png').convert_alpha(), 90)

PlayerDim = [64, 64, 30]

PlayerWidth = PlayerDim[0]
PlayerHeight = PlayerDim[1]
PlayerDistance = PlayerDim[2]
PlayerSpeed = 100

Bulletwidth = 10
BulletHeight = 2
BulletSpeed = 500

class GameObj:
	def __init__(self, x, y, type, speed,   width=None, height=None):
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
	def __init__(self, x, y, width, height,speed, type):
		super().__init__(x, y, type,speed, width, height)
	def draw(self):
		if self.type == "same":
			pygame.draw.rect(screen, "Green", pygame.Rect(self.CTP()[0], self.CTP()[1], self.CTP()[2], self.CTP()[3]))
		elif self.type == "other":
			pygame.draw.rect(screen, "red", pygame.Rect(self.CTP()[0], self.CTP()[1], self.CTP()[2],self.CTP()[3]))

	def update(self):
		if self.type == "same":
			self.x += self.speed * dt
		if self.type == "other":
			self.x -= self.speed * dt
		self.position = (self.x, self.y)

class Healthbar:
	def __init__(self, Parent):
		self.Parent = Parent
	def draw(self):
		Parentx = self.Parent.CTP()[0]
		Parenty = self.Parent.CTP()[1]
		if self.Parent.type == "same":
			pygame.draw.rect(screen, "green", pygame.Rect(Parentx, Parenty - 10, self.Parent.health / 100 * PlayerWidth, 10))
		if self.Parent.type == "other":
			pygame.draw.rect(screen, "red", pygame.Rect(Parentx, Parenty - 10, self.Parent.health / 100 * PlayerWidth, 10))



class Player(GameObj):
	def __init__(self, x, y, type, speed, strength, width, height, health=100):
		super().__init__(x, y, type, speed, width, height)
		self.health = health
		self.strength = strength
		self.position = (self.x, self.y)
		if self.type == "same":
			self.sprite = pygame.transform.scale(GoatSprite, (self.CTP()[2], self.CTP()[3]))
		elif self.type == "other":
			self.sprite = pygame.transform.scale(TrashSprite,(self.CTP()[2], self.CTP()[3]))
	def move(self, direction):
		if direction == "Left":
			self.y -= self.speed * dt 
		elif direction == "Right":
			self.y += self.speed * dt
		self.position = (self.x, self.y)
	def draw(self):
		screen.blit(self.sprite, (self.CTP()[0], self.CTP()[1]))

midY = int(worldCoords[1] // 2)

Player1 = Player(PlayerDistance, midY, "same", PlayerSpeed, 20/PlayerSpeed, PlayerWidth, PlayerHeight)
Player2 = Player(worldCoords[0]-(PlayerDistance + PlayerWidth), midY,"other", PlayerSpeed, 20/PlayerSpeed, PlayerWidth, PlayerHeight)

clock = pygame.time.Clock()
players = [Player1, Player2]
healthbars = [Healthbar(player) for player in players]
bullets = []
running = True


lastFire = 0

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
	if keys[pygame.K_UP]:
		Player2.move("Left")
	if keys[pygame.K_DOWN]:
		Player2.move("Right")
	if keys[pygame.K_SPACE] and time.time() - lastFire >= delay:
		bullets.append( Bullet(Player1.x + PlayerWidth, Player1.y+ PlayerHeight/2,Bulletwidth, BulletHeight,BulletSpeed,"same" ) )
		lastFire = time.time()
	screen.fill("WHITE")

	
	asyncio.run_coroutine_threadsafe(q.put(Player1.y), loop)

	if data:
		Player2.y = int(math.floor(float(data)))

	
	objects = players + bullets
	for object in objects:
		if isinstance(object, Bullet):
			object.update()
		object.draw()


	for healthbar in healthbars:
		healthbar.draw()


	pygame.display.flip()

		
		

pygame.quit()