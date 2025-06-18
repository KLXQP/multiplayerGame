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

q = asyncio.Queue()
dataLock = threading.Lock()
delay = 0.3

dataQ = queue.Queue()
print("queue created ")

def startLoop(loop):
	asyncio.set_event_loop(loop)
	loop.run_forever()



#---------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------
#websocket code
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
				pygameT = Thread(target=Rungame, daemon = False)
				pygameT.start()
		dataQ.put(data)
		
async def sendPos(websocket):
	while True:
		message = await q.get()
		await websocket.send(message)


async def client():
	async with connect("ws://192.168.0.90:3000/game/play") as websocket:
		await asyncio.gather(sendPos(websocket), recieve(websocket))




#--------------------------------------------------------------------------------------------------#
#pygame code

worldCoords = (1000, 700)
dim = (500,350)




PlayerDim = [64, 64, 30]

PlayerWidth = PlayerDim[0]
PlayerHeight = PlayerDim[1]
PlayerDistance = PlayerDim[2]
PlayerSpeed = 100

Bulletwidth = 10
BulletHeight = 2


midY = int(worldCoords[1] // 2)

clock = pygame.time.Clock()



def Rungame():
	global data
	screen = pygame.display.set_mode(dim)
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
				pygame.draw.rect(screen, "red", pygame.Rect(Parentx - 32, Parenty - 10, self.Parent.health / 100 * PlayerWidth, 10))



	class Player(GameObj):
		def __init__(self,sprite, x, y, type, speed, strength, width, height, health=100):
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
					asyncio.run_coroutine_threadsafe(q.put(MoveData), loop)
			elif direction == "Right":
				self.y += self.speed * dt
				if self.type == "same":
					MoveDataDict = {'type': 'action', 'action_type': 'MOVE_DOWN', 'gameId': GameId, 'playerId': PlayerId}
					MoveData = json.dumps(MoveDataDict)
					asyncio.run_coroutine_threadsafe(q.put(MoveData), loop)
			self.position = (self.x, self.y)
		def draw(self):
			screen.blit(self.sprite, (self.CTP()[0], self.CTP()[1]))

	GoatSprite = pygame.transform.rotate(pygame.image.load('you.png').convert_alpha(), -90)
	TrashSprite = pygame.transform.rotate(pygame.image.load('enemy.png').convert_alpha(), 90)
	MySprite = pygame.transform.scale(GoatSprite, (PlayerWidth * dim[0] // worldCoords[0], PlayerHeight * dim[1] // worldCoords[1]))
	OtherSprite = pygame.transform.scale(TrashSprite,(PlayerWidth * dim[0] // worldCoords[0], PlayerHeight * dim[1] // worldCoords[1]))
	Player1 = Player(MySprite, PlayerDistance, int(midY), "same", PlayerSpeed, 20, PlayerWidth, PlayerHeight, MaxHealth)
	Player2 = Player(OtherSprite, worldCoords[0]-(PlayerDistance + PlayerWidth), midY,"other", PlayerSpeed, 20, PlayerWidth, PlayerHeight, MaxHealth)
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
			bullets.append( Bullet(Player1.x + PlayerWidth, Player1.y+ PlayerHeight/2,Bulletwidth, BulletHeight,BulletSpeed,"same" ) )
			FireDataDict = {'type': 'action', 'action_type': 'FIRE', 'gameId': GameId, 'playerId': PlayerId}
			FireData = json.dumps(FireDataDict)
			asyncio.run_coroutine_threadsafe(q.put(FireData), loop)
			lastFire = time.time()
		screen.fill("WHITE")

		
		while not (dataQ.empty()):
			Message = dataQ.get()
			if Message["type"] == "action":
				if Message["action"]["action_type"] == "MOVE_UP":
					Player2.move("Left")
				elif Message["action"]["action_type"] == "MOVE_DOWN":
					Player2.move("Right")
				elif Message["action"]["action_type"] == "FIRE":
					bullets.append(Bullet(Player2.x, Player2.y+ PlayerHeight/2,Bulletwidth, BulletHeight,BulletSpeed,"other" ))
		objects = players + bullets
		playerect = pygame.Rect(Player1.CTP()[0], Player1.CTP()[1], Player1.CTP()[2], Player1.CTP()[3])
		Opponentrect = pygame.Rect(Player2.CTP()[0], Player2.CTP()[1], Player2.CTP()[2], Player2.CTP()[3])
		for object in objects:
			object.draw()
		BTR = []
		for bullet in bullets:
			bullet.update()
		
			if bullet.type == "other":
				bulletRect = pygame.Rect(bullet.CTP()[0],bullet.CTP()[1],bullet.CTP()[2],bullet.CTP()[3])
				if playerect.colliderect(bulletRect):
					Player1.health -= Player2.strength
					BTR.append(bullet)
			elif bullet.type == "same":
				bulletRect = pygame.Rect(bullet.CTP()[0],bullet.CTP()[1],bullet.CTP()[2],bullet.CTP()[3])
				if Opponentrect.colliderect(bulletRect):
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

			
#----------------------------------------
#Requests code

def joinGame(id = None):
	global GameId, BulletSpeed, PlayerId, MaxHealth
	print("Joingame function started ")
	if id == None:
		GameId = input('input the gameID: ')
	else:
		GameId = id
	data = {
	"name": input('input your name: '), 
	"gameId" : GameId
	}
	url = "http://192.168.0.90:3000/game/join"
	response = requests.post(url, json = data)
	rdata = response.json()
	if rdata.get('success') == True:
		print(rdata)
		print('Game Joined')
		BulletSpeed = rdata.get('game').get('bulletSpeed')
		print('BulletSpeed' + '=' + str(BulletSpeed))
		PlayerId = rdata.get('player').get('id')
		print('your player id is', PlayerId)
		MaxHealth = rdata.get('player').get('health')
		print(MaxHealth)
	
def CreateGame():
	print("createGame function started")
	global GameId, BulletSpeed, PlayerId, MaxHealth
	BulletSpeed = int(input("input the Bullet speed: "))
	data = {
	"name": input("input your name: "),
	"bulletSpeed" : BulletSpeed
	}
	url = "http://192.168.0.90:3000/game/create"
	response = requests.post(url, json = data)
	rdata = response.json()
	if rdata.get('success') == True:
		print(rdata)
		print('Game Created')
		GameId = rdata.get('game').get('id')
		PlayerId = rdata.get('player').get('id')
		MaxHealth = rdata.get('player').get('health')
		print(MaxHealth)
		print(GameId)
		
		


def StartMenu():
	ready = False
	while True:
		if not ready:
			action = str(input("What do you wanna do ? \n input( join ) to join a game \n input( create ) to create a game \n"))
			if action == 'join':
				joinGame()
				init = False
				t.start()
				asyncio.run_coroutine_threadsafe(client(), loop)
				init = str(input('type something if you are ready to play'))
				if init:
					initDataDict = {"type": "action","action_type": "INIT","gameId": GameId,"playerId": PlayerId}
					initData = json.dumps(initDataDict)
					asyncio.run_coroutine_threadsafe(q.put(initData), loop)
					ready = True
					continue
			if action ==  'create':
				CreateGame()
				t.start()
				asyncio.run_coroutine_threadsafe(client(), loop)
				initDataDict = {"type": "action","action_type": "INIT","gameId": GameId,"playerId": PlayerId}
				initData = json.dumps(initDataDict)
				asyncio.run_coroutine_threadsafe(q.put(initData), loop)
				ready = True
				continue
			else:
				print("invalid action")
				continue
		if ready and action == "create":
			start = False
			start = str(input('type something if you wanna start the game'))
			if start:
				startDataDict = {"type": "action","action_type": "START_GAME","gameId": GameId,"playerId": PlayerId}
				startData = json.dumps(startDataDict)
				asyncio.run_coroutine_threadsafe(q.put(startData), loop)
				time.sleep(1)
						
		elif ready and action == "join":
			continue
StartMenu()
