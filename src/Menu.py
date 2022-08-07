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
import os, sys, json

import Items
import Creatures
import Effects
import Data
import Core



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


class worldEncoder(json.JSONEncoder):
	def default(self,objToWrite):
		JSONprimitives = {dict,list,str,int,float,bool,None}
		if hasattr(objToWrite,"parent"):
			del objToWrite.parent
		if type(objToWrite) == set:
			return {"__class__":"set","setdata":list(objToWrite)}
		# elif type(objToWrite) == Room:
		# 	return objToWrite.__dict__
		elif Core.hasMethod(objToWrite,"convertToJSON"):
			return objToWrite.convertToJSON()
		elif type(objToWrite) not in JSONprimitives:
			jsonDict = objToWrite.__dict__
			# this is done so the class key appears first in the JSON object
			# TODO: swap the following lines for Python 3.9
			# jsonDict = {"__class__": objToWrite.__class__.__name__} | jsonDict
			jsonDict = {"__class__": objToWrite.__class__.__name__, **jsonDict}
			return jsonDict
		else:
			return objToWrite


def writeJSON(filename,World):
	with open(filename,"w") as fd:
		json.dump(World,fd,cls=worldEncoder,indent="\t")




#########################
## READ DATA FUNCTIONS ##
#########################


def default(jsonDict):
	# print("==== converting object of type: " + str(type(jsonDict)))
	if "__class__" in jsonDict:
		objClassname = jsonDict["__class__"]
		# print("=== class is " + objClassname)
		del jsonDict["__class__"]
		if objClassname == "set":
			return set(jsonDict["setdata"])

		objClass = Core.strToClass(objClassname,["Core","Creatures","Items"])
		if objClass == None:
			raise Exception("Could not find class for world key:",objClassname)
		objAttributes = list(jsonDict.values())
		# print("========: " + jsonDict["name"] + " " + str(objAttributes))
		if objClassname == "Room":
			return Core.Room(*objAttributes)
		elif objClassname == "Empty":
			return Empty()
		elif objClass != None:
			if Core.hasMethod(objClass,"convertFromJSON"):
				return objClass.convertFromJSON(jsonDict)
			try:
				return objClass(*objAttributes)
			except TypeError as e:
				raise TypeError(f"Failed to instantiate object: '{objClassname}' from JSON with attributes:\n",objAttributes,e)
		else:
			raise Exception("ERROR in decoding JSON object class type: " + objClassname)
	else:
		return jsonDict


def readJSON(filename):
	with open(filename,"r") as fd:
		World = json.load(fd,object_hook=default)
	return World


# reads the global game class file, probably named "game.txt"
# takes the world dict as input, returns the Game object
def readGame(filename,World):
	gfd = open(filename,"r")
	gametext = gfd.readlines()			# split game file into a list of lines
	mode = int(gametext[0][:-1])		# first line is gamemode int
	currentroom = gametext[1][:-1]		# second line is name of current room
	prevroom = gametext[2][:-1]			# third line is name of previous room
	time = int(gametext[3][:-1])		# fourth line is time int
	events = eval(gametext[4][:-1])
	gfd.close()
	return Core.Game(mode,World[currentroom],World[prevroom],time,events)




####################
## MENU FUNCTIONS ##
####################


# saves data from player, world, and game objects to respective text files
def saveGame():
	# create save directory if it doesn't exist
	if not os.path.exists("saves"):
		os.mkdir("saves")
	os.chdir("saves")

	# split existing save names into a list and display them
	saves = os.listdir()
	Core.columnPrint(saves,10,10)
	# player names their save
	savename = input("\nWhat name will you give this save file?\n> ").lower()
	if savename == "":
		print("Save name cannot be empty.")
		os.chdir("..")
		return
	if savename == "all":
		print("Save name cannot be 'all'.")
		os.chdir("..")
		return

	# if the save name is used, ask to overwrite it
	if os.path.exists(savename):
		print("A save file with this name already exists.")
		#if dont overwrite, then just return
		if not (Core.yesno("Would you like to overwrite it?")):
			os.chdir("..")
			return
	# if the save name is unused, make a new directory
	else:
		try:
			os.mkdir(savename)
		except:
			print("Invalid save name.")
			os.chdir("..")
			return

	# write world, player, and game files
	os.chdir(savename)
	writeJSON("world.json", Core.world)
	writeJSON("player.json", Core.player)
	writeGame("game.txt", Core.game, Core.world)
	os.chdir("../..")
	sleep(1)
	print("Game saved")
	sleep(1)


# load a game from a save directory
def loadGame(filename):
	Core.clearScreen()
	if not (os.path.exists("saves")) or len(os.listdir("./saves")) == 0:
		print("\nThere are no save files.\n")
		input()
		return False
	os.chdir("saves")

	if filename == None:
		# split save names into a list and display them
		print("Save files: ")
		saves = os.listdir()
		Core.columnPrint(saves,10,10)
		savename = input("\nWhich save file will you load?\n> ")
	else:
		savename = filename

	if savename == "":
		os.chdir("..")
		return False

	# if user inputs a save name that doesn't exist
	if not os.path.exists(savename):
		print(f"\nThere is no save file named '{savename}'.\n")
		os.chdir("..")
		input()
		return False
	os.chdir(savename)
	# try to load the player, world, and game objects
	# try:
	Core.player = readJSON("player.json")
	Core.world = readJSON("world.json")
	Core.game = readGame("game.txt",Core.world)
	# hopefully load doesn't fail, that would suck
	# except:
	# 	print("Could not load game, save data corrupted\n")
	# 	os.chdir("..")
	# 	os.chdir("..")
	# 	return False

	os.chdir("../..")
	Core.ellipsis(3)
	Core.flushInput()
	Core.clearScreen()
	return True


# deletes all save files in 'save' directory (if the user is very, very sure)
def deleteAll():
	Core.clearScreen()
	if not Core.yesno("Are you sure you want to delete all save files?"):
		os.chdir("..")
		return mainMenu()
	if not Core.yesno("Are you very, very sure??"):
		os.chdir("..")
		return mainMenu()
	for savename in os.listdir():
		os.chdir(savename)
		for filename in os.listdir(): os.remove(filename)
		os.chdir("..")
		os.rmdir(savename)
	os.chdir("..")
	sleep(1)
	print("\nAll save files deleted.\n")
	input()


# deletes a save file whose name is given by the user
def delete(filename):
	Core.clearScreen()
	if not os.path.exists("saves") or len(os.listdir("./saves")) == 0:
		print("\nThere are no save files.\n")
		input()
		return
	os.chdir("saves")

	if filename == None:
		# split save names into a list and display them
		print("Save files: ")
		saves = os.listdir()
		Core.columnPrint(saves,10,10)
		savename = input("\nWhich save file will you delete?\n> ")
	else:
		savename = filename

	if savename == "":
		os.chdir("..")
		return
	if savename == "all":
		return deleteAll()

	# if the user inputs a save name that doesn't exist
	if not os.path.exists(savename):
		print(f"\nThere is no save file named '{savename}'.\n")
		os.chdir("..")
		input()
		return mainMenu()
	# ask for confirmation, if no, then return to menu
	if not Core.yesno("Are you sure you want to delete this save file?"):
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
	print("\nDeleted\n")
	input()


# asks for player name and description, starts everything else at initial values
def createCharacter():
	name = input("What is your name?\n> ")
	while len(name) == 0:
		name = input("> ")
	desc = input("Describe yourself.\n> ")
	while len(desc) == 0:
		desc = input("> ")
	return Core.Player(name,desc,[1]*10,[],1,1,0,[],Data.initgear,0,0,[])


# starts a new game and returns player, world, and game objects
def newGame():
	# tries to load a clean new world from initial world file
	Core.world = readJSON("World.json")
	# initializes from the character creation screen
	Core.player = createCharacter()
	# initializes the game at the "cave" room
	Core.game = Core.Game(0,Core.world["cave"],Core.world["cave"],0,{})
	Core.ellipsis(3)
	# enter the starting room
	sleep(0.5)
	Core.clearScreen()
	Core.flushInput()


# automatically starts a new game with a premade character for easy testing
def testGame():
	Core.world = readJSON("World.json")

	inv = [Core.Compass("compass","a plain steel compass with a red arrow",[],"compasses",2,10,[])]
	status = [["fireproof",-1], ["poisoned",5], ["cursed",-2], ["immortal",-1],
	["sharpshooter",50], ["invisible",15], ["poisoned",-1], ["flying",5]]

	Core.player = Core.Player("Norman","a hero",[4]*10,status,24,24,1000,inv,Data.initgear,1585,100,[])
	Core.game = Core.Game(0,Core.world["cave"],Core.world["tunnel"],0,{})

	Core.clearScreen()
	Core.game.mode = 1


def gameInfo():
	Core.clearScreen()
	print(Data.gameinfo)
	input()


# main game menu, used to instantiate global variables P, W, and G in Parser.py
# loops until a new game is made, a save is loaded, or the game is quit
# n denotes how many times mainMenu has recurred
def mainMenu():
	# handle case when running code from src directory instead of main directory
	if "src" in os.getcwd(): os.chdir("..")

	while True:
		Core.clearScreen()
		Core.flushInput()
		print(Data.logo)
		print(Data.menuinstructions)
		g = input("> ").lower().split()

		if len(g) == 0:
			continue
		elif g[0] == "info" and len(g) == 1:
			gameInfo()
		elif g[0] == "new" and len(g) == 1:
			newGame()
			return
		elif g[0] == "load" and len(g) == 1:
			if loadGame(None):
				return
		elif g[0] == "load":
			if loadGame(" ".join(g[1:])):
				return
		elif g[0] == "delete" and len(g) == 1:
			delete(None)
		elif g[0] == "delete":
			delete(" ".join(g[1:]))
		elif g[0] == "quit" and len(g) == 1:
			Core.game.quit = True
			return
		elif g[0] == "test" and len(g) == 1:
			testGame()
			return




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
		logoArray[row][col] = Data.logoLines[row][col]
		poppedBubbles += 1
	# if char is a bubble
	elif char in {".","o","O"}:
		# if bubble is "O" and trapped, have chance to pop it
		if bubbleTrapped(logoArray,row,col):
			if char == "O" and bool(randint(0,1)):
				logoArray[row][col] = "*"
		else:
			# erase char at current location
			logoArray[row][col] = Data.logoLines[row][col]
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
				willGrow = bool(randint(0,2))
			elif char == "o":
				willGrow = bool(randint(0,1))
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
	Core.clearScreen()
	print("\n".join(["".join(line) for line in logoArray]))


# procedurally generated bubble animation, makes, grows, and moves bubbles
# t is the time between frames
# b is the number of bubbles which will be produced in total
# n is the max number of bubbles produced per frame
def dynamicBubbleAnimation(t,b,n):
	# convert logo data into a 2d array so it can be easily operated on
	logoArray = [[char for char in line] for line in Data.logoLines]
	totalBubbles = 0
	currentBubbles = 0
	# get a list of row indices of every other row that contains a "_"
	# flat rows are rows where new bubbles will appear
	flatrows = [nrow for nrow in range(1,len(logoArray)) if "_" in logoArray[nrow]][1::2]
	# run animation until b bubbles have been produced
	while totalBubbles < b:
		# if user presses any key, skip animation
		if Core.kbInput():	return False
		growBubbles(logoArray)
		newBubbles = makeNewBubbles(logoArray,n,flatrows)
		sleep(t)
		printLogoArray(logoArray)
		poppedBubbles = moveBubbles(logoArray)
		totalBubbles += newBubbles
		currentBubbles += newBubbles - poppedBubbles
	# run animation until no bubbles remain
	while currentBubbles > 0:
		# if user presses any key, skip animation
		if Core.kbInput():	return False
		growBubbles(logoArray)
		# add a small delay for the final three bubbles for pizazz
		if currentBubbles < 3:	sleep(t)
		sleep(t)
		printLogoArray(logoArray)
		poppedBubbles = moveBubbles(logoArray)
		currentBubbles -= poppedBubbles
	return True


# prints the static logo and flushes keyboard input at the end of the intro
def endIntro():
	Core.clearScreen()
	print(Data.logo)
	Core.flushInput()


# runs the intro logo animation
# uses data from the bottom of Data.py
def gameIntro():
	tempLines = [line for line in Data.logoLines]
	Core.clearScreen()
	# print logo crawling up
	for line in tempLines:
		# if user presses any key, skip animation
		if Core.kbInput():	return endIntro()
		print(line)
		sleep(0.125)

	# if user skipped bubble animation, skip rest of intro too
	if not dynamicBubbleAnimation(0.25,10,2):
		return endIntro()

	# print PoPy text crawling up
	sleep(0.375)
	l = len(Data.popyLines)
	for i in range(l-4):	#stops at the fourth line from the top
		if Core.kbInput():	return endIntro()
		tempLines[l-i-1] = Data.popyLines[l-i-1]
		Core.clearScreen()
		for line in tempLines:
			print(line)
		sleep(0.125)
		tempLines[l-i-1] = Data.logoLines[l-i-1]
	Core.clearScreen()
	print(Data.logo+"\n"*7)
	sleep(0.625)
	endIntro()
