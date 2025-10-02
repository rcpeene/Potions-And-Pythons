# Core.py
# This file contains all core functions and classes used throughout the game
# This file is a dependency of Objects.py and is dependent on Data.py

# It consists of two main parts;
# 1. Core functions			(used in Objects.py, Menu.py, and Parser.py)
# 2. Dialogue Classes		(DialogueNode and DialogueTree)
# 3. Core class definitions	(empty, game, room, item, creature, player, etc.)

from time import sleep
from random import randint,sample,choice,choices
from math import floor, sqrt
from bisect import insort
from collections.abc import Iterable
import sys, os, re

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
	return term == obj.name.lower() or term == obj.nounPhrase().lower() or term in obj.aliases


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


# color text using ANSI formatting
def Tinge(*args,color=None):
	colorMap = {
		"r":"31", "o": "38;5;215", "y":"38;5;227", "g":"32", 
		"b":"34", "m":"35", "k":"90", "w":"37"
	}
	if color is not None:
		args = list(args)
		c = colorMap[color]
		args[0] = f"\033[{c}m" + args[0]
		args[-1] = args[-1] + f"\033[37m"
	
	return tuple(args)


# used to calculate tinged string display lengths by ignoring formatting chars
def displayLength(text):
	# Regular expression to match ANSI escape sequences
	ansi_escape = re.compile(r"\033\[[0-9;]*m")
	l = len(ansi_escape.sub("", text.replace("\n","")))
	return l


def Print(*args,end="\n",sep="",delay=0.002,color=None,allowSilent=True):
	if game.silent and allowSilent:
		return
	if len(args) > 1 and sep=="":
		sep=" "
	args = [str(arg) for arg in args]
	printLength = sum(displayLength(s) for s in args) + displayLength(sep)*(len(args)-1) + displayLength(end)
	if color is not None:
		args = Tinge(*args,color=color)
	if game.mode == 1 or delay is None:
		print(*args,end=end,sep=sep)
		return printLength

	sleep(delay)
	sys.stdout.flush()
	sleep(delay)
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
	return printLength


# waits for any keyboard input
def waitKbInput(text=None,delay=0.005,color=None):
	sys.stdout.flush
	if text is not None:
		Print(text,delay=delay,color=color,allowSilent=False)
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


def Input(text="",cue="\n> ",low=True,delay=0.005,color=None):
	sys.stdout.flush()
	# should never be silent when asking for input
	Print(text,end="",delay=delay,color=color,allowSilent=False)
	flushInput()
	ret = input(cue)
	if low:
		ret = ret.lower()
	return ret


def InputLoop(prompt,cue="> ",acceptKey=None,escapeKey=None,refuseMsg="",helpMsg="Type 'cancel' to undo.",color=None,delay=0.005):
	if acceptKey is None:
		acceptKey = lambda inp: inp
	if escapeKey is None:
		escapeKey = lambda inp: inp in Data.cancels
	invalid_count = 0
	inp = Input(prompt,"\n"+cue,color=color,delay=delay)
	if refuseMsg != "":
		refuseMsg += "\n"
	while True:
		if inp in ("","\n"):
			inp = Input("",cue)
			continue
		if escapeKey(inp):
			return None
		acceptInp = acceptKey(inp) 
		if acceptInp is not None:
			return acceptInp
		invalid_count += 1
		if invalid_count >= 3:
			Print(helpMsg,color="k",delay=delay)
		inp = Input(refuseMsg,cue,color="k",delay=delay)


# prints a question, gets a yes or no, returns True or False respectively
def yesno(question,delay=0.005,color=None):
	def acceptKey(inp):
		if inp in Data.yesses:
			return True
		elif inp in Data.noes:
			return False
		else:
			return None
	refuseMsg = "Enter yes or no."
	return InputLoop(question,acceptKey=acceptKey,escapeKey=None,helpMsg="",refuseMsg=refuseMsg,color=color,delay=delay)


# prints a timed ellipsis, used for dramatic transitions
def ellipsis(n=3,color=None):
	for i in range(n):
		sleep(1)
		Print(".",color=color)
	sleep(1)
	flushInput()


# prints a list of strings, l, into n columns of width w characters
# if an element is longer than one column, it takes up as many columns as needed
def columnPrint(l,n,w=None,delay=0,color=None):
	# automatically set column width based on longest item
	termLengths = [displayLength(term) for term in l]
	if w is None:
		w = max(termLengths) + 2
	assert w > 1

	# k is the number of characters that have been printed in the current row
	k = 0
	# for each string element in l
	for term, length in zip(l,termLengths):
		# if the string is longer than remaining row width; print on a new row
		if length >= (n*w) - k:
			# subtract 1 to ignore newline
			k = Print("\n" + term,end="",delay=delay,color=color)
		# if the string is short enough, print it, increment k
		else:
			k += Print(term,end="",delay=delay,color=color)
		# to preserve column alignment, print spaces until k is divisble by w
		spaces = w - (k % w)
		k += Print(spaces * ' ',end="",delay=delay,color=color)
	Print()


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
			if entry[0].nounPhrase() == obj.nounPhrase():
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
			liststring += obj.nounPhrase(n=count)
		elif i == l-2:
			liststring += obj.nounPhrase(n=count) + " and "
		else:
			liststring += obj.nounPhrase(n=count) + ", "
	return liststring


# used on room area conditions to extract the info of the condition it causses
def extractConditionInfo(roomCondition):
	if not roomCondition.startswith("AREA"):
		raise Exception("Extracting condition info from invalid area condition")
	condInfo = roomCondition.split(" ")
	name = ' '.join(condInfo[1:-1])
	dur = int(condInfo[-1])
	return [name,dur]


# rolls n dice of range d, adds a modifier m, returns number
def diceRoll(n,d,m=0):
	if d < 1:
		n = 0
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


# returns a number n, bounded by min and max
def bound(n,min,max): return min if n < min else (max if n > max else n)


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
	matches = set()
	if key(root):
		matches.add(root)
	matches = objQueryRecur(root,matches,key,d)
	return matches


def objQueryRecur(node,matches,key,d):
	# if node is terminal: return
	if not hasMethod(node,'contents'):
		return matches

	for obj in node.contents():
		# check if obj is a match
		if key(obj): matches.add(obj)
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
		assert isinstance(obj, (Item, Creature)), f"object is not Item or Creature: {obj}, it is type {type(obj)}"
		obj.assignRefs(parent)
		assignRefsRecur(obj)


# removes any room links values which don't exist in the world
# to prevent errors if the world file was written incorrectly
# also assigns parents for all world objects (read objQuery() comments)
# also assigns dialogue trees for speakers and validates them
def buildWorld():
	# assign all room links to existing rooms
	# ensure all room names are stored as lowercase
	for roomName in world.copy():
		room = world[roomName]
		del world[roomName]
		if room.name.lower() in world:
			raise Exception("Room name exists in world already... two rooms may not have the same name.")
		world[room.name.lower()] = room

	# register all objects that already have an ID
	for room in world.values():
		for obj in room.objTree():
			if obj.id is not None:
				game.registerObject(obj)

	# assign IDs to all items and creatures that don't have one
	for room in world.values():
		for obj in room.objTree():
			if obj.id is None:
				obj.id = game.getNextID()
				game.registerObject(obj)

	# assign references for all rooms and objects, and assign dialogue trees
	for room in world.values():
		assert isinstance(room, Room)
		room.assignRefs()
		assignRefsRecur(room)

		# assign the dialogue trees for all creatures and validate them
		for creature in objQuery(room, d=3, key=lambda x: isinstance(x,Speaker)):
			creature.buildDialogue()



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
	def __init__(self,parent,label,idx,lastTriteRemark=None,visitLimit=None,rapportReq=None,guardCase="True",isCheckpoint=False,loveMod=0,fearMod=0,repMod=0,memories=None,events=None,remark=None,trites=None,cases=None,replies=None,children=[],reactTrue=False):
		self.parent = parent
		self.label = label
		self.id = self.parent.id + (idx,)
		self.lastTriteRemark = lastTriteRemark
		self.visitLimit = visitLimit
		self.guardCase = guardCase
		self.rapportReq = rapportReq
		self.isCheckpoint = isCheckpoint
		self.children = [DialogueNode(self,label,i,**childJson) for i,childJson in enumerate(children)]

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


	### Dunder Methods ###

	def __str__(self):
		return f"{self.label} dlogNode {self.id}"


	### File I/O ###

	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		del jsonDict["id"]
		del jsonDict["globals"]
		return jsonDict
	

	@classmethod
	def convertFromJSON(cls,d):
		return cls(**d)


	# ensures the following:
	# that the tree is structurally valid by determining the ID
	# that all cases (which are stored in JSON as strings) ints or evaluate to a bool
	# that all trites (which are stored in JSON as strings) are valid sets in Data.py
	# note that speaker, player, game, and world are provided to ensure eval() is valid
	def ensureIntegrity(self,speaker,**kwargs):
		err = f"Invalid guard case node condition in {speaker.name}'s node {self.id}: {self.guardCase}"
		context = kwargs | {"speaker":speaker}
		guardCaseRes = eval(self.guardCase,self.globals,context)
		assert type(guardCaseRes) is bool, err
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
		Print()
		for i, reply in enumerate(self.replies):
			Print(f'{i+1}. {reply}')

		def acceptKey(inp):
			try:
				return self.children[int(inp)-1]
			except:
				return None

		refuseMsg = "That is not one of the options. Input a number or type 'cancel'."
		return InputLoop("",acceptKey=acceptKey,refuseMsg=refuseMsg)


	def hop(self,speaker,**kwargs):
		if self.visitLimit is not None:
			if speaker.dlogtree.getVisitCount(self.id) >= self.visitLimit:
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
			speaker.dlogtree.checkpoint = self.id
		if self.remark:
			waitKbInput(f'"{self.remark}"',color="y")
		elif self.trites:
			tritepool = set()
			for trite in self.trites:
				tritepool |= set(game.dlogDict["trites"][trite])

			samples = sample(tritepool,2)
			triteRemark = samples[0]
			if triteRemark == self.lastTriteRemark:
				triteRemark = samples[1]

			waitKbInput(f'"{triteRemark}"',color="y")
			self.lastTriteRemark = triteRemark

		# return next node if this node has children
		nextNode = None
		if self.cases:
			nextNode = self.conditionalHop(speaker,**kwargs)
		elif self.replies:
			nextNode = self.replyHop()
		else:
			for child in self.children:
				if child.hop(speaker,**kwargs):
					nextNode = child
					break

		# count this node as successfully visited
		speaker.dlogtree.countVisit(self.id)

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
		if nextNode and speaker.dlogtree.checkpoint == self.id:
			speaker.dlogtree.checkpoint = None
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
	def __init__(self,parent,label,idx,treeJson):
		DialogueNode.__init__(self,parent,label,idx)
		assert len(self.children) == 0, "Reaction node has non-reaction children"
		self.reactions = {key: DialogueNode(self,label,i,**childJson) for i,(key,childJson) in enumerate(treeJson.items())}
		self.children = (child for child in self.reactions.values())


	def __getitem__(self,key):
		return self.reactions[key]


	def __contains__(self,key):
		return key in self.reactions



class DialogueTree():
	def __init__(self,label,treeJson,visitCounts=None,checkpoint=None):
		self.label = label
		self.id = ()
		# note that chatter is required to be populated; there must be some dialogue
		self.surprise = DialogueNode(self,label,0,**treeJson.get("surprise",{}))
		self.quest = DialogueNode(self,label,1,**treeJson.get("quest",{}))
		self.colloquy = DialogueNode(self,label,2,**treeJson.get("colloquy",{}))
		self.chatter = DialogueNode(self,label,3,**treeJson["chatter"])
		self.reactions = ReactionNode(self,label,4,treeJson.get("reactions",{}))
		self.children = (self.surprise,self.quest,self.colloquy,self.chatter,self.reactions)
		self.visitCounts = {} if visitCounts is None else visitCounts
		self.visitCounts = self.deserializeTupDict(self.visitCounts)
		self.checkpoint = None


	### Dunder Methods ###

	def __str__(self):
		return f"{self.label} dlog tree"


	### File I/O ###

	def deserializeTupDict(self,tupDict):
		return {tuple(tupStr.split(',')): val for tupStr, val in tupDict.items()}


	def convertToJSON(self):
		return {
			"label": self.label,
			"visitCounts": {str(id): count for id, count in self.visitCounts.items()},
			"checkpoint": self.checkpoint
		}


	def copy(self):
		treeCopy = DialogueTree(self.label,{"chatter":{}})
		treeCopy.surprise = self.surprise
		treeCopy.quest = self.quest
		treeCopy.colloquy = self.colloquy
		treeCopy.chatter = self.chatter
		treeCopy.reactions = self.reactions
		treeCopy.children = self.children
		return treeCopy


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
		for id in self.visitCounts.values():
			try:
				self.findNode(id)
			except:
				raise Exception(f"Visited node {id} not found in {speaker.name}'s dialogue tree")			
		if not self.chatter.hasDefiniteDialogue():
			raise Exception(f"{speaker.name} dialogue Tree has no definite dialogue in {speaker.room()}")


	### Operation ###
		
	def countVisit(self,nodeId):
		if nodeId in self.visitCounts:
			self.visitCounts[nodeId] += 1
		else:
			self.visitCounts[nodeId] = 1


	def getVisitCount(self,nodeId):
		if nodeId in self.visitCounts:
			return self.visitCounts[nodeId]
		return 0


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
					if branch is self.colloquy:
						speaker.rapport += 1
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
		print("new parley!")
		self.checkpoint = None
		self.visitCounts = {}




############################
## SUPERCLASS DEFINITIONS ##
############################


# Empty is a class usually used as a placeholder for items. It serves to act as a dummy item which has mostly null values
class EmptyGear:
	_instance = None
	name = "[empty]"
	aliases = set()
	weight = 0
	durability = 0
	composition = None
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
		return self.name


	def __eq__(self, other):
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False


	### Getters ###

	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
		return ""


	def untetheredWeight(self):
		return 0


	def Weight(self):
		return 0


	def asWeapon(self):
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

		# used for saving portals in the world with unique links
		self.portallinks = 0

		# references to all objects in the world, each obj.id should be its key here
		self.objRegistry = {None: None}
		self.nextObjId = 0


	### Operation ###

	def getNextID(self):
		while self.nextObjId in self.objRegistry:
			self.nextObjId += 1
		return self.nextObjId


	def registerObject(self,obj):
		if obj.id in self.objRegistry:
			raise Exception(f"Object ID {obj.id} already exists in registry")
		self.objRegistry[obj.id] = obj


	# exits  the previous room and enters the new room
	def changeRoom(self,newroom):
		if newroom is self.currentroom:
			return
		# if newroom != self.currentroom:
		self.clearPronouns()
		clearScreen()
		self.prevroom = self.currentroom
		self.currentroom = newroom
		newroom.describe()
		return True


	# passes time for each room, and each creature in each room
	# important for decrementing the duration counter on all status conditions
	def passTime(self,t=1):
		prev_hour = self.hour()
		self.time += t
		self.silent = player.hasAnyCondition("asleep","dead")
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
		adjacentRooms = [room for room in Sroom.allLinks().values() if isinstance(room,Room)]
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


	# returns a list of objects in rendered rooms which fit a certain condition
	def queryRooms(self,key=lambda x:True,d=3):
		matchingObjects = []
		for room in self.renderedRooms():
			matchingObjects += room.query(key=key,d=d)
		return matchingObjects


	# returns a set of all objects in the rendered world
	# does not include the player or anything in player inv
	def getAllObjects(self):
		allObjects = []
		for room in self.renderedRooms():
			allObjects |= objQuery(room,key=lambda x:True,d=3)
		return allObjects


	# True if there's an object in rendered rooms whose name matches objname
	# not case sensitive
	def inWorld(self,term):
		key = lambda obj: nameMatch(term,obj)
		objects = self.queryRooms(key)
		return len(objects) > 0


	def hour(self):
		return Data.hours[(self.time % self.daylength) // self.hourlength]


	def checkMoon(self):
		if self.currentroom.altitude < 0 or self.currentroom.type == "shelter":
			return
		mooncycle = (self.time % self.monthlength) // self.daylength
		if mooncycle == 0:
			Print("It is a new moon.",color="b")
			self.events.add("new moon")
		elif mooncycle == 7:
			Print("It is a full moon.",color="b")
			self.events.add("full moon")
		if "new moon" in self.events:
			self.events.remove("new moon")
		if "full moon" in self.events:
			self.events.remove("full moon")


	def checkAstrology(self,update=False):
		if self.currentroom.altitude < 0 or self.currentroom.type == "shelter":
			return
		darkhours = ("hearth","cat","mouse","owl","serpent","wolf")
		aurora_cycle = self.time % 2000
		if aurora_cycle >= 0 and aurora_cycle < 100 and self.hour() in darkhours:
			if "aurora" not in self.events or update:
				Print("There is an aurora in the sky!",color="b")			
			self.events.add("aurora")
		elif "aurora" in self.events:
			self.events.remove("aurora")
			Print("The aurora is over.")

		meteor_cycle = self.time % 3500
		if meteor_cycle >= 0 and meteor_cycle < 300 and self.hour() in darkhours:
			if "meteor shower" not in self.events or update:
				Print("There is a meteor shower in the sky!",color="b")
			self.events.add("meteor shower")
		elif "meteor shower" in self.events:
			self.events.remove("meteor shower")
			Print("The meteor shower is over.")

		lighthours = ("rooster","juniper","bell","sword","willow","lily")
		eclipse_cycle = self.time % (self.monthlength*3+100)
		if eclipse_cycle > 0 and eclipse_cycle < 30 and self.hour() in lighthours:
			if "eclipse" not in self.events or update:
				Print("There is a solar eclipse in the sky!",color="b")
			self.events.add("eclipse")
		elif "eclipse" in self.events:
			self.events.remove("eclipse")
			Print("The solar eclipse is over.")


	### User Output ###		

	def startUp(self):
		clearScreen()
		player.printStats()
		Print()
		self.describeRoom()
		game.checkDaytime()
		game.checkAstrology(update=True)


	def describeRoom(self):
		self.currentroom.describe()
		if not isinstance(player.parent,Room):
			Print(f"You are in {-player.parent}.")
		# if player.carrying:
		# 	Print(f"You are carrying {~player.carrying}.")


	def checkDaytime(self):
		if self.currentroom.altitude < 0:
			return
		if self.hour() in ("stag","rooster","juniper"):
			Print("It is morning.")
		if self.hour() in ("bell","sword","willow","lily"):
			Print("It is day.")
		if self.hour() in ("hearth","cat"):
			Print("It is evening.")
		if self.hour() in ("mouse","owl","serpent","wolf"):
			Print("It is night.")
			self.checkMoon()


	def LookUp(self,target):
		if self.currentroom.altitude < 0:
			Print("You can't see that from here.")
		
		if target == "sky":
			target = "sun" if self.hour() in Data.dayhours else "moon"		

		if "eclipse" in self.events:
			Print("The bold red sun is blackened by the ominous moon. The world is dark above and below but for the ring of violet light tracing the moon. Those golden lines of fire that scar the moon's surface seem like cracks through which the sun's rays seep faintly through. All is still in the heavens as they bear witness to this solemn union.",color="b")
			player.takeDamage(5,"r")
		elif "eclipse" not in self.events and target in ("eclipse","solar eclipse"):
			Print("There's no eclipse happening right now.")
		elif target == "sun":
			if self.hour() in ("stag","rooster","juniper"):
				Print("A burning ball of red fire marches upward in the sky. In the morning air it paints the heavens a tinge of pale green.")
			elif self.hour() in ("bell","sword","willow","lily"):
				Print("A burning ball of red fire hangs high in the sky. It warms your face with its bold glow.")
			elif self.hour() in ("hearth","cat"):
				Print("A burning ball of red fire rests in the sky. As it descends toward the horizon it draws a curtain of violet across the world above.")
			else:
				Print("The sun isn't out right now.")
		elif target in ("moon","stars"):
			if self.hour() in Data.nighthours:
				if "full moon" in self.events:
					Print("A shimmering golden orb dances in the sky pouring whispers of light. You can make out traces of strange golden fire on its surface. The stars seem to dance around it joyously. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate.",color="b")
				elif "new moon" in self.events:
					Print("On a night without the moon the world is full of silence and cold. The stars seem to shiver lonesomely. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate.",color="b")
				else:
					Print("A shimmering golden orb dances in the sky pouring whispers of light. You can make out traces of strange golden fire on its surface. It hangs amongst a scattering of sparkling drops on all sides. You can make out the constellations of Zork, Norman, and Glycon acting out the tales of fate.")
			elif target == "moon":
				Print("The moon isn't out right now.")
			elif target == "stars":
				Print("The stars aren't out right now.")
		
		if "aurora" in self.events:
			Print("Tides of the red, blue, and green aurora gently sweep over the sky. The colors seem to bathe the heavens as it caresses the shimmering silver stars.",color="b")
		elif target in ("aurora","auroras"):
			Print("There's no aurora happening right now.")

		if "meteor shower" in self.events:
			Print("Bolts of yellow light streak deftly across the sky, leaving their imprint for no more than a moment. The almost seem to take turns whizzing past like a flock of birds, eager to follow one another toward the edge of the heavens.",color="b")
		elif target in ("shower","meteors","meteor shower"):
			Print("There's no meteor shower happening right now.")

		return True



# The Room class is the fundamental unit of the game's world.
# The world dict, consists of key:value pairs of the form,
# room name:room object

# Importantly, each room contains an links dict, whose keys are directions...
# such as 'north', 'up', or 'beyond', and whose values are the string names...
# of the room that it leads to.

# Thus, from any room, there are some directions which will yield a room name, # which can be plugged into the world dict to yield the neighboring room object

# In this way, every Room object can be thought of like a node in a large...
# directed graph, facilitated by the world dict, where the links dict specifies
# the edges from a given node to its neighboring nodes.
class Room():
	def __init__(self,name,domain,desc,links,fixtures,items,creatures,size=10,type=None,altitude=0,passprep=None,status=None):
		self.name = name
		self.domain = domain
		self.desc = desc
		self.links = links
		self.fixtures = fixtures
		self.items = items
		self.creatures = creatures
		self.size = size
		# "road", "shelter", None
		self.type = type
		# 0 for outdoors, -1 for indoors, <-1 for underground, >0 for in the sky
		self.altitude = altitude
		self.passprep = "at" if passprep is None else passprep
		self.status = status if status else []
		self.parent = None


	### Dunder Methods ###

	def __repr__(self):
		return f"Room({self.name}, {[room.name for room in self.links.values()]})"


	def __str__(self):
		return self.name


	def __neg__(self):
		return "the " + self.name


	def __pos__(self):
		return "The " + self.name
	

	def __invert__(self):
		return "a " + self.name


	### File I/O ###

	def assignRefs(self):
		for dir, dest in self.links.items():
			if isinstance(dest,str) and dest in world:
				self.links[dir] = world[dest]
			else:
				raise Exception(f"Error: Room {self.name} has a connection to unknown destination '{dest}'.")

		assert all(isinstance(dest,Room) for dest in self.links.values()), f"Error: Room {self.name} has a exit to non-Room '{dest}'."


	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		jsonDict["links"] = {}
		for dir, dest in self.links.items():
			assert isinstance(dest, Room), f"Trying to save room {self.name} with exit to non-Room '{dest}'."
			jsonDict["links"][dir] = dest.name.lower()
		return jsonDict


	### Operation ###

	# add one-way link to a neighboring Room
	# to ensure a bidirectional link between Rooms...
	# this method would have to be called once on each room.
	def addLink(self,dir,loc):
		self.links[dir] = loc


	def addItem(self,I):
		# ensure only one bunch of Gold exists here
		if isinstance(I,Serpens):
			for item in self.items:
				if isinstance(item,Serpens):
					item.merge(I)
					return
		insort(self.items,I)
		I.parent = self
		I.timeDespawn()
		return True


	def add(self,O):
		if not self.canAdd(O):
			return False
		if isinstance(O,Creature):
			return self.addCreature(O)
		elif isinstance(O,Fixture):
			return self.addFixture(O)
		elif isinstance(O,Item):
			return self.addItem(O)


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
		# TODO: should this even be possible? fixtures are fixed...
		if F in self.fixtures:
			self.fixtures.remove(F)


	def remove(self,O):
		if isinstance(O,Creature):
			return self.removeCreature(O)
		elif isinstance(O,Fixture):
			return self.removeFixture(O)
		elif isinstance(O,Item):
			return self.removeItem(O)


	def addAreaCondition(self,areacond):
		cond,dur = extractConditionInfo(areacond)
		key = lambda x: isinstance(x,Creature)
		for creature in self.query(key=key):
			creature.addCondition(cond,dur)


	def removeAreaCondition(self,areacond):
		cond,dur = extractConditionInfo(areacond)
		# depending on how you want room conditions to work, perhaps remove this
		if dur != -1:
			return
		key = lambda x: isinstance(x,Creature)
		for creature in self.query(key=key):
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
		# copy to prevent removing-while-iterating errors
		for name,duration in self.status.copy():
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


	# describe the room, and apply any room effects to the obj entering
	def enter(self,obj):
		self.add(obj)
		# add status conditions from this room
		for cond,dur in self.status:
			applyCond = False
			if cond.startswith("AREA"):
				applyCond = True
			elif cond.startswith("ITEM") and isinstance(obj,Item):
				applyCond = True
			elif cond.startswith("CREATURE") and isinstance(obj,Creature):
				applyCond = True
			if applyCond:
				[name,dur] = extractConditionInfo(cond)
				obj.addCondition(name,dur)


	# remove any room effects from the obj exiting
	def exit(self,obj):
		# remove status conditions from this room
		condsToRemove = [pair for pair in obj.status if pair[1] == -1]
		for cond,dur in condsToRemove:
			obj.removeCondition(cond,-1)
		self.remove(obj)


	### Getters ###

	def canAdd(self,I):
		# TODO: maybe make rooms have a capacity? perhaps 10*size
		return True


	def space(self):
		# TODO: maybe make rooms have a capacity? perhaps 10*size
		return 10000


	# returns dict of links, where keys are (direction,portal) and values are room/object names
	def allLinks(self,d=3):
		links = {}
		for dir in self.links:
			links[(dir,None)] = self.links[dir]
		# for each portal, add its links to links
		for portal in self.query(key=lambda x: isinstance(x,Portal),d=d):
			for dir in portal.getLinksForParent():
				links[(dir,portal)] = portal.links[dir]
		return links


	def allDirs(self):
		return (tuple[0] for tuple in self.allLinks())


	def itemNames(self):
		return [item.name for item in self.items]


	# returns a list of Passage objects within the room's items
	def getPassages(self):
		return [item for item in self.query(key=lambda x: isinstance(x,Passage))]


	def creatureNames(self):
		return [creature.name for creature in self.creatures]


	def contents(self):
		return self.fixtures + self.items + self.creatures


	def allCreatures(self):
		creatures = objQuery(self,key=lambda obj: isinstance(obj,Creature),d=3)
		return sorted(list(creatures), key=lambda x: x.MVMT(), reverse=True)


	# wrapper for objQuery, sets the degree of the query to 2 by default
	def query(self,key=None,d=2):
		matches = objQuery(self,key=key,d=d)
		return matches


	def nameQuery(self,term,d=2):
		term = term.lower()
		key = lambda obj: nameMatch(term,obj)
		return self.query(key=key,d=d)


	def objTree(self):
		matches = objQuery(self,d=3)
		matches.remove(self)
		return matches


	# given a direction (like 'north' or 'down)...
	# return the first portal object with that direction in its links
	def getPortalsFromDir(self,dir):
		portals = []
		for thisDir, portal in self.allLinks(d=0):
			if dir == thisDir:
				portals.append(portal)
		return portals


	# if the given room object, dest, is in one of the rooms links, then find the direction it is in from the room.
	def getDirPortalPair(self,dest):
		for (dir,portal), room in self.allLinks().items():
			if nameMatch(dest,room):
				return dir, portal
		return None, None


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
		Print("\n"+self.domain+"\n"+self.name)
		# if player.countCompasses() == 0:
		# 	Print("\n" + ambiguateDirections(self.desc))
		# else:
		Print("\n" + self.desc)
		self.describeItems()
		self.describeCreatures()


	# prints all the items of the room in sentence form
	def describeItems(self):
		items = self.listableItems()
		if len(items) != 0:
			Print(f"There is {listObjects(items)}.")
			game.setPronouns(items[-1])


	# prints all the creatures in the room in sentence form
	def describeCreatures(self):
		select = lambda creature: creature not in (player, player.carrying, player.riding)
		listCreatures = [creature for creature in self.creatures if select(creature)]
		if len(listCreatures) != 0:
			Print(f"There is {listObjects(listCreatures)}.")
		for creature in listCreatures:
			game.setPronouns(creature)



# The Item class is the main game object class of things that cannot act
# Anything in a Room that is not a Creature will be an Item
# All items come with a name, description, weight, and durability
class Item():
	def __init__(self,name,desc,weight,durability,composition,id=None,aliases=None,status=None,plural=None,determiner=None,pronoun="it",longevity=None,despawnTimer=None,scent=None,taste=None,texture=None):
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
		self.aliases = set(aliases) if aliases else set()
		if plural is None:
			self.plural = self.name + 's'
		else:
			self.plural = plural
		self.determiner=determiner
		self.pronoun = pronoun
		self.parent = None
		self.id = id


	### File I/O ###

	def assignRefs(self,parent):
		self.parent = parent


	### Dunder Methods ###

	def __repr__(self):
		return f"Item({self.name}, {self.desc}, {self.weight}, {self.durability})"


	def __str__(self):
		return self.nounPhrase()


	def __neg__(self):
		return self.nounPhrase('the')


	def __pos__(self):
		return self.nounPhrase('the',cap=1)
	

	def __invert__(self):
		return self.nounPhrase('a')


	def __lt__(self,other):
		return self.name.lower() < other.name.lower()


	def __eq__(self,other) :
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False


	def __hash__(self):
		return hash(id(self))


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
				self.parent.remove(self)			


	def changeLocation(self,newparent):
		prevparent = self.parent
		
		prevparent.exit(self)
		newparent.enter(self)


	def Obtain(self,creature):
		pass


	def Break(self):
		if self.durability == -1:
			if not game.silent:
				Print(f"{+self} cannot be broken.")
			return False
		if self.room() is game.currentroom:
			Print(f"{+self} breaks.")
		self.parent.remove(self)
		return True


	def Fall(self,height=0,room=None):
		if room is None:
			room = self.room()
		if self.room() is game.currentroom:
			Print(f"{+self} falls down.")

		while room.altitude != 0 and "down" in room.links:
			height += room.size
			room = room["down"]
		if room != self.room():
			self.changeLocation(room)
			if self.room() is game.currentroom:
				Print(f"{+self} falls from above.")
				
		self.takeDamage(height,"b")
		return True


	def Use(self,user):
		if user not in self.ancestors():
			Print(f"{+self} is not in your inventory.")
			return False
		Print(f"You use {-self}")


	def takeDamage(self,dmg,type):
		if self in player.surroundings().objTree():
			Print(f"{+self} took {dmg} {Data.dmgtypes[type]} damage.")
		if self.durability != -1 and dmg > self.durability:
			return self.Break()


	def Bombard(self,missile):
		assert isinstance(missile,Projectile)
		if diceRoll(1,100) < bound(missile.aim+self.weight+10,1,99):
			return missile.Collide(self)
		return False


	def nullDespawn(self):
		self.despawnTimer = None
		

	def timeDespawn(self):
		self.despawnTimer = self.longevity


	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		insort(self.status,[name,dur])
		return True


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,reqName=None,reqDuration=None):
		# copy to prevent removing-while-iterating errors
		for name,duration in self.status.copy():
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])


	### Getters ###

	# this is a meaningful method for Creatures, for Items it is same as Weight
	def untetheredWeight(self):
		return self.weight


	def Weight(self):
		return self.weight


	# should be empty for items that aren't containers
	def objTree(self):
		matches = objQuery(self,d=3)
		matches.remove(self)
		return matches


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


	def asProjectile(self):
		return Projectile(self.name,self.desc,self.weight,self.durability,self.composition,min1(self.weight//4),0,"b",item=self)


	# Used to create a generic Weapon() if this item is used to attack something
	def asWeapon(self):
		#TODO: if item is too large/heavy, make it two-handed
		return Weapon(self.name,self.desc,self.weight,self.durability,self.composition,min1(self.weight//4),0,0,0,"b")


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



	### User Output ###

	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
		if det.lower() == "the":
			strname = self.name
		else:
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
		Print(f"It's {~self}.")
		Print(f"{self.desc}.")


	def reflexive(self):
		if self.pronoun in Data.reflexives:
			return Data.reflexives[self.pronoun]
		else:
			return "itself"


# The Creature class is the main class for anything in the game that can act
# Anything in a Room that is not an Item will be a Creature
# The player is a Creature too
# Creatures have 10 base stats, called traits
# They also have abilities; stats which are derived from traits through formulas
class Creature():
	def __init__(self,name,desc,weight,traits,hp,id=None,mp=0,money=0,inv=None,gear=None,love=0,fear=0,carrying=None,carrier=None,riding=None,rider=None,composition="flesh",memories=None,appraisal=None,status=None,descname=None,aliases=None,plural=None,determiner=None,pronoun="it",timeOfDeath=None,lastAte=0,lastSlept=0,regenTimer=0,alert=False,seesPlayer=False,sawPlayer=-1):
		self.name = name
		self.desc = desc
		self.descname = descname if descname else name
		self.aliases = set(aliases) if aliases else set()
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
		
		# this gets decompressed or reassigned by assignRefs
		self.parent = None
		self.id = id
		self.riding = riding
		self.rider = rider
		self.carrying = carrying
		self.carrier = carrier
		self.gear = gear if gear else Data.initgear

		self.weapon = EmptyGear()
		self.weapon2 = EmptyGear()
		self.shield = EmptyGear()
		self.shield2 = EmptyGear()

		self.composition = composition
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
		return self.nounPhrase()


	def __neg__(self):
		return self.nounPhrase('the')


	def __pos__(self):
		return self.nounPhrase('the',cap=1)


	def __invert__(self):
		return self.nounPhrase('a')


	def __eq__(self, other) :
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False


	def __hash__(self):
		return hash(id(self))


	def __lt__(self,other):
		if isinstance(other, Creature):
			return self.MVMT() < other.MVMT()
		return self.name.lower() < other.name.lower()


	### File I/O ###
	
	def assignRefs(self,parent):
		self.parent = parent

		self.carrying = game.objRegistry[self.carrying]
		self.carrier = game.objRegistry[self.carrier]
		self.riding = game.objRegistry[self.riding]
		self.rider = game.objRegistry[self.rider]

		uncompGear = {}
		for slot, idx in self.gear.items():
			if idx == "carrying":
				assert self.carrying is not None, f"Error: Creature {self.name} has gear slot '{slot}' set to 'carrying' but is not carrying anything."
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
			if isinstance(item,Creature):
				cGear[slot] = "carrying"
			elif item is EmptyGear():
				cGear[slot] = None
			else:
				cGear[slot] = self.inv.index(item)
		return cGear


	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		# convert the gear dict to a form more easily writable in a JSON object
		compressedGear = self.compressGear()
		self.carrying = self.carrying.id if self.carrying else None
		self.carrier = self.carrier.id if self.carrier else None
		self.riding = self.riding.id if self.riding else None
		self.rider = self.rider.id if self.rider else None

		jsonDict = self.__dict__.copy()
		dictkeys = list(jsonDict.keys())
		# these attributes do not get stored between saves (except gear)
		for key in dictkeys:
			if key.lower() in Data.traits or key in {"gear","weapon","weapon2","shield","shield2"}:
				del jsonDict[key]
		jsonDict["gear"] = compressedGear
		# convert traits to a form more easily writable in a JSON object
		jsonDict["traits"] = [self.str,self.skl,self.spd,self.stm,self.con,self.cha,self.int,self.wis,self.fth,self.lck]

		# these lines seem redundant (the menu functions handle parent and __class__ attributes)
		# but they're required specifically for reading/writing the Player object
		# they're in Creature class because otherwise I'd have to copy a nearly identical method
		if "parent" in jsonDict:
			del jsonDict["parent"]
		jsonDict["__class__"] = self.__class__.__name__
		return jsonDict


	### Operation ###

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		if self.hasCondition("dead"):
			return False
		prevhp = self.hp
		if(f"{type} vulnerability" in self.status): dmg *= 2
		if(f"{type} resistance" in self.status): dmg //= 2
		if(f"{type} immunity" in self.status): dmg = 0
		# bludgeoning damage can't kill you in one hit
		if type == "b" and self.hp > 1:
			self.hp = min1(self.hp-dmg)			
		# hp lowered to a minimum of 0
		else:
			self.hp = min0(self.hp-dmg)
		total_dmg = prevhp - self.hp
		dmgtype = Data.dmgtypes[type]
		if self.room() is game.currentroom:
			Print(f"{+self} took {total_dmg} {dmgtype} damage.",color="o")
		if self.hp == 0:
			self.death()


	# heals hp a given amount
	def heal(self,heal,overflow=False):
		if self.hp + heal > self.MXHP() and not overflow:
			heal = self.MXHP() - self.hp
		if heal <= 0:
			return 0
		self.hp += heal
		if self is player:
			Print(f"You healed {heal} HP.",color="g")
		return heal


	def resurge(self,mana,overflow=False):
		if self.mp + mana > self.MXMP() and not overflow:
			mana = min0(self.MXHP() - self.mp)
		if mana <= 0:
			return 0
		self.mp += mana
		if self is player:
			Print(f"You regained {mana} MP.",color="b")
		return mana


	def updateMoney(self,money):
		self.money += money


	def updateLove(self,loveMod):
		self.RP = bound(loveMod,-100,100)


	def updateFear(self,fearMod):
		self.RP = bound(fearMod,-100,100)


	def asProjectile(self):
		comp = getattr(self,"composition","flesh")
		return Projectile(self.name,self.desc,self.weight,self.DFNS(),comp,self.weight//4,0,"b",item=self,pronoun=self.pronoun)


	# check if item can fit in inventory
	def canObtain(self,I):
		if isinstance(I,Creature):
			return False
		if I in self.ancestors():
			return False
		if isinstance(I,Serpens):
			return True
		if self.invWeight() + I.Weight() > 2*self.BRDN():
			return False
		return True


	# try to add an Item to Inventory
	# it will fail if the inventory is too heavy
	def add(self,I):
		if isinstance(I,Creature):
			return self.parent.add(I)
		if isinstance(I,Serpens):
			return True
		insort(self.inv,I)
		I.parent = self
		I.nullDespawn()
		return True


	# remove an Item from Inventory
	# if it was equipped, unequip it
	# if it has a Drop() method, call that
	# check if still hindered
	def remove(self,I,silent=False):
		for slot,obj in self.gear.items():
			if I is obj:
				self.unequip(slot,silent=silent)
		if I is self.carrying:
			self.removeCarry(silent=silent)
		if I in self.inv:
			self.inv.remove(I)
		if hasMethod(I,"Drop"):
			I.Drop(self)
		self.checkHindered()


	# takes an item from a source location
	# first checking if it can be added to Inventory
	# if it is added, remove it from source location
	# if it has an Obtain() method, call that
	# finally, check if the new inventory weight has hindered the creature
	def obtainItem(self,I,msg=None):
		oldParent = I.parent
		if self.canObtain(I):
			if self.add(I):
				oldParent.remove(I)
			if msg != None:
				Print(msg)
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
			if hasMethod(self.weapon,"asWeapon"):
				self.weapon = self.weapon.asWeapon()
		if not isinstance(self.weapon2,Weapon):
			if hasMethod(self.weapon,"asWeapon"):
				self.weapon2 = self.weapon.asWeapon()

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
	def unequip(self,slot,silent=False):
		assert slot in self.gear, f"'{slot}' is not a valid gear slot."
		I = self.gear[slot]
		if I is EmptyGear():
			return False
		if I is self.carrying:
			self.removeCarry(silent=silent)
		else:
			self.gear[slot] = EmptyGear()
			self.assignWeaponAndShield()
			if not silent:
				Print(f"You unequip your {I}.")
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
	def equipInHand(self,I,slot="right"):
		assert I in self.inv or I is self.carrying
		if I is self.gear["right"] or I is self.gear["left"]:
			return
		if getattr(self.gear["right"],"twohanded",False):
			self.unequip("right")

		if getattr(I,"twohanded",False):
			self.unequip("right")
			self.unequip("left")
		elif slot == "right" and not self.carrying:
			self.unequip("left")
			self.gear["left"] = self.gear["right"]
		elif slot == "left" and self.gear["right"] is EmptyGear:
			self.gear["right"] = self.gear["left"]
		else:
			self.unequip(slot)

		self.gear[slot] = I
		self.assignWeaponAndShield()
		if hasMethod(I,"Equip"): I.Equip(self)


	def addCarry(self,creature):
		assert isinstance(creature,Creature)
		self.unequip("left")
		if getattr(self.gear["right"],"twohanded",False):
			self.unequip("right")

		self.carrying = creature
		self.gear["left"] = creature
		self.checkHindered()


	def removeCarry(self,silent=False):
		if self is player and not silent:
			Print(f"You drop {-self.carrying}.")
		self.gear["left"] = EmptyGear()
		self.carrying.carrier = None
		self.carrying.removeCondition("restrained",-3)
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
		# copy to prevent removing-while-iterating errors
		for name,duration in self.status.copy():
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])


	def nullDespawn(self):
		pass
		

	def timeDespawn(self):
		pass


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
		if self.invWeight() + carryWeight <= self.BRDN():
			self.removeCondition("hindered")


	def checkHungry(self):
		return False


	def checkTired(self):
		return False


	def checkConditions(self):
		self.checkHindered()
		self.checkHungry()
		self.checkTired()


	# called when a creature's hp hits 0
	def death(self):
		self.timeOfDeath = game.time
		self.addCondition("dead",-3)
		Print(f"{+self} died.",color="o")
		self.descname = f"dead {self.descname}"
		self.aliases = self.aliases | {"dead " + a for a in self.aliases}
		n = diceRoll(3,player.LOOT(),-2)
		self.parent.add(Serpens(n))
		if not game.silent:
			Print(f"Dropped $ {n}.",color="g")
		if game.whoseturn is player:
			r = self.rating()
			# xp granted generally scales with rating
			xp = diceRoll(2, r//2, r-15)
			player.gainxp(xp)


	def Fall(self,height=0,room=None):
		Print(f"{+self} falls.",color="o")

		if self.hasCondition("flying"):
			Print(f"But {self.pronoun} is flying.")
			return False

		if room is None:
			room = self.room()
		while room.altitude != 0 and "down" in room.links:
			height += room.size
			room = room["down"]
		if room != self.room():
			self.changeLocation(room)

		if self.hasCondition("fleetfooted"):
			height = 0
		self.takeDamage(height,"b")
		return True


	def Eat(self,food):
		food.parent.remove(food)
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
		Print(f"{+self} ignores your offer.")


	### Behavior ###

	def changeLocation(self,newparent):
		# shouldn't be changing rooms alone if riding or being carried
		if self.carrier and self.carrier.parent is not newparent:
			return False
		if self.riding and self.riding.parent is not newparent:
			return self.riding.changeLocation(newparent)

		prevparent = self.parent

		prevparent.exit(self)
		if self is player and isinstance(newparent,Room):
			game.changeRoom(newparent)
		newparent.enter(self)

		# propagate location change to creatures riding or being carried
		if self.carrying and self.carrying.parent is not self.parent:
			self.carrying.changeLocation(newparent)
		if self.rider and self.rider.parent is not self.parent:
			self.rider.changeLocation(newparent)

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
			Print(f"You can't {dverb} {-target}, {target.pronoun} is {iverb} {looplink}")
			return True
		return False


	def Bombard(self,missile):
		assert isinstance(missile,Projectile)
		dodge = self.EVSN()
		if missile.speed < self.MVMT():
			# TODO: determine how they'll decide if they catch here
			if diceRoll(1,100) < 50 and hasMethod(self,"Catch"):
				dodge = -10
				if self.Catch(missile):
					return True
		if diceRoll(1,100) < bound(missile.aim+missile.speed-dodge,1,99):
			return missile.Collide(self)
		return False


	def Carry(self,carrier):
		if self.checkTetherLoop(carrier,self,"carry"):
			return False
		if self.Weight() > carrier.BRDN()//2:
			Print(f"{+self} is too heavy to carry.")
			return False
		if not self.Restrain(carrier):
			return False
		self.carrier = carrier
		self.carrier.addCarry(self)
		self.parent.remove(self)
		self.carrier.parent.add(self)
		return True


	def Restrain(self,restrainer,item=None):
		if not self.isAlive():
			return True
		if not self.isFriendly() and self.canMove():
			if item != None:
				#TODO: add restraining with items? like rope??
				pass
			if self.ATHL() > restrainer.ATHL() or self.EVSN() > restrainer.ATHL():
				Print(f"You fail to restrain {-self}!",color="r")
				return False
		self.addCondition("restrained",-3)
		Print(f"You restrain {-self}!",color="g")
		return True


	def Throw(self,missile,target,maxspeed=None):
		if missile is target:
			return False
		if missile is self.carrying:
			self.removeCarry(silent=True)
		else:
			if not self.parent.canAdd(missile):
				return False

			self.equipInHand(missile)
			self.remove(missile,silent=True)
			self.parent.add(missile)

		missile = missile.asProjectile()

		# force is half STR, reduced by 1 for every 4*STR in missile weight
		# basically, its just reduced for the amount of weight the missile has
		force = min1(self.STR()//2) - bound((missile.Weight()//4)//self.STR(),0,10)
		if force <= 0:
			if self is player:
				Print(f"{+missile} is too heavy!")
			missile.asItem().Fall()
			return False

		# bound by SPD; can only throw as fast as you can move
		speed = bound(diceRoll(1,force),1,self.SPD()+2)
		if maxspeed and speed > maxspeed:
			speed = maxspeed

		aim = self.ACCU()
		return missile.Launch(speed,aim,self,target)


	def Hide(self,I):
		if 4 * self.SLTH() > I.weight:
			self.addCondition("hiding",-3)
		else:
			pass


	def Ride(self,rider):
		if self.checkTetherLoop(rider,self,"ride"):
			return False
		if rider.Weight() > self.BRDN()//2:
			Print(f"You are too heavy to ride {-self}")
			return False
		contest = not self.isFriendly() and self.canMove()
		if contest:
			Print(f"{+self} struggles.",color="o")
			athl_contest = self.ATHL() - rider.ATHL()
			if athl_contest > 0:
				Print(f"{+self} shakes you off!",color="r")
				if athl_contest > rider.ATHL():
					rider.Fall(athl_contest-rider.ATHL())
				return False
		self.rider = rider
		rider.riding = self
		Print(f"You ride {-self}.",color="g" if contest else "w")
		return True


	def Smell(self,smeller):
		Print("Smells a little like body odor.")


	def Lick(self,licker):
		# TODO: make creatures evade this or try to
		Print("Yuck!")


	def Touch(self,toucher):
		Print("Feels soft and fleshy.")


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


	def invToll(self):
		return min0(self.invWeight() - self.BRDN())


	def gearToll(self):
		return min0(self.gearWeight()//4 - self.CON())


	# these formulas are difficult to read, check design document for details
	def ACCU(self): return 60 + 2*self.SKL() + self.LCK() + self.weapon.sleight
	def ATCK(self): return diceRoll(self.STR(), self.weapon.might, self.atkmod())
	def ATHL(self): return self.STR() + self.SKL() + self.STM()
	def ATSP(self): return min0(self.SPD() - min0(self.handheldWeight()//4 - self.CON()))
	def BRDN(self): return 12*self.CON() + 6*self.STR() + 3*self.FTH() + self.weight
	def CAST(self): return min0(self.WIS() + self.FTH() + self.INT() - self.gearToll())
	def CRIT(self): return self.SKL() + self.LCK() + self.weapon.sharpness
	def CSSP(self): return min0(self.WIS() - self.invToll() - self.gearToll())
	def DCPT(self): return 2*self.CHA() + self.INT()
	def DFNS(self): return 2*self.CON() + self.protection()
	def ENDR(self): return 2*self.STM() + self.CON()
	def EVSN(self): return 10 if self.hasAnyCondition("sitting","laying") else 2*self.ATSP() + self.LCK() + self.SPD()
	def INVS(self): return 2*self.INT() + self.WIS()
	def KNWL(self): return 2*self.INT() + self.LCK()
	def LOOT(self): return 2*self.LCK() + self.FTH()
	def MVMT(self): return min0(self.SPD() + self.STM() + 10 - self.invToll() - self.gearToll())
	def MXHP(self): return self.level()*self.CON() + (self.level()//10+1) * self.STM() + 1
	def MXMP(self): return self.level()*self.WIS() + (self.level()//10+1) * self.STM() + 1
	def PRSD(self): return 2*self.CHA() + self.WIS()
	def RSTN(self): return 2*self.FTH() + self.STM()
	def RITL(self): return 2*self.FTH() + self.LCK()
	def SLTH(self): return min0(2*self.SKL() + self.INT() - self.invToll()) * 2*int(self.hasCondition("hiding"))
	def SPLS(self): return 3*self.INT()
	def TNKR(self): return 2*self.INT() + self.SKL()


	def untetheredWeight(self):
		return self.weight + self.CON()


	def Weight(self):
		riderWeight = 0 if self.rider is None else self.rider.Weight()
		carryWeight = 0 if self.carrying is None else self.carrying.Weight()
		return self.untetheredWeight() + riderWeight + carryWeight


	def contents(self):
		return self.inv


	# wrapper for objQuery()
	def objTree(self):
		matches = objQuery(self,d=3)
		matches.remove(self)
		return matches


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


	# gets the first ancestor that isn't open, or the final ancestor (room)
	# used to determine the 'root' of a Creature's available surroundings
	def surroundings(self):
		for anc in self.ancestors():
			if not getattr(anc,"open",True):
				return anc
		return self.room()


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


	def carryWeight(self):
		return 0 if self.carrying is None else self.carrying.Weight()

	# returns a list of names of all items in player inventory
	def invNames(self):
		return [item.nounPhrase() if isinstance(item,Creature) else item.name for item in self.inv]


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
				return slot, object
		return None, None


	# return all items in inv whose name matches term, otherwise return None
	def inInv(self,term):
		if term.startswith("my "):
			term = term[3:]
		return [obj for obj in self.inv if nameMatch(term,obj)]


	# returns sum of all protection values of all items in gear
	def protection(self):
		return sum(item.prot for item in self.gear.values() if hasattr(item,"prot"))


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

	def nounPhrase(self,det="",n=-1,plural=False,cap=-1):
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
		Print(f"It's {~self}.")
		Print(f"{self.desc}.")


	def reflexive(self):
		if self.pronoun in Data.reflexives:
			return Data.reflexives[self.pronoun]
		else:
			return "itself"


# the class representing the player, contains all player stats
class Player(Creature):
	def __init__(self,name,desc,weight,traits,hp,mp,xp,rp,spells=None,**kwargs):
		Creature.__init__(self,name,desc,weight,traits,hp,mp=mp,**kwargs)
		self.xp = xp
		self.rp = rp
		self.spells = spells if spells else []


	def __neg__(self):
		return "yourself" if game.whoseturn is self else "you"


	def __pos__(self):
		return "You"
	

	def __invert__(self):
		return "yourself" if game.whoseturn is self else "you"


	### Operation ###

	def awaken(self,wellRested=True):
		game.silent = False
		sleep(1)
		Print("You wake up!",color="o")
		sleep(1)
		if wellRested:
			self.lastSlept = game.time
			self.checkTired()
		sleep(1)
		Print("\n\n")
		game.startUp()


	def Teleport(self,newroom):
		if type(self.parent) is not Room:
			raise Exception(f"Can't change rooms. Stuck inside {self.parent}")
		game.changeRoom(newroom)
		if self.riding:
			Print(f"You are no longer riding {self.riding}.")
			self.riding = None
		if self.carrying:
			Print(f"You are no longer carrying {self.carrying}.")
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
			self.hp = min1(self.hp-dmg)			
		# player hp lowered to a minimum of 0
		else:
			self.hp = min0(self.hp-dmg)
		total_dmg = prevhp - self.hp
		p = "!" if player.hasCondition("asleep") or total_dmg > self.MXHP() // 4 else "."
		color = "r" if total_dmg > 0 else "w"
		Print(f"You took {total_dmg} {Data.dmgtypes[type]} damage{p}",allowSilent=False,color=color)
		if self.hp == 0:
			return self.death()
		if total_dmg > 0 and self.hasCondition("asleep"):
			self.removeCondition("asleep")


	# player gets 1 QPs for each level gained, can dispense them into any trait
	def levelUp(self,oldlv,newlv):
		waitKbInput(f"You leveled up to level {newlv}!\n",color="g")
		QP = newlv-oldlv
		while QP > 0:
			self.printTraits()
			Print(f"\nQuality Points:	{QP}")
			trait = Input("What trait will you improve?")
			Print()
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
		self.rp = bound(repMod,-100,100)


	def updateMoney(self,money):
		self.money += money
		if money == 0:
			Print(f"You have $ {self.money}.")
		else:
			Print(f"You have $ {self.money}!",color="g")


	def obtainItem(self,I,tookMsg=None,failMsg=None):
		oldParent = I.parent
		if self.canObtain(I):
			if self.add(I):
				oldParent.remove(I)
			if tookMsg != None:
				Print(tookMsg)
			I.Obtain(self)
			self.checkHindered()
			return True
		if failMsg != None:
			Print(failMsg)
		return False


	# adds xp, checks for player level up
	def gainxp(self,newxp):
		oldlv = self.level()
		Print(f"You gained {newxp} xp.",color="g")
		self.xp += newxp
		# Print(f"You have {self.xp}")
		newlv = self.level()
		if oldlv != newlv:
			self.levelUp(oldlv,newlv)


	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		if not self.hasCondition(name):
			color = "w"
			if name in Data.buffs | Data.blessings:
				color = "g"
			if name in Data.debuffs | Data.curses:
				color = "r"
			if name in Data.curses:
				Print(f"You have the curse of {name}.",allowSilent=False,color=color)
			elif name in Data.blessings:
				Print(f"You have the blessing of {name}.",allowSilent=False,color=color)
			elif name == "asleep":
				Print(f"You fall {name}.",allowSilent=False)
			else:
				Print(f"You are {name}.",allowSilent=False,color=color)
		insort(self.status,[name,dur])
		return True


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,reqName=None,reqDuration=None):
		wasSleeping = self.hasCondition("asleep")
		wellRested = False

		# copy to prevent removing-while-iterating errors
		for name,duration in self.status.copy():
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])

					if name == "asleep" and duration == 0:
						wellRested = True
					if name != "asleep" and not self.hasCondition(name):
						Print(f"You are no longer {name}.",allowSilent=False)
		
		if wasSleeping and not self.hasCondition("asleep"):
			self.awaken(wellRested=wellRested)


	def checkHindered(self):
		if self.invWeight() + self.carryWeight() > self.BRDN():
			if not self.hasCondition("hindered"):
				Print("Your Inventory grows heavy.")
				self.addCondition("hindered",-3)
		if self.invWeight() + self.carryWeight() <= self.BRDN():
			if self.hasCondition("hindered"):
				Print("Your Inventory feels lighter.")
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
		Print("You have died!",color="r")
		ellipsis(color="r")
		
		if self.hasCondition("anointed",reqDuration=-3):
			sleep(1)
			Print("You reawaken!",color="g")
			self.hp = 1
		else:
			self.addCondition("dead",-3)
			waitKbInput()
			self.timeOfDeath = game.time
		return True


	def dualAttack(self,target):
		Print("\nDual Attack!",color="o")
		hit = bound(self.ACCU() - target.EVSN(),1,99)
		if diceRoll(1,100) <= hit:
			crit = diceRoll(1,100) <= self.CRIT()
			attack = self.ATCK()
			if crit:
				waitKbInput("Critical hit!",color="o")
				self.weapon2.dull(1)
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if not target.isAlive():
				return
		else:
			Print("Aw it missed.")
		waitKbInput()


	def attackCreature(self,target):
		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			Print(f"{n} attacks!",color="o")
		for i in range(n):
			if n > 1:
				waitKbInput(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = bound(self.ACCU() - target.EVSN(),1,99)
			if diceRoll(1,100) <= hit:
				crit = diceRoll(1,100) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					waitKbInput("Critical hit!",color="o")
					self.weapon.dull(1)
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
			else:
				Print("Aw it missed.")
			waitKbInput()
			if not target.isAlive():
				return
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	def attackItem(self,target):
		# TODO determine damage type here instead of always bludgeoning
		attack = self.ATCK()
		return target.takeDamage(attack,"b")


	def Catch(self,missile):
		assert isinstance(missile,Projectile)
		self.unequip("left")
		canCatch = 5*self.ATHL() > missile.weight and self.canObtain(missile)
		catch = bound(self.ACCU() - missile.speed*missile.weight,1,99)
		if canCatch and diceRoll(1,100) <= catch:
			missileItem = missile.asItem()
			Print(f"You catch {-missileItem}!",color="o")
			self.obtainItem(missileItem)
			self.equipInHand(missileItem)
			return True
		else:
			Print(f"You fail to catch {-missile}.")
			return False


	def Fall(self,height=0,room=None):
		Print(f"You fall!",color="o")

		if self.hasCondition("flying"):
			Print(f"But you're flying.",color="g")
			return False

		if room is None:
			room = self.room()
		while room.altitude != 0 and "down" in room.links:
			height += room.size
			room = room["down"]
		if room != self.room():
			ellipsis()
			self.changeLocation(room)
			
		if self.hasCondition("fleetfooted"):
			height = 0
		self.takeDamage(height,"b")
		return True


	def Bombard(self,missile):
		assert isinstance(missile,Projectile)
		dodge = self.EVSN()
		if missile.speed < self.MVMT():
			if yesno(f"Will you try to catch {-missile}?"):
				dodge = -10
				if self.Catch(missile):
					return True
		if diceRoll(1,100) < bound(missile.aim+missile.speed-dodge,1,99):
			return missile.Collide(self)
		return False


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

	# prints all 10 player traits
	def printTraits(self,trait=None):
		if trait == None:
			traits = [f"{t.upper()}: {getattr(self,t)}" for t in Data.traits]
			columnPrint(traits,5,10)
			return	
		Print(f"{trait.upper()}: {getattr(self,trait)}")


	def printAbility(self,ability=None):
		if ability == "ATCK":
			Print(f"ATCK: {self.STR()} - {self.weapon.might*self.STR()}")
		elif ability == "BRDN":
			Print(f"BRDN: {self.invWeight()}/{self.BRDN()}")
		elif ability is not None:
			Print(f"{ability}: {getattr(self,ability)()}")
		else:
			for ability in Data.abilities:
				self.printAbility(ability.upper())


	# each prints a different player stat
	def printMoney(self, *args): Print(f"$ {self.money}",color="g")
	def printHP(self, *args): Print(f"HP: {self.hp}/{self.MXHP()}",color="r")
	def printLV(self, *args): Print(f"LV: {self.level()}",color="o")
	def printMP(self, *args): Print(f"MP: {self.mp}/{self.MXMP()}",color="b")
	def printXP(self, *args): Print(f"XP: {self.xp}",color="o")
	def printRP(self, *args): Print(f"RP: {self.rp}",color="y")


	def printSpells(self, *args):
		Print(f"Spells: {len(self.spells)}/{self.SPLS()}")
		if len(self.spells) == 0:
			Print("\nYou don't know any spells.")
		else:
			columnPrint(self.spells,8,12)


	# prints player inventory
	def printInv(self, *args):
		W = self.invWeight() + self.carryWeight()
		color = "o" if W / self.BRDN() > 0.80 else "w"
		color = "r" if W > self.BRDN() else color
		if len(self.inv) == 0:
			Print("\nYour Inventory is empty.")
		else:
			columnPrint(self.invNames(),8,16)
		self.printCarrying(silent=True)
		Print(f"Weight: {W}/{self.BRDN()}", color=color)


	# print each player gear slot and the items equipped in them
	def printGear(self, *args):
		Print()
		for slot in self.gear:
			val = self.gear[slot].name
			if slot == "left" and self.carrying:
				val = self.carrying.name
			Print(slot + ":\t",end="")
			Print(val)


	def printCarrying(self,silent=False,*args):
		if self.carrying is not None:
			Print(f"Carrying {~self.carrying}")
			# Print(f"Weight: {self.carrying.Weight()}")
		elif silent is False:
			Print("Carrying nothing")


	def printRiding(self,silent=False,*args):
		if self.riding:
			Print(f"Riding {~self.riding}")
		elif silent is False:
			Print("Riding nothing")


	def printStatus(self, *args):
		if len(self.status) == 0:
			Print("None")
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
		columnPrint(statusdisplay,2)


	# prints player level, money, hp, mp, rp, and status effects
	def printStats(self, *args):
		stats = [self.name,f"$ {self.money}",f"LV: {self.level()}",f"RP: {self.rp}/100",f"HP: {self.hp}/{self.MXHP()}",f"MP: {self.mp}/{self.MXMP()}"]
		colors = ["w","g","o","y","r","b"]
		stats = [Tinge(stats[i],color=colors[i])[0] for i in range(len(stats))]
		columnPrint(stats,3)

		if self.carrying is not None:
			Print(f"Carrying {self.carrying}")
		if self.riding is not None:
			Print(f"Riding {self.riding}")
		if len(self.status) != 0:
			Print()
			self.printStatus()


	# for every item in player inventory, if its a weapon, print it
	def printWeapons(self, *args):
		if len(self.weapons()) == 0:
			Print("You have no weapons.")
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
			Print(f"\n{self.name}'s turn!")
		if self.canMove():
			self.attack()


	def dualAttack(self,target):
		Print("\nDual Attack!",color="o")
		hit = bound(self.ACCU() - target.EVSN(),1,99)
		if diceRoll(1,100) <= hit:
			crit = diceRoll(1,100) <= self.CRIT()
			attack = self.ATCK()
			if crit:
				waitKbInput("Critical hit!",color="o")
				self.weapon2.dull(1)
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if not target.isAlive():
				return
		else:
			Print("It missed!")
		waitKbInput()


	def attack(self):
		if not self.canMove():
			return
		select = lambda obj: isinstance(obj,Creature) and obj is not self
		targets = [obj for obj in self.parent.contents() if select(obj)]
		if self.parent is player.parent:
			targets += [player]
		if len(targets) > 0:
			target = choice(targets)
			return self.attackCreature(target)
		return False


	def attackCreature(self,target):
		Print(f"{+self} tries to attack {-target}.",color="o")

		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			Print(f"{n} attacks!")
		for i in range(n):
			if n > 1:
				waitKbInput(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = bound(self.ACCU() - target.EVSN(),1,99)
			if diceRoll(1,100) <= hit:
				crit = diceRoll(1,100) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					waitKbInput("Critical hit!",color="o")
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
			else:
				Print("It missed!")
			waitKbInput()
			if not target.isAlive():
				return
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	def Catch(self,missile):
		assert isinstance(missile,Projectile)
		self.unequip("left")
		canCatch = 5*self.ATHL() > missile.weight and self.canObtain(missile)
		catch = bound(self.ACCU() - missile.speed*missile.weight,1,99)
		if canCatch and diceRoll(1,100) <= catch:
			missileItem = missile.asItem()
			Print(f"{+self} catches {-missileItem}!",color="o")
			self.obtainItem(missileItem)
			self.equipInHand(missileItem)
			return True
		else:
			Print(f"{+self} fails to catch {-missile}.")
			return False


	### Getters ###

	def describe(self):
		Print(f"It's {~self}.")
		Print(f"{self.desc}.")
		gearitems = [item for item in self.gear.values() if item is not EmptyGear()]
		if len(gearitems) != 0:
			Print(f"It has {listObjects(gearitems)}.")


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
	def __init__(self,name,desc,weight,traits,hp,dlogName=None,dlogtree=None,rapport=0,lastParley=None,**kwargs):
		Creature.__init__(self,name,desc,weight,traits,hp,**kwargs)
		self.dlogName = name if dlogName is None else dlogName
		self.dlogtree = dlogtree
		self.rapport = rapport
		self.lastParley = lastParley


	def buildDialogue(self):
		savedDlogData = self.dlogtree
		savedDlogData = {} if self.dlogtree is None else self.dlogtree
		self.dlogtree = game.dlogDict["trees"][self.dlogName].copy()
		if "visitCounts" in savedDlogData:
			self.dlogtree.visitCounts = savedDlogData["visitCounts"]
		if "checkpoint" in savedDlogData:
			self.dlogtree.checkpoint = savedDlogData["checkpoint"]
		self.dlogtree.ensureIntegrity(self)


	### Behavior ###

	def firstImpression(self,player):
		# TODO: add this
		print(self.name, "impression")
		# adjust love, fear from person baselines
		self.memories.add("met")
		self.updateLove(player.rp)
		self.updateFear(player.rp)


	def appraise(self):
		if self.lastParley is None:
			self.lastParley = game.time
		elif game.time - self.lastParley > 100:
			self.dlogtree.newParley()
		self.lastParley = game.time
		if player.isNaked():
			self.appraisal.add("naked")
		

	def Talk(self):
		if "met" not in self.memories:
			self.firstImpression(player)
		self.appraise()
		if not self.dlogtree.visit(self):
			Print(f"{self.name} says nothing...")


	def Give(self,I):
		if not self.canObtain(I):
			Print(f"{+self} can't carry any more!")	
		elif self.dlogtree.react("Give",self,I=I):
			# if we fail to obtain item for whatever reason, drop it into room
			if not self.obtainItem(I):
				game.currentroom.add(I)
		else:
			Print(f"{+self} ignores your offer.")			
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
				self.aliases.update(("boy","male"))
			else:
				self.aliases.update(("man","guy","dude","male"))
		elif self.pronoun == "she":
			if isChild:
				self.aliases.update(("girl","female"))
			else:
				self.aliases.update(("woman","lady","dudette","female"))
		else:
			self.pronoun = "they"
		if isChild:
			self.aliases.update(("child","kid"))
		self.aliases.add("person")
	

	### Operation ###


	def act(self):
		pass


	### User Output ###

	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
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
		self.dlogName = self.species if dlogName is None else dlogName


	def buildDialogue(self):
		savedDlogData = {} if self.dlogtree is None else self.dlogtree

		# dlogName must either be the name of a tree or a trite
		if self.dlogName in game.dlogDict["trees"]:
			self.dlogtree = game.dlogDict["trees"][self.dlogName].copy()
		else:
			self.dlogtree = DialogueTree(self.dlogName,{"chatter":{"trites":self.dlogName}})

		if "visitCounts" in savedDlogData:
			self.dlogtree.visitCounts = savedDlogData["visitCounts"]
		if "checkpoint" in savedDlogData:
			self.dlogtree.checkpoint = savedDlogData["checkpoint"]
		self.dlogtree.ensureIntegrity(self)


	def act(self):
		if self.timeOfDeath:
			return
		if not game.silent:
			Print(f"\n{self.name}'s turn!")
		self.attack()


	def Give(self,I):
		if hasMethod(I,"Eat"):
			I.Eat(self)
			self.updateLove(1)
			self.updateFear(-1)
		else:
			Print(f"{+self} ignores your offer.")


	def Talk(self):
		if not player.hasCondition("wildtongued"):
			sounds = game.dlogDict["sounds"][self.species]
			sound = sample(sounds,1)[0]
			waitKbInput(f'"{sound}"',color="y")
			return True
		if "met" not in self.memories:
			self.firstImpression(player)
		self.appraise()
		if not self.dlogtree.visit(self):
			Print(f"{self.name} says nothing...")


	def Touch(self,toucher):
		if self.species in Data.textures:
			Print(Data.textures[self.species])
		else:
			return super().Touch(toucher)


	def attack(self):
		Print(f"{self.name} attack?")
		matches = self.parent.nameQuery('chest')
		if len(matches) == 1:
			chest = matches.pop()
			if player in chest.contents():
				chest.changeLocation(world['phlegethon'])


	def climb():
		pass


	def go():
		pass


	def steal():
		pass


	def swim():
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


# Portals are guaranteed to have a traverse and transfer method and a links and passprep attribute
class Portal(Item):
	def __init__(self,name,desc,weight,durability,composition,links,descname,passprep="into",**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.links = links
		self.descname = descname
		self.passprep = passprep


	### File I/O ###

	# search in world for the portal that has a link with the same pairkey
	# and link that portal to self
	def linkPortals(self, pairkey):
		pairedPortals = set()
		for room in world.values():
			pairedPortals |= objQuery(room,key=lambda x: isinstance(x,Portal) and pairkey in x.links.values(),d=3)
		pairedPortals.remove(self)
		if len(pairedPortals) != 1:
			raise Exception(f"Error: Portal {self.name} has an ambiguous connection for '{pairkey}'. Found {len(pairedPortals)} matches.")
		pairedPortal = list(pairedPortals)[0]
		# link paired portal to self
		for dir, dest in self.links.items():
			if dest == pairkey:
				self.links[dir] = pairedPortal
		# link self to the paired portal
		for dir, dest in pairedPortal.links.items():
			if dest == pairkey:
				pairedPortal.links[dir] = self


	def assignRefs(self,parent):
		self.parent = parent

		for dir, dest in self.links.items():
			if isinstance(dest,str) and dest in world:
				self.links[dir] = world[dest]
			elif isinstance(dest,str) and dest.startswith("port:"):
				self.linkPortals(dest)
			elif isinstance(dest,int):
				self.linkPortals(dest)
			elif isinstance(dest,Room) or isinstance(dest,Portal):
				continue
			else:
				raise Exception(f"Error: Portal {self.name} has a connection to unknown destination '{dest}'.")


	def assignLinkIDs(self,pairportal,linkid):
		if not hasattr(self, "compressedLinks"):
			self.compressedLinks = self.links.copy()

		assert pairportal in self.compressedLinks.values()
		for dir, dest in self.compressedLinks.items():
			if dest is pairportal:
				self.compressedLinks[dir] = linkid


	def convertToJSON(self):
		# must copy links for saving to JSON so real links remain intact if game continues
		if not hasattr(self, "compressedLinks"):
			self.compressedLinks = self.links.copy()

		# convert room links to strings, and portal links to unique link ids
		for portal in {v for v in self.compressedLinks.values() if isinstance(v,Portal)}:
			linkId = game.portallinks
			self.assignLinkIDs(portal,linkId)
			portal.assignLinkIDs(self,linkId)
			game.portallinks += 1

		for dir, dest in self.compressedLinks.items():
			if isinstance(dest,Room):
				self.compressedLinks[dir] = dest.name.lower()
		# all links should now be either strings or ints
		assert all([isinstance(dest,(str,int)) for dest in self.compressedLinks.values()])

		jsonDict = self.__dict__.copy()
		jsonDict["links"] = jsonDict["compressedLinks"]
		del jsonDict["compressedLinks"]
		return jsonDict


	### Operation ###

	def getDefaultDir(self):
		if len(set(self.links.values())) == 1:
			return list(self.links.keys())[0]
		elif "down" in self.links:
			return "down"
		return choice(self.links)


	def getNewLocation(self,dir):
		newloc = self.links[dir]
		if isinstance(newloc, Portal):
			newloc = newloc.parent
			if isinstance(newloc,Creature):
				newloc = newloc.parent
		return newloc


	# method for creatures travelling through the portal
	def Traverse(self,traverser,dir=None):
		if self in traverser.objTree():
			if traverser is player:
				Print(f"You can't enter {-self}. It's within your Inventory.")
			else:
				Print(f"{+traverser} can't enter {-self}. It's within {-traverser}'s Inventory.")
			return False

		if dir == None or dir not in self.links:
			if len(set(self.links.values())) == 1:
				dir = list(self.links.keys())[0]
			else:
				msg = f"Which direction on the {self.name}?"
				dir = InputLoop(msg)
				if dir is None:
					return False
		if dir not in self.links:
			Print(f"The {self.name} does not go '{dir}'.")
			return False

		newloc = self.getNewLocation(dir)
		if not newloc.canAdd(traverser):
			if traverser is player:
				Print(f"You can't enter {-self}. There's not enough room.")
			return False

		if traverser is player:
			waitKbInput(f"You go {dir} the {self.name}.")
		traverser.changeLocation(newloc)
		return True


	# method for items travelling through portal
	def Transfer(self,item):
		if isinstance(item,Creature):
			dir = self.getDefaultDir()
			if dir == "down":
				return item.Fall(1,room=self.getNewLocation("down"))
			return self.Traverse(item,dir=dir)
		if self in item.objTree():
			Print(f"{+item} can't enter {-self}. It's within {-item}'s contents.")
			return False

		if "down" in self.links:
			return item.Fall(room=self.links["down"])

		# item can't randomly go up
		dir = choice([dir for dir in self.links])
		if self.links[dir] == self.links.get("up",None):
			return item.Fall()

		# Print(f"{+item} goes {self.passprep} {-self}.")	
		newloc = self.getNewLocation(dir)
		if not newloc.canAdd(item):
			return False

		item.changeLocation(newloc)


	def Bombard(self,missile):
		assert isinstance(missile,Projectile)
		if diceRoll(1,100) < bound(missile.aim+self.weight+10,1,99):
			if getattr(self,"open",True):
				Print(f"{+missile} goes {self.passprep} {-self}.")
				self.Transfer(missile.asItem())
			else:
				missile.Collide(self)
			return True
		return False


	### Getters ###

	# returns dict of links, where keys are directions and values are room names
	def allLinks(self,d=3):
		links = {}
		for dir in self.links:
			links[(dir,None)] = self.links[dir]
		# get a list of passages in the room
		portals = self.query(key=lambda x: isinstance(x,Portal),d=d)
		# for each portal, add its connections to links
		for portal in portals:
			for dir in portal.getLinksForParent():
				if dir not in links:
					links[(dir,portal)] = portal.links[dir]
		return links


	# get the links dict to use in the parent's allLinks method
	def getLinksForParent(self):
		return self.links


	def getPassages(self):
		return [item for item in self.query(key=lambda x: isinstance(x,Passage))]


	# given a direction (like 'north' or 'down)...
	# return the first portal object with that direction in its connections
	def getPortalsFromDir(self,dir):
		portals = []
		for thisDir, portal in self.allLinks(d=0):
			if dir == thisDir and portal is not None:
				portals.append(portal)
		return portals


	# if the given room object, dest, is in one of the rooms links, then find the direction and portal it is in from the room.
	def getDirPortalPair(self,dest):
		for (dir,portal), room in self.allLinks().items():
			if nameMatch(dest,room):
				return dir, portal
		return None, None


	def allDirs(self):
		return (tuple[0] for tuple in self.allLinks())




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
				Print(f"The {self.name} cannot be broken.")
			return False
		Print(f"The {self.name} breaks.")
		self.parent.removeFixture(self)
		return True



class Passage(Portal,Fixture):
	def __init__(self,name,desc,weight,durability,composition,links,descname,passprep="into",mention=False,**kwargs):
		Fixture.__init__(self,name,desc,weight,durability,composition,mention=mention,**kwargs)
		self.passprep = passprep
		self.links = links
		self.descname = descname





class Projectile(Item):
	def __init__(self,name,desc,weight,durability,composition,might,sharpness,type,speed=0,item=None,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.might = might
		self.sharpness = sharpness
		self.type = type
		self.speed = speed
		self.item = item


	### Dunder Methods ###

	def __str__(self):
		return str(self) if self.item else self.name


	def __neg__(self):
		return super().__neg__() if self.item else "the " + self.name


	def __pos__(self):
		return super().__pos__() if self.item else "The " + self.name


	def __invert__(self):
		return super().__invert__() if self.item else "a " + self.name


	### Operation ###
	
	def Launch(self,speed,aim,launcher,target):
		self.speed = speed
		self.aim = 90 if self.hasCondition("homing") and aim < 90 else aim

		if isinstance(target,Room):
			self = self.asItem()
			self.changeLocation(target)
			return self.Fall(speed//2)
		if self.item.parent not in (target,target.parent):
			if not getattr(self.item.parent,"open",True):
				return self.item.parent.Bombard(self)
			self.item.parent.remove(self.item)
			target.parent.add(self.item)

		if not target.Bombard(self):
			Print(f"{self.pronoun.title()} misses!")
			self.Miss(launcher,target)
		return True


	def Miss(self,launcher,target):
		self.aim = -10 if self.asItem().hasCondition("homing") else min1(self.aim-10)
		parent = self.item.parent

		# have a chance to randomly hit a different object in room
		otherObjs = [obj for obj in parent.contents() if obj not in (self,self.item,launcher,target)]
		weights = [obj.weight for obj in otherObjs]
		if isinstance(parent,Room):
			otherObjs += [None]
			weights += [parent.size*10]
		else:
			otherObjs += [parent]
			weights += [parent.weight]
		victim = choices(otherObjs,weights)[0]
		if victim is None:
			return False
		if victim is target.parent:
			return victim.Bombard(self)
		Print(f"{self.pronoun.title()} whizzes toward {-victim}!", color="o")
		if not victim.Bombard(self):
			Print(f"{self.pronoun.title()} misses...")


	def dull(self,dec):
		if hasMethod(self.item,"dull"):
			return self.item.dull(dec)
		if self.hasCondition("keen"):
			return
		self.sharpness = min0(self.sharpness - dec)


	def Collide(self,target):
		if target is player:
			Print(f"{+self} hits you!",color="o")
		else:
			Print(f"{+self} hits {-target}.")

		# deal damage to target
		d = self.might * self.speed
		if diceRoll(1,100) <= self.sharpness:
			d *= 2
			Print("Critical hit!",color="o")
			self.dull(1)
		damage = diceRoll(0,d,d)
		target.takeDamage(damage,self.type)

		# take self damage
		if self.item:
			selfdmg = 0
			# if hits a creature, take damage according to one of the creature's gear
			if isinstance(target,Creature):
				gearItems = [item for item in target.gear.values()]
				weights = [min1(item.Weight()) for item in gearItems]
				target = choices(gearItems,weights)[0]
			if target.durability == -1:
				selfdmg = self.speed * 3
			elif target.durability > self.durability:
				selfdmg = self.speed * (target.durability // self.durability)
			if selfdmg > 0:
				self.item.takeDamage(selfdmg,"b")
		else:
			self.parent.remove(self)
		return True


	def asItem(self):
		if self.item is not None:
			return self.item
		else:
			return self


	def asProjectile(self):
		return self



class Serpens(Item):
	def __init__(self,value,**kwargs):
		desc = f"{str(value)} glistening coins made of an ancient metal"
		Item.__init__(self,"Gold",desc,value,-1,"gold",**kwargs)
		self.aliases = {"coin","coins","money","serpen","serpens"}
		self.plural = "gold"
		self.descname = str(value) + " Gold"
		self.value = value


	### File I/O ###

	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		return {
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

	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
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


	def dull(self,dec):
		if self.hasCondition("keen"):
			return
		self.sharpness = min0(self.sharpness - dec)


	def show(self):
		Print(f"{self.name} {self.might} {self.sleight}")
		Print(f"{self.sharpness} { self.twohanded} {self.range}")


	def lick(self,licker):
		if self.composition in ("glass","bronze","iron","steel"):
			Print("It tastes like... blood.")
			licker.takeDamage(3,"s")
			return True

		if self.composition in Data.tastes:
			Print(Data.tastes[self.composition])
		if self.composition in Data.scents:
			Print(Data.scents[self.composition].replace("scent","taste"))


	def asProjectile(self):
		return Projectile(self.name,self.desc,self.weight,self.durability,self.composition,self.might,self.sharpness,self.type,item=self)



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
		Print("Orienting you northward!")




#############
## GLOBALS ##
#############


player = Player("","",0,[0]*10,0,0,0,0)
defaultRoom = Room("","","",{},[],[],[])
game = Game(-1,defaultRoom,defaultRoom,-1,-1,{},{})
world = {}