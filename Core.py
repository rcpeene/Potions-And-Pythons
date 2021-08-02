# Core.py
# This file contains all core functions and classes used throughout the game
# This file is a dependency of Objects.py and is dependent on Data.py

# It consists of four main parts;
# 1. Core functions			(used in Objects.py, Menu.py, and Parser.py)
# 2. Core class definitions	(empty, game, room, item, creature, player, etc.)
# 3. Effect functions 		(functions which affect the game in some unique way)
# 4. Effect dictionary		(used to identify effect functions from strings)

from time import sleep
from random import randint,choice
from math import floor, log10
from bisect import insort

from Data import *


####################
## CORE FUNCTIONS ##
####################

def hasMethod(obj,methodname):
	possibleMethod = getattr(obj,methodname,None)
	if not possibleMethod:
		possibleMethod = getattr(obj.__class__,methodname,None)
	if possibleMethod != None and callable(possibleMethod):
		return True
	return False

# prints 30 newlines
def clearScreen():
	# try: os.system("cls")
	# except: os.system("clear")
	print("\n"*64)

def flushInput():
	try:
		import msvcrt
		while msvcrt.kbhit():
			msvcrt.getch()
	except ImportError:
		import sys, termios
		termios.tcflush(sys.stdin,termios.TCIOFLUSH)

def kbInput():
	try:
		import msvcrt
		return msvcrt.kbhit()
	except ImportError:
		print("cannot check for keyboard input on non-windows OS")

# prints a timed ellipsis, used for transitions
def ellipsis(n):
	for i in range(n):
		sleep(1)
		print(".")

# prints a list of strings l into n columns of width w characters
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

# grammar print, adds punctuation and determiners
# n is the 'number' of an item, denoting its plurality
def gprint(det,text,pos,n):
	if text[0] in vowels and det == "a":
		det = "an"
	if n > 1:
		det = str(n)
		text = text + "s" #pluralize the text, maybe find a more robust way
	string = det + " " + text
	if pos == 0:
		string = string[0].upper() + string[1:]
	elif pos == 2:
		string = string + "."
	elif pos == 3:
		string = string + ","
	string = string + " "
	return string

# capitalizes all the words in a string
def capWords(string):
	listString = string.split(' ')
	cappedString = ''
	for word in listString: cappedString += word[0].upper() + word[1:] + ' '
	return cappedString[0:-1]	# removes trailing space character

# returns the ordinal string for a number n
def ordinal(n):
	lastDigit = n % 10
	if lastDigit == 1:		suffix = "st"
	elif lastDigit == 2:	suffix = "nd"
	elif lastDigit == 3:	suffix = "rd"
	else:					suffix = "th"
	return str(n) + suffix

def expandDir(term):
	if term in directions:	return directions[term]
	else:					return term

# returns a list of element names for L, a list of objects with name attribute
def namesList(L):
	names = []
	for elem in L:
		if hasattr(elem,"descname"):
			names.append(elem.descname)
		else:
			names.append(elem.name)
	return names

# takes a list of strings and converts it to a list of pairs of the form;
# [(str1, n1), (str2, n2), (str3, n3)] where n is the count of of each element
def bagItems(items):
	bag = []
	for name in items:
		for entry in bag:
			if entry[0] == name:
				entry[1] +=1
				break
		else:
			bag.append([name,1])
	return bag

# takes a list of item objects. Defines names as a bagged list of item names
# returns a string that grammatically lists all strings in names
def listItems(items):
	nameBag = bagItems(namesList(items))
	l = len(nameBag)
	string = ""
	for i in range(l):
		name = nameBag[i][0]
		count = nameBag[i][1]
		if i == l-1:	string += gprint("a",name,1,count)
		elif i == l-2:	string += gprint("a",name,3,count) + "and "
		else:			string += gprint("a",name,3,count)
	return string

# prints a question, gets a yes or no, returns True or False respectively
def yesno(question):
	while True:
		command = input(question + '\n> ').lower()
		if command in yesses:	return True
		elif command in noes:	return False
		print("Enter yes or no")

# rolls n dice of range d adds a modifier m, returns number
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
# thus all objects within a room can be thought of as a tree graph...
# where each node is an item or creature, and the root is the room
# the player object can also be thought of this way where the player is the root

# this function recursively searches the tree of objects for an object...
# whose name matches the given term, (not case sensitive)
# if returnPath; returns a list of the path from the found node to the root node
# elif returnSource; returns a tuple of the found node and its parent
# if reqSource != None, then the search only succeeds if it finds an object...
# which belongs to a parent object whose name matches reqSource

# d is the 'degree' of the search; how thorough it is'
# if d is 3, searches through all objects from the root
# elif d is 2, searches through all objects which are not locked
# elif d is 1, searches through objects which are not locked and not in...
# creature inventories; i.e. objects which are "accessible" to the player
# if d is 0, searches through items which are not "closed" and not in...
# creature inventories; i.e. objects which are "visible" to the player
def objSearch(term,root,d=0,getPath=False,getSource=False,reqSource=None):
	O,S,path = objSearchRecur(term,root,[],d,reqSource)
	if getPath:		return O,path
	elif getSource:	return O,S
	else:			return O

def objSearchRecur(term,node,path,d,reqSource):
	S = None						# source object is initially None
	O = None						# object is initially None
	# choose list of objects to search through depending on the node's type
	if isinstance(node,Room):	searchThrough = node.contents + node.occupants
	elif hasattr(node,"contents"):	searchThrough = node.contents
	elif hasattr(node,"inv"):		searchThrough = node.inv
	# if node is unsearchable, return
	else:	return O,S,path
	# first, just searches objects in the "top level" of the tree
	for I in searchThrough:
		# don't search the current node if it is not the required source
		if reqSource != None and reqSource != node.name:	break
		if I.name.lower() == term:
			S,O = node,I
			break
	# then, recursively searches each object's subtree
	for I in searchThrough:
		# if target object was already found, no need to search deeper
		if O != None:	break
		# depending on the degree, skips closed, locked, or creature objects
		if d == 0 and hasattr(I,"open") and not I.open:		continue
		elif (d <= 1) and isinstance(I,Creature):			continue
		elif d <= 2 and hasattr(I,"locked") and I.locked:	continue
		# recur objSearch on each object node, I
		O,S,path = objSearchRecur(term,I,path,d,reqSource)
	# if an object was found, append the search path before returning
	if O != None:	path.append(node)
	return O,S,path

# this function takes the same principle as objSearch, recursively traversing...
# the tree of objects, except that it does not search for a specific object...
# it returns a set of all the objects found in the tree
# d, the degree of the traversal, works the same as in objSearch() above
# if getSources, the set will consist of tuples of object,source pairs
def objTreeToSet(root,d=0,getSources=False):
	# A is the set of all objects encountered by the traversal
	A = set()
	# determine what to search through based on the root's type
	if isinstance(root,Room):	searchThrough = root.contents + root.occupants
	elif hasattr(root,"contents"):	searchThrough = root.contents
	elif hasattr(root,"inv"):		searchThrough = root.inv
	# if the item is not searchable, return empty set
	else:	return set()
	for I in searchThrough:
		# add the item to the set of all items
		if getSources:	A.add((I,root))
		else:			A.add(I)
		# depending on the degree, skips closed, locked, or creature objects
		if d == 0 and hasattr(I,"open") and not I.open:		continue
		elif (d <= 1) and isinstance(I,Creature):			continue
		elif d <= 2 and hasattr(I,"locked") and I.locked:	continue
		# unionize the set of all items with item I's set
		A = A | objTreeToSet(I,d=d,getSources=getSources)
	return A


############################
## SUPERCLASS DEFINITIONS ##
############################

# used for general instances that must have certain attributes, but can all be 0
class Empty():
	def __init__(self):
		self.name = "[empty]"
		self.weight = 0
		self.prot = 0
		self.might = 1
		self.sleight = 0
		self.sharpness = 0
		self.type = "e"

	def __repr__(self):
		return "{}".format(self.name)

	def __str__(self):
		return "{}".format(self.name)

	def __eq__(self, other) :
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False

	def writeAttributes(self, fd):
		fd.write("")

	def Weight(self):	return 0

	def improviseWeapon(self):
		return Weapon("empty hand","",0,-1,1,0,0,0,False,"b")

# contains attributes that are used globally throughout the game
class Game():
	def __init__(self,mode,currentroom,prevroom,time):
		self.mode = mode
		self.currentroom = currentroom
		self.prevroom = prevroom
		self.time = time
		self.whoseturn = None
		self.lastRawCommand = None
		# pronoun attributes store an object which may be...
		# implied by that pronoun from user input
		self.it = None
		self.they = None
		self.her = None
		self.him = None

	def startUp(self,P,W):
		self.currentroom.describe()

	def describeRoom(self):
		self.currentroom.describe()

	def incrementTime(self,P,W):
		self.time += 1
		P.passTime(1)
		for room in self.renderedRooms(W):
			room.passTime(1)
			for creature in room.occupants:
				creature.passTime(1)

	def clearPronouns(self):
		self.it = None
		self.they = None
		self.her = None
		self.him = None

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

	def sortOccupants(self,W):
		for room in self.renderedRooms(W):
			room.sortOccupants()

	# recursively adds all adjacent rooms to the set of found rooms
	# n is the path length at which the search stops
	# Sroom is the "source" room, or the current node in the search
	def roomFinder(self,n,Sroom,pathlen,foundrooms,W):
		if pathlen >= n:
			return
		adjacentRooms = [W[name] for name in Sroom.allExits().values()]
		for room in adjacentRooms:
			foundrooms.add(room)
			self.roomFinder(n,room,pathlen+1,foundrooms,W)

	# returns set of all rooms connected to currentroom with path < REND_DIST
	def renderedRooms(self,W):
		# constant render distance of rooms in world
		REND_DIST = 3
		R = {self.currentroom}
		self.roomFinder(REND_DIST,self.currentroom,0,R,W)
		return R

	# gets set of all rendered rooms except the current room
	def nearbyRooms(self,W):
		R = self.renderedRooms(W)
		R.remove(self.currentroom)
		return R

	def changeRoom(self,newroom,P,W):
		self.clearPronouns()
		self.prevroom.exit(P,W,self)
		self.prevroom = self.currentroom
		self.currentroom = newroom
		self.currentroom.enter(P,W,self)
		return True

	def destroyCreature(self,C,W):
		for room in self.renderedRooms(W):
			if C in room.occupants:
				room.removeCreature(C)

	## perhaps unnecessary code
	# def destroyItem(self,I,W):
	# 	for room in self.renderedRooms(W):
	# 		allObjects = objTreeToSet(room,d=3,getSources=True)
	# 		for (object,source) in allObjects:
	# 			if object is I:
	# 				source.removeItem(object)

	# returns a list of objects in rendered rooms which fit a certain condition
	def searchRooms(self,key,W,d=3):
		matchingObjects = []
		for room in self.renderedRooms(W):
			allObjects = objTreeToSet(room,d=d)
			for obj in allObjects:
				if key(obj):
					matchingObjects.append(obj)
		return matchingObjects

	# returns a set of all objects in the world (does not include player inv)
	def getAllObjects(self,W,getSources=False):
		allObjects = []
		for room in self.renderedRooms(W):
			roomObjects = objTreeToSet(room,d=3,getSources=getSources)
			for elem in roomObjects:
				allObjects.append(elem)
		return allObjects

	# true if there's an object in rendered rooms whose name matches objname
	def inWorld(self,objname,W):
		key = lambda obj: obj.name.lower() == objname
		objects = self.searchRooms(key,W)
		return len(objects) > 0


# used to define all rooms in the world
class Room():
	def __init__(self,name,desc,exits,contents,occupants,status):
		self.name = name
		self.desc = desc
		self.exits = exits
		self.contents = contents
		self.occupants = occupants
		self.status = status

	def __repr__(self):
		return f"#{self.name}"

	def __str__(self):
		return f"#{self.name}"

	# prints all the contents of the room in sentence form
	def describeContents(self):
		if len(self.contents) != 0:
			print("There is " + listItems(self.contents))

	# prints all the creatures in the room in sentence form
	def describeOccupants(self):
		if len(self.occupants) != 0:
			print("There is " + listItems(self.occupants))

	def sortOccupants(self):
		self.occupants.sort(key=lambda x: x.MVMT(), reverse=True)

	def addConnection(self,dir,loc):
		self.exits[dir] = loc

	def getPassages(self):
		return [item for item in self.contents if isinstance(item,Passage)]

	def getPassageFromDir(self,dir):
		for passage in self.getPassages():
			if dir in passage.connections:
				return passage
		return None

	def getDirFromDest(self,dest):
		if dest in self.allExits().values():
			idx = list(self.allExits().values()).index(dest)
			dir = list(self.allExits().keys())[idx]
			return dir

	# returns dict of exits, where keys are pairs of a direction and passage...
	# and values are room names
	def allExits(self):
		all = {}
		for dir in self.exits:
			all[dir] = self.exits[dir]
		# get a list of passages in the room (non-recursive search)
		passages = self.getPassages()
		# for each passage, add its connections to all
		for passage in passages:
			for dir in passage.connections:
				all[dir] = passage.connections[dir]
		return all

	# prints room name, description, all its contents and creatures
	def describe(self):
		print("\n" + capWords(self.name))
		print(self.desc)
		self.describeContents()
		self.describeOccupants()

	def enter(self,P,W,G):
		self.describe()
		# for tuple in effectslist:
		# 	func name = tuple

	def exit(self,P,W,G):
		pass

	def addItem(self,I):
		insort(self.contents,I)

	def removeItem(self,I):
		if I in self.contents:
			self.contents.remove(I)

	def addCreature(self,C):
		insort(self.occupants,C)

	def removeCreature(self,C):
		if C in self.occupants:
			self.occupants.remove(C)

	def search(self,term,d=0,getSource=False,getPath=False,reqSource=None):
		return objSearch(term,self,d=d,
		getSource=getSource,getPath=getPath,reqSource=reqSource)

	# takes a string, term, and searches the room's contents
	# if an item is found that matches term, return it, otherwise, return None
	def inContents(self,term):
		for item in self.contents:
			if item.name == term:	return item
		return None

	# takes a string, term, and searches the room's occuptants
	# if a creature matches the term , return it, otherwise, return False
	def inOccupants(self,term):
		for creature in self.occupants:
			if creature.name == term:	return creature
		return None

	def contentNames(self):
		return [item.name for item in self.contents]

	def occupantNames(self):
		return [creature.name for creature in self.occupants]

	def addCondition(self,name,dur,stackable=False):
		# TODO: include stackability
		pair = [name,dur]
		insort(self.status,pair)

	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					self.status.remove([condname,duration])

	def hasCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					return True
		return False

	def passTime(self,t):
		for condition in self.status:
			# if condition is a special condition, ignore it
			if condition[1] < 0:
				continue
			# subtract remaining duration on condition
			elif condition[1] > 0:
				condition[1] -= t
			# if, after subtraction, condition is non-positive, remove it
			if condition[1] <= 0:
				self.removeCondition(condition[0],0)

# general item class, all items come with a name, description, weight
class Item():
	def __init__(self,name,desc,weight,durability):
		self.name = name
		self.desc = desc
		self.weight = weight
		self.durability = durability

	def __repr__(self):
		return f"${self.name}"

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

	# used to create a generic Weapon() if this item is used to attack something
	def improviseWeapon(self):
		#TODO: if item is too large/heavy, make it two-handed
		return Weapon(self.name,self.desc,self.weight,self.durability,min1(self.weight//4),0,0,0,False,"b")

	def describe(self):
		print("It's " + gprint("a",self.name,3,1), end="")
		print(self.desc)

	def Weight(self):
		return self.weight

	def Obtain(self,P,W,G):
		pass

	def Break(self,G,W,S):
		S.removeItem(self)

# general creature class for all living things in the game
class Creature():
	def __init__(self,name,desc,hp,mp,traits,money,inv,gear,status):
		self.name = name
		self.desc = desc
		self.hp = hp
		self.mp = mp

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

		self.money = money
		self.inv = inv
		# convert gear from its stored form in files to its runtime form
		self.gear = {key: inv[gear[key]] if gear[key] != -1 else Empty() for key in gear}

		self.status = status
		# sort status effects by duration; change '1' to '0' to sort by name
		self.status.sort(key=lambda x: x[1])

		self.weapon = Empty()
		self.weapon2 = Empty()
		self.shield = Empty()
		self.shield2 = Empty()

		# these attributes remain unused in the Player subclass
		self.alive = True
		self.alert = False
		self.seesPlayer = False
		self.sawPlayer = -1

	def __repr__(self):
		return f"!{self.name}"

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

	# converts the gear dict to a form more easily writable to a save file
	# replaces all objects in gear.values() with an integer which represents...
	# the index of the equipped object in the creature's inventory
	# if the gear slot is empty, replaces it with -1
	def compressGear(self):
		C = {}
		for key in self.gear:
			item = self.gear[key]
			if item == Empty():
				C[key] = -1
				continue
			try:	C[key] = self.inv.index(item)
			except:	raise Exception("gear item not found in inventory")
		return C

	def convertToJSON(self):
		compressedGear = self.compressGear()
		d = self.__dict__.copy()
		dictkeys = list(d.keys())
		for key in dictkeys:
			if key in traits or key in {"gear","weapon","weapon2","shield","shield2","alive","alert","seesPlayer","sawPlayer"}:
				del d[key]
		d["gear"] = compressedGear
		d["traits"] = [self.STR,self.SKL,self.SPD,self.STM,self.CON,self.CHA,self.INT,self.WIS,self.FTH,self.LCK]
		d["__class__"] = self.__class__.__name__
		return d

	@classmethod
	def convertFromJSON(cls,d):
		# thisobj = cls(0,0,0,0,[0 for i in range(10)],0,0,{},[])
		# for key in d:
		# 	val = dict[key]
		# 	setattr(thisobj,key,val)
		thisobj = cls(d["name"],d["desc"],d["hp"],d["mp"],d["traits"],d["money"],d["inv"],d["gear"],d["status"])
		return thisobj

	# returns sum of the weight of all items in player inventory
	def invWeight(self):
		weight = 0
		for item in self.inv: weight += item.Weight()
		return weight

	def handheldWeight(self):
		return self.weapon.weight + self.weapon2.weight + self.shield.weight + self.shield2.weight

	# returns a list of names of all items in player inventory
	def invNames(self,lower = False):
		if lower:
			return [item.name.lower() for item in self.inv]
		return [item.name for item in self.inv]

	# just a function wrapper for functions that call contentNames on objects
	def contentNames(self):
		return self.invNames()

	# searches through inventory for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return None
	def inInv(self,term):
		for item in self.inv:
			if item.name.lower() == term:	return item
		return None

	# searches through gear for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return None
	def inGear(self,term):
		for slot in self.gear:
			if self.gear[slot].name.lower() == term:
				return self.gear[slot]
		return None

	# returns sum of the weight of all items in player gear
	def gearWeight(self):
		weight = 0
		for item in self.gear:
			if hasattr(self.gear[item], "weight"):
				weight += self.gear[item].Weight()
		return weight

	def improviseWeapon(self):
		#TODO: if item is too large/heavy, make it two-handed
		return Weapon(self.name,self.desc,self.CON,self.CON,min1(self.Weight()//4),0,0,0,False,"b")

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
			self.weapon = self.weapon.improviseWeapon()
		if not isinstance(self.weapon2,Weapon):
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
		#finds the slot whose value is item, sets it to empty
		slot = gearslots[gearitems.index(I)]
		self.gear[slot] = Empty()
		self.assignWeaponAndShield()
		if hasMethod(I,"Unequip"):
			I.Unequip(self)

	# if the item is armor, equip it, otherwise return False
	def equipArmor(self,I):
		if isinstance(I,Helm):		self.gear["head"] = I
		elif isinstance(I,Tunic):	self.gear["body"] = I
		elif isinstance(I,Greaves):	self.gear["legs"] = I
		else:	return False
		I.Equip(self)
		return True

	# unequips the lefthanded item, moves righthanded item to left,
	# equips the new item in right hand
	# if the new item is twohanded, set lefthand to Empty()
	# calls the new item's Equip() method if it has one
	def equipInHand(self,I):
		self.unequip(self.gear["left"])
		self.gear["left"] = self.gear["right"]
		self.gear["right"] = I
		if hasattr(I, "twohanded") and I.twohanded:
			self.gear["left"] = Empty()
		self.assignWeaponAndShield()
		if hasMethod(I,"Equip"): I.Equip(self)

	def describe(self):
		if hasattr(self,"descname"):
			print(f"It's {gprint('a',self.descname,3,1)}", end="")
		else:
			print(f"It's {gprint('a',self.name,3,1)}", end="")
		print(self.desc)

	def addItem(self,I):
		if self.invWeight() + I.Weight() > self.BRDN() * 2:
			return False
		insort(self.inv,I)
		return True

	def removeItem(self,I):
		if I in self.gear.values():
			self.unequip(I)
		self.inv.remove(I)
		if hasMethod(I,"Drop"):
			I.Drop(self)
		if self.invWeight() < self.BRDN():
			self.removeCondition("hindered",-3)

	def passTime(self,t):
		for condition in self.status:
			# if condition is a special condition, ignore it
			if condition[1] < 0:
				continue
			# subtract remaining duration on condition
			elif condition[1] > 0:
				condition[1] -= t
			# if, after subtraction, condition is non-positive, remove it
			if condition[1] <= 0:
				self.removeCondition(condition[0],0)

	def addCondition(self,name,dur,stackable=False):
		# TODO: include stackability
		pair = [name,dur]
		insort(self.status,pair)

	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					self.status.remove([condname,duration])

	def hasCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					return True
		return False

	def checkHindered():
		if self.invWeight() + I.Weight() > self.BRDN():
			if not self.hasCondition("hindered"):
				print("Your inventory grows heavy")
				self.addCondition("hindered",-3)

	# these are creature stats that are determined dynamically with formulas
	# these formulas are difficult to read, check design document for details
	def ACCU(self): return 50 + 2*self.SKL + self.LCK + self.weapon.sleight
	def ATCK(self): return diceRoll(self.STR, self.weapon.might, 0)
	def ATHL(self): return self.STR + self.SKL + self.STM
	def ATSP(self): return self.SPD - min0(self.handheldWeight()//4 - self.CON)
	def BRDN(self): return self.CON * self.STR * 4 + 60
	def CAST(self): return self.WIS + self.FTH + self.INT - min0(self.gearWeight()//4 - self.CON)
	def CRIT(self): return self.SKL + self.LCK + self.weapon.sharpness
	def CSSP(self): return self.WIS - min0(self.invWeight() - self.BRDN()) - min0(self.gearWeight()//4 - self.CON)
	def DCPT(self): return 2*self.CHA + self.INT
	def DFNS(self): return self.CON + self.armor()
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
	def SLTH(self): return ( 2*self.SKL + self.INT - min0(self.invWeight() - self.BRDN()) ) * 2*self.hasCondition("hiding")
	def SPLS(self): return 2*self.INT
	def TNKR(self): return 2*self.INT + self.SKL

	# returns sum of all protection values of all items in gear
	def armor(self):
		prot = 0
		for slot in self.gear:
			item = self.gear[slot]
			if hasattr(item, "prot"):
				prot += item.prot
		return prot

	# called when a creature's hp hits 0
	def death(self,P,G,W):
		self.alive = False
		print("agh its... ded?")
		G.destroyCreature(self,W)
		#drop some wealth or items if its players turn
		if G.whoseturn is P:
			P.gainxp(10)
			P.gainMoney(P.LOOT())

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takedmg(self,dmg,type,P,G,W):
		if(f"{type} vulnerability" in self.status):	dmg *= 2
		if(f"{type} resistance" in self.status):	dmg //= 2
		if(f"{type} immunity" in self.status):		dmg = 0
		print(f"Took {dmg} {dmgtypes[type]} damage")
		self.hp = min0( self.hp-dmg)	#player hp lowered to a minimum of 0
		if(self.hp == 0):
			self.death(P,G,W)

	def Restrain(self,restrainer,item):
		if item != None:
			#TODO: add restraining with items? like rope??
			pass
		if self.ATHL() > restrainer.ATHL() or self.EVSN() > restrainer.ATHL():
			return False
		restrainer.addCondition("restraining",-3)
		self.addCondition("restrained",-3)
		return True

	def isBloodied(self):
		# returns true is creature has less than half health
		pass

	def alliesPresent(self):
		# returns number of allies creature can see
		pass

	def enemiesPresent(self):
		# returns number of enemies creature can see
		pass

# the class representing the player, contains all player stats
class Player(Creature):
	def __init__(self,name,desc,hp,mp,traits,money,inv,gear,status,xp,rp,crouched):
		Creature.__init__(self,name,desc,hp,mp,traits,money,inv,gear,status)
		self.xp = xp
		self.rp = rp
		self.crouched = crouched

	@classmethod
	def convertFromJSON(cls,d):
		thisobj = cls(d["name"],d["desc"],d["hp"],d["mp"],d["traits"],d["money"],d["inv"],d["gear"],d["status"],d["xp"],d["rp"],d["crouched"])
		return thisobj

	# wrapper for objSearch, sets the degree of the search 2 by default
	# returns an item in player inv object tree whose name matches given term
	def search(self,term,d=2,getSource=False,getPath=False,reqSource=None):
		return objSearch(term,self,
		d=d,getSource=getSource,getPath=getPath,reqSource=reqSource)

	# wrapper for objTreeToSet()
	# returns player inventory as a set of all items
	def invSet(self):
		return objTreeToSet(self,d=2)

	def weapons(self):
		return [I for I in self.inv if isinstance(I,Weapon)]

	# weird formula right? returns an integer greater than 1 rounded down
	# graph it if you want to know what the curve looks like
	def level(self):
		return 1 if self.xp < 16 else floor(5*log10(self.xp/10))

	# player gets 3 QPs for each level gained, can dispense them into any trait
	def levelUp(self,oldlv,newlv):
		print(f"You leveled up to level {newlv}!\n")
		QP = 3*(newlv-oldlv)
		while QP > 0:
			self.printTraits()
			print(f"\nQuality Points:	{QP}")
			trait = input("What trait will you improve?\n> ").upper()
			i = 0
			while trait not in traits:
				trait = input("> ").upper()
			# increment corresponding player trait
			traitval = getattr(self,trait)
			setattr(self,trait.upper(),traitval+1)
			QP -= 1
		self.printTraits()

	# adds xp, checks for player level up
	def gainxp(self,newxp):
		oldlv = self.level()
		print(f"\nYou gained {newxp} xp\n{self.xp} + {newxp} = {self.xp+newxp}")
		self.xp += newxp
		newlv = self.level()
		if oldlv != newlv: self.levelUp(oldlv,newlv)

	# adds money
	def gainMoney(self,money):
		print(f"\nYou gained Ᵽ{money}!")
		self.money += money

	# called when player hp hits 0
	def death(self):
		print("You have died!")
		# check if there's any auto-resurrect features
		# ask to continue from checkpoint (last save)
		# or to load a different save
		# or to quit game

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takedmg(self,dmg,type):
		if(f"{type} vulnerability" in self.status):	dmg *= 2
		if(f"{type} resistance" in self.status):	dmg /= 2
		if(f"{type} immunity" in self.status):		dmg = 0
		print(f"You took {dmg} {dmgtypes[type]} damage")
		self.hp = min0( self.hp-dmg)	#player hp lowered to a minimum of 0
		if(self.hp == 0):
			self.death()

	# heals player hp a given amount
	def heal(self,heal):
		if self.hp + heal > self.MXHP():
			heal = self.MXHP() - self.hp
		self.hp += heal
		print(f"You healed {heal} HP")
		return heal

	def addCondition(self,name,dur,stackable=False):
		# TODO: include stackability
		pair = [name,dur]
		insort(self.status,pair)
		print("You are " + name)

	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeCondition(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					self.status.remove([condname,duration])
					if not self.hasCondition(condname):
						print("You are no longer " + condname)


	def obtainItem(self,I,S,W,G,msg=None):
		if self.addItem(I):
			S.removeItem(I)
			if msg != None:
				print(msg)
			if hasMethod(I,"Obtain"):
				I.Obtain(self,W,G)
			return True
		print(f"You can't take the {I.name}, your Inventory is too full")
		return False

	def countCompasses(self):
		count = 0
		for item in self.inv:
			if isinstance(item,Compass):
				count +=1
		return count

	def dualAttack(self,target,G,W):
		hit = min1(maxm(99, self.ACCU() - target.EVSN()))
		if diceRoll(1,100,0) <= hit:
			print()
			crit = diceRoll(1,100,0) <= self.CRIT()
			attack = self.ATCK()
			if crit:
				print("Critical hit!")
				attack *= 2
			damage = min0( attack - target.DFNS())
			target.takedmg(damage,self.weapon2.type,self,G,W)
			if target.alive == False:
				return
		else:
			print("Aw it missed")

	def attackCreature(self,target,G,W):
		n = min1( self.ATSP() // min1(target.ATSP()))
		print(f"{n} attacks:")
		for i in range(n):
			print(f"\n{ordinal(i+1)} attack")
			# TODO: what about if weapon is ranged?
			hit = min1(maxm(99, self.ACCU() - target.EVSN()))
			if diceRoll(1,100,0) <= hit:
				crit = diceRoll(1,100,0) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					print("Critical hit!")
					attack *= 2
				damage = min0( attack - target.DFNS())
				target.takedmg(damage,self.weapon.type,self,G,W)
				if target.alive == False:	return
			else:
				print("Aw it missed")
			if self.weapon2 != Empty():	self.dualAttack(target,G,W)
			if target.alive == False:	return

	def attackItem(self,target,G,W):
		attack = self.ATCK()
		print(f"{attack} damage")
		if target.durability != -1 and attack > target.durability:
			target.Break(self,G,G.currentroom)
		else:
			print("Nothing happens")
			return

	# prints all 10 player traits
	def printTraits(self):
		for trait in traits:
			if trait in {"STR","CHA"}:	print()
			else:						print("\t\t",end="")
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
		for ability in abilities:
			self.printAbility(ability)

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

		# make list of strings to display conditions and their durations
		statusdisplay = []
		for i in range(len(conditions)):
			statusdisplay.append(conditions[i])
			if durations[i] < 0:
				statusdisplay.append("--")
			else:
				statusdisplay.append(str(durations[i]))

		# dynamically determine display column width based on longest name
		colWidth = len(max(conditions, key=len)) + 4
		columnPrint(statusdisplay,2,colWidth)

	# each prints a different player stat
	def printMoney(self): print(f"Ᵽ{self.money}")
	def printHP(self): print(f"HP: {self.hp}/{self.MXHP()}")
	def printLV(self): print(f"LV: {self.level()}")
	def printMP(self): print(f"MP: {self.mp}/{self.MXMP()}")
	def printXP(self): print(f"XP: {self.xp}")
	def printRP(self): print(f"RP: {self.rp}")

	# print each player gear slot and the items equipped in them
	def printGear(self):
		print()
		for slot in self.gear:
			print(slot + ":\t",end="")
			print(self.gear[slot].name)

	# prints player inventory
	def printInv(self):
		if len(self.inv) == 0:
			print("Inventory is empty")
		else:
			print("Weight:",self.invWeight())
			columnPrint(self.invNames(),8,12)

	# prints player level, money, hp, mp, rp, and status effects
	def printStats(self):
		stats = [self.name, f"Ᵽ{self.money}", f"LV: {self.level()}", f"RP: {self.rp}", f"HP: {self.hp}/{self.MXHP()}", f"MP: {self.mp}/{self.MXMP()}"]
		columnPrint(stats,2,16)
		if len(self.status) != 0:
			self.printStatus()

	# for every item in player inventory, if its a weapon, print it
	def printWeapons(self):
		if len(self.weapons()) == 0:
			print("You have no weapons")
		else:	columnPrint(self.weapons,12,12)


##########################
## SUBCLASS DEFINITIONS ##
##########################

class Animal(Creature):
	def act(self,P,room,silent):
		if not silent:	print(f"\n{self.name}'s turn!")
		self.attack(P,silent)

	def attack(self,P,silent):
		if not silent:	print("attack?")

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

class Monster(Creature):
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
	def act(self,P,currentroom,silent):
		pass

# almost identical to the item class, but fixtures may not be removed from their initial location. Fixtures also have a size attribute
class Fixture(Item):
	def __init__(self,name,desc,weight,durability):
		Item.__init__(self,name,desc,weight,durability)

class Passage(Fixture):
	def __init__(self,name,desc,weight,durability,connections,descname):
		self.name = name
		self.desc = desc
		self.weight = weight
		self.durability = durability
		self.connections = connections
		self.descname = descname

	def Traverse(self,P,W,G,dir=None):
		if dir == None:
			if len(self.connections) == 1:
				dir = self.connections.keys()[0]
			else:
				msg = f"Which direction will you go on the {self.name}?\n> "
				dir = input(msg)
		if dir not in self.connections:
			print(f"The {self.name} does not go '{dir}'")
			return False
		print(f"You go {dir} the {self.name}")
		newroom = W[self.connections[dir]]
		G.changeRoom(newroom,P,W)
		return True

class Weapon(Item):
	def __init__(self,name,desc,weight,durability,might,sleight,sharpness,range,twohanded,type):
		Item.__init__(self,name,desc,weight,durability)
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
	def __init__(self,name,desc,weight,durability,prot):
		Item.__init__(self,name,desc,durability,weight)
		self.prot = prot

class Armor(Item):
	def __init__(self,name,desc,weight,durability,prot):
		Item.__init__(self,name,desc,weight,durability)
		self.prot = prot

	def Equip(self,P):
		pass

	def Unequip(self,P):
		pass

class Helm(Armor):
	def __init__(self,name,desc,weight,durability,prot):
		Armor.__init__(self,name,desc,weight,prot)

class Tunic(Armor):
	def __init__(self,name,desc,weight,durability,prot):
		Armor.__init__(self,name,desc,weight,durability,prot)

class Greaves(Armor):
	def __init__(self,name,desc,weight,durability,prot):
		Armor.__init__(self,name,desc,weight,durability,prot)

class Compass(Item):
	def Orient(self):
		print("Orienting you northward!")


#######################
##  EFFECT FUNCTIONS ##
#######################

# changes global game mode from 1 to 0 or 0 to 1
def changeMode(G):
	print("Ring!")
	G.mode = 1 if G.mode == 0 else 0

def changeTime(G,t):
	G.time = t

def setStat(C,attrString,val):
	# try:
	attr = getattr(C,attrString)
	# except:
	# 	print("Attribute does not exist")
	# 	return
	if isinstance(attr,int):
		try:
			val = int(val)
		except:
			print("Invalid value type")
			return
	setattr(C,attrString,val)

def changeStat(C,attr,diff):
	try:
		attr = getattr(P,attr)
	except:
		print("Attribute does not exist")
		return
	setattr(C,attr,attr+val)

def addCondition(A,cond):
	A.addCondition(cond)

def removeCondition(A,cond):
	A.removeCondition(cond)

# spawns an item in the room
def spawnItem(G,I):
	print(f"A {I.name} appears in front of you!")
	G.currentroom.addItem(I)

# def destroyItem(S,I):
# 	if isinstance(S,Player):	print(f"Your {I.name} is destroyed")
# 	else:						print(f"The {I.name} is destroyed")
# 	S.removeItem(I)

def destroyItemsByType(R,Type,d=0,msg=""):
	#TODO: make this work efficiently
	items = objTreeToSet(S,d=d)
	for item in items:
		if isinstance(item,Type):
			S,I = objSearch(item.name,R,d=d,reqSource=True)
			S.removeItem(I)
	if msg != "":
		print(msg)


# effects may include:

# spawning/destroying an item
# lowering/raising an items stats
# spawning/destroying a creature
# lowering/raising a creature's stats
# adding/remove a status effect
# altering time/initiative order
# adding/removing a room connection
# adding/removing a room status effect
# creating some obstacle
# changing current room
# to simply give the player information


#######################
## EFFECT DICTIONARY ##
#######################

# effects = {
# 	"addPoisoned":addPoisoned,
# 	"changeMode":changeMode,
# 	"removePoisoned":removePoisoned,
# 	"spawnItem":spawnItem
# }
