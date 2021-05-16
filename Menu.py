# Menu.py
# This file serves as an API for Parser.py to save and load game data with files
# This file is dependent on Objects.py and is a dependency of Parser.py

# It consists of four major parts;
# 1. Write data functions	(functions to write objects P, W, and G to files)
# 2. Read data functions	(functions to read save files; player, world, game)
# 3. Menu functions			(functions to load, save, delete, start new games)
# 4. Game Intro functions	(functions to print game intro animation)

import sys
import os

from Objects import *


##########################
## WRITE DATA FUNCTIONS ##
##########################

# writes the player object to a file, probably named player.popy
def writePlayer(filename,P):
	pfd = open(filename,"w")
	P.writeAttributes(pfd)
	pfd.close()

# writes the world dictionary to a file, probably named "world.popy"
def writeWorld(filename,W):
	wfd = open(filename,'w')
	# write each room in the world dict
	for roomname in W:
		room = W[roomname]
		# name denoted by '#', description denoted by '@'
		wfd.write(f'#{roomname}\n')
		wfd.write(f'@{room.desc}\n')
		# write each exit direction and name, denoted by '%'
		for exit in room.exits:
			wfd.write(f'%"{exit}": "{room.exits[exit]}"\n')
		# write each item name, denoted by '$'
		for item in room.contents:
			writeObj(wfd,item)
			wfd.write('\n')
		# write each creature name, denoted by '#'
		for creature in room.occupants:
			writeObj(wfd,creature)
			wfd.write('\n')
		# ends a room block with a '~' and some newlines
		wfd.write("~\n\n")
	wfd.close()

# just writes the game object to a file, probably named "game.popy"
def writeGame(filename,G):
	gfd = open(filename,"w")
	gfd.write(str(G.mode) + "\n")
	gfd.write(G.currentroom.name + "\n")
	gfd.write(G.prevroom.name + "\n")
	gfd.write(str(G.time) + "\n")
	gfd.close()


#########################
## READ DATA FUNCTIONS ##
#########################

# takes text between quotations and replaces \n and \t with respective values
def readString(text):
	quote = text[0]
	start = 1
	end = text.find(quote,start)
	string = text[start:end]
	return string.replace('\\n','\n').replace('\\t','\t')

# strips whitepsace and casts text to integer
def readInt(text):
	return int(text.strip())

# strips whitespace and casts text to corresponding boolean value
def readBool(text):
	text = text.strip()
	if text == "False":		return False
	elif text == "True":	return True
	else:	raise Exception("Text is not boolean value")

# reads the given text as a list, delimited by both ':' and ',' then...
# casts that list to a dict by iterating through every other index in the list
def readDict(text):
	l = readList(text,',:')
	try:	return {l[i]: l[i+1] for i in range(0,len(l),2)}
	except: raise Exception("Dict data not convertable from list to dict")

# reads a list from text, given a set of delimiters (usually just ',')
# iterates through the text with i and finds the index of the next delimiter
# isolates text between i and next delimiter, assigns it to elemtext
# attempts to define elem by passing elemtext to the appropriate read function
# skips i to the index following the last delimiter that was used
# if elemtext is correctly read into a data type, append that data to the list
def readList(text,delimiters):
	list = []
	i = 0
	while i < len(text):
		elem = None
		delimiter = findNextDelimiter(delimiters,text,i)
		elemtext = text[i:delimiter].strip()
		if elemtext[0] == '"':
			elem = readString(elemtext)
			i = delimiter + 1
		elif elemtext[0] in numsymbols:
			elem = readInt(elemtext)
			i = delimiter + 1
		elif elemtext == 'True' or elemtext == 'False':
			elem = readBool(elemtext)
			i = delimiter + 1
		elif elemtext[0] == '[':
			symbol = elemtext[0]
			liststart = text.find(symbol,i)
			listend = findMatchingParenth(text,liststart)
			listtext = text[liststart+1:listend]
			elem = readList(listtext,',')
			i = findNextDelimiter(delimiters,text,listend) + 1
		elif elemtext[0] == '{':
			symbol = elemtext[0]
			dictstart = text.find(symbol,i)
			dictend = findMatchingParenth(text,dictstart)
			dicttext = text[dictstart+1:dictend]
			elem = readDict(dicttext)
			i = findNextDelimiter(delimiters,text,dictend) + 1
		elif elemtext[0] in {'$','!'}: # the element is be an object
			tag = elemtext[0]
			objStart = text.find(tag,i)
			open = text.find('(',i)
			close = findMatchingParenth(text,open)
			elem = readObj(text[objStart:close+1])
			i = findNextDelimiter(delimiters,text,close) + 1
		else:
			raise Exception('Unreadable data element in list: ' + elemtext)
		list.append(elem)
	return list

# reads object text of the form: ?Classname (attribute1,attribute2...)
# where ? is a tag '$' or '!' which signifies the broad type of object
# instantiates an Item() or Creature() object and returns it
def readObj(objtext):
	tag = objtext[0]
	open = objtext.index("(")
	classname = objtext[1:open].strip()
	close = findMatchingParenth(objtext,open)
	attributetext = objtext[open+1:close]
	attributes = readList(attributetext,",")
	classobj = strToClass(classname)
	return classobj(*attributes)

# takes roomtext, a list of lines of data, as input, as well as the world dict
# instantiates a Room() object from roomtext and adds the room to the world dict
def readRoom(roomtext,world):
	name = ""
	desc = ""
	exits = {}
	contents = []
	occupants = []
	roomeffects = []
	# for each line in roomtext
	for l in range(len(roomtext)):
		line = roomtext[l]
		if line[0] == "#":		# room name
			name = line[1:-1]
		elif line[0] == "@":	# room description
			desc = line[1:-1]
		elif line[0] == "%":	# room exit
			colon = line.index(":")
			key = readString(line[1:colon].strip())
			value = readString(line[colon+1:-1].strip())
			exits[key] = value
		elif line[0] in {"$","!"}:	# Item() or Creature()
			tag = line[0]
			objtext = " ".join(roomtext[l:])
			obj = readObj(objtext)
			if tag == "$":	contents.append(obj)
			if tag == "!":	occupants.append(obj)
		elif line[0] == "*":	# room effects
			pass
			# effect = effects[]
			# roomeffects.append()
		elif line[0] == "~":	# end room data
			world[name] = Room(name,desc,exits,contents,occupants,roomeffects)

# reads all data in the world file, probably named "world.popy"
# returns the World object as a dictionary of string: Room() pairs
def readWorld(filename):
	world = {}
	wfd = open(filename,"r")
	worldtext = wfd.readlines()
	l = 0
	while l < len(worldtext):
		if worldtext[l][0] == "#":
			endroomtext = findLineStartsWith(worldtext,"~",l)
			roomtext = worldtext[l:endroomtext+1]
			readRoom(roomtext,world)
			l = endroomtext
		else:
			l += 1
	wfd.close()
	return world

# reads the global game class file, probably named "game.popy"
# takes the world dict as input, returns the Game object
def readGame(filename,W):
	gfd = open(filename,"r")
	gametext = gfd.readlines()			# split game file into a list of lines
	mode = int(gametext[0][:-1])		# first line is gamemode int
	currentroom = gametext[1][:-1]		# second line is name of current room
	prevroom = gametext[2][:-1]			# third line is name of previous room
	time = int(gametext[3][:-1])		# fourth line is time int
	gfd.close()
	return Game(mode,W[currentroom],W[prevroom],time)

# reads the player file, probably named "player.popy"
# returns the Player object
def readPlayer(filename):
	pfd = open(filename, "r")
	playertext = pfd.readlines()
	playertext = " ".join(playertext)
	attributes = readList(playertext,",")
	pfd.close()
	return Player(*attributes)


####################
## MENU FUNCTIONS ##
####################

# saves data from player, world, and game objects to respective text files
def saveGame(P,W,G):
	if not os.path.exists("saves"):	#create save directory if it doesn't exist
		os.mkdir("saves")
	os.chdir("saves")

	# split existing save names into a list and display them
	saves = os.listdir()
	columnPrint(saves,10,10)
	# player names their save
	savename = input("\nWhat name will you give this save file?\n> ").lower()
	if savename == '':
		print("Save name cannot be empty")
		os.chdir("..")
		return
	# if the save name is unused, make a new directory
	if not (os.path.exists(savename)):
		try:	os.mkdir(savename)
		except:
			print("Invalid save name")
			os.chdir("..")
			return
	# if the save name is used, ask to overwrite it
	else:
		print("A save file with this name already exists")
		#if dont overwrite, then just return
		if not (yesno("Would you like to overwrite it?")):
			os.chdir("..")
			return

	# write world, player, and game files
	os.chdir(savename)
	writeWorld("world.popy", W)
	writePlayer("player.popy", P)
	writeGame("game.popy", G)
	os.chdir("..")
	os.chdir("..")
	sleep(1)
	print("Game saved")
	sleep(1)

# load a game from a save directory
def loadGame(filename):
	if not (os.path.exists("saves")) or len(os.listdir(".\\saves")) == 0:
		print("There are no save files")
		return mainMenu()
	os.chdir("saves")

	if filename == None:
		# split save names into a list and display them
		saves = os.listdir()
		columnPrint(saves,10,10)
		savename = input("\nWhich save file will you load?\n> ")
	else:	savename = filename

	# if user inputs a save name that doesn't exist
	if not os.path.exists(savename):
		print("There is no save file named '" + savename + "'\n")
		os.chdir("..")
		return mainMenu()
	# try to load the player, world, and game objects
	# try:
	os.chdir(savename)
	P = readPlayer("player.popy")
	W = readWorld("world.popy")
	G = readGame("game.popy",W)
	# # hopefully load doesn't fail, that would suck
	# except:
	# 	print("Could not load game, save file corrupted\n")
	# 	os.chdir("..")
	# 	os.chdir("..")
	# 	return mainMenu()

	os.chdir("..")
	os.chdir("..")
	ellipsis(3)
	# describe the current room
	G.startUp(P,W)
	return P, W, G

# deletes all save files in 'save' directory (if the user is very, very sure)
def deleteAll():
	if not yesno("Are you sure you want to delete all save files?"):
		os.chdir("..")
		return mainMenu()
	if not yesno("Are you very, very sure??"):
		os.chdir("..")
		return mainMenu()
	for savename in os.listdir():
		os.chdir(savename)
		for filename in os.listdir(): os.remove(filename)
		os.chdir("..")
		os.rmdir(savename)
	os.chdir("..")
	sleep(1)
	print("All save files deleted")
	sleep(1)
	print()
	return mainMenu()

# deletes a save file whose name is given by the user
def delete(filename):
	if not os.path.exists("saves") or len(os.listdir(".\\saves")) == 0:
		print("There are no save files")
		return mainMenu()
	os.chdir("saves")

	if filename == None:
		# split save names into a list and display them
		saves = os.listdir()
		columnPrint(saves,10,10)
		savename = input("\nWhich save file will you delete?\n> ")
	else: savename = filename

	if savename == "all":
		return deleteAll()

	# if the user inputs a save name that doesn't exist
	if not os.path.exists(savename):
		print("There is no save file named '" + savename + "'\n")
		os.chdir("..")
		return mainMenu()
	# ask for confirmation, if no, then return to menu
	if not yesno("Are you sure you want to delete this save file?"):
		os.chdir("..")
		return mainMenu()

	# remove all files in this save directory, and remove that save directory
	os.chdir(savename)
	for filename in os.listdir(): os.remove(filename)
	os.chdir("..")
	os.rmdir(savename)
	os.chdir("..")
	sleep(1)
	print("Deleted")
	sleep(1)
	print()
	return mainMenu()

# just asks for player name, starts everything else at initial values
def createCharacter():
	name = input("What is your name?\n> ")
	while len(name) == 0: name = input('> ')
	return Player(name,"a guy",1,1,inittraits,0,[],initgear,[],False,0,0)

# starts a new game and returns player, world, and game objects
def newGame():
	# tries to load a clean new world from initial world file
	W = readWorld("world.popy")
	# initializes from the character creation screen
	P = createCharacter()
	# initializes the game at the "cave" room
	G = Game(0,W["cave"],W["cave"],0)
	ellipsis(3)
	# enter the starting room
	sleep(0.5)
	clearScreen()
	G.startUp(P,W)
	return P, W, G

# automatically starts a new game with a premade character for easy testing
def testGame():
	W = readWorld("world.popy")
	traits = [4 for _ in range(10)]
	C = Compass("compass", "a plain steel compass with a red arrow", 2, 10)
	status = [["fireproof",-1], ["poisoned",5], ["cursed",-2], ["immortal",-1],
	["sharpshooter",50],["invisible",15], ["poisoned",-1]]
	P = Player("Norman","a hero",24,24,traits,1000,[C],initgear,status,1585,100,False)

	clearScreen()
	G = Game(0,W["cave"],W["tunnel"],0)
	G.startUp(P,W)
	G.mode = 1
	return P, W, G

# main game menu, used to instantiate global variables P, W, and G in Parser.py
# loops until a new game is made, a save is loaded, or the game is quit
# n denotes how many times mainMenu has recurred
def mainMenu():
	while True:
		print(menuinstructions)
		g = input("> ").lower().split()
		if len(g) == 0: 						continue
		if g[0] == "info" and len(g) == 1:		print("\n"*64+gameinfo+"\n")
		if g[0] == "new" and len(g) == 1:		return newGame()

		if g[0] == "load" and len(g) == 1:		return loadGame(None)
		if g[0] == "load":						return loadGame(" ".join(g[1:]))

		if g[0] == "delete" and len(g) == 1:	return delete(None)
		elif g[0] == "delete":					return delete(" ".join(g[1:]))

		if g[0] == "quit" and len(g) == 1:		sys.exit()
		if g[0] == "test" and len(g) == 1:		return testGame()


##########################
## GAME INTRO FUNCTIONS ##
##########################

# print logo bubbling animation from statically stored string "frames"
# unused function, replaced by dynamicBubbleAnimation()
def staticBubbleAnimation():
	for i in range(len(bubbleFrames)):
		print("\n"*64)
		print(bubbleFrames[i])
		sleep(0.125)
	clearScreen()
	print(logo+"\n"*7)
	sleep(0.625)

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
		logoArray[row][col] = logoLines[row][col]
		poppedBubbles += 1
	# if char is a bubble
	elif char in {".","o","O"}:
		if bubbleTrapped(logoArray,row,col):
			if char == "O" and bool(randint(0,1)):
				logoArray[row][col] = "*"
		else:
			# erase char at current location
			logoArray[row][col] = logoLines[row][col]
			# generate "drift"; it may move left or right as it also moves up
			drift = randint(-1,1)
			# if bubble is blocked above by a wall, it must drift accordingly
			if logoArray[row-1][col] == "\\":		drift = -1
			elif logoArray[row-1][col] == "/":		drift = 1
			# determine new unoccupied location as bubble moves upward
			newLoc = logoArray[row-1][col+drift]
			while newLoc not in {" ","*","O","o","."}:
				if logoArray[row-1][col] == "\\":	drift = -1
				elif logoArray[row-1][col] == "/":	drift = 1
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

# generate between 1,n new bubbles represented by "." at any "_" in logo
# rows is a list of indices of the logo rows upon which new bubbles will appear
# returns the number of new bubbles generated
def makeNewBubbles(logoArray,n,rows):
	newBubbles = randint(1,n)
	for i in range(newBubbles):
		row = 1
		col = 0
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

		logoArray[row][col] = "."
	return newBubbles

# joins 2d array of characters into list of strings
# then joins list of strings into one string with newlines, then prints it
def printLogoArray(logoArray):
	clearScreen()
	print("\n".join(["".join(line) for line in logoArray]))

# procedurally generated bubble animation, makes, grows, and moves bubbles
# t is the time unit between frames
# b is the number of bubbles which will be produced in total
# n is the max number of bubbles produced per frame
def dynamicBubbleAnimation(t,b,n):
	# convert logo data into a 2d array so it can be easily operated on
	logoArray = [[char for char in line] for line in logoLines]
	totalBubbles = 0
	currentBubbles = 0
	# get a list of row indices of every other row which contains a "_"
	flatrows = [nrow for nrow in range(1,len(logoArray)) if "_" in logoArray[nrow]][1::2]
	# run animation until b bubbles have been produced
	while totalBubbles < b:
		# if user presses any key, skip animation
		if kbInput():	return False
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
		if kbInput():	return False
		growBubbles(logoArray)
		# add a small delay for the final bubbles
		if currentBubbles < 3:	sleep(t)
		sleep(t)
		printLogoArray(logoArray)
		poppedBubbles = moveBubbles(logoArray)
		currentBubbles -= poppedBubbles
	return True

# prints the static logo and flushes keyboard input at the end of the intro
def endIntro():
	clearScreen()
	print(logo)
	flushInput()

# runs the intro logo animation
# uses data in the bottom of Data.py
def gameIntro():
	tempLines = []
	for line in logoLines:	tempLines.append(line)
	clearScreen()
	# print logo crawling up
	for line in tempLines:
		# if user presses any key, skip animation
		if kbInput():	return endIntro()
		print(line)
		sleep(0.125)

	# if user skipped bubble animation, skip rest of intro too
	if not dynamicBubbleAnimation(0.20,10,2):	return endIntro()

	# print PoPy text crawling up
	sleep(0.375)
	l = len(popyLines)
	for i in range(l-4):
		if kbInput():	return endIntro()
		tempLines[l-i-1] = popyLines[l-i-1]
		clearScreen()
		for line in tempLines:
			print(line)
		sleep(0.125)
		tempLines[l-i-1] = logoLines[l-i-1]
	clearScreen()
	print(logo+"\n"*7)
	sleep(0.625)
	endIntro()


################################################################################
#
# THE FOLLOWING CODE COULD BE USED FOR A FUTURE TRANSITION TO SAVING GAME DATA IN JSON FORMAT
#
# Note: the current main incompatability with this code is the fact that some objects' __init__ method takes the data in a way which does not have a 1:1 relationship with the objects attributes.
# for instance, python.__init__() takes many numerical attributes as an array, but the attributes are not stored like this in JSON format.
#
################################################################################
#
# import json
# JSONprimitives = {dict,list,str,int,float,bool,None}

# class worldEncoder(json.JSONEncoder):
# 	def default(self, o):
# 		if type(o) == set:
# 			return {"__class__":"set","setdata":list(o)}
# 		# elif type(o) == Room:
# 		# 	return o.__dict__
# 		elif type(o) not in JSONprimitives:
# 			d = o.__dict__
# 			d["__class__"] = o.__class__.__name__
# 			return d
# 			# return [o.__class__.__name__] + list(o.__dict__.values())
# 		else:
# 			return o
#
# def default(d):
# 	print(type(d))
# 	if "__class__" in d and d["__class__"] == "set":
# 		return set(d["setdata"])
# 	elif "__class__" in d.keys():
# 		objClassname = d["__class__"]
# 		del d["__class__"]
#
# 		objAttributes = list(d.values())
# 		print("========================: " + d["name"] + str(objAttributes))
# 		if objClassname == "Room":
# 			return Room(*objAttributes)
# 		elif objClassname == "Empty":
# 			return Empty()
# 		elif objClassname in creatures:
# 			return creatures[objClassname](*objAttributes)
# 		elif objClassname in items:
# 			return items[objClassname](*objAttributes)
# 		else:
# 			raise Exception("ERROR in decoding JSON object class type")
# 	else:
# 		return d
#
# def readJSON(filename):
# 	with open(filename,"r") as fd:
# 		W = json.load(fd,object_hook=default)
# 	return W
#
# def writeJSON(filename,W):
# 	with open(filename,"w") as fd:
# 		json.dump(W,fd,cls=worldEncoder,indent="\t")
