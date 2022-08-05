# Core.py
# This file contains all core functions and classes used throughout the game
# This file is a dependency of Objects.py and is dependent on Data.py

# It consists of two main parts;
# 1. Core functions			(used in Objects.py, Menu.py, and Parser.py)
# 2. Core class definitions	(empty, game, room, item, creature, player, etc.)

from time import sleep
from random import randint,choice
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


def clearScreen():
	if os.name == "nt":
		os.system("cls")
	else:
		os.system("clear")
	# print("\n"*64)


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


# checks for any keyboard input
# TODO: add functionality for non-windows operating systems
def kbInput():
	try:
		dr,dw,de = select.select([sys.stdin], [], [], 0.00001)
		return dr != []
	except:
		return msvcrt.kbhit()


# prints a timed ellipsis, used for dramatic transitions
def ellipsis(n):
	for i in range(n):
		sleep(1)
		print(".")


# prints a list of strings, l, into n columns of width w characters
# if an element is longer than one column, it takes up as many columns as needed
def columnPrint(l,n,w):
	print()
	# k is the number of characters that have been printed in the current row
	k = 0
	# for each string element in l
	for term in l:
		# if the string is longer than remaining row width; print on a new row
		if len(term) >= (n*w) - k:
			print("\n" + term, end="")
			k = len(term)
		# if the string is short enough, print it, increment k
		else:
			print(term, end="")
			k += len(term)
		# to preserve column alignment, print spaces until k is divisble by w
		spaces = w - (k % w)
		print(spaces * ' ', end="")
		k += spaces
	print()


# grammar print; adds punctuation and determiners
# n is the 'number' of an item, denoting its plurality
def gprint(det,text,pos,n):
	if text[0] in Data.vowels and det == "a":
		det = "an"
	if n > 1:
		det = str(n)
		#pluralize the text, maybe find a more robust way
		text = pluralize(text)
	if "pylars" not in text.lower():
		text = det + " " + text
	if pos == 0:
		text = text[0].upper() + text[1:]
	elif pos == 2:
		text = text + "."
	elif pos == 3:
		text = text + ","
	text = text + " "
	return text


# capitalizes the first letter of all the words in a string
# if n is given, then only capitalize the first n words
def capWords(string,n=-1):
	listString = string.split(' ')
	cappedString = ''
	for idx,word in enumerate(listString):
		if len(word) > 0:
			if n != -1 and idx < n:
				cappedString += word[0].upper() + word[1:] + ' '
			else:
				cappedString += word + ' '
	# removes trailing space character
	return cappedString[0:-1]


def pluralize(term):
	# TODO: do some checking for special words here
	return term + "s"


def singularize(term):
	# TODO: do some checking for special words here
	if term.endswith("s"):
		return term[:-1]
	else:
		return term


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
			if entry[0].descname == obj.descname:
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
		raise Exception("extracting condition info from invalid area condition")
	condInfo = roomCondition.split(" ")
	name = ' '.join(condInfo[1:-1])
	dur = int(condInfo[-1])
	return [name,dur]


# prints a question, gets a yes or no, returns True or False respectively
def yesno(question):
	while True:
		command = input(question + "\n> ").lower()
		if command in Data.yesses:
			return True
		elif command in Data.noes:
			return False
		print("Enter yes or no")


# rolls n dice of range d, adds a modifier m, returns number
def diceRoll(n,d,m):
	x = 0
	for roll in range(n):
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



# the room, creatures, and some items can contain items within themselves...
# thus all objects within a room can be thought of as a tree...
# where each node is an item or creature, and the root is the room
# the player object can also be thought of this way where the player is the root
# this function recursively searches the tree of objects for an object...
# whose name matches the given term, (not case sensitive)
# the object tree might look as follows:

#           _____Room_____
#         /    /     \     \
#     cat  trunk   sword  wizard
#    /     /   \         /   |   \
# key   jar  candle  potion wand scroll
#        |
#     saffron

# d is the 'degree' of the search; how thorough it is'
# if d is 3: searches through all objects from the root
# elif d is 2: searches through all objects which are not locked
# elif d is 1: searches through objects which are not locked and not in...
# creature inventories; i.e. objects which are "accessible" to the player
# if d is 0: searches through items which are not "closed" and not in...
# creature inventories; i.e. objects which are "visible" to the player

# this function is a wrapper for objSearchRecur()
def objSearch(root,key=lambda obj:True,d=0):
	matches = objSearchRecur(root,[],key,d)
	return matches


def objSearchRecur(node,matches,key,d):
	# choose list of objects to search through depending on the node's type
	if isinstance(node,Room): searchThrough = node.contents()
	elif hasattr(node,"items"): searchThrough = node.items
	elif hasattr(node,"inv"): searchThrough = node.inv
	# if node is unsearchable: return
	else: return matches

	for obj in searchThrough:
		# check if obj is a match
		if key(obj): matches.append(obj)
		# depending on the degree, may skip closed, locked, or creature objects
		if d == 0 and hasattr(obj,"open") and not obj.open: continue
		elif (d <= 1) and isinstance(obj,Creature): continue
		elif d <= 2 and hasattr(obj,"locked") and obj.locked: continue
		# recur the search on each object's subtree
		matches = objSearchRecur(obj,matches,key,d)
	return matches


# helper function for assignParents()
# iterates through objects within the root and assigns root as their parent
# recurs for each object
def assignParentsRecur(root):
	if isinstance(root,Room): searchThrough = root.contents()
	elif hasattr(root,"items"): searchThrough = root.items
	elif hasattr(root,"inv"): searchThrough = root.inv
	else: return

	for obj in searchThrough:
		obj.parent = root
		assignParentsRecur(obj)


# iterates through each object in the object tree of each room and assigns...
# its 'parent' attribute to the object it is contained in
def assignParents():
	for room in world.values():
		assignParentsRecur(room)
	assignParentsRecur(player)


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
	# this is done in a separate loop to prevent errors caused by...
	# deleting elements from dict while iterating over the dict
	for name in namesToDelete:
		del world[name]


############################
## SUPERCLASS DEFINITIONS ##
############################


# Empty is a class usually used as a placeholder for items. It serves to act as a dummy item which has mostly null values
class Empty():
	def __init__(self):
		self.name = "[empty]"
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

	def Weight(self):	return 0


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
		# the gamemode, either 0 for normal mode or 1 for god mode
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
		self.her = None
		self.him = None



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
	def incrementTime(self):
		self.time += 1
		player.passTime(1)
		for room in self.renderedRooms():
			self.silent = room is not self.currentroom
			room.passTime(1)
			for creature in room.creatures:
				creature.passTime(1)


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
				self.him = obj
			elif obj.gender == "f":
				self.her = obj


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
	# n is the path length at which the search stops
	# Sroom is the "source" room, or the current node in the search
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
	# d is the 'degree' of the search. See objSearch() for details
	def searchRoom(self,room=None,key=lambda x:True,d=3):
		if room == None:
			room = self.currentroom
		return objSearch(room,key=key,d=d)


	# returns a list of objects in rendered rooms which fit a certain condition
	def searchRooms(self,key=lambda x:True,d=3):
		matchingObjects = []
		for room in self.renderedRooms():
			matchingObjects += self.searchRoom(room,key=key,d=d)
		return matchingObjects


	# returns a set of all objects in the rendered world
	# does not include the player or anything in player inv
	def getAllObjects(self):
		allObjects = []
		for room in self.renderedRooms():
			allObjects += objSearch(room,key=lambda x:True,d=3)
		return allObjects


	# True if there's an object in rendered rooms whose name matches objname
	# not case sensitive
	def inWorld(self,objname):
		key = lambda obj: objname == obj.name.lower() or objname == obj.descname.lower() or objname in obj.aliases
		objects = self.searchRooms(key)
		return len(objects) > 0


	### User Output ###

	def startUp(self):
		player.printStats()
		print()
		self.currentroom.describe()


	def describeRoom(self):
		self.currentroom.describe()




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
	def __init__(self,name,domain,desc,exits,fixtures,items,creatures,status):
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
		if isinstance(I,Pylars):
			for item in self.items:
				if isinstance(item,Pylars):
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
		self.creatures = list(filter(lambda x: x.alive, self.creatures))


	def addFixture(self,F):
		insort(self.fixtures,F)
		F.parent = self


	def removeFixture(self,F):
		if F in self.fixtures:
			self.fixtures.remove(F)


	def addAreaCondition(areacond):
		cond,dur = extractConditionInfo(areacond)
		key = lambda x: hasMethod(x,"addCondition")
		for creature in game.searchRoom(key):
			creature.addCondition(cond,dur)


	def removeAreaCondition(areacond):
		cond,dur = extractConditionInfo(areacond)
		# depending on how you want room conditions to work, perhaps remove this
		if dur != -1:
			return
		key = lambda x: hasMethod(x,"removeCondition")
		for creature in game.searchRoom(key):
			creature.removeCondition(cond,-1)


	# add a status condition to the room with a name and duration
	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		pair = [name,dur]
		insort(self.status,pair)
		if name.startswith("AREA"):
			self.addAreaCondition(name)


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


	# describe the room, and apply any room effects to the creature entering
	def enter(self,creature):
		# if the player is entering the room, describe the room
		if creature is player:
			self.describe()
		for cond,dur in self.status:
			if cond.startswith("AREA"):
				[name,dur] = extractConditionInfo(cond)
				creature.addCondition(name,dur)


	# remove any room effects from the creature exiting
	def exit(self,creature):
		condsToRemove = [pair for pair in creature.status if pair[1] == -1]
		for cond,dur in condsToRemove:
			creature.removeCondition(cond,-1)



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


	# takes a string, term, and searches the room's items
	# if an item is found that matches term, return it, otherwise, return None
	def inItems(self,term):
		term = term.lower()
		matches = []
		for item in self.items:
			if term == item.name.lower() or term in item.aliases:
				matches.append(item)
		return matches


	def itemNames(self):
		return [item.name for item in self.items]


	# returns a list of Passage objects within the room's items
	def getPassages(self):
		return [item for item in self.contents() if isinstance(item,Passage)]


	# takes a string, term, and searches the room's occuptants
	# if a creature matches the term , return it, otherwise, return False
	def inCreatures(self,term):
		term = term.lower()
		matches = []
		for creature in self.creatures:
			if term == creature.name.lower() or term in creature.aliases:
				matches.append(creatures)
		return matches


	def creatureNames(self):
		return [creature.name for creature in self.creatures]


	def contents(self):
		return self.fixtures + self.items + self.creatures


	def inContents(self,term):
		term = term.lower()
		matches = []
		for item in self.contents():
			if term == item.name.lower() or term in item.aliases:
				matches.append(item)
		return matches


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


	# wrapper for objSearch()
	# recursively searches the room for object whose names match given term
	def search(self,term,d=0,reqParent=None):
		term = term.lower()
		key = lambda obj: term == obj.name.lower() or term == obj.descname.lower() or term in obj.aliases
		matches = objSearch(self,key=key,d=d)

		if reqParent != None:
			reqParent = reqParent.lower()
			condition = lambda obj: reqParent == obj.parent.name.lower() or reqParent == obj.parent.descname.lower() or reqParent in obj.parent.aliases
			matches = list(filter(condition,matches))

		return matches


	def listableItems(self):
		# don't list fixtures which are not 'mentioned'
		condition = lambda x: not (isinstance(x,Fixture) and not x.mention)
		objects = list(filter(condition,self.items))
		return objects



	### User Output ###

	# prints room name, description, all its items and creatures
	def describe(self):
		print("\n\n" + self.domain)
		print(self.name)
		if player.countCompasses() == 0:
			print("\n" + ambiguateDirections(self.desc))
		else:
			print("\n" + self.desc)
		self.describeItems()
		self.describeCreatures()


	# prints all the items of the room in sentence form
	def describeItems(self):
		items = self.listableItems()
		if len(items) != 0:
			print(f"There is {listObjects(self.listableItems())}.")


	# prints all the creatures in the room in sentence form
	def describeCreatures(self):
		if len(self.creatures) != 0:
			print(f"There is {listObjects(self.creatures)}.")




# The Item class is the main game object class of things that cannot act
# Anything in a Room that is not a Creature will be an Item
# All items come with a name, description, weight, and durability
class Item():
	def __init__(self,name,desc,aliases,plural,weight,durability,status):
		self.name = name
		self.descname = name
		self.desc = desc
		self.aliases = aliases
		self.plural = plural
		self.weight = weight
		self.durability = durability
		self.status = status
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

	def Obtain(self,creature):
		pass


	def Break(self):
		if self.durability == -1:
			if not game.silent:
				print(f"The {self.name} cannot be broken.")
			return False
		self.parent.removeItem(self)


	def takeDamage(self,dmg):
		if dmg > self.durability:
			return self.Break()


	def addCondition(self,name,dur,stackable=False):
		if self.hasCondition(name) and not stackable:
			return False
		pair = [name,dur]
		insort(self.status,pair)
		return True



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
		return Weapon(self.name,self.desc,self.aliases,self.plural,self.weight,self.durability,[],min1(self.weight//4),0,0,0,False,"b")



	### User Output ###

	def describe(self):
		print(f"It's {self.stringName()}.")
		print(self.desc)


	def stringName(self,n=1,plural=False,definite=False,cap=False):
		strname = self.descname
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = pluralize(strname)
		if n > 1:
			strname = str(n) + " " + strname
		if definite:
			strname = "the " + strname
		elif not plural:
			if strname[0] in Data.vowels:
				strname = "an " + strname
			else:
				strname = "a " + strname
		if cap:
			strname = capWords(strname)
		return strname




# The Creature class is the main class for anything in the game that can act
# Anything in a Room that is not an Item will be a Creature
# The player is a Creature too
# Creatures have 10 base stats, called traits
# They also have abilities; stats which are derived from traits through formulas
class Creature():
	def __init__(self,name,desc,aliases,plural,traits,status,hp,mp,money,inv,gear):
		self.name = name
		self.descname = name
		self.desc = desc
		self.aliases = aliases
		self.plural = plural

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
		self.gear = {key: inv[idx] if idx != -1 else Empty() for key, idx in gear.items()}

		self.parent = None

		self.weapon = Empty()
		self.weapon2 = Empty()
		self.shield = Empty()
		self.shield2 = Empty()

		# these attributes remain unused in the Player subclass
		self.alive = True
		self.alert = False
		self.seesPlayer = False
		self.sawPlayer = -1



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
		return self.MVMT() < other.MVMT()



	### File I/O ###

	# converts the gear dict to a form more easily writable to a save file
	# replaces all objects in gear.values() with an integer which represents...
	# the index of the equipped object in the creature's inventory
	# if the gear slot is empty, replaces it with -1
	def compressGear(self):
		return {key: (self.inv.index(item) if item != Empty() else -1) for key, item in self.gear.items()}


	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		# convert the gear dict to a form more easily writable in a JSON object
		compressedGear = self.compressGear()
		d = self.__dict__.copy()
		dictkeys = list(d.keys())
		# these attributes do not get stored between saves (except gear)
		for key in dictkeys:
			if key in Data.traits or key in {"gear","weapon","weapon2","shield","shield2","alive","alert","seesPlayer","sawPlayer"}:
				del d[key]
		d["gear"] = compressedGear
		# convert traits to a form more easily writable in a JSON object
		d["traits"] = [self.STR,self.SKL,self.SPD,self.STM,self.CON,self.CHA,self.INT,self.WIS,self.FTH,self.LCK]
		# TODO: swap the following lines for Python 3.9
		# d = {"__class__":self.__class__.__name__} | d
		d = {"__class__":self.__class__.__name__, **d}
		return d


	# returns an instance of this class given a dict from a JSON file
	@classmethod
	def convertFromJSON(cls,d):
		return cls(d["name"],d["desc"],d["aliases"],d["plural"],d["traits"],d["status"],d["hp"],d["mp"],d["money"],d["inv"],d["gear"])



	### Operation ###

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		if(f"{type} vulnerability" in self.status): dmg *= 2
		if(f"{type} resistance" in self.status): dmg //= 2
		if(f"{type} immunity" in self.status): dmg = 0
		print(f"Took {dmg} {Data.dmgtypes[type]} damage")
		#player hp lowered to a minimum of 0
		self.hp = min0( self.hp-dmg)
		if self.hp == 0:
			self.death()


	# adds money
	def gainMoney(self,money):
		self.money += money


	# try to add an Item to Inventory
	# it will fail if the inventory is too heavy
	def addItem(self,I):
		if isinstance(I,Pylars):
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
		source = I.parent
		if self.addItem(I):
			if source != None:
				source.removeItem(I)
			if msg != None:
				print(msg)
			I.Obtain(self)
			self.checkHindered()
			return True
		return False


	# only used by equip and unequip to reassign several attributes
	# specifically, weapon, weapon2, shield, shield2
	def assignWeaponAndShield(self):
		#if unassigned, attributes are empty, self.weapon is always assigned
		self.weapon2 = Empty()
		self.shield = Empty()
		self.shield2 = Empty()

		# assign weapon and weapon2 based on types of gear in left and right
		if isinstance(self.gear["right"],Weapon) and isinstance(self.gear["left"],Weapon):
			self.weapon2 = self.gear["left"]
		elif isinstance(self.gear["left"],Weapon) and not isinstance(self.gear["right"],Weapon):
			self.weapon = self.gear["left"]
		elif isinstance(self.gear["left"],Item) and self.gear["right"] == Empty():
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


	# finds the slot in which item resides, sets it to Empty()
	# calls the item's Unequip() method if it has one
	def unequip(self,I):
		gearslots = list(self.gear.keys())
		gearitems = list(self.gear.values())
		# finds the slot whose value is I, sets it to empty
		slot = gearslots[gearitems.index(I)]
		self.gear[slot] = Empty()
		self.assignWeaponAndShield()
		if hasMethod(I,"Unequip"): I.Unequip()


	# if the item is armor, equip it, otherwise return False
	def equipArmor(self,I):
		if isinstance(I,Helm): self.gear["head"] = I
		elif isinstance(I,Tunic): self.gear["body"] = I
		elif isinstance(I,Greaves): self.gear["legs"] = I
		else: return False
		I.Equip()
		return True


	# unequips the lefthanded item, moves righthanded item to left,
	# equips the new item in right hand
	# if the new item is twohanded, set lefthand to Empty()
	# calls the new item's Equip() method if it has one
	def equipInHand(self,I):
		self.unequip(self.gear["left"])
		self.gear["left"] = self.gear["right"]
		self.gear["right"] = I
		if (hasattr(I,"twohanded") and I.twohanded) or isinstance(I,Creature):
			self.gear["left"] = Empty()
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
		self.alive = False
		print("agh its... ded?")
		# TODO: make this just drop some random number of money not just LOOT
		n = diceRoll(3,player.LOOT(),-2)
		self.room().addItem(Pylars(n,[]))
		if not game.silent:
			print(f"Dropped Ᵽ {n}.")
		if game.whoseturn is player:
			player.gainxp(diceRoll(1,player.LCK,1))


	def Carry(self,creature):
		self.addCondition("carrying",-3,silent=True)
		self.equipInHand(creature)
		creature.addCondition("carried",-3)
		return True


	def Restrain(self,restrainer,item=None):
		if item != None:
			#TODO: add restraining with items? like rope??
			pass
		if self.ATHL() > restrainer.ATHL() or self.EVSN() > restrainer.ATHL():
			return False
		restrainer.addCondition("restraining",-3,silent=True)
		self.addCondition("restrained",-3)
		return True


	def Hide(self,I):
		if 4 * self.SLTH() > I.weight:
			self.addCondition("hiding",-3)
		else:
			pass



	### Getters ###

	# these are creature stats that are determined dynamically with formulas
	# these formulas are difficult to read, check design document for details
	def ACCU(self): return 50 + 2*self.SKL + self.LCK + self.weapon.sleight
	def ATCK(self): return diceRoll(self.STR, self.weapon.might, self.atkmod())
	def ATHL(self): return self.STR + self.SKL + self.STM
	def ATSP(self): return self.SPD - min0(self.handheldWeight()//4 - self.CON)
	def BRDN(self): return self.CON * self.STR * 4 + 60
	def CAST(self): return self.WIS + self.FTH + self.INT - min0(self.gearWeight()//4 - self.CON)
	def CRIT(self): return self.SKL + self.LCK + self.weapon.sharpness
	def CSSP(self): return self.WIS - min0(self.invWeight() - self.BRDN()) - min0(self.gearWeight()//4 - self.CON)
	def DCPT(self): return 2*self.CHA + self.INT
	def DFNS(self): return self.CON + self.protection()
	def ENDR(self): return 2*self.STM + self.CON
	def EVSN(self): return 2*self.ATSP() + self.LCK
	def INVS(self): return 2*self.INT + self.WIS
	def KNWL(self): return 2*self.INT + self.LCK
	def LOOT(self): return 2*self.LCK + self.FTH
	def MVMT(self): return self.SPD + self.STM + 10 - min0(self.invWeight() - self.BRDN()) - min0(self.gearWeight()//4 - self.CON)
	def MXHP(self): return self.level()*self.CON + self.STM
	def MXMP(self): return self.level()*self.WIS + self.STM
	def PRSD(self): return 2*self.CHA + self.WIS
	def RESC(self): return 2*self.FTH + self.STM
	def RITL(self): return 2*self.FTH + self.LCK
	def SLTH(self): return ( 2*self.SKL + self.INT - min0(self.invWeight() - self.BRDN()) ) * 2*int(self.hasCondition("hiding"))
	def SPLS(self): return 3*self.INT
	def TNKR(self): return 2*self.INT + self.SKL


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
		weight = 0
		for item in self.inv: weight += item.Weight()
		return weight


	# returns a list of names of all items in player inventory
	def invNames(self,lower=False):
		if lower:
			return [item.name.lower() for item in self.inv]
		return [item.name for item in self.inv]


	# just a function wrapper for functions that call itemNames on objects
	def itemNames(self):
		return self.invNames()


	# searches through inventory for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return None
	def inInv(self,term):
		term = term.lower()
		matches = []
		for item in self.inv:
			if term == item.name.lower() or term in item.aliases:
				matches.append(item)
		return matches


	def weapons(self):
		return [I for I in self.inv if isinstance(I,Weapon)]


	# returns sum of the weight of all items in player gear
	def gearWeight(self):
		weight = 0
		for item in self.gear:
			if hasattr(self.gear[item], "weight"):
				weight += self.gear[item].Weight()
		return weight


	# searches through gear for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return None
	def inGear(self,term):
		for slot in self.gear:
			if self.gear[slot].name.lower() == term:
				return self.gear[slot]
		return None


	# returns sum of all protection values of all items in gear
	def protection(self):
		prot = 0
		for item in self.gear.values():
			if hasattr(item, "prot"):
				prot += item.prot
		return prot


	def hasCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					return True
		return False


	# returns the sum of the weight of all items being held
	def handheldWeight(self):
		return self.weapon.weight + self.weapon2.weight + self.shield.weight + self.shield2.weight


	def isBloodied(self):
		# returns true is creature has less than half health
		pass


	def alliesPresent(self):
		# returns number of allies creature can see
		pass


	def enemiesPresent(self):
		# returns number of enemies creature can see
		pass



	### User Output ###

	def stringName(self,n=1,plural=False,definite=False,cap=False):
		strname = self.descname
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = pluralize(strname)
		if n > 1:
			strname = str(n) + " " + strname
		if definite:
			strname = "the " + strname
		elif not plural:
			if strname[0] in Data.vowels:
				strname = "an " + strname
			else:
				strname = "a " + strname
		if cap:
			strname = capWords(strname)
		return strname



	def describe(self):
		print(f"It's {self.stringName()}.")
		print(self.desc)




# the class representing the player, contains all player stats
class Player(Creature):
	def __init__(self,name,desc,traits,status,hp,mp,money,inv,gear,xp,rp,spells):
		Creature.__init__(self,name,desc,"","",traits,status,hp,mp,money,inv,gear)
		self.xp = xp
		self.rp = rp
		self.spells = spells



	### File I/O ###

	@classmethod
	def convertFromJSON(cls,d):
		return cls(d["name"],d["desc"],d["traits"],d["status"],d["hp"],d["mp"],d["money"],d["inv"],d["gear"],d["xp"],d["rp"],d["spells"])



	### Operation ###

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		if(f"{type} vulnerability" in self.status): dmg *= 2
		if(f"{type} resistance" in self.status): dmg /= 2
		if(f"{type} immunity" in self.status): dmg = 0
		print(f"You took {dmg} {Data.dmgtypes[type]} damage.")
		# player hp lowered to a minimum of 0
		self.hp = min0(self.hp-dmg)
		if(self.hp == 0):
			self.death()


	# heals player hp a given amount
	def heal(self,heal):
		if self.hp + heal > self.MXHP():
			heal = self.MXHP() - self.hp
		self.hp += heal
		print(f"You healed {heal} HP.")
		return heal


	# player gets 3 QPs for each level gained, can dispense them into any trait
	def levelUp(self,oldlv,newlv):
		input(f"You leveled up to level {newlv}!\n")
		QP = 3*(newlv-oldlv)
		while QP > 0:
			clearScreen()
			self.printTraits()
			print(f"\nQuality Points:	{QP}")
			trait = input("What trait will you improve?\n> ").upper()
			if trait not in Data.traits:
				continue
			# increment corresponding player trait
			traitval = getattr(self,trait)
			if traitval >= 20:
				input(f"Your {trait} cannot be raised any higher.\n")
				continue
			setattr(self,trait.upper(),traitval+1)
			QP -= 1
		clearScreen()
		self.printTraits()
		print(f"\nQuality Points:	{QP}")
		input("You are done leveling up.\n")
		clearScreen()
		self.checkHindered()


	# adds money
	def gainMoney(self,money):
		print(f"\nYou gained Ᵽ{money}!")
		self.money += money


	def obtainItem(self,I,msg=None):
		source = I.parent
		if self.addItem(I):
			if source != None:
				source.removeItem(I)
			if msg != None:
				print(msg)
			I.Obtain(self)
			self.checkHindered()
			return True
		print(f"You can't take the {I.name}, your Inventory is too full.")
		return False


	# adds xp, checks for player level up
	def gainxp(self,newxp):
		oldlv = self.level()
		print(f"\nYou gained {newxp} xp.\n{self.xp} + {newxp} = {self.xp+newxp}")
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
			print(f"You are {name}.")


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					self.status.remove([condname,duration])
					if not self.hasCondition(condname):
						print(f"You are no longer {condname}.")


	def checkHindered(self):
		if self.invWeight() > self.BRDN():
			if not self.hasCondition("hindered"):
				print("Your Inventory grows heavy.")
				self.addCondition("hindered",-3)
		if self.invWeight() <= self.BRDN():
			if self.hasCondition("hindered"):
				print("Your Inventory feels lighter.")
				self.removeCondition("hindered",-3)


	# called when player hp hits 0
	def death(self):
		print("You have died!")
		game.quit = True
		# TODO:
		# check if there's any auto-resurrect features
		# ask to continue from checkpoint (last save)
		# or to load a different save
		# or to quit game


	def dualAttack(self,target):
		print("\nDual Attack!")
		hit = min1(maxm(99, self.ACCU() - target.EVSN()))
		if diceRoll(1,100,0) <= hit:
			crit = diceRoll(1,100,0) <= self.CRIT()
			attack = self.ATCK()
			if crit:
				print("Critical hit!")
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if target.alive == False:
				return
		else:
			print("Aw it missed.")


	def attackCreature(self,target):
		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			print(f"{n} attacks:")
		for i in range(n):
			if n > 1:
				print(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = min1(maxm(99, self.ACCU() - target.EVSN()))
			if diceRoll(1,100,0) <= hit:
				crit = diceRoll(1,100,0) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					print("Critical hit!")
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
				if target.alive == False:
					return
			else:
				print("Aw it missed.")
			if self.weapon2 != Empty():
				self.dualAttack(target)
			if target.alive == False:
				return


	def attackItem(self,target):
		attack = self.ATCK()
		print(f"{attack} damage")
		if target.durability != -1 and attack > target.durability:
			target.Break()
		else:
			print("Nothing happens.")
			return



	### Getters ###

	def countCompasses(self):
		return len([item for item in self.inv if isinstance(item,Compass)])


	# wrapper for objSearch()
	# returns player Inventory as a set of all items in the Item Tree
	def invSet(self):
		return objSearch(self,d=2)


	# weird formula right? returns a positive number rounded down to nearest int
	# to see an approximate curve, graph y = 5*log10(x/10)
	# note that a lower bound is set to level 1 when xp < 16
	# also note that the level cannot be higher than 50
	def level(self):
		return 1 if self.xp < 16 else maxm(50,floor( 5*log10(self.xp/10) ))


	# wrapper for objSearch, sets the degree of the search 2 by default
	# returns items in player inv object tree whose names match given term
	def search(self,term,d=2,reqParent=None):
		term = term.lower()
		key = lambda obj: term == obj.name.lower() or term == obj.descname.lower() or term in obj.aliases
		matches = objSearch(self,key=key,d=d)

		if reqParent != None:
			reqParent = reqParent.lower()
			condition = lambda obj: reqParent == obj.parent.name.lower() or reqParent == obj.parent.descname.lower() or reqParent in obj.parent.aliases
			matches = list(filter(condition,matches))

		return matches


	### User Output ###

	# prints all 10 player traits
	def printTraits(self):
		for trait in Data.traits:
			if trait in {"STR","CHA"}:
				print()
			else:
				print("\t\t",end="")
			print(f"{trait}: {getattr(self,trait)}",end="")
		print()


	def printAbility(self,ability):
		if ability == "ATCK":
			print(f"ATCK: {self.STR} - {self.weapon.might*self.STR}")
		elif ability == "BRDN":
			print(f"BRDN: {self.invWeight()}/{self.BRDN()}")
		else:
			print(f"{ability}: {getattr(self,ability)()}")


	def printAbilities(self):
		for ability in Data.abilities:
			self.printAbility(ability)


	# each prints a different player stat
	def printMoney(self): print(f"Ᵽ {self.money}")
	def printHP(self): print(f"HP: {self.hp}/{self.MXHP()}")
	def printLV(self): print(f"LV: {self.level()}")
	def printMP(self): print(f"MP: {self.mp}/{self.MXMP()}")
	def printXP(self): print(f"XP: {self.xp}")
	def printRP(self): print(f"RP: {self.rp}")


	def printSpells(self):
		print(f"Spells: {len(self.spells)}/{self.SPLS()}")
		if len(self.spells) == 0:
			print("\nYou don't know any spells.")
		else:
			columnPrint(self.spells,8,12)


	# prints player inventory
	def printInv(self):
		print(f"Weight: {self.invWeight()}/{self.BRDN()}")
		if len(self.inv) == 0:
			print("\nInventory is empty.")
		else:
			columnPrint(self.invNames(),8,12)


	# print each player gear slot and the items equipped in them
	def printGear(self):
		print()
		for slot in self.gear:
			print(slot + ":\t",end="")
			print(self.gear[slot].name)


	def printStatus(self):
		if len(self.status) == 0:
			print("None")
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
	def printStats(self):
		stats = [self.name, f"Ᵽ {self.money}", f"LV: {self.level()}", f"RP: {self.rp}", f"HP: {self.hp}/{self.MXHP()}", f"MP: {self.mp}/{self.MXMP()}"]
		columnPrint(stats,2,16)
		if len(self.status) != 0:
			self.printStatus()


	# for every item in player inventory, if its a weapon, print it
	def printWeapons(self):
		if len(self.weapons()) == 0:
			print("You have no weapons.")
		else:
			columnPrint(self.weapons(),12,12)




##########################
## SUBCLASS DEFINITIONS ##
##########################


class Animal(Creature):
	def act(self):
		if not self.alive:
			return
		if not game.silent:
			print(f"\n{self.name}'s turn!")
		self.attack()


	def attack(self):
		if not game.silent:
			print("attack?")


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
	def __init__(self,name,desc,aliases,plural,weight,durability,status,mention):
		Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.mention = mention
		self.parent = None



	### Operation ###

	def Break(self):
		if self.durability == -1:
			if not game.silent:
				print(f"The {self.name} cannot be broken.")
			return False
		self.parent.removeFixture(self)



class Passage(Fixture):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,mention,connections,descname,passprep):
		Fixture.__init__(self,name,desc,aliases,plural,weight,durability,status,mention)
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
			print(f"The {self.name} does not go '{dir}'.")
			return False

		if self.passprep != "":
			print(f"You go {dir} {self.passprep} the {self.name}.")
		else:
			print(f"You go {dir} the {self.name}.")

		newroom = world[self.connections[dir]]
		game.changeRoom(newroom)
		return True




class Pylars(Item):
	def __init__(self,value,status):
		self.name = "Gold"
		self.desc = f"{str(value)} glistening coins made of an ancient metal"
		self.aliases = ["coin","coins","money","pylar","pylars"]
		self.plural = "gold"
		self.weight = value
		self.durability = -1
		self.status = []
		self.descname = str(value) + " Gold"
		self.value = value



	### File I/O ###

	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		return {
			"__class__": self.__class__.__name__,
			"value": self.value,
			"status": []
		}



	### Operation ###

	def Obtain(self,creature):
		creature.gainMoney(self.value)


	def merge(self,other):
		if not isinstance(other,Pylars):
			raise TypeError("Cannot merge non-Pylars with Pylars")

		self.status += other.status
		self.value += other.value
		self.desc = f"{str(self.value)} glistening coins made of an ancient metal"



	### User Output ###

	def stringName(self,n=1,plural=False,definite=False,cap=False):
		strname = self.descname
		strname = "Gold"
		strname = str(self.value) + " " + strname
		if definite:
			strname = "the " + strname
		if cap:
			strname = capWords(strname)
		return strname




class Weapon(Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,might,sleight,sharpness,range,twohanded,type):
		Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.might = might
		self.sleight = sleight
		self.sharpness = sharpness
		self.range = range
		self.twohanded = bool(twohanded)
		self.type = type


	def print(self):
		print(f"{self.name} {self.might} {self.sleight}")
		print(f"{self.sharpness} { self.twohanded} {self.range}")




class Shield(Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,prot):
		Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.prot = prot




class Armor(Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,prot):
		Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.prot = prot


	def Equip(self):
		pass


	def Unequip(self):
		pass




class Helm(Armor):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,prot):
		Armor.__init__(self,name,desc,aliases,plural,weight,durability,status,prot)




class Tunic(Armor):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,prot):
		Armor.__init__(self,name,desc,aliases,plural,weight,durability,status,prot)




class Greaves(Armor):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,prot):
		Armor.__init__(self,name,desc,aliases,plural,weight,durability,status,prot)




class Compass(Item):
	def Orient(self):
		print("Orienting you northward!")




class Monster(Creature):
	### Operation ###

	def act(self):
		if not self.alive:
			return
		if not game.silent:
			print(f"\n{self.name}'s turn!")
		self.attack()


	def attack(self):
		# if creature is not in same room as player
		if game.currentroom != self.room():
			return
		# choose strongest weapon or use hand
		# if len(self.weapons()) == 0:
		# 	weapon = Hand("goblin hand","",4,-1,[])
		# 	weapon = weapon.improviseWeapon()
		# else:
		# 	weapon = max(self.weapons(),key=lambda x: x.might)


	# called when a creature's hp hits 0
	def death(self):
		self.alive = False
		print("\nagh its... ded?")
		# TODO: make this just drop some random number of money not just LOOT
		n = diceRoll(3,player.LOOT(),-2)
		self.room().addItem(Pylars(n,[]))
		if not game.silent:
			print(f"Dropped Ᵽ {n}.")
		if game.whoseturn is player:
			# TODO: verify that this is an acceptable formula
			lv = player.level()
			xp = lv * self.level() + diceRoll(lv,self.LCK,self.LCK)
			player.gainxp(xp)


	### Getters ###

	def describe(self):
		print(f"It's {self.stringName()}.")
		print(self.desc)
		gearitems = [item for item in self.gear.values() if item != Empty()]
		if len(gearitems) != 0:
			print(f"It has {listObjects(gearitems)}.")


	def level(self):
		return self.rating() // 10


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




class Person(Creature):
	def act(self):
		pass



player = Player("","",[0]*10,[],0,0,0,[],{},0,0,[])
game = Game(-1,-1,-1,-1,-1)
world = {}
