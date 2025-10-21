# Menu.py
# This file serves as an API for Parser.py to save and load game data with files
# This file is dependent on Objects.py and is a dependency of Parser.py

# It consists of four main parts;
# 1. Write data functions	(functions to write objects P, W, and G to files)
# 2. Read data functions	(functions to read save files; player, world, game)
# 3. Menu functions			(functions to load, save, delete, start new games)
# 4. Game Intro functions	(functions to print game intro animation)

from time import sleep
from random import randint, choice
import os, json, sys

import Data
import Core
import Creatures
import Items


##########################
## WRITE DATA FUNCTIONS ##
##########################


# just writes the game object to a file, probably named "game.txt"
def writeGame(filename,Game,World):
	gfd = open(filename,"w")
	gfd.write(str(Game.mode) + "\n")
	gfd.write(Core.getRoomKey(Game.currentroom,World) + "\n")
	gfd.write(Core.getRoomKey(Game.prevroom,World) + "\n")
	gfd.write(str(Game.time) + "\n")
	gfd.write(str(Game.events) + "\n")
	gfd.close()


visitedobjects = set()
class worldEncoder(json.JSONEncoder):
	def default(self,objToWrite):
		# print(objToWrite)
		# for k,v in getattr(objToWrite,"__dict__",{}).items():
		# 	print(f"  {k}: {v}")
		if objToWrite in visitedobjects:
			raise Exception(f"{objToWrite} already visited")

		JSONprimitives = {dict,list,str,int,float,bool,None}
		if type(objToWrite) is set:
			return {"__class__":"set","setdata":list(objToWrite)}
		elif Core.hasMethod(objToWrite,"convertToJSON"):
			jsonDict = objToWrite.convertToJSON()
			jsonDict = {"__class__": objToWrite.__class__.__name__, **jsonDict}
			if "parent" in jsonDict:
				del jsonDict["parent"]
			for k, v in jsonDict.items():
				if isinstance(v, (Core.Creature, Core.Item)):
					jsonDict[k] = v.id
			return jsonDict
		elif type(objToWrite) is Core.Player:
			return {"__class__": "Player"}
		# elif type(objToWrite) == Room:
		# 	return objToWrite.__dict__
		elif type(objToWrite) not in JSONprimitives:
			jsonDict = objToWrite.__dict__
			# this is done so the class key appears first in the JSON object
			# TODO: swap the following lines for Python 3.9
			# jsonDict = {"__class__": objToWrite.__class__.__name__} | jsonDict
			jsonDict = {"__class__": objToWrite.__class__.__name__, **jsonDict}
			if "parent" in jsonDict:
				del jsonDict["parent"]
			return jsonDict
		else:
			return objToWrite


def serialize_safe(obj, encoder_class):
	try:
		# Try serializing the object to check if it's serializable
		return json.dumps(obj, cls=encoder_class), None
	except Exception as e:
		# Return None and raise the exception
		# print(f"Serialization failed: {e}")
		return None, e


def find_problematic_subobject(obj):
	global visitedobjects
	visitedobjects = set()
	if isinstance(obj, dict):
		for key, value in obj.items():
			result, error = serialize_safe(value, worldEncoder)
			if result is None:  # If serialization failed
				print(f"Problematic key: {key}")
				print(f"Error: {error}")
				print(f"Object causing the error: {value}")
				break  # Once the problematic sub-object is found, exit the loop
	elif isinstance(obj, list):
		for idx, item in enumerate(obj):
			result, error = serialize_safe(item, worldEncoder)
			if result is None:  # If serialization failed
				print(f"Problematic index: {idx}")
				print(f"Error: {error}")
				print(f"Object causing the error: {item}")
				break  # Once the problematic sub-object is found, exit the loop
	else:
		# Base case for other types (e.g., int, str)
		result, error = serialize_safe(obj, worldEncoder)
		if result is None:
			print(f"Problematic object: {repr(obj)}")
			print(f"Error: {error}")


def writeWorld(filename,World):
	try:
		with open(filename, "w") as fd:
			json.dump(World, fd, cls=worldEncoder, indent="\t")
	except Exception as e:
		print("Error while serializing object to JSON:")
		print(f"Error: {e}")

		# Now we try to isolate the problematic sub-object in World
		print("Attempting to find the problematic sub-object...")
		find_problematic_subobject(World)

		raise  # Re-raise the exception for further handling


def writePlayer(filename,Player):
	global visitedobjects
	visitedobjects = set()

	try:
		with open(filename, "w") as fd:
			json.dump(Player.convertToJSON(), fd, cls=worldEncoder, indent="\t")
	except Exception as e:
		print("Error while serializing object to JSON:")
		print(f"Error: {e}")

		# Now we try to isolate the problematic sub-object in World
		print("Attempting to find the problematic sub-object...")
		find_problematic_subobject(Player)

		raise  # Re-raise the exception for further handling



#########################
## READ DATA FUNCTIONS ##
#########################


def objDecoder(jsonDict):
	# print("==== converting object of type: " + str(type(jsonDict)))
	if "__class__" in jsonDict:
		objClassname = jsonDict["__class__"]
		# print("=== class is " + objClassname)
		del jsonDict["__class__"]
		if objClassname == "set":
			return set(jsonDict["setdata"])
		if objClassname == "DialogueTree":
			return jsonDict
		if objClassname == "factoryCreature":
			return Creatures.factory[jsonDict["name"]]()
		elif objClassname == "factoryItem":
			return Items.factory[jsonDict["name"]]()
		objClass = Core.strToClass(objClassname,["Core","Creatures","Items"])
		if objClass == None:
			raise Exception("Could not find class for classname in world:",objClassname)
		objAttributes = jsonDict
		# print("========: " + jsonDict["name"] + " " + str(objAttributes))
		if objClassname == "Room":
			return Core.Room(**objAttributes)
		elif objClass != None:
			# if Core.hasMethod(objClass,"convertFromJSON"):
			# 	return objClass.convertFromJSON(jsonDict)
			try:
				return objClass(**objAttributes)
			except TypeError as e:
				attributeStr = "\n".join(f"{key}: {value}" for key, value in objAttributes.items())
				raise TypeError(f"Failed to instantiate object: '{objClassname}' from JSON with attributes above: {attributeStr}", e)
		else:
			raise Exception("ERROR in decoding JSON object class type: " + objClassname)
	else:
		return jsonDict


def worldDecoder(jsonDict):
	if jsonDict.get("__class__",None) == "Player":
		return Core.player
	else:
		return objDecoder(jsonDict)


def readJSON(filename,object_hook=None):
	with open(filename,"r") as fd:
		JSON = json.load(fd,object_hook=object_hook)
	return JSON


def readDialogue(filename):
	jsonDict = readJSON(filename)
	resDict = {}
	resDict["sounds"] = jsonDict["sounds"]
	resDict["trites"] = jsonDict["trites"]
	resDict["trees"] = {}
	for treeLabel, treeJson in jsonDict["trees"].items():
		resDict["trees"][treeLabel] = Core.DialogueTree(treeLabel,treeJson)
	return resDict


# reads the global game class file, probably named "game.txt"
# takes the world dict as input, returns the Game object
def readGame(filename,World,dlogDict):
	gfd = open(filename,"r")
	gametext = gfd.readlines()			# split game file into a list of lines
	mode = int(gametext[0][:-1])		# first line is gamemode int
	currentroom = gametext[1][:-1]		# second line is name of current room
	prevroom = gametext[2][:-1]			# third line is name of previous room
	time = int(gametext[3][:-1])		# fourth line is time int
	events = eval(gametext[4][:-1])
	gfd.close()
	return Core.Game(mode,World[currentroom],World[prevroom],time,events,dlogDict,Creatures.factory,Items.factory)




####################
## MENU FUNCTIONS ##
####################


def quickSave(savename):
	assert savename not in ("", "all")
	# create save directory if it doesn't exist
	os.makedirs(f"saves/{savename}",exist_ok=True)
	os.chdir(f"saves/{savename}")
	writeWorld("world.json", Core.world)
	writePlayer("player.json", Core.player)
	writeGame("game.txt", Core.game, Core.world)
	Core.game.lastsave = Core.game.time
	os.chdir("../..")


# saves data from player, world, and game objects to respective text files
def saveGame(savename=None):
	# create save directory if it doesn't exist
	if not os.path.exists("saves"):
		os.mkdir("saves")
	os.chdir("saves")

	# split existing save names into a list and display them
	saves = os.listdir()
	if savename is None:
		# player names their save
		Core.columnPrint(saves,10,10,delay=0,color="k")
		savename = Core.Input("\nWhat name will you give this save file?",delay=0,color="k").lower()
	if savename in ("", "all", "autosave", "quicksave") or savename in Data.cancels:
		if savename == "":
			Core.Print(f"Save name cannot be empty.",delay=0,color="k")
		else:
			Core.Print(f"Save name cannot be '{savename}'.",delay=0,color="k")
		os.chdir("..")
		return

	# if the save name is used, ask to overwrite it
	if os.path.exists(savename):
		Core.Print("A save file with this name already exists.",delay=0,color="k")
		#if dont overwrite, then just return
		if not Core.yesno("Would you like to overwrite it?",delay=0,color="k"):
			os.chdir("..")
			return
	# if the save name is unused, make a new directory
	else:
		try:
			os.mkdir(savename)
		except:
			Core.Print("Invalid save name.",delay=0,color="k")
			os.chdir("..")
			return

	# write world, player, and game files
	os.chdir(savename)
	writeWorld("world.json", Core.world)
	writePlayer("player.json", Core.player)
	writeGame("game.txt", Core.game, Core.world)
	os.chdir("../..")
	sleep(1)
	Core.Print(f"Game saved as {savename}.",delay=0,color="k")
	Core.game.lastsave = Core.game.time
	sleep(1)


# load a game from a save directory
def loadGame(filename=None):
	if not (os.path.exists("saves")) or len(os.listdir("./saves")) == 0:
		Core.Print("\nThere are no save files.\n",delay=0,color="k")
		Core.waitInput()
		return False
	os.chdir("saves")

	if filename is None:
		Core.clearScreen()
		# split save names into a list and display them
		Core.Print("Save files: ",delay=0,color="k")
		saves = os.listdir()
		Core.columnPrint(saves,10,10,delay=0,color="k")
		savename = Core.Input("\nWhich save file will you load?",delay=0)
	else:
		savename = filename

	if savename == "":
		os.chdir("..")
		return False

	# if user inputs a save name that doesn't exist
	if not os.path.exists(savename):
		Core.Print(f"\nThere is no save file named '{savename}'.",delay=0,color="k")
		os.chdir("..")
		Core.waitInput()
		return False
	os.chdir(savename)
	# try to load the player, world, and game objects
	# try:
	Core.player = readJSON("player.json",object_hook=objDecoder)
	Core.world = readJSON("world.json",object_hook=worldDecoder)
	dlogDict = readDialogue("../../Dialogue.json")
	Core.game = readGame("game.txt",Core.world,dlogDict)
	# hopefully load doesn't fail, that would suck
	# except:
	# 	Core.Print("Could not load game, save data corrupted\n",delay=0,color="k")
	# 	os.chdir("..")
	# 	os.chdir("..")
	# 	return False

	os.chdir("../..")
	Core.buildWorld()

	Core.ellipsis()
	Core.flushInput()

	# describe the current room
	Core.game.startUp()
	return True


# deletes all save files in 'save' directory (if the user is very, very sure)
def deleteAll():
	if not Core.yesno("Are you sure you want to delete all save files?",delay=0):
		os.chdir("..")
		return
	if not Core.yesno("Are you very, very sure??",delay=0):
		os.chdir("..")
		return
	for savename in os.listdir():
		os.chdir(savename)
		for filename in os.listdir(): os.remove(filename)
		os.chdir("..")
		os.rmdir(savename)
	os.chdir("..")
	sleep(1)
	Core.waitInput("\nAll save files deleted.\n",delay=0,color="k")


# deletes a save file whose name is given by the user
def delete(filename):
	if not os.path.exists("saves") or len(os.listdir("./saves")) == 0:
		Core.Print("\nThere are no save files.\n",delay=0,color="k")
		Core.waitInput()
		return
	os.chdir("saves")

	if filename is None:
		Core.clearScreen()
		# split save names into a list and display them
		Core.Print("Save files: ",delay=0,color="k")
		saves = os.listdir()
		Core.columnPrint(saves,10,10,delay=0,color="k")
		savename = Core.Input("\nWhich save file will you delete?",delay=0)
	else:
		savename = filename

	if savename == "":
		os.chdir("..")
		return
	if savename == "all":
		return deleteAll()

	# if the user inputs a save name that doesn't exist
	if not os.path.exists(savename):
		Core.Print(f"\nThere is no save file named '{savename}'.\n",delay=0,color="k")
		os.chdir("..")
		Core.waitInput()
		return
	# ask for confirmation, if no, then return to menu
	if not Core.yesno("Are you sure you want to delete this save file?",delay=0):
		os.chdir("..")
		return

	# remove all files in this save directory, and remove that save directory
	os.chdir(savename)
	for filename in os.listdir():
		os.remove(filename)
	os.chdir("..")
	os.rmdir(savename)
	os.chdir("..")
	sleep(1)
	Core.waitInput("\nDeleted\n",delay=0,color="k")
	return


# asks for player name and description, starts everything else at initial values
def createCharacter():
	Core.Print("What is your name?",end="",delay=0,color="k")
	name = Core.InputLock(delay=0).title()
	Core.Print("Describe yourself.",end="",delay=0,color="k")
	desc = Core.InputLock(cue="\nYou are ",delay=0)
	return Core.Player(name,desc,29,[1]*10,2,2,0,0)


# starts a new game and returns player, world, and game objects
def newGame():
	# initializes the game at the "cave" room
	dlogDict = readDialogue("Dialogue.json")
	Core.game = Core.Game(0,Core.defaultRoom,Core.defaultRoom,0,set(),dlogDict,Creatures.factory,Items.factory)
	# initializes from the character creation screen
	Core.player = createCharacter()
	# tries to load a clean new world from initial world file, must be defined after player
	Core.world = readJSON("World.json",object_hook=worldDecoder)

	Core.game.currentroom = Core.world["cave"]
	Core.game.prevroom = Core.world["cave"]
	Core.buildWorld()

	# Core.ellipsis()
	# enter the starting room
	sleep(0.5)
	Core.clearScreen()
	Core.flushInput()

	Core.player.changeLocation(Core.game.currentroom)
	# describe the current room
	Core.game.startUp()



# automatically starts a new game with a premade character for easy testing
def testGame():
	inv = [Core.Compass("compass","a plain steel compass with a red arrow",2,10,"steel",plural="compasses")]
	status = [["fireproof",-1], ["poisoned",5], ["cursed",-2], ["immortal",-1],
	["sharpshooter",50], ["invisible",15], ["poisoned",-1], ["flying",5]]
	Core.player = Core.Player("Norman","a hero",10,[4]*10,100,100,1000,50,inv=inv,love=100,fear=100,spells=[],status=status)

	# world must be defined after player
	Core.world = readJSON("World.json",object_hook=worldDecoder)

	dlogDict = readDialogue("Dialogue.json")
	Core.game = Core.Game(0,Core.world["cave"],Core.world["tunnel"],0,set(),dlogDict,Creatures.factory)

	Core.buildWorld()

	Core.clearScreen()
	Core.flushInput()

	# describe the current room
	Core.game.startUp()

	Core.game.mode = 1
	Core.game.silent = False


def gameInfo(*args): # requires args when called from Interpreter
	Core.clearScreen()
	Core.Print(Data.gameinfo,delay=0,color="k")
	Core.waitInput()
	Core.clearScreen()


# main game menu, used to instantiate global variables P, W, and G in Parser.py
# loops until a new game is made, a save is loaded, or the game is quit
# n denotes how many times mainMenu has recurred
def mainMenu():
	# handle case when running code from src directory instead of main directory
	if "src" in os.getcwd(): os.chdir("..")

	menucmds = ("info","new","load","delete","quit","test")
	acceptKey = lambda inp: inp.startswith(menucmds)
	while True:
		Core.clearScreen()
		Core.flushInput()
		print(Data.logo)
		Core.Print(Data.menuinstructions,end="",delay=0,color="k")
		g = Core.InputLock(delay=0,acceptKey=acceptKey).split()

		if len(g) == 0:
			continue
		elif g[0] == "info" and len(g) == 1:
			gameInfo()
		elif g[0] == "new" and len(g) == 1:
			newGame()
			return
		elif g[0] == "load" and len(g) == 1:
			if loadGame():
				return
		elif g[0] == "load":
			if loadGame(" ".join(g[1:])):
				return
		elif g[0] == "delete" and len(g) == 1:
			delete(None)
		elif g[0] == "delete":
			delete(" ".join(g[1:]))
		elif g[0] == "quit" and len(g) == 1:
			Core.game.quit = 1
			return
		elif g[0] == "test" and len(g) == 1:
			testGame()
			return


def restart():
	next = None
	Core.flushInput()
	while next is None:
		if Core.yesno(f"Would you like to return to the main menu?",delay=0,color="k"):
			next = "restart"
		elif Core.yesno("Would you like to quit?",delay=0,color="k"):
			next = "quit"
		else:
			Core.Print("You must choose! Don't be a sore loser.",delay=0,color="k")
	if next == "restart":
		Core.game.quit = 0
		mainMenu()
		return True
	return quit()


def quit():
	if Core.game.mode != 1:
		Core.waitInput("Goodbye.",delay=0,color="k")
		Core.game.quit = 1
	return False



##########################
## GAME INTRO FUNCTIONS ##
##########################


# returns true if bubble at row,col is under a "_" and under or beside a "wall"
def bubbleTrapped(logoArray,row,col):
	walls = "_\\/|"
	if logoArray[row-1][col] == "_":
		if logoArray[row-1][col-1] in walls or logoArray[row-1][col+1] in walls:
			return True
		if logoArray[row][col-1] == walls or logoArray[row][col+1] in walls:
			return True
	return False


# takes a specific char in the logoArray, alters it depending on its value
# if char at row,col is a *, erase it
# if char at row,col is a bubble, pop it if its a big "O" and its trapped above
# otherwise, move bubble up, not drifting out of the lines or hitting a wall
# if the bubble collides with another bubble, poppedBubbles += 1
def moveBubble(logoArray,row,col):
	poppedBubbles = 0
	char = logoArray[row][col]
	# if char is a popped bubble
	if char == '*':
		# replace char at current location with the static logo's character
		logoArray[row][col] = Data.logoFrame[row][col]
		poppedBubbles += 1
	# if char is a bubble
	elif char in {".","o","O"}:
		# if bubble is "O" and trapped, have chance to pop it
		if bubbleTrapped(logoArray,row,col):
			if char == "O" and randint(0,2) == 2:
				logoArray[row][col] = "*"
		else:
			# erase char at current location
			logoArray[row][col] = Data.logoFrame[row][col]
			# generate "drift"; it may move left or right as it also moves up
			drift = randint(-1,1)
			# if bubble is blocked above by a wall, it must drift accordingly
			if logoArray[row-1][col] == "\\": drift = -1
			elif logoArray[row-1][col] == "/": drift = 1
			# determine new unoccupied location as bubble moves upward
			newLoc = logoArray[row-1][col+drift]
			while newLoc not in {" ","*","O","o","."}:
				if logoArray[row-1][col] == "\\": drift = -1
				elif logoArray[row-1][col] == "/": drift = 1
				drift = randint(-1,1)
				newLoc = logoArray[row-1][col+drift]
			#if bubble collides with another bubble, remove one of them
			if newLoc in {"*","O","o","."}:
				poppedBubbles += 1
			# set new location of bubble
			logoArray[row-1][col+drift] = char
	# return the number of bubbles which were removed during this function
	return poppedBubbles


# for each character in the array, move bubble at row,col
# when a bubble moves, it has a chance to pop itself or other bubbles
# returns the number of bubbles which were popped after altering them all
def moveBubbles(logoArray):
	poppedBubbles = 0
	for row in range(1,len(logoArray)):
		for col in range(1,len(logoArray[row])-1):
			poppedBubbles += moveBubble(logoArray,row,col)
	# return the number of bubbles which were removed during this function
	return poppedBubbles


# for each bubble in the logo, has a chance to grow it from "." to "o" to "O"
def growBubbles(logoArray):
	for row in range(1,len(logoArray)):
		for col in range(1,len(logoArray[row])-1):
			char = logoArray[row][col]
			if char == ".":
				willGrow = randint(0,2) != 0
			elif char == "o":
				willGrow = randint(0,2) == 2
			else:
				continue
			if willGrow and char == "o":
				char = "O"
			if willGrow and char == ".":
				char = "o"
			logoArray[row][col] = char


# generate between 1,n new bubbles represented by "." at any "_" in 'rows'
# rows is a list of indices of the logo rows upon which new bubbles will appear
# returns the number of new bubbles generated
def makeNewBubbles(logoArray,n,rows):
	newBubbles = randint(1,n)
	for i in range(newBubbles):
		row = 1
		col = 0
		# randomly select a _ position in the logoarray for the new bubble
		while logoArray[row][col] != "_":
			# only produce new bubbles on given rows, 2, 5, and 7 of the logo
			row = choice(rows)
			# produce new bubbles in any column
			col = randint(1,22)
			# regenerate location if location is under or beside another bubble
			# this is to increase the homogeneity of the bubbles; it looks nicer
			if logoArray[row][col-1] == "." or logoArray[row][col+1] == "." or \
			logoArray[row-1][col] in {".","o","O"}:
				row = choice([5,7])
				col = randint(1,22)
		# place the new bubble
		logoArray[row][col] = "."
	return newBubbles


# joins 2d array of characters into list of strings
# then joins list of strings into one string with newlines, then prints it
def printLogoArray(logoArray):
	Core.movePrintCursor(len(logoArray))
	for line in logoArray:
		print("".join(line))


# procedurally generated bubble animation, makes, grows, and moves bubbles
# t is the time between frames
# b is the number of bubbles which will be produced in total
# n is the max number of bubbles produced per frame
def dynamicBubbleAnimation(t,b,n):
	# convert logo data into a 2d array so it can be easily operated on
	logoArray = [[char for char in line] for line in Data.logoFrame]
	totalBubbles = 0
	currentBubbles = 0
	# get a list of row indices of every other row that contains a "_"
	# flat rows are rows where new bubbles will appear
	flatrows = [nrow for nrow in range(1,len(logoArray)) if "_" in logoArray[nrow]][1::2]
	# run animation until b bubbles have been produced
	while totalBubbles < b:
		# if user presses any key, skip animation
		if Core.kbInput(): break
		growBubbles(logoArray)
		newBubbles = makeNewBubbles(logoArray,n,flatrows)
		sleep(t)
		printLogoArray(logoArray)
		poppedBubbles = moveBubbles(logoArray)
		totalBubbles += newBubbles
		currentBubbles += newBubbles - poppedBubbles
	Core.flushInput()
	# run animation until no bubbles remain
	while currentBubbles > 0:
		# if user presses any key, skip animation
		if Core.kbInput():	return False
		growBubbles(logoArray)
		# add a small delay for the final bubbles for pizazz
		if currentBubbles < 3:	sleep(t)
		# if currentBubbles == 1: sleep(t)
		sleep(t)
		printLogoArray(logoArray)
		poppedBubbles = moveBubbles(logoArray)
		currentBubbles -= poppedBubbles
	return True


# runs the intro logo animation
# uses data from the bottom of Data.py
def gameIntro():
	tempLines = Data.logoFrame.copy()
	Core.clearScreen(delay=0)
	# print logo crawling up
	l = len(tempLines)
	for i in range(l,-1,-1):
		Core.movePrintCursor(l,clear=True)
		# if user presses any key, skip animation
		if Core.kbInput():	return
		print("\n".join(tempLines[i:l]))
		sleep(0.125)

	# if user skipped bubble animation, skip rest of intro too
	if not dynamicBubbleAnimation(0.2,25,2):
		return

	# print PoPy text crawling up
	sleep(0.5)
	l = len(Data.logoFrame)
	for i in range(l-1,3,-1):	# stops at the fourth line from the top
		tempLines = Data.logoFrame.copy()
		Core.movePrintCursor(l+1)
		if Core.kbInput():	return
		tempLines[i] = Data.titleMask[i]
		for line in tempLines:
			# we need to overwrite the lines already printed with whitespace
			if line == "": line = " "*30
			print(line)
		sleep(0.15)
	sleep(0.5)
