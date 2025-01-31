# Core.py
# This file contains all core functions and classes used throughout the game
# This file is a dependency of Objects.py and is dependent on Data.py

# It consists of two main parts;
# 1. Core functions			(used in Objects.py, Menu.py, and Parser.py)
# 2. Dialogue Classes		(DialogueNode and DialogueTree)
# 3. Core class definitions	(empty, game, room, item, creature, player, etc.)

from time import sleep
from random import randint,sample
from math import floor, sqrt
from bisect import insort
from collections.abc import Iterable
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
	if term is None or obj is None:
		return False
	term = term.lower()
	if isinstance(obj, Room):
		return term == obj.name.lower() or term in ["here", "room"]
	return term == obj.name.lower() or term == obj.stringName().lower() or term in obj.aliases


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


def clearScreen(delay=0.1):
	if os.name == "nt":
		os.system("cls")
		# ensure screen isn't being cleared during subsequent output
		sleep(delay)
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
def waitKbInput(text=None):
	sys.stdout.flush
	if text is not None:
		game.Print(text,allowSilent=False)
	# just pass if in test mode
	if game.mode == 1:
		return True
	flushInput()
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
	sleep(1)

# prints a list of strings, l, into n columns of width w characters
# if an element is longer than one column, it takes up as many columns as needed
def columnPrint(l,n,w,printf=None):
	if printf is None:
		printf = game.Print
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
			if entry[0].stringName == obj.stringName:
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
		printf = game.Print
	if inputf is None:
		inputf = game.Input
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
	return min1(x)


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


# recurs through objects within the parent and assigns it as their parent
def assignRefsRecur(parent):
	if not hasMethod(parent,'contents'):
		return
	for obj in parent.contents():
		# everything in the world or player inv should be Item or Creature
		assert isinstance(obj, (Item, Creature))
		obj.assignParent(parent)
		assignRefsRecur(obj)


# removes any room connection values which don't exist in the world
# to prevent errors if the world file was written incorrectly
# also assigns parents for all world objects (read objQuery() comments)
# also assigns dialogue trees for speakers and validates them
def buildWorld():
	player.assignParent(game.currentroom)

	namesToDelete = []
	for room in world.values():
		assert isinstance(room, Room)
		assignRefsRecur(room)

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

		# assign the dialogue trees for all creatures and validate them
		for creature in objQuery(room, d=3, key=lambda x: isinstance(x,Speaker)):
			creature.buildDialogue()
			creature.dlogtree.ensureIntegrity(creature)

	# this is done in a separate loop to prevent errors caused by...
	# deleting elements from dict while iterating over the dict
	for name in namesToDelete:
		del world[name]




############
## LOGGER ##
############


class TeeLogger:
	def __init__(self,logFile,inputFile=None):
		self.terminal = sys.stdout
		self.originalStdin = sys.stdin
		self.errorTerminal = sys.stderr
		os.makedirs(os.path.dirname(logFile),exist_ok=True)
		self.log = open(logFile,"w")
		self.stdin = open(inputFile,"r") if inputFile else self.originalStdin


	def write(self, message):
		self.terminal.write(message)
		self.log.write(message)


	def write_error(self,message):
		self.errorTerminal.write(message)  # Print errors to stderr in terminal
		self.log.write(message)  # Log errors in the same file
		self.flush()


	def readline(self):
		input_text = self.stdin.readline()
		self.log.write(input_text)
		self.log.flush()
		return input_text


	def flush(self):
		self.terminal.flush()
		self.log.flush()


	def setInputFile(self, inputFilename):
		if self.stdin != self.originalStdin:
			self.stdin.close()
		self.stdin = open(inputFilename,"r")




######################
## DIALOGUE CLASSES ##
######################


# in order for characters to produce unique and variable dialogue with minimal repetition
# and apparent intelligence, the dialogue is stored as a directed tree

# in addition to having children, each node in the tree may have a few important parameters;
# a node may contain either a remark or a list of 'trites' from which to generate dialogue
# - a remark is a simple line of output dialogue. A trite is the name of a 'triteset'
# - tritesets are sets of predetermined remarks, which can be sampled by many characters
# the node may also contain either a 'cases' list or a 'replies' list
# - cases is a list of boolean expressions which can reference the character, player, game, or world objects
# - instead of a boolean expression, a case may be an integer, representing a random probability
# - replies is a list of potential dialogue replies that the user may choose during the dialogue
# the child that is visited next can depend on the value of the corresponding case or the user-selected reply

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
	def __init__(self,parent,root,nVisits=0,lastTriteRemark=None,visitLimit=None,rapportReq=None,guardCase="True",isCheckpoint=False,loveMod=0,fearMod=0,repMod=0,memories=None,events=None,remark=None,trites=None,cases=None,replies=None,children=[],reactTrue=False):
		self.parent = parent
		self.root = root
		self.nVisits = nVisits
		self.lastTriteRemark = lastTriteRemark
		self.visitLimit = visitLimit
		self.guardCase = guardCase
		self.rapportReq = rapportReq
		self.isCheckpoint = isCheckpoint
		self.children = [DialogueNode(self,root,**childJson) for childJson in children]

		### the following are effects that visiting the node will have
		# these modify speaker stats
		self.loveMod=loveMod
		self.fearMod=fearMod
		self.repMod=repMod
		# this adds memory to speaker memories
		self.memories = set() if memories is None else memories
		if type(memories) is list:
			self.memories = set(memories)
		elif type(memories) is str:
			self.memories = {memories}
		for memory in self.memories:
			assert type(memory) is str
		# this adds event to game events
		self.events = set() if events is None else events
		if type(events) is list:
			self.events = set(events)
		elif type(events) is str:
			self.events = {events}
		for event in self.events:
			assert type(event) is str

		### the following are possible dialogue outputs from visiting the node
		# this is a basic output dialogue remark
		self.remark = remark
		# these are names of sets of strings in Dialogue.json, contianing 'canned' dialogue
		self.trites = [] if trites is None else trites
		if type(self.trites) is not list:
			self.trites = [trites]
		for trite in self.trites:
			assert type(trite) is str
		
		# should only be used for terminal nodes in 'reactions' branch of tree
		# meant so dialogue tree can be used to determine if speaker's reaction is 'True'
		# i.e. if a speaker refuses or accepts a player's 'Give' action
		self.reactTrue = reactTrue
		assert len(self.children) == 0 or not self.reactTrue

		### the following are mechanisms to determine which child to branch to
		# these are strings of python code which should evaluate to a bool or int
		self.cases = [] if cases is None else cases
		# these are the optional Player replies to the dialogue
		self.replies = [] if replies is None else replies
		# ensure the number of child nodes matches the cases or replies
		if self.cases:
			if type(self.cases) is not list:
				self.cases = [self.cases]
			# one extra child for when all cases are false
			assert len(self.children) == len(self.cases) + 1
		elif self.replies:
			if type(self.replies) is not list:
				self.replies = [self.replies]
			assert len(self.children) == len(self.replies)

		# ensure node doesn't have both a remark and a trite set
		assert self.remark is None or self.trites == []
		# ensure node doesn't have both conditional cases and reply cases
		assert self.cases == [] or self.replies == []
		
		if hasattr(self.parent, 'replies'):
			assert self.visitLimit is None and self.rapportReq is None, 'child of reply node must not have visitLimit or rapportReq'

		self.globals = {"player":player,"game":game,"world":world}


	### File I/O ###

	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		del jsonDict["root"]
		del jsonDict["id"]
		return jsonDict
	

	@classmethod
	def convertFromJSON(cls,d):
		game.Print('converting...')
		game.Print(d)
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
	def ensureIntegrity(self,speaker,**kwargs):
		self.id = self.getID()
		err = f"Invalid guard case node condition in {speaker.name}'s node {self.id}: {self.guardCase}"
		context = kwargs | {"speaker":speaker}
		guardCaseRes = eval(self.guardCase,self.globals,context)
		# assert type(guardCaseRes) is bool, err
		for case in self.cases:
			err = f"Invalid case node condition in {speaker.name}'s node {self.id}: {case}"
			caseRes = eval(str(case),self.globals,context)
			assert type(caseRes) in (bool,int), err
		for trite in self.trites:
			triteset = game.dlogDict["trites"][trite]
			assert len(triteset) > 2
		for child in self.children:			
			child.ensureIntegrity(speaker,**kwargs)


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
	def conditionalHop(self,speaker,**kwargs):
		for i, case in enumerate(self.cases):
			nextNode = self.children[i]

			context = kwargs | {"speaker":speaker}
			# cases can either be boolean cases or integers representing probability
			if type(case) is int and diceRoll(1,100) <= case:
				if nextNode.hop(speaker,**kwargs):
					return nextNode

			elif type(case) is str and eval(case,self.globals,context) is True:
				if nextNode.hop(speaker,**kwargs):
					return nextNode

		else:
			nextNode = self.children[-1]
			if nextNode.hop(speaker,**kwargs):
				return nextNode
		
		return None


	# try to visit the child corresponding to the user-chosen dialogue reply
	# users can end the dialogue by inputting a cancel command
	def replyHop(self):
		for i, reply in enumerate(self.replies):
			game.Print(f'{i+1}. {reply}\n')

		while True:
			choice = input("\n> ").lower()
			if choice == "":
				continue
			if choice in Data.cancels: 
				return None

			try:
				# note that this does *not* hop(); it ignores child's visitLimit, rapportReq, guardCase
				return self.children[int(choice)-1]
			except:
				game.Print('That is not one of the options. Input a number or type "cancel"')
				continue


	def hop(self,speaker,**kwargs):
		if self.visitLimit and self.nVisits >= self.visitLimit:
			return False
		if self.rapportReq is not None:
			if speaker.rapport != self.rapportReq:
				return False
		context = kwargs | {"speaker":speaker}
		if not eval(self.guardCase,self.globals,context):
			return False
		return True


	# attempt to branch down the tree, visiting this node
	# printing a dialogue remark if the node has one, and visiting a child node
	def visit(self,speaker,**kwargs):	
		# output this node's remark
		if self.isCheckpoint:
			self.root.checkpoint = self.id
		if self.remark:
			waitKbInput(f'"{self.remark}"')
		elif self.trites:
			tritepool = set()
			for trite in self.trites:
				tritepool |= set(game.dlogDict["trites"][trite])

			samples = sample(tritepool,2)
			triteRemark = samples[0]
			if triteRemark == self.lastTriteRemark:
				triteRemark = samples[1]

			waitKbInput(f'"{triteRemark}"')
			self.lastTriteRemark = triteRemark

		# return next node if this node has children
		nextNode = None
		if self.cases:
			nextNode = self.conditionalHop(speaker,**kwargs)
		elif self.replies:
			nextNode = self.replyHop(speaker)
		else:
			for child in self.children:
				if child.hop(speaker,**kwargs):
					nextNode = child
					break

		# count this node as successfully visited
		self.nVisits += 1
		if self.rapportReq != None:
			speaker.rapport += 1
		
		# reaching a node can change the speaker's love or fear for the player
		speaker.updateLove(self.loveMod)
		speaker.updateFear(self.fearMod)
		# or the player's reputation
		player.updateReputation(self.repMod)
		# or affect the speaker's memories or game's events
		for memory in self.memories:
			speaker.memories.add(memory)
		for event in self.events:
			game.events.add(event)

		# unmark checkpoint if this node was succesfully visited
		if nextNode and self.root.checkpoint == self.id:
			self.root.checkpoint = None
		return nextNode


	### Getters ###

	# ensures that at least one path in the tree will provide dialogue in all cases
	def hasDefiniteDialogue(self):
		if self.remark or self.trites:
			return True
		if self.cases:
			if self.children[-1].hasDefiniteDialogue():
				return True
			return False
		for child in self.children:
			if child.hasDefiniteDialogue():
				return True
		return False


class ReactionNode(DialogueNode):
	def __init__(self,parent,root,treeJson):
		DialogueNode.__init__(self,parent,root)
		self.reactions = {key: DialogueNode(self,root,**childJson) for key,childJson in treeJson.items()}
		self.children = [child for child in self.reactions.values()]


	def __getitem__(self,key):
		return self.reactions[key]


	def __contains__(self,key):
		return key in self.reactions



class DialogueTree():
	def __init__(self,treeJson):
		# note that chatter is required to be populated; there must be some dialogue
		self.surprise = DialogueNode(self,self,**treeJson.get("surprise",{}))
		self.quest = DialogueNode(self,self,**treeJson.get("quest",{}))
		self.colloquy = DialogueNode(self,self,**treeJson.get("colloquy",{}))
		self.chatter = DialogueNode(self,self,**treeJson["chatter"])
		self.reactions = ReactionNode(self,self,treeJson.get("reactions",{}))
		self.checkpoint = treeJson.get("checkpoint",None)
		self.id = []
		self.children = (self.surprise,self.quest,self.colloquy,self.chatter,self.reactions)


	### File I/O ###

	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		del jsonDict["id"]
		del jsonDict["children"]
		return jsonDict
	

	@classmethod
	def convertFromJSON(cls,d):
		return cls(**d)


	# ensures the following;
	# that the tree is structurally valid (parents are assigned to children)
	# that the checkpoint, if there is one, is a valid node
	# that at least one path of the tree will yield dialogue in all cases
	def ensureIntegrity(self,speaker):
		# this is used for running eval (specifically reaction nodes)
		dummyContext = {"I": Item("","",0,0,""), "C": Creature("","",0,[0]*10,0)}
		for child in self.children:
			child.ensureIntegrity(speaker,**dummyContext)
		if self.checkpoint:
			try:
				self.findNode(self.checkpoint)
			except:
				raise Exception(f"Checkpoint {self.checkpoint} not found in {speaker.name}'s dialogue tree")
		if not self.chatter.hasDefiniteDialogue():
			raise Exception(f"{speaker.name} dialogue Tree has no definite dialogue in {speaker.room()}")


	### Operation ###

	# visit the branch, return True if navigating any branch resulted in speaker dialogue
	def visitBranch(self,node,speaker):
		had_dialogue = False
		while node:
			if node.remark or node.trites:
				had_dialogue = True
			node = node.visit(speaker)
		return had_dialogue

	
	# visit the corresponding reaction branch, return True if reached a 'reactTrue' node 
	def react(self,reaction,speaker,**kwargs):
		if reaction not in self.reactions:
			return False
		node = self.reactions[reaction]
		if node.hop(speaker,**kwargs):
			while node:
				nextNode = node.visit(speaker,**kwargs)
				if node.reactTrue:
					return True
				node = nextNode
		return False


	# attempt to visit each branch of the tree until one yields dialogue
	# after the surprise branch, start at the dialogue checkpoint if there is one
	# returns True if any branch successfully yielded dialogue. Visiting 'chatter' should always succeed
	def visit(self,speaker):
		if self.surprise.hop(speaker):
			if self.visitBranch(self.surprise,speaker):
				return True

		if self.checkpoint:
			checkpointNode = self.findNode(self.checkpoint)
			if checkpointNode.hop(speaker):
				if self.visitBranch(checkpointNode,speaker):
					return True

		for branch in (self.quest,self.colloquy,self.chatter):
			if branch.hop(speaker):
				if self.visitBranch(branch,speaker):
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
class EmptyGear:
	_instance = None
	name = "[empty]"
	aliases = []
	weight = 0
	prot = 0
	might = 1
	sleight = 0
	sharpness = 0
	type = "e"



	### Dunder Methods ###

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance


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

	def stringName(self,det="",n=-1,plural=False,cap=0):
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
	def __init__(self,mode,currentroom,prevroom,time,events,dlogDict,creatureFactory):
		# 0 for normal mode, 1 for testing mode, 2 for god mode
		self.mode = mode
		# the room that the player is currently in
		self.currentroom = currentroom
		# the room that the player was in last
		self.prevroom = prevroom
		# the number of game loops that have elapsed since the game's start
		self.time = time
		# the time of the last save made
		self.lastsave = time
		# set of important events that have transpired in the game's progression
		self.events = events
		# used to generate dialogue dynamically by Speaker class
		self.dlogDict = dlogDict
		# used to spawn creatures
		self.creatureFactory = creatureFactory
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

		# used to trigger a quit from the player
		self.quit = False

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
	def passTime(self,t=1):
		prev_hour = self.hour()
		self.time += t
		self.silent = player.hasAnyCondition("asleep","dead")
		player.passTime(t)
		for room in self.renderedRooms():
			self.silent = room is not self.currentroom or player.hasAnyCondition("asleep","dead")
			room.passTime(t)
		self.silent = player.hasAnyCondition("asleep","dead")
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
		if hasattr(obj,"pronoun"):
			if obj.pronoun == "he":
				self.he = obj
			elif obj.pronoun == "she":
				self.she = obj


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
		if self.currentroom.altitude < 0:
			return
		mooncycle = (self.time % self.monthlength) // self.daylength
		if mooncycle == 0:
			self.Print("It is a new moon.")
			self.events.add("new moon")
		elif mooncycle == 7:
			self.Print("It is a full moon.")
			self.events.add("full moon")
		if "new moon" in self.events:
			self.events.remove("new moon")
		if "full moon" in self.events:
			self.events.remove("full moon")


	def checkAstrology(self,update=False):
		if self.currentroom.altitude < 0:
			return
		darkhours = ("hearth","cat","mouse","owl","serpent","wolf")
		aurora_cycle = self.time % 2000
		if aurora_cycle >= 0 and aurora_cycle < 100 and self.hour() in darkhours:
			if "aurora" not in self.events or update:
				self.Print("There is an aurora in the sky!")			
			self.events.add("aurora")
		elif "aurora" in self.events:
			self.events.remove("aurora")
			self.Print("The aurora is over.")

		meteor_cycle = self.time % 3500
		if meteor_cycle >= 0 and meteor_cycle < 300 and self.hour() in darkhours:
			if "meteor shower" not in self.events or update:
				self.Print("There is a meteor shower in the sky!")
			self.events.add("meteor shower")
		elif "meteor shower" in self.events:
			self.events.remove("meteor shower")
			self.Print("The meteor shower is over.")

		lighthours = ("rooster","juniper","bell","sword","willow","lily")
		eclipse_cycle = self.time % (self.monthlength*3+100)
		if eclipse_cycle > 0 and eclipse_cycle < 30 and self.hour() in lighthours:
			if "eclipse" not in self.events or update:
				self.Print("There is a solar eclipse in the sky!")
			self.events.add("eclipse")
		elif "eclipse" in self.events:
			self.events.remove("eclipse")
			self.Print("The solar eclipse is over.")


	### User Output ###
	
	def Input(self,text="",low=True):
		sys.stdout.flush()
		# should never be silent when asking for input
		self.Print(text,end='',allowSilent=False)
		flushInput()
		if not low:
			ret = input()
		else:
			ret = input().lower()
		return ret


	def Print(self,*args,end="\n",sep='',delay=0.005,allowSilent=True):
		sys.stdout.flush()
		if self.silent and allowSilent:
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
		sleep(delay)
		sys.stdout.write(end)
		sys.stdout.flush()
		sleep(delay)
		

	def startUp(self):
		player.printStats()
		game.Print()
		self.currentroom.describe()
		game.checkDaytime()
		game.checkAstrology(update=True)


	def describeRoom(self):
		self.currentroom.describe()


	def checkDaytime(self):
		if self.currentroom.altitude < 0:
			return
		if self.hour() in ("stag","rooster","juniper"):
			self.Print("It is morning.")
		if self.hour() in ("bell","sword","willow","lily"):
			self.Print("It is day.")
		if self.hour() in ("hearth","cat"):
			self.Print("It is evening.")
		if self.hour() in ("mouse","owl","serpent","wolf"):
			self.Print("It is night.")
			self.checkMoon()


	def LookUp(self,target):
		if self.currentroom.altitude < 0:
			self.Print("You can't see that from here.")
		
		if target == "sky":
			target = "sun" if self.hour() in Data.dayhours else "moon"		

		if "eclipse" in self.events:
			self.Print("The bold red sun is blackened by the ominous moon. The world is dark below and above but for the ring of violet light tracing the moon. Those golden lines of fire that scar the moon's surface seem like cracks through which the sun's rays seep faintly through. All is still in the heavens as they bear witness to this solemn union.")
			player.takeDamage(5,"r")
		elif "eclipse" not in self.events and target in ("eclipse","solar eclipse"):
			self.Print("There's no eclipse happening right now.")
		elif target == "sun":
			if self.hour() in ("stag","rooster","juniper"):
				self.Print("A burning ball of red fire marches upward in the sky. In the morning air it paints the heavens a tinge of pale green.")
			elif self.hour() in ("bell","sword","willow","lily"):
				self.Print("A burning ball of red fire hangs high in the sky. It warms your face with its bold glow.")
			elif self.hour() in ("hearth","cat"):
				self.Print("A burning ball of red fire rests in the sky. As it descends toward the horizon it draws a curtain of violet across the world above.")
			else:
				self.Print("The sun isn't out right now.")
		elif target in ("moon","stars"):
			if self.hour() in Data.nighthours:
				if "full moon" in self.events:
					self.Print("A shimmering golden orb dances in the sky pouring whispers of light. You can make out traces of strange golden fire on its surface. The stars seem to dance around it joyously. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate.")
				elif "new moon" in self.events:
					self.Print("On a night without the moon the world is full of silence and cold. The stars seem to shiver lonesomely. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate.")
				else:
					self.Print("A shimmering golden orb dances in the sky pouring whispers of light. You can make out traces of strange golden fire on its surface. It hangs amongst a scattering of sparkling drops on all sides. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate.")
			elif target == "moon":
				self.Print("The moon isn't out right now.")
			elif target == "stars":
				self.Print("The stars aren't out right now.")
		
		if "aurora" in self.events:
			self.Print("Tides of the red, blue, and green aurora gently sweep over the sky. The colors seem to bathe the heavens as it caresses the shimmering silver stars.")
		elif target in ("aurora","auroras"):
			self.Print("There's no aurora happening right now.")

		if "meteor shower" in self.events:
			self.Print("Bolts of yellow light streak deftly across the sky, leaving their imprint for no more than a moment. The almost seem to take turns whizzing past like a flock of birds, eager to follow one another toward the edge of the heavens.")
		elif target in ("shower","meteors","meteor shower"):
			self.Print("There's no meteor shower happening right now.")

		return True


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
	def __init__(self,name,domain,desc,exits,fixtures,items,creatures,altitude=0,isRoad=False,status=None):
		self.name = name
		self.domain = domain
		self.desc = desc
		self.exits = exits
		self.fixtures = fixtures
		self.items = items
		self.creatures = creatures
		# 0 for outdoors, -1 for indoors, <-1 for underground, >0 for in the sky
		self.altitude = altitude
		# used by NPCs to navigate
		self.isRoad = isRoad
		self.status = status if status else []


	### Dunder Methods ###

	def __repr__(self):
		return f"Room({self.name}, {tuple(self.exits.values())}...)"


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
		I.despawnTimer = I.longevity
		return True


	def removeItem(self,I):
		if I in self.items:
			self.items.remove(I)


	def addCreature(self,C):
		insort(self.creatures,C)
		C.parent = self


	def removeCreature(self,C):
		self.creatures.remove(C)


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
		insort(self.status,[name,dur])
		if name.startswith("AREA"):
			self.addAreaCondition(name)
		return True


	# removes all conditions of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,reqName=None,reqDuration=None):
		# deep copy to prevent removing-while-iterating errors
		for name,duration in [_ for _ in self.status]:
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])
					if name.startswith("AREA"):
						self.removeAreaCondition(name)


	# decrements the duration for each status condition applied to the room by t
	# removes status conditions whose duration is lowered past 0
	def passTime(self,t):
		for condition in self.status:
			# if condition is has a special duration, ignore it
			if condition[1] < 0:
				continue
			# subtract remaining duration on condition
			elif condition[1] > 0:
				condition[1] = min0(condition[1] - t)
		
		# remove conditions with 0 duration left
		self.removeCondition(reqDuration=0)

		for obj in self.contents():
			obj.passTime(t)
		
		# spawn up to 1 creature in the room
		if len(self.creatures) > 0 or self is game.currentroom:
			return
		for name, prob in Data.spawnpools.get(self.domain,()):
			if randint(1,100) <= prob and len(self.creatures) > 0:
				self.addCreature(game.creatureFactory[name]())

		# sort all Creatures occupying the room by their MVMT() value, descending
		self.creatures.sort(key=lambda x: x.MVMT(), reverse=True)


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
		game.Print("\n"+self.domain+"\n"+self.name)
		# if player.countCompasses() == 0:
		# 	game.Print("\n" + ambiguateDirections(self.desc))
		# else:
		game.Print("\n" + self.desc)
		self.describeItems()
		self.describeCreatures()


	# prints all the items of the room in sentence form
	def describeItems(self):
		items = self.listableItems()
		if len(items) != 0:
			game.Print(f"There is {listObjects(self.listableItems())}.")
		if len(items) == 1:
			game.setPronouns(items[0])


	# prints all the creatures in the room in sentence form
	def describeCreatures(self):
		listCreatures = [creature for creature in self.creatures if creature is not player.riding and creature is not player.carrying]
		if len(listCreatures) != 0:
			game.Print(f"There is {listObjects(listCreatures)}.")
		for creature in listCreatures:
			game.setPronouns(creature)




# The Item class is the main game object class of things that cannot act
# Anything in a Room that is not a Creature will be an Item
# All items come with a name, description, weight, and durability
class Item():
	def __init__(self,name,desc,weight,durability,composition,longevity=None,despawnTimer=None,scent=None,taste=None,texture=None,status=None,aliases=None,plural=None,determiner=None):
		self.name = name
		self.desc = desc
		self.weight = weight
		self.durability = durability
		self.composition = composition
		# how long it lasts in despawnable conditions
		self.longevity = longevity
		self.despawnTimer = despawnTimer
		self.scent = scent
		self.taste = taste
		self.texture = texture
		self.status = status if status else []
		self.aliases = aliases if aliases else []
		if plural is None:
			self.plural = self.name + 's'
		else:
			self.plural = plural
		self.determiner=determiner
		self.parent = None


	### File I/O ###

	def assignParent(self,parent):
		self.parent = parent


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
				condition[1] = min0(condition[1] - t)

		# remove conditions with 0 duration left
		self.removeCondition(reqDuration=0)
		
		if self.despawnTimer is not None:
			self.despawnTimer -= t
			if self.despawnTimer <= 0 and self.parent is not game.currentroom:
				self.parent.removeItem(self)			


	def Obtain(self,creature):
		pass


	def Break(self):
		if self.durability == -1:
			if not game.silent:
				game.Print(f"The {self.name} cannot be broken.")
			return False
		game.Print(f"The {self.name} breaks.")
		self.parent.removeItem(self)
		return True


	def Use(self,user):
		if user not in self.ancestors():
			game.Print(f"{self.stringName('the',cap=1)} is not in your inventory.")
			return False
		print(f"You use {self.name}")


	def takeDamage(self,dmg):
		if dmg > self.durability:
			return self.Break()


	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		insort(self.status,[name,dur])
		return True


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,reqName=None,reqDuration=None):
		# deep copy to prevent removing-while-iterating errors
		for name,duration in [_ for _ in self.status]:
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])


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

	def stringName(self,det="",n=-1,plural=False,cap=0):
		strname = getattr(self,"descname",self.name)
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		if self.determiner is not None and det == "":
			det = self.determiner
		if det == "" and n == 1:
			det = "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname
	

	def describe(self):
		game.Print(f"It's {self.stringName('a')}.")
		game.Print(f"{self.desc}.")




# The Creature class is the main class for anything in the game that can act
# Anything in a Room that is not an Item will be a Creature
# The player is a Creature too
# Creatures have 10 base stats, called traits
# They also have abilities; stats which are derived from traits through formulas
class Creature():
	def __init__(self,name,desc,weight,traits,hp,mp=0,money=0,inv=None,gear=None,love=0,fear=0,carrying=None,carrier=None,riding=None,rider=None,memories=None,appraisal=None,status=None,descname=None,aliases=None,plural=None,determiner=None,pronoun="it",timeOfDeath=None,lastAte=0,lastSlept=0,regenTimer=0,alert=False,seesPlayer=False,sawPlayer=-1):
		self.name = name
		self.desc = desc
		self.descname = descname if descname else name
		self.aliases = aliases if aliases else []
		self.determiner = determiner
		if plural is None:
			self.plural = self.name + 's'
		else:
			self.plural = plural
		self.weight = weight
		self.pronoun = pronoun

		self.str = traits[0]
		self.spd = traits[1]
		self.skl = traits[2]
		self.stm = traits[3]
		self.con = traits[4]
		self.cha = traits[5]
		self.int = traits[6]
		self.wis = traits[7]
		self.fth = traits[8]
		self.lck = traits[9]

		self.status = status if status else []
		# sort status effects by duration; change '1' to '0' to sort by name
		self.status.sort(key=lambda x: x[1])

		self.hp = hp
		self.mp = mp
		self.money = money
		self.inv = inv if inv else []
		self.love = love
		self.fear = fear
		self.memories = memories if memories else set()
		self.appraisal = appraisal if appraisal else set()
		
		# this gets decompressed or reassigned by assignParent
		self.parent = None
		self.riding = riding
		self.rider = rider
		self.carrying = carrying
		self.carrier = carrier
		self.gear = gear if gear else Data.initgear

		self.weapon = EmptyGear()
		self.weapon2 = EmptyGear()
		self.shield = EmptyGear()
		self.shield2 = EmptyGear()

		self.timeOfDeath = timeOfDeath
		# health regens very slowly
		self.regenTimer = regenTimer
		# eventually creatures get hungry and sleepy
		self.lastAte = lastAte
		self.lastSlept = lastSlept
		# these attributes remain unused in the Player subclass
		self.alert = alert
		self.seesPlayer = seesPlayer
		self.sawPlayer = sawPlayer


	### Dunder Methods ###

	def __repr__(self):
		traits = [self.str, self.spd, self.skl, self.stm, self.con, self.cha, self.int, self.wis, self.fth, self.lck]
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
	
	def assignParent(self,parent):
		self.parent = parent

		def uncompressTether(idx):
			if idx is None:
				return None
			elif idx == "player":
				return player
			else:
				return self.parent.contents()[idx]

		self.carrying = uncompressTether(self.carrying)
		self.carrier = uncompressTether(self.carrier)
		self.riding = uncompressTether(self.riding)
		self.rider = uncompressTether(self.rider)

		uncompGear = {}
		for slot, idx in self.gear.items():
			if idx == "carrying":
				uncompGear[slot] = self.carrying
			elif idx is None:
				uncompGear[slot] = EmptyGear()
			else:
				uncompGear[slot] = self.inv[idx]
		self.gear = uncompGear


	# converts the gear dict to a form more easily writable to a save file
	# replaces all objects in gear.values() with an integer which represents...
	# the index of the equipped object in the creature's inventory
	# if the gear slot is empty, replaces it with -1
	def compressGear(self):
		cGear = {}
		for slot, item in self.gear.items():			
			if type(item) is Creature:
				cGear[slot] = "carrying"
			elif item is EmptyGear():
				cGear[slot] = None
			else:
				cGear[slot] = item
		return cGear			


	def compressTethers(self):
		def compressTether(obj):
			if obj is None:
				return None
			elif obj is player:
				return "player"
			else:
				return self.parent.contents().index(obj)

		tethers = {
			"carrying": compressTether(self.carrying),
			"carrier": compressTether(self.carrier),
			"riding": compressTether(self.riding),
			"rider": compressTether(self.rider)
		}
		return tethers


	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		# convert the gear dict to a form more easily writable in a JSON object
		compressedGear = self.compressGear()
		tethers = self.compressTethers()
		d = self.__dict__.copy()
		dictkeys = list(d.keys())
		# these attributes do not get stored between saves (except gear)
		for key in dictkeys:
			if key.lower() in Data.traits or key in {"gear","carrying","riding","carrier","rider","weapon","weapon2","shield","shield2"}:
				del d[key]
		d["gear"] = compressedGear
		# convert traits to a form more easily writable in a JSON object
		d["traits"] = [self.str,self.skl,self.spd,self.stm,self.con,self.cha,self.int,self.wis,self.fth,self.lck]
		# TODO: swap the following lines for Python 3.9
		# d = {"__class__":self.__class__.__name__} | d
		d |= tethers
		d = {"__class__":self.__class__.__name__, **d}
		del d["parent"]
		return d


	### Operation ###

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		prevhp = self.hp
		if(f"{type} vulnerability" in self.status): dmg *= 2
		if(f"{type} resistance" in self.status): dmg //= 2
		if(f"{type} immunity" in self.status): dmg = 0
		# bludgeoning damage can't kill you in one hit
		if type == "b" and self.hp > 1:
			self.hp = minm(1,self.hp-dmg)			
		# hp lowered to a minimum of 0
		else:
			self.hp = min0(self.hp-dmg)
		total_dmg = prevhp - self.hp
		game.Print(f"{self.stringName('the',cap=1)} took {total_dmg} {Data.dmgtypes[type]} damage.")
		if self.hp == 0:
			self.death()


	# heals hp a given amount
	def heal(self,heal,overflow=False):
		if self.hp + heal > self.MXHP() and not overflow:
			heal = self.MXHP() - self.hp
		self.hp += heal
		if isinstance(self,Player):
			game.Print(f"You healed {heal} HP.")
		return heal


	def resurge(self,mana,overflow=False):
		if self.mp + mana > self.MXMP() and not overflow:
			mana = self.MXHP() - self.mp
		self.mp += mana
		return mana


	def updateMoney(self,money):
		self.money += money


	def updateLove(self,loveMod):
		self.RP = maxm(100, minm(-100, loveMod))


	def updateFear(self,fearMod):
		self.RP = maxm(100, minm(-100, fearMod))


	# check if item can fit in inventory
	def canObtain(self,I):
		if self.invWeight() + I.Weight() > 2*self.BRDN():
			return False
		return True


	# try to add an Item to Inventory
	# it will fail if the inventory is too heavy
	def addItem(self,I):
		if not self.canObtain(I):
			return False
		insort(self.inv,I)
		I.parent = self
		I.despawnTimer = None
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
				game.Print(msg)
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
	def unequip(self,I,silent=False):
		if type(I) is str:
			I = self.gear[I]
		if I is EmptyGear():
			return False
		gearslots = list(self.gear.keys())
		gearitems = list(self.gear.values())
		# finds the slot whose value is I, sets it to empty
		slot = gearslots[gearitems.index(I)]
		self.gear[slot] = EmptyGear()
		self.assignWeaponAndShield()
		if not silent:
			game.Print(f"You unequip your {I.name}.")
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


	def addCarry(self,creature):
		if self.gear["left"] is not EmptyGear():
			self.gear.unequip("left")
		self.carrying = creature
		self.gear["left"] = creature
		self.checkHindered()
		

	def removeCarry(self):
		self.gear["left"] = EmptyGear()
		self.carrying.carrier = None
		self.carrying = None
		self.checkHindered()


	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		insort(self.status,[name,dur])
		return True


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,reqName=None,reqDuration=None):
		# deep copy to prevent removing-while-iterating errors
		for name,duration in [_ for _ in self.status]:
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])


	def passTime(self,t):
		for condition in self.status:
			# if condition is has a special duration, ignore it
			if condition[1] < 0:
				continue
			# subtract remaining duration on condition
			elif condition[1] > 0:
				condition[1] = min0(condition[1] - t)

		# remove conditions with 0 duration left
		self.removeCondition(reqDuration=0)

		# take damage from damaging status conditions
		for condition, _ in [_ for _ in self.status]:
			if condition in Data.conditionDmg:
				factor, type = Data.conditionDmg[condition]
				dmg = min1(randint(1,factor) - self.LCK())
				self.takeDamage(dmg,type)

		self.checkTired()
		self.checkHungry()

		# natural healing is faster with a higher endurance
		if not self.hasAnyCondition("hungry","starving"):
			self.regenTimer += 1
			if self.regenTimer >= 50 - self.ENDR() or self.hasCondition("mending"):
				self.regenTimer = 0
				h = 5 if self.hasAnyCondition("cozy","mending") else 1
				self.heal(h)
				self.resurge(1)

		# delete self if in a room and it has been 299 time since death
		reapable = lambda creature: creature.timeOfDeath is not None and \
		(game.time - creature.timeOfDeath) > 299 and \
		isinstance(self.parent, Room) and \
		self.parent is not game.currentroom()
		if reapable(self):
			self.parent.removeCreature(self)


	def checkHindered(self):
		carryWeight = 0 if self.carrying is None else self.carrying.Weight()
		if self.invWeight() + carryWeight > self.BRDN():
			self.addCondition("hindered",-3)
		if self.invWeight() + + carryWeight <= self.BRDN():
			self.removeCondition("hindered")


	def checkHungry(self):
		return False


	def checkTired(self):
		return False


	# called when a creature's hp hits 0
	def death(self):
		self.timeOfDeath = game.time
		self.addCondition("dead",-3)
		game.Print("\n" + f"{self.stringName('the',cap=1)} died.")
		self.descname = f"dead {self.descname}"
		n = diceRoll(3,player.LOOT(),-2)
		self.room().addItem(Serpens(n))
		if not game.silent:
			game.Print(f"Dropped $ {n}.")
		if game.whoseturn is player:
			r = self.rating()
			# xp granted generally scales with rating
			xp = diceRoll(2, r//2, r-15)
			player.gainxp(xp)


	def Eat(self,food):
		food.parent.removeItem(food)
		food.Eat()


	def Sit(self):
		self.removeCondition("laying")
		self.removeCondition("crouching")
		self.addCondition("sitting",-3)


	def Crouch(self):
		self.removeCondition("sitting")
		self.removeCondition("laying")
		self.addCondition("crouching",-3)
		

	def Lay(self):
		self.removeCondition("crouching")
		self.removeCondition("sitting")
		self.addCondition("laying",-3)


	def Give(self,I):
		game.Print(f"{self.stringName('the',cap=1)} ignores your offer.")


	### Behavior ###

	def changeRoom(self,newroom):
		# can only change rooms if not stuck inside some item
		if type(self.parent) is not Room:
			return False
		# shouldn't be changing rooms alone if being carried
		if self.carrier and self.carrier.parent is not newroom:
			return False

		prevroom = self.parent
		prevroom.exit(self)
		prevroom.removeCreature(self)
		self.parent = newroom
		newroom.addCreature(self)		
		newroom.enter(self)

		if self.carrying and self.carrying.parent is not self.parent:
			self.carrying.changeRoom(newroom)
		if self.riding and self.riding.parent is not self.parent:
			self.riding.changeRoom(newroom)
		if self.rider and self.rider.parent is not self.parent:
			self.rider.changeRoom(newroom)

		assert self.carrying is None or self.carrying.parent is self.parent
		return True

			
	def Teleport(self,newroom):
		prevroom = self.parent
		prevroom.exit(self)
		prevroom.removeCreature(self)
		self.parent = newroom
		newroom.addCreature(self)		
		newroom.enter(self)
		if self.riding:
			self.riding = None
		if self.carrying:
			self.carrying = None


	def act(self):
		pass


	# since creatures can carry creatures while also being carried themselves,
	# and same can happen for riding and riders, loops could form where
	# a carrier is trying to carry the creature that is carrying them
	# this must be prevented
	def checkTetherLoop(self,actor,target,dverb):
		assert dverb in ("carry","ride")
		looplink = None		

		iverb = "carrying"
		carrier = actor
		while carrier:
			if carrier.carrier == target:
				looplink = carrier
			carrier = carrier.carrier

		iverb = "being carried by"
		carrying = actor
		while carrying:
			if carrying.carrying == target:
				looplink = carrying
			carrying = carrying.carrying

		iverb = "riding"
		rider = actor
		while rider:
			if rider.rider == target:
				looplink = rider
			rider = rider.rider

		iverb = "being ridden by"
		riding = actor
		while riding:
			if riding.riding == target:
				looplink = riding
			riding = riding.riding
		
		# if a creature is found creating a loop with the actor and attempted target,
		# identify the culprit
		if looplink:
			game.Print(f"You can't {dverb} {target.stringName('the')}, {target.pronoun} is {iverb} {looplink}")
			return True
		return False


	def Carry(self,carrier):
		if self.checkTetherLoop(carrier,self,"carry"):
			return False
		if self.Weight() > carrier.BRDN():
			game.Print(f"{self.stringName('the',cap=1)} is too heavy to carry.")
			return False
		if not self.Restrain(carrier):
			return False
		self.carrier = carrier
		self.carrier.addCarry(self)
		return True


	def Restrain(self,restrainer,item=None):
		if not self.isAlive():
			return True
		if not self.isFriendly() and self.canMove():
			if item != None:
				#TODO: add restraining with items? like rope??
				pass
			if self.ATHL() > restrainer.ATHL() or self.EVSN() > restrainer.ATHL():
				game.Print(f"You fail to restrain {self.stringName('the')}!")
				return False
		self.addCondition("restrained",-3)
		game.Print(f"You restrain {self.stringName('the')}!")
		return True


	def Hide(self,I):
		if 4 * self.SLTH() > I.weight:
			self.addCondition("hiding",-3)
		else:
			pass


	def Ride(self,rider):
		if self.checkTetherLoop(rider,self,"ride"):
			return False
		if rider.Weight() > self.BRDN():
			game.Print(f"You are too heavy to ride {self.stringName('the')}")
			return False
		if not self.isFriendly() and self.canMove():
			game.Print(f"{self.stringName('the',cap=1)} struggles.")
			athl_contest = self.ATHL() - rider.ATHL()
			if athl_contest > 0:
				game.Print(f"{self.stringName('the',cap=1)} shakes you off!")
				if athl_contest > rider.ATHL():
					rider.takeDamage(athl_contest-rider.ATHL(),"b")
				return False
		self.rider = rider
		rider.riding = self
		game.Print(f"You ride {self.stringName('the')}.")
		return True


	def Smell(self,smeller):
		game.Print("Smells a little like body odor.")


	def Lick(self,licker):
		# TODO: make creatures evade this or try to
		game.Print("Yuck!")


	def Touch(self,toucher):
		game.Print("Feels soft and fleshy.")


	### Getters ###

	def conditionalMod(self,stat,bonuses=[],min=None,max=None):
		for condname, bonus in bonuses:
			if self.hasCondition(condname):
				stat = stat + bonus
		if min:
			stat = minm(min,stat)
		if max:
			stat = maxm(max,stat)
		return stat


	# these are creature stats that are determined dynamically with formulas
	def STR(self):
		modifiers = (("brawniness",10), ("weakness",-10))
		return self.conditionalMod(self.str, modifiers, min=1)


	def SPD(self):
		modifiers = (("swiftness",10), ("slowness",-10))
		return self.conditionalMod(self.spd, modifiers, min=1)


	def SKL(self):
		modifiers = (("prowess",10), ("clumsiness",-10))
		return self.conditionalMod(self.skl, modifiers, min=1)


	def STM(self):
		modifiers = (("liveliness",10), ("weariness",-10), ("tired",-3), ("fatigued",-5))
		return self.conditionalMod(self.stm, modifiers, min=1)


	def CON(self):
		modifiers = (("toughness",10), ("illness",-10))
		return self.conditionalMod(self.con, modifiers, min=1)


	def CHA(self):
		modifiers = (("felicity",10), ("timidity",-10))
		return self.conditionalMod(self.cha, modifiers, min=1)


	def INT(self):
		modifiers = [("sagacity",10), ("stupidity",-10)]
		return self.conditionalMod(self.int, modifiers, min=1)


	def WIS(self):
		modifiers = [("lucidity",10), ("instanity",-10), ("fatigued",-3)]
		return self.conditionalMod(self.wis, modifiers, min=1)


	def FTH(self):
		modifiers = [("fidelity",10), ("apathy",-10)]
		return self.conditionalMod(self.fth, modifiers, min=1)


	def LCK(self):
		modifiers = [("prosperity",10), ("calamity",-10)]
		return self.conditionalMod(self.lck, modifiers, min=1)


	def LOVE(self):
		modifiers = [("enchanted",50)]
		return self.conditionalMod(self.love, modifiers, min=-100, max=100)


	def FEAR(self):
		modifiers = [("haunted",50)]
		return self.conditionalMod(self.fear, modifiers, min=-100, max=100)


	# these formulas are difficult to read, check design document for details
	def ACCU(self): return 45 + 2*self.SKL() + self.LCK() + self.weapon.sleight
	def ATCK(self): return diceRoll(self.STR(), self.weapon.might, self.atkmod())
	def ATHL(self): return self.STR() + self.SKL() + self.STM()
	def ATSP(self): return self.SPD() - min0(self.handheldWeight()//4 - self.CON())
	def BRDN(self): return 20*self.CON() + 10*self.STR() + 5*self.FTH() + self.weight
	def CAST(self): return self.WIS() + self.FTH() + self.INT() - min0(self.gearWeight()//4 - self.CON())
	def CRIT(self): return self.SKL() + self.LCK() + self.weapon.sharpness
	def CSSP(self): return self.WIS() - min0(self.invWeight() - self.BRDN()) - min0(self.gearWeight()//4 - self.CON())
	def DCPT(self): return 2*self.CHA() + self.INT()
	def DFNS(self): return 2*self.CON() + self.protection()
	def ENDR(self): return 2*self.STM() + self.CON()
	def EVSN(self): return 10 if self.hasAnyCondition("sitting","laying") else 2*self.ATSP() + self.LCK() + self.SPD()
	def INVS(self): return 2*self.INT() + self.WIS()
	def KNWL(self): return 2*self.INT() + self.LCK()
	def LOOT(self): return 2*self.LCK() + self.FTH()
	def MVMT(self): return self.SPD() + self.STM() + 10 - min0(self.invWeight() - self.BRDN()) - min0(self.gearWeight()//4 - self.CON())
	def MXHP(self): return self.level()*self.CON() + self.STM()
	def MXMP(self): return self.level()*self.WIS() + self.STM()
	def PRSD(self): return 2*self.CHA() + self.WIS()
	def RSTN(self): return 2*self.FTH() + self.STM()
	def RITL(self): return 2*self.FTH() + self.LCK()
	def SLTH(self): return ( 2*self.SKL() + self.INT() - min0(self.invWeight() - self.BRDN()) ) * 2*int(self.hasCondition("hiding"))
	def SPLS(self): return 3*self.INT()
	def TNKR(self): return 2*self.INT() + self.SKL()


	def Weight(self):
		riderWeight = 0 if self.rider is None else self.rider.Weight()
		carryWeight = 0 if self.carrying is None else self.carrying.Weight()
		return self.weight + self.invWeight() + riderWeight + carryWeight


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
		return ((self.rating() - 10) // 10) + 1


	def rating(self):
		return self.str + self.spd + self.skl + self.stm + self.con + self.cha + self.int + self.wis + self.fth + self.lck


	# returns sum of the weight of all items in the inventory
	def invWeight(self):
		return sum(item.Weight() for item in self.inv)


	# returns a list of names of all items in player inventory
	def invNames(self):
		return [item.stringName() if isinstance(item,Creature) else item.name for item in self.inv]


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
		if term.startswith("my "):
			term = term[3:]
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


	def hasAnyCondition(self,*names):
		if len(names) == 0:
			return len(self.status) > 0
		if len(names) == 1:
			names = names[0]
		assert isinstance(names,Iterable)
		for name in names:
			if self.hasCondition(name):
				return True


	# returns the sum of the weight of all items being held
	def handheldWeight(self):
		return 0
		carryingWeight = 0 if self.carrying is None else self.carrying.Weight()
		return self.gear["left"].Weight() + self.gear["right"].Weight() + carryingWeight


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
		return self.hasCondition("tamed")


	def canMove(self):
		conds = ("restrained","paralyzed","frozen","unconscious")
		return self.isAlive() and not self.hasAnyCondition(conds)


	### User Output ###

	def stringName(self,det="",n=-1,plural=False,cap=-1):
		strname = getattr(self,"descname",self.name)
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		if self.determiner is not None:
			det = self.determiner
		if det == "" and n == 1:
			det = "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


	def describe(self):
		game.Print(f"It's {self.stringName('a')}.")
		game.Print(f"{self.desc}.")




# the class representing the player, contains all player stats
class Player(Creature):
	def __init__(self,name,desc,weight,traits,hp,mp,xp,rp,spells=None,**kwargs):
		Creature.__init__(self,name,desc,weight,traits,hp,mp=mp,**kwargs)
		self.xp = xp
		self.rp = rp
		self.spells = spells if spells else []


	### Operation ###

	def changeRoom(self,newroom):
		# can only change rooms if not stuck inside some item
		if type(self.parent) is not Room:
			raise Exception(f"Can't change rooms. Stuck inside {self.parent}")
		game.changeRoom(newroom)
		if self.riding:
			self.riding.changeRoom(newroom)
		if self.carrying:
			self.carrying.changeRoom(newroom)
		
		assert self.carrying is None or self.carrying.parent is self.parent
		return True


	def awaken(self,wellRested=True):
		game.silent = False
		sleep(1)
		game.Print("You wake up!")
		sleep(1)
		if wellRested:
			self.lastSlept = game.time
			self.checkTired()
		sleep(1)
		game.Print("\n\n")
		game.startUp()


	def Teleport(self,newroom):
		if type(self.parent) is not Room:
			raise Exception(f"Can't change rooms. Stuck inside {self.parent}")
		game.changeRoom(newroom)
		if self.riding:
			game.Print(f"You are no longer riding {self.riding.stringName()}.")
			self.riding = None
		if self.carrying:
			game.Print(f"You are no longer carrying {self.carrying.stringName()}.")
			self.carrying = None


	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		if self.hasCondition("dead"):
			return False
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
		p = "."
		if player.hasCondition("asleep") or total_dmg > self.MXHP() // 2:
			p = "!"
		game.Print(f"You took {total_dmg} {Data.dmgtypes[type]} damage{p}",allowSilent=False)
		if self.hp == 0:
			return self.death()
		if total_dmg > 0 and self.hasCondition("asleep"):
			self.removeCondition("asleep")


	# player gets 1 QPs for each level gained, can dispense them into any trait
	def levelUp(self,oldlv,newlv):
		waitKbInput(f"You leveled up to level {newlv}!\n")
		QP = newlv-oldlv
		while QP > 0:
			self.printTraits()
			game.Print(f"\nQuality Points:	{QP}")
			trait = game.Input("What trait will you improve?\n> ")
			game.Print()
			if trait not in Data.traits:
				continue
			# increment corresponding player trait
			traitval = getattr(self,trait)
			if traitval >= 20:
				waitKbInput(f"Your {trait} cannot be raised any higher.\n")
				continue
			setattr(self,trait,traitval+1)
			QP -= 1
		self.printTraits()
		waitKbInput("You are done leveling up.\n")
		self.checkHindered()
		self.checkTired()
		self.checkHungry()


	def updateReputation(self,repMod):
		self.rp = maxm(100, minm(-100, repMod))


	def updateMoney(self,money):
		self.money += money
		if money > 0:
			game.Print(f"You have $ {self.money}!")
		else:
			game.Print(f"You have $ {self.money}.")


	def obtainItem(self,I,tookMsg=None,failMsg=None):
		oldParent = I.parent
		if self.addItem(I):
			oldParent.removeItem(I)
			if tookMsg != None:
				game.Print(tookMsg)
			I.Obtain(self)
			self.checkHindered()
			return True
		if failMsg != None:
			game.Print(failMsg)
		return False


	# adds xp, checks for player level up
	def gainxp(self,newxp):
		oldlv = self.level()
		game.Print(f"\nYou gained {newxp} xp.")
		self.xp += newxp
		# game.Print(f"You have {self.xp}")
		newlv = self.level()
		if oldlv != newlv:
			self.levelUp(oldlv,newlv)


	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		if not self.hasCondition(name):
			if name in Data.curses:
				game.Print(f"You have the curse of {name}.",allowSilent=False)
			elif name in Data.blessings:
				game.Print(f"You have the blessing of {name}.",allowSilent=False)
			elif name == "asleep":
				game.Print(f"You fall {name}.",allowSilent=False)
			else:
				game.Print(f"You are {name}.",allowSilent=False)
		insort(self.status,[name,dur])
		return True


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,reqName=None,reqDuration=None):
		wasSleeping = self.hasCondition("asleep")
		wellRested = False

		# deep copy to prevent removing-while-iterating errors
		for name,duration in [_ for _ in self.status]:
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])

					if name == "asleep" and duration == 0:
						wellRested = True
					if name != "asleep" and not self.hasCondition(name):
						game.Print(f"You are no longer {name}.",allowSilent=False)
		
		if wasSleeping and not self.hasCondition("asleep"):
			self.awaken(wellRested=wellRested)


	def checkHindered(self):
		carryWeight = 0 if self.carrying is None else self.carrying.Weight()
		if self.invWeight() + carryWeight > self.BRDN():
			if not self.hasCondition("hindered"):
				game.Print("Your Inventory grows heavy.")
				self.addCondition("hindered",-3)
		if self.invWeight() + carryWeight <= self.BRDN():
			if self.hasCondition("hindered"):
				game.Print("Your Inventory feels lighter.")
				self.removeCondition("hindered",-3)


	def checkHungry(self):
		# being invigorated prevents hunger but not starving
		invigorated = self.hasCondition("invigorated")
		# hunger takes longer with more endurance
		sinceLastAte = game.time - self.lastAte
		if sinceLastAte > 100 + 10*self.ENDR():
			self.removeCondition("hungry",-3)
			self.addCondition("starving",-3)
		elif sinceLastAte > 50 + 5*self.ENDR() and not invigorated:
			self.addCondition("hungry",-3)
		elif sinceLastAte < 100:
			self.removeCondition("starving")
			self.removeCondition("hungry")
		elif invigorated:
			self.removeCondition("hungry")			


	def checkTired(self):
		# being invigorated prevents tired and fatigue
		invigorated = self.hasCondition("invigorated")
		# sleep deprivation takes longer with more endurance
		sinceLastSlept = game.time - self.lastSlept
		if sinceLastSlept > 300 + 40*self.ENDR() and not invigorated:
			self.removeCondition("tired",-3)
			self.addCondition("fatigued",-3)
		elif sinceLastSlept > 150 + 20*self.ENDR() and not invigorated:
			self.addCondition("tired",-3)
		elif sinceLastSlept < 100 or invigorated:
			self.removeCondition("fatigued")
			self.removeCondition("tired")


	# called when player hp hits 0
	def death(self):
		game.Print("You have died!")
		ellipsis(3)
		
		if self.hasCondition("Anointed",reqDuration=-3):
			sleep(1)
			game.Print("You reawaken!")
			self.hp = 1
		else:
			self.addCondition("dead",-3)
			waitKbInput()
			self.timeOfDeath = game.time
		return True


	def dualAttack(self,target):
		game.Print("\nDual Attack!")
		hit = min1(maxm(99, self.ACCU() - target.EVSN()))
		if diceRoll(1,100) <= hit:
			crit = diceRoll(1,100) <= self.CRIT()
			attack = self.ATCK()
			if crit:
				waitKbInput("Critical hit!")
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if not target.isAlive():
				return
		else:
			game.Print("Aw it missed.")
		waitKbInput()


	def attackCreature(self,target):
		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			game.Print(f"{n} attacks!")
		for i in range(n):
			if n > 1:
				waitKbInput(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = min1(maxm(99, self.ACCU() - target.EVSN()))
			if diceRoll(1,100) <= hit:
				crit = diceRoll(1,100) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					waitKbInput("Critical hit!")
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
			else:
				game.Print("Aw it missed.")
			waitKbInput()
			if not target.isAlive():
				return
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	def attackItem(self,target):
		attack = self.ATCK()
		game.Print(f"{attack} damage")
		if target.durability != -1 and attack > target.durability:
			target.Break()
		else:
			game.Print("Nothing happens.")
			return
		

	### Getters ###

	def countCompasses(self):
		return len([item for item in self.inv if isinstance(item,Compass)])


	# returns the sum of the weight of all items being held
	def handheldWeight(self):
		carryingWeight = 0 if self.carrying is None else self.carrying.Weight()
		return self.gear["left"].Weight() + self.gear["right"].Weight() + carryingWeight


	# weird formula right? returns a positive number rounded down to nearest int
	# note that a lower bound is set to level 1 when xp < 8
	# also note that the level cannot be higher than 100
	def level(self):
		return 1 if self.xp < 8 else maxm(100,floor( sqrt(self.xp/2) ))


	### User Output ###

	def stringName(self,det="",n=-1,plural=False,cap=-1):
		return "yourself"

	# prints all 10 player traits
	def printTraits(self,trait=None):
		if trait == None:
			traits = [f"{t.upper()}: {getattr(self,t)}" for t in Data.traits]
			columnPrint(traits,5,10)
			return	
		game.Print(f"{trait.upper()}: {getattr(self,trait)}")


	def printAbility(self,ability=None):
		if ability == "atck":
			game.Print(f"atck: {self.STR} - {self.weapon.might*self.STR}")
		elif ability == "brdn":
			game.Print(f"brdn: {self.invWeight()}/{self.BRDN()}")
		elif ability is not None:
			game.Print(f"{ability}: {getattr(self,ability)()}")
		else:
			for ability in Data.abilities:
				self.printAbility(ability.upper())


	# each prints a different player stat
	def printMoney(self, *args): game.Print(f"$ {self.money}")
	def printHP(self, *args): game.Print(f"HP: {self.hp}/{self.MXHP()}")
	def printLV(self, *args): game.Print(f"LV: {self.level()}")
	def printMP(self, *args): game.Print(f"MP: {self.mp}/{self.MXMP()}")
	def printXP(self, *args): game.Print(f"XP: {self.xp}")
	def printRP(self, *args): game.Print(f"RP: {self.rp}")


	def printSpells(self, *args):
		game.Print(f"Spells: {len(self.spells)}/{self.SPLS()}")
		if len(self.spells) == 0:
			game.Print("\nYou don't know any spells.")
		else:
			columnPrint(self.spells,8,12)


	# prints player inventory
	def printInv(self, *args):
		game.Print(f"Weight: {self.invWeight()}/{self.BRDN()}")
		if len(self.inv) == 0:
			game.Print("\nYour Inventory is empty.")
		else:
			columnPrint(self.invNames(),8,12)


	# print each player gear slot and the items equipped in them
	def printGear(self, *args):
		game.Print()
		for slot in self.gear:
			val = self.gear[slot].name
			if slot == "left" and self.carrying:
				val = self.carrying.name
			game.Print(slot + ":\t",end="")
			game.Print(val)


	def printCarrying(self, *args):
		if self.carrying:
			game.Print(f"Carrying {self.carrying.stringName('a')}")
			game.Print(f"Weight: {self.carrying.Weight()}")
		else:
			game.Print("Carrying nothing")


	def printRiding(self, *args):
		if self.riding:
			game.Print(f"Riding {self.riding.stringName('a')}")
		else:
			game.Print("Riding nothing")


	def printStatus(self, *args):
		if len(self.status) == 0:
			game.Print("None")
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
		if self.carrying is not None:
			game.Print(f"Carrying {self.carrying.stringName()}")
		if self.riding is not None:
			game.Print(f"Riding {self.riding.stringName()}")
		if len(self.status) != 0:
			game.Print()
			self.printStatus()


	# for every item in player inventory, if its a weapon, print it
	def printWeapons(self, *args):
		if len(self.weapons()) == 0:
			game.Print("You have no weapons.")
		else:
			columnPrint(self.weapons(),12,12)




##########################
## SUBCLASS DEFINITIONS ##
##########################


class Humanoid(Creature):
	### Operation ###

	def act(self):
		if not self.isAlive():
			return
		if not game.silent:
			game.Print(f"\n{self.name}'s turn!")
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
		game.Print(f"{self.stringName('the', cap=1)} tries to attack {targetname}")

		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			game.Print(f"{n} attacks!")
		for i in range(n):
			if n > 1:
				waitKbInput(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = min1(maxm(99, self.ACCU() - target.EVSN()))
			if diceRoll(1,100) <= hit:
				crit = diceRoll(1,100) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					waitKbInput("Critical hit!")
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
			else:
				game.Print("It missed!")
			waitKbInput()
			if not target.isAlive():
				return
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	### Getters ###

	def describe(self):
		game.Print(f"It's {self.stringName('a')}.")
		game.Print(f"{self.desc}.")
		gearitems = [item for item in self.gear.values() if item != EmptyGear()]
		if len(gearitems) != 0:
			game.Print(f"It has {listObjects(gearitems)}.")


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




class Speaker(Creature):
	def __init__(self,name,desc,weight,traits,hp,dlogName=None,rapport=0,lastParley=None,**kwargs):
		Creature.__init__(self,name,desc,weight,traits,hp,**kwargs)
		self.dlogName = name if dlogName is None else dlogName
		self.rapport = rapport
		self.lastParley = lastParley


	def buildDialogue(self):
		self.dlogtree = DialogueTree(game.dlogDict["trees"][self.dlogName])


	def firstImpression(self,player):
		# TODO: add this
		print(self.name, "impression")
		# adjust love, fear from person baselines
		self.memories.add("met")
		self.updateLove(player.rp)
		self.updateFear(player.rp)


	def appraise(self,player,game):
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
		if not self.dlogtree.visit(self):
			game.Print(f"{self.name} says nothing...")


	def Give(self,I):
		if not self.canObtain(I):
			game.Print(f"{self.stringName(det='the',cap=1)} can't carry any more!")	
		elif self.dlogtree.react("Give",self,I=I):
			# if we fail to obtain item for whatever reason, drop it into room
			if not self.obtainItem(I):
				game.currentroom.addItem(I)
		else:
			game.Print(f"{self.stringName(det='the',cap=1)} ignores your offer.")			
		return True



class Person(Speaker,Humanoid):
	def __init__(self,name,descname,weight,traits,hp,pronoun,spells=None,desc=None,isChild=False,**kwargs):
		Speaker.__init__(self,name,"",weight,traits,hp,**kwargs)
		self.descname = descname
		self.pronoun = pronoun
		self.spells = spells if spells else []
		if desc:
			self.desc = desc
		else:
			prefix = "An " if self.descname[0] in Data.vowels else "A "
			self.desc = prefix + self.descname

		if self.pronoun == "he":
			if isChild:
				self.aliases.extend(("boy","male"))
			else:
				self.aliases.extend(("man","guy","dude","male"))
		elif self.pronoun == "she":
			if isChild:
				self.aliases.extend(("girl","female"))
			else:
				self.aliases.extend(("woman","lady","dudette","female"))
		else:
			self.pronoun = "they"
		if isChild:
			self.aliases.append("child","kid")
		self.aliases.append("person")
	

	### Operation ###


	def act(self):
		pass


	### User Output ###

	def stringName(self,det="",n=-1,plural=False,cap=0):
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
		if self.determiner is not None and det == "":
			det = self.determiner
		if det == "" and n == 1:
			det = "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname




class Animal(Speaker):
	def __init__(self,name,desc,weight,traits,hp,species=None,dlogName=None,**kwargs):
		Speaker.__init__(self,name,desc,weight,traits,hp,**kwargs)
		self.species = name if species is None else species
		# dlogName was assigned by Speaker init, but should be reassigned here
		self.dlogName = self.species if dlogName is None else self.dlogName


	def buildDialogue(self):
		self.sounds = game.dlogDict["sounds"][self.species]
		# dlogName must either be the name of a tree or a trite
		if self.dlogName in game.dlogDict["trees"]:
			self.dlogtree = DialogueTree(game.dlogDict["trees"][self.dlogName])
		else:
			self.dlogtree = DialogueTree({"chatter":{"trites":self.dlogName}})


	def act(self):
		if not self.timeOfDeath:
			return
		if not game.silent:
			game.Print(f"\n{self.name}'s turn!")
		self.attack()


	def Give(self,I):
		if hasMethod(I,"Eat"):
			I.Eat(self)
			self.updateLove(1)
			self.updateFear(-1)
		else:
			game.Print(f"{self.stringName('the',cap=1)} ignores your offer.")


	def Talk(self,player,game,world):
		if not player.hasCondition("wildtongued"):
			sound = sample(self.sounds,1)[0]
			waitKbInput(f'"{sound}"')
			return True
		if "met" not in self.memories:
			self.firstImpression(player)
		self.appraise(player,game)
		if not self.dlogtree.visit(self,player,game,world):
			game.Print(f"{self.name} says nothing...")


	def Touch(self,toucher):
		if self.species in Data.textures:
			game.Print(Data.textures[self.species])
		else:
			return super().Touch(toucher)


	def attack(self):
		if not game.silent:
			game.Print(f"{self.name} attack?")


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
	def __init__(self,name,desc,weight,durability,composition,mention=False,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.mention = mention
		self.parent = None


	### Operation ###

	def Break(self):
		if self.durability == -1:
			if not game.silent:
				game.Print(f"The {self.name} cannot be broken.")
			return False
		game.Print(f"The {self.name} breaks.")
		self.parent.removeFixture(self)
		return True




class Passage(Fixture):
	def __init__(self,name,desc,weight,durability,composition,connections,descname,passprep=None,mention=False,**kwargs):
		Fixture.__init__(self,name,desc,weight,durability,composition,mention=mention,**kwargs)
		self.connections = connections
		self.descname = descname
		self.passprep = passprep


	### Operation ###

	def Traverse(self,traverser,dir=None):
		if dir == None or dir not in self.connections:
			if len(set(self.connections.values())) == 1:
				dir = list(self.connections.keys())[0]
			else:
				msg = f"Which direction will you go on the {self.name}?\n> "
				dir = game.Input(msg)
		if dir in Data.cancels:
			return False
		if dir not in self.connections:
			game.Print(f"The {self.name} does not go '{dir}'.")
			return False

		game.Print(f"You go {dir} the {self.name}.")
		newroom = world[self.connections[dir]]
		traverser.changeRoom(newroom)
		return True




class Serpens(Item):
	def __init__(self,value,status=None):
		self.name = "Gold"
		self.desc = f"{str(value)} glistening coins made of an ancient metal"
		self.aliases = ["coin","coins","money","serpen","serpens"]
		self.plural = "gold"
		self.weight = value
		self.durability = -1
		self.composition = "gold"
		self.status = status if status else []
		self.descname = str(value) + " Gold"
		self.value = value


	### File I/O ###

	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		return {
			"__class__": self.__class__.__name__,
			"value": self.value,
			"status": self.status
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

	def stringName(self,det="",n=-1,plural=False,cap=0):
		strname = "Gold"
		strname = str(self.value) + " " + strname
		if det:
			strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname




class Weapon(Item):
	def __init__(self,name,desc,weight,durability,composition,might,sleight,sharpness,range,type,twohanded=False,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.might = might
		self.sleight = sleight
		self.sharpness = sharpness
		self.range = range
		self.twohanded = twohanded
		self.type = type


	def print(self):
		game.Print(f"{self.name} {self.might} {self.sleight}")
		game.Print(f"{self.sharpness} { self.twohanded} {self.range}")


	def Lick(self,licker):
		if self.composition in ("glass","bronze","iron","steel"):
			game.Print("It tastes like... blood.")
			licker.takeDamage(3,"s")
			return True

		if self.composition in Data.tastes:
			game.Print(Data.tastes[self.composition])
		if self.composition in Data.scents:
			game.Print(Data.scents[self.composition].replace("scent","taste"))

			



class Shield(Item):
	def __init__(self,name,desc,weight,durability,composition,prot,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.prot = prot




class Armor(Item):
	def __init__(self,name,desc,weight,durability,composition,prot,slots=None,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.prot = prot
		self.slots = slots if slots else []
		if type(slots) is not list:
			self.slots = [slots]


	def Equip(self):
		pass


	def Unequip(self):
		pass




class Compass(Item):
	def Orient(self):
		game.Print("Orienting you northward!")










player = Player("","",0,[0]*10,0,0,0,0)
defaultRoom = Room("","","",{},[],[],[])
game = Game(-1,defaultRoom,defaultRoom,-1,-1,{},{})
world = {}