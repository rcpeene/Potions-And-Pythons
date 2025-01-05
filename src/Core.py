# Core.py
# This file contains all core functions and classes used throughout the game
# This file is a dependency of Objects.py and is dependent on Data.py

# It consists of two main parts;
# 1. Core functions			(used in Objects.py, Menu.py, and Parser.py)
# 2. Dialogue Classes		(DialogueNode and DialogueTree)
# 3. Core class definitions	(empty, game, room, item, creature, player, etc.)

from time import sleep
from random import randint,sample
from math import floor, log10
from bisect import insort
import sys, os

try:
	import msvcrt
except:
	import termios, select

import Data




####################
## CORE FUNCTIONS ##
####################


# Used to determine if a term has a match with any of an object's names
def nameMatch(term,obj):
	if term == None:
		return False
	term = term.lower()
	if isinstance(obj, Room):
		return term == obj.name.lower() or term in ["here", "room"]
	return term == obj.name.lower() or term == obj.stringName(det=False).lower() or term in obj.aliases


# retrieves a class object with className from the modules list
# returns None if no such object exists
def strToClass(className,moduleNames):
	classObject = None
	for moduleName in moduleNames:
		try:
			classObject = getattr(sys.modules[moduleName],className)
		except:
			continue
	return classObject


# returns bool indicating whether an obj has a method with the given string name
# used as a shortcut for more readable code than the traditional method
def hasMethod(obj,methodName):
	possibleMethod = getattr(obj,methodName,None)
	if not possibleMethod:
		possibleMethod = getattr(obj.__class__,methodName,None)
	if possibleMethod != None and callable(possibleMethod):
		return True
	return False


def getRoomKey(room,world):
	for key,value in world.items():
		if value == room:
			return key


def clearScreen(*args):
	if os.name == "nt":
		os.system("cls")
	else:
		os.system("clear")


# clears pending keyboard input. strategy varies by operating system.
def flushInput():
	try:
		while msvcrt.kbhit():
			msvcrt.getch()
	except NameError:
		try:
			termios.tcflush(sys.stdin,termios.TCIOFLUSH)
		except termios.error:
			pass


# checks for any keyboard input in buffer
def kbInput():
	try:
		dr,dw,de = select.select([sys.stdin], [], [], 0.00001)
		return dr != []
	except:
		return msvcrt.kbhit()


# waits for any keyboard input
def waitKbInput(text=""):
	# just pass if in test mode
	if game.mode == 1:
		return True
	flushInput()
	game.print(text)
	if os.name == 'nt':  # For Windows
		import msvcrt
		msvcrt.getch()
	else:  # For Unix-based systems
		import termios
		import tty
		fd = sys.stdin.fileno()
		old_settings = termios.tcgetattr(fd)
		try:
			tty.setraw(fd)
			sys.stdin.read(1)  # Wait for a single keypress
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# prints a timed ellipsis, used for dramatic transitions
def ellipsis(n):
	for i in range(n):
		sleep(1)
		print(".")


# prints a list of strings, l, into n columns of width w characters
# if an element is longer than one column, it takes up as many columns as needed
def columnPrint(l,n,w,printf=None):
	if printf is None:
		printf = game.print
	# k is the number of characters that have been printed in the current row
	k = 0
	# for each string element in l
	for term in l:
		# if the string is longer than remaining row width; print on a new row
		if len(term) >= (n*w) - k:
			printf("\n" + term, end="")
			k = len(term)
		# if the string is short enough, print it, increment k
		else:
			printf(term, end="")
			k += len(term)
		# to preserve column alignment, print spaces until k is divisble by w
		spaces = w - (k % w)
		printf(spaces * ' ', end="")
		k += spaces
	printf()


# capitalizes the first letter of all the words in a string
# if c is given, then only capitalize the first c words
def capWords(string,c=-1):
	listString = string.split(' ')
	cappedString = ''
	for idx,word in enumerate(listString):
		if len(word) > 0:
			if c != -1 and idx < c:
				cappedString += word[0].upper() + word[1:] + ' '
			else:
				cappedString += word + ' '
	# removes trailing space character
	return cappedString[0:-1]


# returns the ordinal string for a number n
def ordinal(n):
	lastDigit = n % 10
	if lastDigit == 1: suffix = "st"
	elif lastDigit == 2: suffix = "nd"
	elif lastDigit == 3: suffix = "rd"
	else: suffix = "th"
	return str(n) + suffix


def ambiguateDirections(text):
	text = text.replace("north","???")
	text = text.replace("east","???")
	text = text.replace("south","???")
	text = text.replace("west","???")
	return text


# returns an abbreviated direction into an expanded one
# for example, converts 'nw' -> 'northwest' or 'u' -> 'up'
def expandDir(term):
	if term in Data.directions:
		return Data.directions[term]
	else:
		return term


# returns a list of element names for L, a list of objects with name attribute
def namesList(L):
	names = []
	for elem in L:
		if hasattr(elem,"descname"):
			names.append(elem.descname)
		else:
			names.append(elem.name)
	return names


def bagObjects(objects):
	bag = []
	for obj in objects:
		for entry in bag:
			if entry[0].name == obj.name:
				entry[1] += 1
				break
		else:
			bag.append([obj,1])
	return bag


# takes a list of objects. Defines names as a bagged list of object names
# returns a string that grammatically lists all strings in names
def listObjects(objects):
	objBag = bagObjects(objects)
	liststring = ""
	l = len(objBag)
	for i, (obj, count) in enumerate(objBag):
		if i == l-1:
			liststring += obj.stringName(n=count)
		elif i == l-2:
			liststring += obj.stringName(n=count) + " and "
		else:
			liststring += obj.stringName(n=count) + ", "
	return liststring


# used on room area conditions to extract the info of the condition it causses
def extractConditionInfo(roomCondition):
	if not roomCondition.startswith("AREA"):
		raise Exception("Extracting condition info from invalid area condition")
	condInfo = roomCondition.split(" ")
	name = ' '.join(condInfo[1:-1])
	dur = int(condInfo[-1])
	return [name,dur]


# prints a question, gets a yes or no, returns True or False respectively
def yesno(question,printf=None,inputf=None):
	if printf is None:
		printf = game.print
	if inputf is None:
		inputf = game.input
	while True:
		command = inputf(question + "\n> ").lower()
		if command in Data.yesses:
			return True
		elif command in Data.noes:
			return False
		printf("Enter yes or no")


# rolls n dice of range d, adds a modifier m, returns number
def diceRoll(n,d,m=0):
	x = 0
	for _ in range(n):
		x += randint(1,d)
	x += m
	return x


# returns a number, n, with a lower bound of m
def minm(m,n): return m if n < m else n


# returns a number, n, with a lower bound of 0
def min0(n): return 0 if n < 0 else n


# returns a number, n, with a lower bound of 1
def min1(n): return 1 if n < 1 else n


# returns a number, n, with an upper bound of m
def maxm(m,n): return m if n > m else n



# the room, creatures, and some items can contain items within themselves
# thus all objects within a room can be thought of as a tree
# where each node is an item or creature, and the root is the room
# the player object can also be thought of this way where the player is the root
# this function recursively queries the tree of objects for an object
# whose name matches the given term, (not case sensitive)
# the object tree might look as follows:

#           _____Room_____
#         /    /     \     \
#     cat  trunk   sword  wizard
#    /     /   \         /   |   \
# key   jar  candle  potion wand scroll
#        |
#     saffron

# d is the 'degree' of the query; how thorough it is'
# if d is 3: queries through all objects from the root
# elif d is 2: queries through all objects which are not locked
# elif d is 1: queries through objects which are not locked and not in
# creature inventories; i.e. objects which are "accessible" to the player
# if d is 0: queries through items which are not "closed" and not in
# creature inventories; i.e. objects which are "visible" to the player

# this function is a wrapper for objQueryRecur()
def objQuery(root,key=lambda obj:True,d=0):
	matches = objQueryRecur(root,[],key,d)
	return matches


def objQueryRecur(node,matches,key,d):
	# if node is terminal: return
	if not hasMethod(node, 'contents'):
		return matches

	for obj in node.contents():
		# check if obj is a match
		if key(obj): matches.append(obj)
		# depending on the degree, may skip closed, locked, or creature objects
		if d == 0 and hasattr(obj,"open") and not obj.open: continue
		elif (d <= 1) and isinstance(obj,Creature): continue
		elif d <= 2 and hasattr(obj,"locked") and obj.locked: continue
		# recur the query on each object's subtree
		matches = objQueryRecur(obj,matches,key,d)
	return matches


# iterates through each object in the object tree of each room and assigns...
# its 'parent' attribute to the object it is contained in
def assignParents():
	for room in world.values():
		assignParentsRecur(room)
	player.parent = game.currentroom
	assignParentsRecur(player)


# helper function for assignParents()
# iterates through objects within the root and assigns root as their parent
# recurs for each object
def assignParentsRecur(parent):
	if not hasMethod(parent,'contents'):
		return
	for obj in parent.contents():
		obj.parent = parent
		assignParentsRecur(obj)


# takes a dict of room names and room objects,
# removes any room connection values which don't exist in the world
# this is in case the world file which was read as a JSON had invalid names...
# to prevent errors if the world file was written incorrectly
def ensureWorldIntegrity():
	namesToDelete = []
	for room in world.values():
		for direction in room.exits:
			connection = room.exits[direction]
			if connection not in world:
				namesToDelete.append(connection)

		for passage in room.getPassages():
			connectionsToDelete = []
			for connection in passage.connections:
				roomname = passage.connections[connection]
				if roomname not in world:
					connectionsToDelete.append(connection)

			for connection in connectionsToDelete:
				del passage.connections[connection]

		for creature in objQuery(room, d=3, key=lambda x: isinstance(x,Person)):
			creature.dlogtree.ensureIntegrity(creature,player,game,world)

	# this is done in a separate loop to prevent errors caused by...
	# deleting elements from dict while iterating over the dict
	for name in namesToDelete:
		del world[name]



######################
## DIALOGUE CLASSES ##
######################


# in order for characters to produce unique and variable dialogue with minimal repetition
# and apparent intelligence, the dialogue is stored as a directed tree

# in addition to having children, each node in the tree may have a few important parameters;
# a node may contain either a remark or a list of 'trites' from which to generate dialogue
# - a remark is a simple line of output dialogue. A trite is the name of a 'triteset'
# - tritesets are sets of predetermined remarks, which can be sampled by many characters
# the node may also contain either a 'cases' list or a 'responses' list
# - cases is a list of boolean expressions which can reference the character, player, game, or world objects
# - instead of a boolean expression, a case may be an integer, representing a random probability
# - responses is a list of potential dialogue responses that the user may choose during the dialogue
# the child that is visited next can depend on the value of the corresponding case or the user-selected response

# there are four branches from the root; surprise, quest, colloquy, and chatter
# the tree will try to traverse each branch in order until one produces dialogue output
# 1. surprise is for dialogue which a character would prioritize before any other possibilities
# 2. quest is for dialogue which indicates tasks for the player
# 3. colloquy is for dialogue that is meant to give the character depth or individuality
# 4. chatter is for when all other dialogue is exhausted, it is randomly sampled from specified tritesets 

# a few additional features of dialogue trees:
# to give the characters the appearance of short term memory, the tree maintains its state until a new 'parley'
# a new parley occurs after a set period of time since the previous dialogue
# it can store a node 'checkpoint' in case the user leaves and reenters the dialogue
# nodes may have a 'visitLimit', to ensure dialogue is not repeated in one parley
# nodes may have a 'rapportReq' which requires the character has a certain 'rapport' value to be visited
# the characters's rapport value is incremented as the user engages in more dialogue
# rapport is meant to give the dialogue a progression throughout the game
# reaching certain nodes can modify the character's love and fear for the player


class DialogueNode():
	def __init__(self,parent,root,nVisits=0,visitLimit=None,rapportReq=None,isCheckpoint=False,loveMod=0,fearMod=0,repMod=0,remark=None,trites=[],cases=[],responses=[],children=[]):
		self.parent = parent
		self.root = root
		self.nVisits = nVisits
		self.visitLimit = visitLimit
		self.rapportReq = rapportReq
		self.isCheckpoint = isCheckpoint
		self.loveMod=loveMod
		self.fearMod=fearMod
		self.repMod=repMod
		self.remark = remark
		self.children = [DialogueNode(self,root,**child_json) for child_json in children]

		# these are names of sets of strings in Data.py, representing 'canned' dialogue
		self.trites = trites
		if type(self.trites) != list:
			self.trites = [trites]
		# these are strings of python code which should evaluate to a bool or int
		self.cases = cases
		# these are the optional Player responses to the dialogue
		self.responses = responses

		# cases or responses correspond to child nodes and are used to determine where to visit next
		# ensure the number of child nodes matches the cases or responses
		if self.cases:
			if type(self.cases) != list:
				self.cases = [self.cases]
			# one extra child for when all cases are false
			assert len(self.children) == len(self.cases) + 1
		elif self.responses:
			if type(self.responses) != list:
				self.responses = [self.responses]
			assert len(self.children) == len(self.responses)

		# ensure node doesn't have both a remark and a trite set
		assert self.remark is None or self.trites == []
		# ensure node doesn't have both conditional cases and response cases
		assert self.cases == [] or self.responses == []
		
		if hasattr(self.parent, 'responses'):
			assert self.visitLimit == None and self.rapportReq == None, 'child of response node must not have visitLimit or rapportReq'


	### File I/O ###

	def convertToJSON(self):
		del self.id
		return self.__dict__.copy()
	

	@classmethod
	def convertFromJSON(cls,d):
		game.print('converting...')
		game.print(d)
		return cls(**d)


	# ID is the same thing as the 'path' through the tree
	# which is a list of indices, specifying which child to go to from each parent
	def getID(self):
		for idx, child in enumerate(self.parent.children):
			if self is child:
				return self.parent.id + [idx]
		else:
			raise Exception("node not found in parent's children")


	# ensures the following:
	# that the tree is structurally valid by determining the ID
	# that all cases (which are stored in JSON as strings) ints or evaluate to a bool
	# that all trites (which are stored in JSON as strings) are valid sets in Data.py
	# note that speaker, player, game, and world are provided to ensure eval() is valid
	def ensureIntegrity(self,speaker,player,game,world):
		self.id = self.getID()
		for case in self.cases:
			try:
				assert type(case) == int or type(eval(case)) == bool
			except Exception as e:
				raise Exception(f"Invalid case node condition in {speaker.name}'s node {self.id}: {case}, {e}")
		for trite in self.trites:
			assert type(getattr(Data,trite)) is set
		for child in self.children:
			child.ensureIntegrity(speaker,player,game,world)


	### Operation ###

	# set all visit counts back to 0 
	def newParley(self):
		self.nVisits = 0
		for child in self.children:
			child.newParley()


	# try to visit the child with the first true case
	# cases can be numbers, representing a probability of visiting that child
	# if all are false, visit the last child (like an 'else')
	# note that speaker, player, game, and world are provided to ensure eval() is valid
	def conditionalHop(self,speaker,player,game,world):
		for i, case in enumerate(self.cases):
			nextNode = self.children[i]

			# cases can either be boolean cases or integers representing probability
			if type(case) is int and diceRoll(1,100) <= case:
				if nextNode.hop(speaker):
					return nextNode

			elif type(case) is str and eval(case) is True:
				if nextNode.hop(speaker):
					return nextNode

		else:
			nextNode = self.children[-1]
			if nextNode.hop(speaker):
				return nextNode
		
		return None
	

	# try to visit the child corresponding to the user-chosen dialogue response
	# users can end the dialogue by inputting a cancel command
	def responseHop(self,speaker):
		for i, response in enumerate(self.responses):
			game.print(f'{i+1}. {response}\n')

		while True:
			choice = input("\n> ").lower()
			if choice == "":
				continue
			if choice in Data.cancels: 
				return None

			try:
				# note that this does *not* hop(); it ignores child's visitLimit and rapportReq
				return self.children[int(choice)-1]
			except:
				game.print('That is not one of the options. Input a number or type "cancel"')
				continue


	def hop(self,speaker):
		if self.visitLimit and self.nVisits >= self.visitLimit:
			return False
		if self.rapportReq != None:
			if speaker.rapport != self.rapportReq:
				return False
		return True


	# attempt to branch down the tree, visiting this node
	# printing a dialogue remark if the node has one, and visiting a child node
	def visit(self,speaker,player,game,world):		
		# output this node's remark
		if self.isCheckpoint:
			self.root.checkpoint = self.id
		if self.remark:
			waitKbInput(f'"{self.remark}"')
		elif self.trites:
			tritepool = set()
			for trite in self.trites:
				tritepool |= getattr(Data,trite)
			triteRemark = sample(tritepool,1)[0]
			waitKbInput(f'"{triteRemark}"')

		# return next node if this node has children
		nextNode = None
		if self.cases:
			nextNode = self.conditionalHop(speaker,player,game,world)
		elif self.responses:
			nextNode = self.responseHop(speaker)
		else:
			for child in self.children:
				if child.hop(speaker):
					nextNode = child
					break
		if nextNode == None:
			return None

		# count this node as successfully visited
		self.nVisits += 1
		if self.rapportReq != None:
			speaker.rapport += 1
		
		# reaching a node can change the speaker's love or fear for the player
		speaker.love += self.loveMod
		speaker.fear += self.fearMod
		
		# or the player's reputation
		player.updateReputation(self.repMod)

		# unmark checkpoint if this node was succesfully visited
		if nextNode and self.root.checkpoint == self.id:
			self.root.checkpoint = None
		return nextNode


	### Getters ###

	# ensures that at least one path in the tree will provide dialogue in all cases
	def hasUnconditionalDialogue(self):
		if self.remark or self.trites:
			return True
		if self.cases:
			if self.children[-1].hasUnconditionalDialogue():
				return True
			return False
		for child in self.children:
			if child.hasUnconditionalDialogue():
				return True
		return False



class DialogueTree():
	def __init__(self,tree_json):
		self.surprise = DialogueNode(self,self,**tree_json['surprise'])
		self.quest = DialogueNode(self,self,**tree_json['quest'])
		self.colloquy = DialogueNode(self,self,**tree_json['colloquy'])
		self.chatter = DialogueNode(self,self,**tree_json['chatter'])
		self.checkpoint = tree_json.get('checkpoint',None)
		self.id = []
		self.children = [self.surprise, self.quest, self.colloquy, self.chatter]


	### File I/O ###

	def convertToJSON(self):
		del self.id
		del self.children
		return self.__dict__.copy()
	

	@classmethod
	def convertFromJSON(cls,d):
		return cls(**d)


	# ensures the following;
	# that the tree is structurally valid (parents are assigned to children)
	# that the checkpoint, if there is one, is a valid node
	# that at least one path of the tree will yield dialogue in all cases
	def ensureIntegrity(self,speaker,player,game,world):
		for child in self.children:
			child.ensureIntegrity(speaker,player,game,world)
		if self.checkpoint:
			try:
				self.findNode(self.checkpoint)
			except:
				raise Exception(f"Checkpoint {self.checkpoint} not found in {speaker.name}'s dialogue tree")
		if not self.chatter.hasUnconditionalDialogue():
			raise Exception("Dialogue Tree has no unconditional dialogue")


	### Operation ###

	# visit the branch, return True if navigating any branch resulted in speaker dialogue
	def visitBranch(self,node,speaker,player,game,world):
		had_dialogue = False
		while node:
			if node.remark or node.trites:
				had_dialogue = True
			node = node.visit(speaker,player,game,world)
		return had_dialogue


	# attempt to visit each branch of the tree until one yields dialogue
	# after the surprise branch, start at the dialogue checkpoint if there is one
	# returns True if any branch successfully yielded dialogue. Visiting 'chatter' should always succeed
	def visit(self,speaker,player,game,world):
		if self.surprise.hop(speaker):
			if self.visitBranch(self.surprise,speaker,player,game,world):
				return True

		if self.checkpoint:
			checkpointNode = self.findNode(self.checkpoint)
			if checkpointNode.hop(speaker):
				if self.visitBranch(checkpointNode,speaker,player,game,world):
					return True

		for branch in self.quest,self.colloquy,self.chatter:
			if branch.hop(speaker):
				if self.visitBranch(branch,speaker,player,game,world):
					return True

		return False


	# uses a nodeId (the path to the node using child indices) to retrieve node
	def findNode(self,nodeId):
		node = self
		for idx in nodeId:
			node = node.children[idx]
		return node


	# resets all nodes for new parley
	def newParley(self):
		self.checkpoint = None
		for node in self.children:
			node.newParley()




############################
## SUPERCLASS DEFINITIONS ##
############################


# Empty is a class usually used as a placeholder for items. It serves to act as a dummy item which has mostly null values
class EmptyGear():
	def __init__(self):
		self.name = "[empty]"
		self.aliases = []
		self.weight = 0
		self.prot = 0
		self.might = 1
		self.sleight = 0
		self.sharpness = 0
		self.type = "e"



	### Dunder Methods ###

	def __repr__(self):
		return f"<empty>"


	def __str__(self):
		return "{}".format(self.name)


	def __eq__(self, other):
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False



	### Getters ###

	def stringName(self,det=True,definite=False,n=1,plural=False,cap=False,c=1):
		return ""


	def Weight(self):
		return 0


	def improviseWeapon(self):
		return self



# The Game class stores a series of global data about the game that is not...
# contained in the global world dict, W, including things like the time,...
# a pointer to the current room and previous room, and a pointer to the...
# Creature who is currently taking a turn.
# It also offers a series of methods for identifying the currently rendered...
# rooms and finding information about them.
class Game():
	def __init__(self,mode,currentroom,prevroom,time,events):
		# 0 for normal mode, 1 for testing mode, 2 for god mode
		self.mode = mode
		# the room that the player is currently in
		self.currentroom = currentroom
		# the room that the player was in last
		self.prevroom = prevroom
		# the number of game loops that have elapsed since the game's start
		self.time = time
		# set of important events that have transpired in the game's progression
		self.events = events
		# used to break out of the main input loop when the player wants to quit
		self.quit = False
		# used for determining whether or not to print certain things
		# usually, silent is True when events happen outside the current room
		self.silent = False
		# the creature who is currently acting
		self.whoseturn = None
		# stores the last command before processing. Used for cheatcode input
		self.lastRawCommand = None
		# these pronoun attributes will point to an object which the user may...
		# implicitly refer to with the given pronoun in their user input
		# for instance, if the user inputs "attack him", or "take it"
		self.it = None
		self.they = None
		self.he = None
		self.she = None

		# 23 minutes in an hour
		self.hourlength = 23
		self.daylength = len(Data.hours) * self.hourlength
		# 14 days in a month
		self.monthlength = 14 * self.daylength



	### Operation ###

	# exits the previous room and enters the new room
	def changeRoom(self,newroom):
		self.clearPronouns()
		self.prevroom.exit(player)
		self.prevroom = self.currentroom
		self.currentroom = newroom
		player.parent = newroom
		self.currentroom.enter(player)
		return True


	# passes time for each room, and each creature in each room
	# important for decrementing the duration counter on all status conditions
	def passTime(self, t=1):
		prev_hour = self.hour()
		self.time += t
		player.passTime(t)
		for room in self.renderedRooms():
			self.silent = room is not self.currentroom
			room.passTime(t)
		if prev_hour != self.hour():
			self.checkDaytime()
		self.checkAstrology()


	def clearPronouns(self):
		self.it = None
		self.they = None
		self.her = None
		self.him = None


	# sets pronoun attributes based on the type of object
	def setPronouns(self,obj):
		if not isinstance(obj,Person):
			self.it = obj
		if isinstance(obj,Creature):
			self.they = obj
		if hasattr(obj,"gender"):
			if obj.gender == "m":
				self.he = obj
			elif obj.gender == "f":
				self.she = obj


	def reapCreatures(self):
		for room in self.renderedRooms():
			room.reapCreatures()


	# sorts the creatures of each room based on their MVMT() stat
	def sortCreatures(self):
		for room in self.renderedRooms():
			room.sortCreatures()


	def destroyCreature(self,C):
		pass
		### change creature to be a dead creature or something
		# for room in self.renderedRooms():
		# 	if C in room.creatures:
		# 		room.removeCreature(C)


	### Getters ###

	# recursively adds all adjacent rooms to the set of found rooms
	# used by renderedRooms()
	# n is the path length at which the query stops
	# Sroom is the "source" room, or the current node in the query
	def roomFinder(self,n,Sroom,pathlen,foundrooms):
		if pathlen >= n:
			return
		adjacentRooms = [world[name] for name in Sroom.allExits().values()]
		for room in adjacentRooms:
			foundrooms.add(room)
			self.roomFinder(n,room,pathlen+1,foundrooms)


	# returns set of all rooms connected to currentroom with path < REND_DIST
	def renderedRooms(self):
		# constant render distance of rooms in world
		REND_DIST = 3
		# the set of found rooms initially includes only the current room
		R = {self.currentroom}
		# add all rooms within a distance of REND_DIST to R
		self.roomFinder(REND_DIST,self.currentroom,0,R)
		return R


	# gets set of all rendered rooms except the current room
	def nearbyRooms(self):
		R = self.renderedRooms()
		R.remove(self.currentroom)
		return R


	# returns a list of objects in current room which fit a certain condition
	# key is a function which identifies a condition about the obj
	# d is the 'degree' of the query. See objQuery() for details
	def queryRoom(self,room=None,key=lambda x:True,d=3):
		if room == None:
			room = self.currentroom
		return objQuery(room,key=key,d=d)


	# returns a list of objects in rendered rooms which fit a certain condition
	def queryRooms(self,key=lambda x:True,d=3):
		matchingObjects = []
		for room in self.renderedRooms():
			matchingObjects += self.queryRoom(room,key=key,d=d)
		return matchingObjects


	# returns a set of all objects in the rendered world
	# does not include the player or anything in player inv
	def getAllObjects(self):
		allObjects = []
		for room in self.renderedRooms():
			allObjects += objQuery(room,key=lambda x:True,d=3)
		return allObjects


	def nameQueryRoom(self,term,d=3,room=None):
		term = term.lower()
		key = lambda obj: nameMatch(term,obj)
		return self.queryRoom(room=room,key=key,d=d)


	# True if there's an object in rendered rooms whose name matches objname
	# not case sensitive
	def inWorld(self,term):
		key = lambda obj: nameMatch(term,obj)
		objects = self.queryRooms(key)
		return len(objects) > 0


	def hour(self):
		return Data.hours[(self.time % self.daylength) // self.hourlength]


	def checkMoon(self):
		mooncycle = (self.time % self.monthlength) // self.daylength
		if mooncycle() == 0:
			self.print("It is a new moon.")
			self.events.add("new moon")
		elif mooncycle() == 7:
			self.print("It is a full moon.")
			self.events.add("full moon")
		else:
			self.events.remove("new moon")
			self.events.remove("full moon")


	def checkAstrology(self, startUp=False):
		darkhours = ("cat","mouse","owl","serpent","wolf")
		aurora_cycle = self.time % 2000
		if aurora_cycle >= 0 and aurora_cycle < 100 and self.hour() in darkhours:
			if "aurora" not in self.events or startUp:
				self.print("There is an aurora in the sky!")			
			self.events.add("aurora")
		elif "aurora" in self.events:
			self.events.remove("aurora")
			self.print("The aurora is over.")

		meteor_cycle = self.time % 3500
		if meteor_cycle >= 0 and meteor_cycle < 300 and self.hour() in darkhours:
			if "meteor shower" not in self.events or startUp:
				self.print("There is a meteor shower in the sky!")
			self.events.add("meteor shower")
		elif "meteor shower" in self.events:
			self.events.remove("meteor shower")
			self.print("The meteor shower is over.")

		lighthours = ("rooster","juniper","bell","sword","willow","lily")
		eclipse_cycle = (self.time % (self.monthlength*3+100))
		if eclipse_cycle > 0 and eclipse_cycle < 30 and self.hour() in lighthours:
			if "eclipse" not in self.events or startUp:
				self.print("There is a solar eclipse in the sky!")
			self.events.add("eclipse")
		elif "eclipse" in self.events:
			self.events.remove("eclipse")
			self.print("The solar eclipse is over.")



	### User Output ###
	
	def input(self,text="",lower=True):
		self.print(text,end='')
		flushInput()
		if not lower:
			return input()
		return input().lower()


	def print(self,*args,end="\n",sep='',delay=0.005):
		if self.silent:
			return
		if self.mode == 1:
			return print(*args,end=end,sep=sep)
		if len(args) > 1:
			sep=' '
		for arg in args:
			for char in str(arg):
				if kbInput():
					delay = 0
				sys.stdout.write(char)
				sys.stdout.flush()
				sleep(delay)
			sys.stdout.write(sep)
			sys.stdout.flush()
		sys.stdout.write(end)
		

	def startUp(self):
		player.printStats()
		game.print()
		self.currentroom.describe()
		game.checkDaytime()
		game.checkAstrology(startUp=True)


	def describeRoom(self):
		self.currentroom.describe()


	def checkDaytime(self):
		if self.hour() in ('stag','rooster','juniper'):
			self.print('It is morning.')
		if self.hour() in ('bell','sword','willow','lily'):
			self.print('It is day.')
		if self.hour() in ('hearth','cat','mouse'):
			self.print('It is evening.')
		if self.hour() in ('owl','serpent','wolf'):
			self.print('It is night.')
			self.checkMoon()



# The Room class is the fundamental unit of the game's world.
# The world dict, consists of key:value pairs of the form,
# room name:room object

# Importantly, each room contains an exits dict, whose keys are directions...
# such as 'north', 'up', or 'beyond', and whose values are the string names...
# of the room that it leads to.

# Thus, from any room, there are some directions which will yield a room name, # which can be plugged into the world dict to yield the neighboring room object

# In this way, every Room object can be thought of like a node in a large...
# directed graph, facilitated by the world dict, where the exits dict specifies
# the edges from a given node to its neighboring nodes.
class Room():
	def __init__(self,name,domain,desc,exits,fixtures,items,creatures,status=[]):
		self.name = name
		self.domain = domain
		self.desc = desc
		self.exits = exits
		self.fixtures = fixtures
		self.items = items
		self.creatures = creatures
		self.status = status


	### Dunder Methods ###

	def __repr__(self):
		return f"Room({self.name}, {self.desc}, {self.exits}...)"


	def __str__(self):
		return f"#{self.name}"



	### Operation ###

	# add one-way connection to a neighboring Room
	# to ensure a bidirectional connectiom between Rooms...
	# this method would have to be called once on each room.
	def addConnection(self,dir,loc):
		self.exits[dir] = loc


	def addItem(self,I):
		# ensure only one bunch of Gold exists here
		if isinstance(I,Serpens):
			for item in self.items:
				if isinstance(item,Serpens):
					item.merge(I)
					return
		insort(self.items,I)
		I.parent = self


	def removeItem(self,I):
		if I in self.items:
			self.items.remove(I)


	def addCreature(self,C):
		insort(self.creatures,C)
		C.parent = self


	def removeCreature(self,C):
		if C in self.creatures:
			self.creatures.remove(C)


	# sort all Creatures occupying the room by their MVMT() value, descending
	def sortCreatures(self):
		self.creatures.sort(key=lambda x: x.MVMT(), reverse=True)


	# remove all dead creatures from creatures list
	def reapCreatures(self):
		reapable = lambda creature: creature.timeOfDeath is not None and \
		(game.time - creature.timeOfDeath) > 100 and \
		self is not game.currentroom() and \
		player not in creature.ancestors()

		self.creatures = [creature for creature in self.creatures if not reapable(creature)]


	def addFixture(self,F):
		insort(self.fixtures,F)
		F.parent = self


	def removeFixture(self,F):
		if F in self.fixtures:
			self.fixtures.remove(F)


	def addAreaCondition(areacond):
		cond,dur = extractConditionInfo(areacond)
		key = lambda x: isinstance(x,Creature)
		for creature in game.queryRoom(key=key):
			creature.addCondition(cond,dur)


	def removeAreaCondition(areacond):
		cond,dur = extractConditionInfo(areacond)
		# depending on how you want room conditions to work, perhaps remove this
		if dur != -1:
			return
		key = lambda x: isinstance(x,Creature)
		for creature in game.queryRoom(key=key):
			creature.removeCondition(cond,-1)


	# add a status condition to the room with a name and duration
	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		pair = [name,dur]
		insort(self.status,pair)
		if name.startswith("AREA"):
			self.addAreaCondition(name)
		return True


	# removes all conditions of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					self.status.remove([condname,duration])
					if condname.startswith("AREA"):
						self.removeAreaCondition(condname)


	# decrements the duration for each status condition applied to the room by t
	# removes status conditions whose duration is lowered past 0
	def passTime(self,t):
		for i, condition in self.status:
			# if condition is has a special duration, ignore it
			if condition[1] < 0:
				continue
			# subtract remaining duration on condition
			elif condition[1] > 0:
				condition[1] = min0(condition[1]-t)
		# remove all condition with 0 duration
		self.status = [(cond,dur) for cond,dur in self.status if dur != 0]

		for obj in self.contents():
			obj.passTime(t)


	# describe the room, and apply any room effects to the creature entering
	def enter(self,creature):
		# if the player is entering the room, describe the room
		if creature is player:
			self.describe()
		condsToRemove = [pair for pair in creature.status if pair[1] == -1]
		# remove status conditions from previous room
		for cond,dur in condsToRemove:
			creature.removeCondition(cond,-1)
		# add status conditions from this room
		for cond,dur in self.status:
			if cond.startswith("AREA"):
				[name,dur] = extractConditionInfo(cond)
				creature.addCondition(name,dur)


	# remove any room effects from the creature exiting
	def exit(self,creature):
		pass


	### Getters ###

	# returns dict of exits, where keys are directions and values are room names
	def allExits(self):
		all = {}
		for dir in self.exits:
			all[dir] = self.exits[dir]
		# get a list of passages in the room
		passages = self.getPassages()
		# for each passage, add its connections to all
		for passage in passages:
			for dir in passage.connections:
				all[dir] = passage.connections[dir]
		return all


	def itemNames(self):
		return [item.name for item in self.items]


	# returns a list of Passage objects within the room's items
	def getPassages(self):
		return [item for item in self.contents() if isinstance(item,Passage)]


	def creatureNames(self):
		return [creature.name for creature in self.creatures]


	def contents(self):
		return self.fixtures + self.items + self.creatures


	# given a direction (like 'north' or 'down)...
	# return the first Passage object with that direction in its connections
	def getPassageFromDir(self,dir):
		for passage in self.getPassages():
			if dir in passage.connections:
				return passage
		return None


	# if the given room object, dest, is in one of the rooms exits, then find the direction it is in from the room.
	def getDirFromDest(self,dest):
		if dest in self.allExits().values():
			idx = list(self.allExits().values()).index(dest)
			dir = list(self.allExits().keys())[idx]
			return dir


	# returns True if the room has a status condition with given name.
	# if reqDuration is given, only returns True if duration matches reqDur
	def hasCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					return True
		return False


	def listableItems(self):
		# don't list fixtures which are not 'mentioned'
		condition = lambda x: not (isinstance(x,Fixture) and not x.mention)
		objects = list(filter(condition,self.items))
		return objects



	### User Output ###

	# prints room name, description, all its items and creatures
	def describe(self):
		game.print("\n" + self.domain)
		game.print(self.name)
		# if player.countCompasses() == 0:
		# 	game.print("\n" + ambiguateDirections(self.desc))
		# else:
		game.print("\n" + self.desc)
		self.describeItems()
		self.describeCreatures()


	# prints all the items of the room in sentence form
	def describeItems(self):
		items = self.listableItems()
		if len(items) != 0:
			game.print(f"There is {listObjects(self.listableItems())}.")
		if len(items) == 1:
			game.setPronouns(items[0])


	# prints all the creatures in the room in sentence form
	def describeCreatures(self):
		if len(self.creatures) != 0:
			game.print(f"There is {listObjects(self.creatures)}.")
		for creature in self.creatures:
			game.setPronouns(creature)



# The Item class is the main game object class of things that cannot act
# Anything in a Room that is not a Creature will be an Item
# All items come with a name, description, weight, and durability
class Item():
	def __init__(self,name,desc,weight,durability,status=[],aliases=[],plural=None):
		self.name = name
		self.desc = desc
		self.weight = weight
		self.durability = durability
		self.status = status
		self.aliases = aliases
		if plural is None:
			self.plural = self.name + 's'
		else:
			self.plural = plural
		self.parent = None



	### Dunder Methods ###

	def __repr__(self):
		return f"Item({self.name}, {self.desc}, {self.weight}, {self.durability})"


	def __str__(self):
		return f"${self.name}"


	def __lt__(self,other):
		return self.name.lower() < other.name.lower()


	def __eq__(self,other) :
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False


	def __hash__(self):
		return hash(frozenset(self.__dict__)) * hash(id(self))



	### Operation ###

	def passTime(self,t):
		for condition in self.status:
			# if condition is has a special duration, ignore it
			if condition[1] < 0:
				continue
			# subtract remaining duration on condition
			elif condition[1] > 0:
				condition[1] -= t
			# if, after subtraction, condition is non-positive, remove it
			if condition[1] <= 0:
				self.removeCondition(condition[0],0)


	def Obtain(self,creature):
		pass


	def Break(self):
		if self.durability == -1:
			if not game.silent:
				game.print(f"The {self.name} cannot be broken.")
			return False
		game.print(f"The {self.name} breaks.")
		self.parent.removeItem(self)
		return True


	def takeDamage(self,dmg):
		if dmg > self.durability:
			return self.Break()


	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		pair = [name,dur]
		insort(self.status,pair)
		return True


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					self.status.remove([condname,duration])



	### Getters ###

	def Weight(self):
		return self.weight


	def ancestors(self):
		ancs = []
		ancestor = self.parent
		ancs.append(ancestor)
		while not isinstance(ancestor,Room):
			ancestor = ancestor.parent
			ancs.append(ancestor)
		return ancs


	def room(self):
		return self.ancestors()[-1]


	# Used to create a generic Weapon() if this item is used to attack something
	def improviseWeapon(self):
		#TODO: if item is too large/heavy, make it two-handed
		return Weapon(self.name,self.desc,self.weight,self.durability,min1(self.weight//4),0,0,0,"b")


	### User Output ###

	def describe(self):
		game.print(f"It's {self.stringName()}.")
		game.print(f"{self.desc}.")


	def stringName(self,det=True,definite=False,n=1,plural=False,cap=False,c=1):
		strname = getattr(self,"descname",self.name)
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		if det:
			if definite:
				strname = "the " + strname
			elif not plural:
				if strname[0] in Data.vowels:
					strname = "an " + strname
				else:
					strname = "a " + strname
		if cap:
			strname = capWords(strname,c=c)
		return strname




# The Creature class is the main class for anything in the game that can act
# Anything in a Room that is not an Item will be a Creature
# The player is a Creature too
# Creatures have 10 base stats, called traits
# They also have abilities; stats which are derived from traits through formulas
class Creature():
	def __init__(self,name,desc,weight,traits,hp,mp,money,inv,gear,plural=None,carrying=None,carrier=None,riding=None,rider=None,status=[],aliases=[],descname=None,timeOfDeath=None,alert=False,seesPlayer=False,sawPlayer=-1):
		self.name = name
		if descname is None:
			self.descname = name
		self.desc = desc
		self.aliases = aliases
		if plural is None:
			self.plural = self.name + 's'
		else:
			self.plural = plural
		self.weight = weight

		self.STR = traits[0]
		self.SPD = traits[1]
		self.SKL = traits[2]
		self.STM = traits[3]
		self.CON = traits[4]
		self.CHA = traits[5]
		self.INT = traits[6]
		self.WIS = traits[7]
		self.FTH = traits[8]
		self.LCK = traits[9]

		self.status = status
		# sort status effects by duration; change '1' to '0' to sort by name
		self.status.sort(key=lambda x: x[1])

		self.hp = hp
		self.mp = mp
		self.money = money
		self.inv = inv

		# convert gear from its stored form in files to its runtime form
		self.gear = {key: inv[idx] if idx != None else EmptyGear() for key, idx in gear.items()}
		self.riding = riding
		self.rider = rider
		self.carrying = carrying
		self.carrier = carrier

		self.parent = None

		self.weapon = EmptyGear()
		self.weapon2 = EmptyGear()
		self.shield = EmptyGear()
		self.shield2 = EmptyGear()

		# these attributes remain unused in the Player subclass
		self.timeOfDeath = timeOfDeath
		self.alert = alert
		self.seesPlayer = seesPlayer
		self.sawPlayer = sawPlayer



	### Dunder Methods ###

	def __repr__(self):
		traits = [self.STR, self.SPD, self.SKL, self.STM, self.CON, self.CHA, self.INT, self.WIS, self.FTH, self.LCK]
		return f"Creature({self.name}, {self.desc}, {self.hp}, {self.mp}, {traits}, {self.money} ...)"


	def __str__(self):
		return f"!{self.name}"


	def __eq__(self, other) :
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False


	def __hash__(self):
		return hash(frozenset(self.__dict__)) * hash(id(self))


	def __lt__(self,other):
		if isinstance(other, Creature):
			return self.MVMT() < other.MVMT()
		return self.name.lower() < other.name.lower()



	### File I/O ###

	# converts the gear dict to a form more easily writable to a save file
	# replaces all objects in gear.values() with an integer which represents...
	# the index of the equipped object in the creature's inventory
	# if the gear slot is empty, replaces it with -1
	def compressGear(self):
		return {key: (self.inv.index(item) if item != EmptyGear() else None) for key, item in self.gear.items()}


	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		# convert the gear dict to a form more easily writable in a JSON object
		compressedGear = self.compressGear()
		d = self.__dict__.copy()
		dictkeys = list(d.keys())
		# these attributes do not get stored between saves (except gear)
		for key in dictkeys:
			if key.lower() in Data.traits or key in {"gear","weapon","weapon2","shield","shield2"}:
				del d[key]
		d["gear"] = compressedGear
		# convert traits to a form more easily writable in a JSON object
		d["traits"] = [self.STR,self.SKL,self.SPD,self.STM,self.CON,self.CHA,self.INT,self.WIS,self.FTH,self.LCK]
		# TODO: swap the following lines for Python 3.9
		# d = {"__class__":self.__class__.__name__} | d
		d = {"__class__":self.__class__.__name__, **d}
		return d


	# # returns an instance of this class given a dict from a JSON file
	# @classmethod
	# def convertFromJSON(cls,d):
	# 	return cls(**d)



	### Operation ###

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		if(f"{type} vulnerability" in self.status): dmg *= 2
		if(f"{type} resistance" in self.status): dmg //= 2
		if(f"{type} immunity" in self.status): dmg = 0
		game.print(f"Took {dmg} {Data.dmgtypes[type]} damage")
		#player hp lowered to a minimum of 0
		self.hp = min0(self.hp-dmg)
		if self.hp == 0:
			self.death()


	# adds money
	def updateMoney(self,money):
		self.money += money


	# try to add an Item to Inventory
	# it will fail if the inventory is too heavy
	def addItem(self,I):
		if isinstance(I,Serpens):
			return True
		if self.invWeight() + I.Weight() > self.BRDN() * 2:
			return False
		insort(self.inv,I)
		I.parent = self
		return True


	# remove an Item from Inventory
	# if it was equipped, unequip it
	# if it has a Drop() method, call that
	# check if still hindered
	def removeItem(self,I):
		if I in self.gear.values():
			self.unequip(I)
		self.inv.remove(I)
		if hasMethod(I,"Drop"):
			I.Drop(self)
		if self.invWeight() < self.BRDN():
			self.removeCondition("hindered",-3)


	# takes an item from a source location
	# first checking if it can be added to Inventory
	# if it is added, remove it from source location
	# if it has an Obtain() method, call that
	# finally, check if the new inventory weight has hindered the creature
	def obtainItem(self,I,msg=None):
		oldParent = I.parent
		if self.addItem(I):
			oldParent.removeItem(I)
			if msg != None:
				game.print(msg)
			I.Obtain(self)
			self.checkHindered()
			return True
		return False


	# only used by equip and unequip to reassign several attributes
	# specifically, weapon, weapon2, shield, shield2
	def assignWeaponAndShield(self):
		#if unassigned, attributes are empty, self.weapon is always assigned
		self.weapon2 = EmptyGear()
		self.shield = EmptyGear()
		self.shield2 = EmptyGear()

		# assign weapon and weapon2 based on types of gear in left and right
		if isinstance(self.gear["right"],Weapon) and isinstance(self.gear["left"],Weapon):
			self.weapon2 = self.gear["left"]
		elif isinstance(self.gear["left"],Weapon) and not isinstance(self.gear["right"],Weapon):
			self.weapon = self.gear["left"]
		elif isinstance(self.gear["left"],Item) and self.gear["right"] == EmptyGear():
			self.weapon = self.gear["left"]
		else:
			self.weapon = self.gear["right"]

		# ensure that weapons are of type Weapon
		if not isinstance(self.weapon,Weapon):
			if hasMethod(self.weapon,"improviseWeapon"):
				self.weapon = self.weapon.improviseWeapon()
		if not isinstance(self.weapon2,Weapon):
			if hasMethod(self.weapon,"improviseWeapon"):
				self.weapon2 = self.weapon.improviseWeapon()

		# assign shield and shield2 based on types of gear in left and right
		if isinstance(self.gear["right"],Shield) and isinstance(self.gear["left"],Shield):
			self.shield = self.gear["right"]
			self.shield2 = self.gear["left"]
		elif isinstance(self.gear["right"],Shield):
			self.shield = self.gear["right"]
		elif isinstance(self.gear["left"],Shield):
			self.shield = self.gear["left"]


	# finds the slot in which item resides, sets it to EmptyGear()
	# calls the item's Unequip() method if it has one
	def unequip(self,I,silent=True):
		gearslots = list(self.gear.keys())
		gearitems = list(self.gear.values())
		# finds the slot whose value is I, sets it to empty
		slot = gearslots[gearitems.index(I)]
		self.gear[slot] = EmptyGear()
		self.assignWeaponAndShield()
		if not silent:
			game.print(f"You unequip your {I.name}")
		if hasMethod(I,"Unequip"): I.Unequip()


	# if the item is armor, equip it, otherwise return False
	def equipArmor(self,I,slot=None):
		assert I in self.inv
		if slot == None:
			slot = I.slots[0]
		if slot not in I.slots:
			return False
		if slot not in self.gear.keys():
			return False
		self.gear[slot] = I
		I.Equip()
		return True


	# unequips the lefthanded item, moves righthanded item to left,
	# equips the new item in right hand
	# if the new item is twohanded, set lefthand to EmptyGear()
	# calls the new item's Equip() method if it has one
	def equipInHand(self,I):
		assert I in self.inv
		self.unequip(self.gear["left"])
		self.gear["left"] = self.gear["right"]
		self.gear["right"] = I
		if (hasattr(I,"twohanded") and I.twohanded) or isinstance(I,Creature):
			self.gear["left"] = EmptyGear()
		self.assignWeaponAndShield()
		if hasMethod(I,"Equip"): I.Equip(self)


	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		pair = [name,dur]
		insort(self.status,pair)
		return True


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					self.status.remove([condname,duration])


	def passTime(self,t):
		for condition in self.status:
			# if condition is has a special duration, ignore it
			if condition[1] < 0:
				continue
			# subtract remaining duration on condition
			elif condition[1] > 0:
				condition[1] -= t
			# if, after subtraction, condition is non-positive, remove it
			if condition[1] <= 0:
				self.removeCondition(condition[0],0)


	def checkHindered(self):
		if self.invWeight() > self.BRDN():
			if not self.hasCondition("hindered"):
				self.addCondition("hindered",-3)


	# called when a creature's hp hits 0
	def death(self):
		self.timeOfDeath = game.time
		game.print("\n" + f"{self.stringName(definite=True,cap=True,c=1)} died.")
		self.descname = f"dead {self.descname}"
		n = diceRoll(3,player.LOOT(),-2)
		self.room().addItem(Serpens(n,[]))
		if not game.silent:
			game.print(f"Dropped $ {n}.")
		if game.whoseturn is player:
			# TODO: verify that this is an acceptable formula
			lv = player.level()
			xp = lv * self.level() + diceRoll(lv,player.LCK,player.LCK)
			player.gainxp(xp)



	### Behavior ###
			
	def act(self):
		pass


	def Carry(self,carrier):
		if self.Weight() > carrier.BRDN():
			game.print(f"{self.stringName(definite=True,cap=True)} is too heavy to carry.")
			return False
		if not self.Restrain(carrier):
			return False
		self.carrier = carrier
		return True


	def Restrain(self,restrainer,item=None):
		if not self.isAlive():
			return True
		if not self.isFriendly() and self.canMove():
			if item != None:
				#TODO: add restraining with items? like rope??
				pass
			if self.ATHL() > restrainer.ATHL() or self.EVSN() > restrainer.ATHL():
				game.print(f"You fail to restrain {self.stringName(definite=True)}!")
				return False
		restrainer.addCondition("restraining",-3,silent=True)
		self.addCondition("restrained",-3)
		game.print(f"You restrain {self.stringName(definite=True)}!")
		return True


	def Hide(self,I):
		if 4 * self.SLTH() > I.weight:
			self.addCondition("hiding",-3)
		else:
			pass


	def Ride(self,rider):
		if rider.Weight() > self.BRDN():
			game.print(f"You are too heavy to ride {self.stringName(definite=True)}")
			return False
		if not self.isFriendly() and self.canMove():
			game.print(f"{self.stringName(definite=True,cap=True)} struggles.")
			athl_contest = self.ATHL() - rider.ATHL()
			if athl_contest > 0:
				game.print(f"{self.stringName(definite=True,cap=True)} shakes you off!")
				if athl_contest > rider.ATHL():
					rider.takeDamage(athl_contest-rider.ATHL(),"b")
				return False
		self.rider = rider
		rider.riding = self
		game.print(f"You ride {self.stringName(definite=True)}.")
		return True



	### Getters ###

	# these are creature stats that are determined dynamically with formulas
	# these formulas are difficult to read, check design document for details
	def ACCU(self): return 45 + 2*self.SKL + self.LCK + self.weapon.sleight
	def ATCK(self): return diceRoll(self.STR, self.weapon.might, self.atkmod())
	def ATHL(self): return self.STR + self.SKL + self.STM
	def ATSP(self): return self.SPD - min0(self.handheldWeight()//4 - self.CON)
	def BRDN(self): return self.CON * self.STR * 4 + self.FTH + self.weight
	def CAST(self): return self.WIS + self.FTH + self.INT - min0(self.gearWeight()//4 - self.CON)
	def CRIT(self): return self.SKL + self.LCK + self.weapon.sharpness
	def CSSP(self): return self.WIS - min0(self.invWeight() - self.BRDN()) - min0(self.gearWeight()//4 - self.CON)
	def DCPT(self): return 2*self.CHA + self.INT
	def DFNS(self): return 2*self.CON + self.protection()
	def ENDR(self): return 2*self.STM + self.CON
	def EVSN(self): return 2*self.ATSP() + self.LCK
	def INVS(self): return 2*self.INT + self.WIS
	def KNWL(self): return 2*self.INT + self.LCK
	def LOOT(self): return 2*self.LCK + self.FTH
	def MVMT(self): return self.SPD + self.STM + 10 - min0(self.invWeight() - self.BRDN()) - min0(self.gearWeight()//4 - self.CON)
	def MXHP(self): return self.level()*self.CON + self.STM
	def MXMP(self): return self.level()*self.WIS + self.STM
	def PRSD(self): return 2*self.CHA + self.WIS
	def RSTN(self): return 2*self.FTH + self.STM
	def RITL(self): return 2*self.FTH + self.LCK
	def SLTH(self): return ( 2*self.SKL + self.INT - min0(self.invWeight() - self.BRDN()) ) * 2*int(self.hasCondition("hiding"))
	def SPLS(self): return 3*self.INT
	def TNKR(self): return 2*self.INT + self.SKL


	def Weight(self):
		riderWeight = 0 if self.rider is None else self.rider.Weight()
		return self.weight + self.invWeight() + riderWeight


	def inStatus(self,*args):
		if type(args[0]) == list:
			condnames = args[0]
		else:
			condnames = args
		for condname in condnames:
			for cond, dur in self.status:
				if condname == cond:
					return True


	def contents(self):
		return self.inv


	# wrapper for objQuery()
	# returns player Inventory as a set of all items in the Item Tree
	def invSet(self):
		return objQuery(self,d=2)


	# wrapper for objQuery, sets the degree of the query to 2 by default
	def query(self,key=None,d=2):
		matches = objQuery(self,key=key,d=d)
		return matches


	def nameQuery(self,term,d=2):
		term = term.lower()
		key = lambda obj: nameMatch(term,obj)
		return self.query(key=key,d=d)


	def ancestors(self):
		ancs = []
		ancestor = self.parent
		ancs.append(ancestor)
		while not isinstance(ancestor,Room):
			ancestor = ancestor.parent
			ancs.append(ancestor)
		return ancs


	def room(self):
		return self.ancestors()[-1]


	# TODO: add logic here for conditions which improve atkmod
	def atkmod(self):
		return 0


	def level(self):
		return 1


	def rating(self):
		return self.STR + self.SPD + self.SKL + self.STM + self.CON + self.CHA + self.INT + self.WIS + self.FTH + self.LCK


	# returns sum of the weight of all items in the inventory
	def invWeight(self):
		return sum(item.Weight() for item in self.inv)


	# returns a list of names of all items in player inventory
	def invNames(self):
		return [item.stringName(det=False) if isinstance(item,Creature) else item.name for item in self.inv]


	# just a function wrapper for functions that call itemNames on objects
	def itemNames(self):
		return self.invNames()


	def weapons(self):
		return [I for I in self.inv if isinstance(I,Weapon)]


	# returns sum of the weight of all items in player gear
	def gearWeight(self):
		weight = 0
		for item in self.gear:
			if hasattr(self.gear[item], "weight"):
				weight += self.gear[item].Weight()
		return weight


	# looks through gear for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return None
	def inGear(self,term):
		for slot,object in self.gear.items():
			if nameMatch(term,object) or term.lower() == slot.lower():
				return object
		return None


	# return all items in inv whose name matches term, otherwise return None
	def inInv(self,term):
		return [obj for obj in self.inv if nameMatch(term,obj)]


	# returns sum of all protection values of all items in gear
	def protection(self):
		return sum(item.prot for item in self.gear.values() if hasattr(item, "prot"))


	def hasCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					return True
		return False


	# returns the sum of the weight of all items being held
	def handheldWeight(self):
		return self.weapon.weight + self.weapon2.weight + self.shield.weight + self.shield2.weight


	def isNaked(self):
		return False
		if self.gear['legs'] == EmptyGear() and self.gear['torso'] == EmptyGear():
			return True


	def isHolding(self, term):
		if nameMatch(term, self.gear['left']) or nameMatch(term, self.gear['right']):
			return True


	def isAlive(self):
		return self.timeOfDeath is None


	def isBloodied(self):
		# returns true is creature has less than half health
		pass


	def alliesPresent(self):
		# returns number of allies creature can see
		pass


	def enemiesPresent(self):
		# returns number of enemies creature can see
		pass


	def isFriendly(self):
		return self.inStatus("tamed")


	def canMove(self):
		conditions = ("restrained","paralyzed","frozen","unconscious")
		return self.isAlive() and not self.inStatus(conditions)


	### User Output ###

	def stringName(self,det=True,definite=False,n=1,plural=False,cap=False,c=1):
		strname = getattr(self,"descname",self.name)
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		if det:
			if definite:
				strname = "the " + strname
			elif not plural:
				if strname[0] in Data.vowels:
					strname = "an " + strname
				else:
					strname = "a " + strname
		if cap:
			strname = capWords(strname,c=c)
		return strname



	def describe(self):
		game.print(f"It's {self.stringName()}.")
		game.print(f"{self.desc}.")




# the class representing the player, contains all player stats
class Player(Creature):
	def __init__(self,name,desc,weight,traits,hp,mp,money,inv,gear,xp,rp,status=[],spells=[],descname=None,aliases=None,plural=None,**kwargs):
		Creature.__init__(self,name,desc,weight,traits,hp,mp,money,inv,gear,status=status,descname=descname,aliases=aliases,plural=plural)
		self.xp = xp
		self.rp = rp
		self.spells = spells



	### File I/O ###

	# @classmethod
	# def convertFromJSON(cls,d):
	# 	return cls(**d)



	### Operation ###

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		prevhp = self.hp
		if(f"{type} vulnerability" in self.status): dmg *= 2
		if(f"{type} resistance" in self.status): dmg /= 2
		if(f"{type} immunity" in self.status): dmg = 0
		# bludgeoning damage can't kill you in one hit
		if type == "b" and self.hp > 1:
			self.hp = minm(1,self.hp-dmg)			
		# player hp lowered to a minimum of 0
		else:
			self.hp = min0(self.hp-dmg)
		total_dmg = prevhp - self.hp
		game.print(f"You took {total_dmg} {Data.dmgtypes[type]} damage.")
		if self.hp == 0:
			self.death()


	# heals player hp a given amount
	def heal(self,heal):
		if self.hp + heal > self.MXHP():
			heal = self.MXHP() - self.hp
		self.hp += heal
		game.print(f"You healed {heal} HP.")
		return heal


	# player gets 3 QPs for each level gained, can dispense them into any trait
	def levelUp(self,oldlv,newlv):
		game.print(f"You leveled up to level {newlv}!\n")
		waitKbInput()
		QP = 3*(newlv-oldlv)
		while QP > 0:
			self.printTraits()
			game.print(f"\nQuality Points:	{QP}")
			trait = game.input("What trait will you improve?\n> ")
			if trait not in Data.traits:
				continue
			# increment corresponding player trait
			traitval = getattr(self,trait.upper())
			if traitval >= 20:
				game.print(f"Your {trait} cannot be raised any higher.\n")
				waitKbInput()
				continue
			setattr(self,trait.upper(),traitval+1)
			QP -= 1
		self.printTraits()
		game.print(f"\nQuality Points:	{QP}")
		input("You are done leveling up.\n")
		self.checkHindered()


	def updateReputation(self,repMod):
		self.RP = maxm(100, minm(-100, repMod))


	def updateMoney(self,money):
		self.money += money
		if money > 0:
			game.print(f"\nYou have $ {self.money}!")
		else:
			game.print(f"\nYou have $ {self.money}.")


	def obtainItem(self,I,tookMsg=None,failMsg=None):
		oldParent = I.parent
		if self.addItem(I):
			oldParent.removeItem(I)
			if tookMsg != None:
				game.print(tookMsg)
			I.Obtain(self)
			self.checkHindered()
			return True
		if failMsg != None:
			game.print(failMsg)
		return False


	# adds xp, checks for player level up
	def gainxp(self,newxp):
		oldlv = self.level()
		game.print(f"\nYou gained {newxp} xp.")
		game.print(f"{self.xp} + {newxp} = {self.xp+newxp}")
		self.xp += newxp
		newlv = self.level()
		if oldlv != newlv:
			self.levelUp(oldlv,newlv)


	def addCondition(self,name,dur,stackable=False,silent=False):
		if self.hasCondition(name) and not stackable:
			return False
		pair = [name,dur]
		insort(self.status,pair)
		if not silent:
			if name in Data.curses or name in Data.blessings:
				game.print(f"You have {name}.")
			else:
				game.print(f"You are {name}.")
		return True


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					self.status.remove([condname,duration])
					if not self.hasCondition(condname):
						game.print(f"You are no longer {condname}.")


	def checkHindered(self):
		if self.invWeight() > self.BRDN():
			if not self.hasCondition("hindered"):
				game.print("Your Inventory grows heavy.")
				self.addCondition("hindered",-3)
		if self.invWeight() <= self.BRDN():
			if self.hasCondition("hindered"):
				game.print("Your Inventory feels lighter.")
				self.removeCondition("hindered",-3)


	# called when player hp hits 0
	def death(self):
		game.print("You have died!")
		game.quit = True
		# TODO:
		# check if there's any auto-resurrect features
		# ask to continue from checkpoint (last save)
		# or to load a different save
		# or to quit game


	def dualAttack(self,target):
		game.print("\nDual Attack!")
		hit = min1(maxm(99, self.ACCU() - target.EVSN()))
		if diceRoll(1,100) <= hit:
			crit = diceRoll(1,100) <= self.CRIT()
			attack = self.ATCK()
			if crit:
				game.print("Critical hit!")
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if not target.isAlive():
				return
		else:
			game.print("Aw it missed.")


	def attackCreature(self,target):
		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			game.print(f"{n} attacks:")
		for i in range(n):
			if n > 1:
				game.print(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = min1(maxm(99, self.ACCU() - target.EVSN()))
			if diceRoll(1,100) <= hit:
				crit = diceRoll(1,100) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					game.print("Critical hit!")
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
				if not target.isAlive():
					return
			else:
				game.print("Aw it missed.")
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	def attackItem(self,target):
		attack = self.ATCK()
		game.print(f"{attack} damage")
		if target.durability != -1 and attack > target.durability:
			target.Break()
		else:
			game.print("Nothing happens.")
			return



	### Getters ###

	def countCompasses(self):
		return len([item for item in self.inv if isinstance(item,Compass)])


	# weird formula right? returns a positive number rounded down to nearest int
	# to see an approximate curve, graph y = 5*log10(x/10)
	# note that a lower bound is set to level 1 when xp < 16
	# also note that the level cannot be higher than 50
	def level(self):
		return 1 if self.xp < 16 else maxm(50,floor( 5*log10(self.xp/10) ))



	### User Output ###

	def stringName(self,det=True,definite=False,n=1,plural=False,cap=False,c=1):
		return "yourself"

	# prints all 10 player traits
	def printTraits(self,trait=None):
		if trait == None:
			traits = [f"{t.upper()}: {getattr(self,t.upper())}" for t in Data.traits]
			columnPrint(traits,5,10)
			return	
		game.print(f"{trait.upper()}: {getattr(self,trait.upper())}\n")


	def printAbility(self,ability=None):
		if ability == "atck":
			game.print(f"atck: {self.STR} - {self.weapon.might*self.STR}")
		elif ability == "brdn":
			game.print(f"brdn: {self.invWeight()}/{self.BRDN()}")
		elif ability is not None:
			game.print(f"{ability}: {getattr(self,ability)()}")
		else:
			for ability in Data.abilities:
				self.printAbility(ability.upper())


	# each prints a different player stat
	def printMoney(self, *args): game.print(f"$ {self.money}")
	def printHP(self, *args): game.print(f"HP: {self.hp}/{self.MXHP()}")
	def printLV(self, *args): game.print(f"LV: {self.level()}")
	def printMP(self, *args): game.print(f"MP: {self.mp}/{self.MXMP()}")
	def printXP(self, *args): game.print(f"XP: {self.xp}")
	def printRP(self, *args): game.print(f"RP: {self.rp}")


	def printSpells(self, *args):
		game.print(f"Spells: {len(self.spells)}/{self.SPLS()}")
		if len(self.spells) == 0:
			game.print("\nYou don't know any spells.")
		else:
			columnPrint(self.spells,8,12)


	# prints player inventory
	def printInv(self, *args):
		game.print(f"Weight: {self.invWeight()}/{self.BRDN()}")
		if len(self.inv) == 0:
			game.print("\nYour Inventory is empty.")
		else:
			columnPrint(self.invNames(),8,12)


	# print each player gear slot and the items equipped in them
	def printGear(self, *args):
		game.print()
		for slot in self.gear:
			game.print(slot + ":\t",end="")
			game.print(self.gear[slot].name)


	def printStatus(self, *args):
		if len(self.status) == 0:
			game.print("None")
			return

		conditions = []
		durations = []
		# populate conditions with unique condition names affecting the player
		# populate durations with the highest duration for that condition
		# negative (special) durations take precedence over positive durations
		for cond, dur in sorted(self.status, key=lambda x: x[1]):
			if cond not in conditions:
				conditions.append(cond)
				durations.append(dur)
			else:
				idx = conditions.index(cond)
				olddur = durations[idx]
				newdur = dur if dur > olddur and olddur > 0 else olddur
				durations[idx] = newdur

		nDigits = len(str(max(durations)))
		# make list of strings to display conditions and their durations
		statusdisplay = []
		for i in range(len(conditions)):
			statusdisplay.append(conditions[i])
			if durations[i] < 0:
				statusdisplay.append("-"*nDigits)
			else:
				statusdisplay.append(str(durations[i]))

		# dynamically determine display column width based on longest name
		colWidth = len(max(conditions, key=len)) + 2
		columnPrint(statusdisplay,2,colWidth)


	# prints player level, money, hp, mp, rp, and status effects
	def printStats(self, *args):
		stats = [self.name, f"$ {self.money}", f"LV: {self.level()}", f"RP: {self.rp}", f"HP: {self.hp}/{self.MXHP()}", f"MP: {self.mp}/{self.MXMP()}"]
		columnPrint(stats,2,16)
		if len(self.status) != 0:
			self.printStatus()


	# for every item in player inventory, if its a weapon, print it
	def printWeapons(self, *args):
		if len(self.weapons()) == 0:
			game.print("You have no weapons.")
		else:
			columnPrint(self.weapons(),12,12)




##########################
## SUBCLASS DEFINITIONS ##
##########################


class Person(Creature):
	def __init__(self,name,descname,gender,weight,traits,hp,mp,money,inv,gear,dlogtree,desc=None,love=0,fear=0,rapport=0,status=[],spells=[],aliases=[],lastParley=None,memories=set(),appraisal=set(),**kwargs):
		if desc == None:
			desc = f"A {descname}"
		Creature.__init__(self,name,desc,weight,traits,hp,mp,money,inv,gear,status=status,aliases=aliases,descname=descname)
		self.descname = descname
		self.gender = gender
		self.spells = spells
		self.love = love
		self.fear = fear
		self.dlogtree = DialogueTree(dlogtree)
		self.rapport = rapport
		self.lastParley = lastParley
		self.appraisal = appraisal
		self.memories = memories


	### File I/O ###

	# @classmethod
	# def convertFromJSON(cls,d):
	# 	return cls(**d)


	# def convertToJSON(self):
	# 	d = self.__dict__.copy()
	# 	d = {"__class__":self.__class__.__name__, **d}
	# 	return d


	### Operation ###

	def act(self):
		pass

	
	def firstImpression(self,player):
		# adjust love, fear from person baselines
		self.memories.add("met")
		self.love += player.rp
		self.fear += player.rp


	def appraise(self,player,game):
		self.appraisal = set()

		if self.lastParley is None:
			self.lastParley = game.time
		elif game.time - self.lastParley > 100:
			self.dlogtree.newParley()
		self.lastParley = game.time
		if player.isNaked():
			self.appraisal.add("naked")
		
		
	def Talk(self,player,game,world):
		if "met" not in self.memories:
			self.firstImpression(player)
		self.appraise(player,game)
		if not self.dlogtree.visit(self,player,game,world):
			game.print(f"{self.name} says nothing...")


	### User Output ###

	def stringName(self,det=True,definite=False,n=1,plural=False,cap=False,c=1):
		if "met" in self.memories:
			return self.name
		strname = self.descname			
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		if det:
			if definite:
				strname = "the " + strname
			elif not plural:
				if strname[0] in Data.vowels:
					strname = "an " + strname
				else:
					strname = "a " + strname
		if cap:
			strname = capWords(strname,c=c)
		return strname

	


class Animal(Creature):
	def act(self):
		if not self.timeOfDeath:
			return
		if not game.silent:
			game.print(f"\n{self.name}'s turn!")
		self.attack()


	def attack(self):
		if not game.silent:
			game.print("attack?")


	def climb():
		pass


	def go():
		pass


	def steal():
		pass


	def swim():
		pass


	def throw():
		pass



notes = '''
self.alive = True
self.seesPlayer = False
self.sawPlayer = -1

creatures can take 'actions'
they have a 'act' function, which dictates their actions

actions they can take on a turn include;
moving (swimming, climbing)
attacking
casting a spell
speaking
equipping/unequipping an item
using an item (eating food, using a key, etc.)
hiding somewhere
dropping/taking an item
stealing
throwing
heal itself
shield/defend

in their turn function, actions are dictated by several factors, including;
if they know the player is present,
if they recently saw the player,
if the player has weapons, or if the player is bloodied
if other creatures are present (and if they are allies or not)
if they have a weapon
if they have food or healing items
if their own stats are higher than a certain number
if they have a specific status condition
what the player's RP is

different types of creatures act with different limitations;
animal cannot speak, trade, or equip, take, and use items, or cast spells,
monsters cannot speak, or trade

_______________________________
TECHNICAL DESIGN

prior to taking a turn, each creature updates a series of attributes which just represent its perception of its surroundings. current values are;

all creatures:
Bool seesPlayer
Int sawPlayer
Bool alliesPresent()
Bool enemiesPresent()

monsters and people:
Int player.rp
Bool isArmed
Bool hasHealing
Bool playerBloodied()
Bool playerArmed()

other values utilized in taking a turn:
Set status

'''

# almost identical to the item class, but fixtures may not be removed from their initial location.
class Fixture(Item):
	def __init__(self,name,desc,mention,weight=-1,durability=-1,status=[],aliases=[],plural=None):
		Item.__init__(self,name,desc,weight=weight,durability=durability,status=status,aliases=aliases,plural=plural)
		self.mention = mention
		self.parent = None



	### Operation ###

	def Break(self):
		if self.durability == -1:
			if not game.silent:
				game.print(f"The {self.name} cannot be broken.")
			return False
		game.print(f"The {self.name} breaks.")
		self.parent.removeFixture(self)
		return True



class Passage(Fixture):
	def __init__(self,name,desc,mention,connections,descname,passprep,weight=-1,durability=-1,status=[],aliases=[],plural=None):
		Fixture.__init__(self,name,desc,mention,weight=weight,durability=durability,status=status,aliases=aliases,plural=plural)
		self.connections = connections
		self.descname = descname
		self.passprep = passprep



	### Operation ###

	def Traverse(self,dir=None):
		if dir == None or dir not in self.connections:
			if len(set(self.connections.values())) == 1:
				dir = list(self.connections.keys())[0]
			else:
				msg = f"Which direction will you go on the {self.name}?\n> "
				dir = input(msg).lower()
		if dir in Data.cancels:
			return False
		if dir not in self.connections:
			game.print(f"The {self.name} does not go '{dir}'.")
			return False

		if self.passprep != "":
			game.print(f"You go {dir} {self.passprep} the {self.name}.")
		else:
			game.print(f"You go {dir} the {self.name}.")

		newroom = world[self.connections[dir]]
		game.changeRoom(newroom)
		return True




class Serpens(Item):
	def __init__(self,value,status=[]):
		self.name = "Gold"
		self.desc = f"{str(value)} glistening coins made of an ancient metal"
		self.aliases = ["coin","coins","money","serpen","serpens"]
		self.plural = "gold"
		self.weight = value
		self.durability = -1
		self.status = status
		self.descname = str(value) + " Gold"
		self.value = value



	### File I/O ###

	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		return {
			"__class__": self.__class__.__name__,
			"value": self.value,
			"status": {}
		}



	### Operation ###

	def Obtain(self,creature):
		creature.updateMoney(self.value)


	def merge(self,other):
		if not isinstance(other,Serpens):
			raise TypeError("Cannot merge non-Serpens with Serpens")

		self.status += other.status
		self.value += other.value
		self.desc = f"{str(self.value)} glistening coins made of an ancient metal"



	### User Output ###

	def stringName(self,det=True,definite=False,n=1,plural=False,cap=False,c=1):
		strname = "Gold"
		strname = str(self.value) + " " + strname
		if definite:
			strname = "the " + strname
		if cap:
			strname = capWords(strname,c=c)
		return strname




class Weapon(Item):
	def __init__(self,name,desc,weight,durability,might,sleight,sharpness,range,type,twohanded=False,status=[],aliases=[],plural=None):
		Item.__init__(self,name,desc,weight,durability,status=status,aliases=aliases,plural=plural)
		self.might = might
		self.sleight = sleight
		self.sharpness = sharpness
		self.range = range
		self.twohanded = twohanded
		self.type = type


	def print(self):
		game.print(f"{self.name} {self.might} {self.sleight}")
		game.print(f"{self.sharpness} { self.twohanded} {self.range}")




class Shield(Item):
	def __init__(self,name,desc,weight,durability,prot,status=[],aliases=[],plural=None):
		Item.__init__(self,name,desc,weight,durability,status=status,aliases=aliases,plural=plural)
		self.prot = prot




class Armor(Item):
	def __init__(self,name,desc,weight,durability,prot,slots,status=[],aliases=[],plural=None):
		Item.__init__(self,name,desc,weight,durability,status=status,aliases=aliases,plural=plural)
		self.prot = prot
		if type(slots) is not list:
			self.slots = [slots]


	def Equip(self):
		pass


	def Unequip(self):
		pass



class Compass(Item):
	def Orient(self):
		game.print("Orienting you northward!")




class Monster(Creature):
	### Operation ###

	def act(self):
		if not self.isAlive():
			return
		if not game.silent:
			game.print(f"\n{self.name}'s turn!")
		self.attack()


	def attack(self):
		# if creature is not in same room as player
		if game.currentroom != self.room():
			return
		else:
			self.attackCreature(player)


	def attackCreature(self,target):
		if target == player:
			targetname = "you"
		else:
			targetname = target.stringName()
		game.print(f"{self.stringName(definite=True, cap=True)} tries to attack {targetname}")

		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			game.print(f"{n} attacks:")
		for i in range(n):
			if n > 1:
				game.print(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = min1(maxm(99, self.ACCU() - target.EVSN()))
			if diceRoll(1,100) <= hit:
				crit = diceRoll(1,100) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					game.print("Critical hit!")
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
				if not target.isAlive():
					return
			else:
				game.print("It missed!")
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	### Getters ###

	def describe(self):
		game.print(f"It's {self.stringName()}.")
		game.print(f"{self.desc}.")
		gearitems = [item for item in self.gear.values() if item != EmptyGear()]
		if len(gearitems) != 0:
			game.print(f"It has {listObjects(gearitems)}.")


	def level(self):
		return (self.rating() - 10) // 10


	def isArmed():
		# returns true if monster is armed
		pass


	def hasHealing():
		# returns true is monster has healing potion or food
		pass


	def playerBloodied():
		# returns true if monster believes player is bloodied
		pass


	def playerArmed():
		# returns true if monster believes player is armed
		pass






player = Player("","",0,[0]*10,0,0,0,[],{},0,0)
defaultRoom = Room("","","",{},[],[],[],set())
game = Game(-1,defaultRoom,defaultRoom,-1,-1)
world = {}