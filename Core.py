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
# import json

from Data import *


####################
## CORE FUNCTIONS ##
####################

# prints 30 newlines
def clearScreen():
	print("\n"*64)

def flushInput():
	try:
		import msvcrt
		while msvcrt.kbhit():
			msvcrt.getch()
	except ImportError:
		import sys, termios
		termios.tcflush(sys.stdin, termios.TCIOFLUSH)

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
# n is the 'number' of an item
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
	command = input(question + '\n> ').lower()
	if command in yesses:	return True
	elif command in noes:	return False
	print("Enter yes or no")
	return yesno(question)

# rolls n dice of range d adds a modifier m, returns number
def diceRoll(n,d,m):
	x = 0
	for roll in range(n):
		x += randint(1,d)
	x += m
	return x

# returns a number, n, with a lower bound of m
def minm(m,n): return m if n < m else n

#returns a number, n, with an upper bound of m
def maxm(m,n): return m if n > m else n

# searches a string, text, starting at start index, for matching parenthesis
# returns the index of the closing parenthesis that matches the open parenthesis
# ignores characters which are between quotations ""
def findMatchingParenth(text,start):
	o = text[start]
	if o == '(':	c = ')'
	elif o == '[':	c = ']'
	elif o == '{':	c = '}'
	elif o == '<':	c = '>'
	else:	raise Exception('start character not a valid parenthesis')
	inString = False
	depth = 0
	i = start
	while i < len(text):
		if text[i] == '"':	inString = not inString
		if text[i] == o and not inString:	depth += 1
		if text[i] == c and not inString:	depth -= 1
		if depth == 0:		return i
		i += 1
	raise Exception('no matching parenthesis found')

# takes a set of symbols which count as delimiters
# searches a string, text, starting at start index for the next delimiter symbol
# ignores characters which are between quotations ""
# returns the index of the next delimiter
# if no delimiter is found, returns the length of text
def findNextDelimiter(symbols,text,start):
	inString = False
	for i in range(start,len(text)):
		if text[i] == '"':
			inString = not inString
		if text[i] in symbols and not(inString):
			return i
	return len(text)

# searches through a list of strings, starting at index l
# returns the earliest index of the string which begins with a given symbol
def findLineStartsWith(lines,symbol,start):
	l = start
	while l < len(lines):
		if lines[l][0] == symbol:
			return l
		l += 1

# takes an object of class Empty(), Creature(), or Item()
# writes all the text necessary to store an object's class and its attributes
def writeObj(fd,obj):
	classname = obj.__class__.__name__
	if isinstance(obj, Empty):
		fd.write("")
		return
	elif isinstance(obj, Item):	fd.write("$")
	elif isinstance(obj, Creature):	fd.write("!")
	else:	raise Exception("trying to write obj which is not Item or Creature")
	fd.write(classname + " (")
	obj.writeAttributes(fd)
	fd.write(")")

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
	if getPath:
		return O,path
	elif getSource:
		return O,S
	else:
		return O

def objSearchRecur(term,node,path,d,reqSource):
	S = None						# source object is initially None
	O = None						# object is initially None
	# choose list of objects to search through depending on the node node's type
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
def objTreeToSet(root,d=0):
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
		A.add(I)
		# depending on the degree, skips closed, locked, or creature objects
		if d == 0 and hasattr(I,"open") and not I.open:		continue
		elif (d <= 1) and isinstance(I,Creature):			continue
		elif d <= 2 and hasattr(I,"locked") and I.locked:	continue
		# merge the set of all items with item I's set
		A = A | objTreeToSet(I,d=d)
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
		self.lastRawCommand = None

	def startUp(self,P,W):
		self.currentroom.describe()

	def describeRoom(self):
		self.currentroom.describe()

	def incrementTime(self,P):
		self.time += 1
		P.passTime(1)
		# TODO:
		# for each creature and room (& maybe item):
		# 	for each status effect
		# 		if its duration > 0
		# 			decrement its duration
		# 		if its duration is 0
		# 			delete it
		# 		if its duration is -1
		# 			do nothing

	# recursively adds all adjacent rooms to the set of found rooms
	# n is the path length at which the search stops
	# Sroom is the "source" room, or the current node in the search
	def roomFinder(self,n,Sroom,pathlen,foundrooms,W):
		if pathlen >= n:
			return
		adjacentRooms = [W[name] for name in Sroom.exits.values()]
		for room in adjacentRooms:
			foundrooms.add(room)
			self.roomFinder(n,room,pathlen+1,foundrooms,W)

	# gets set of all other rooms with a path to currentroom less than length n
	def nearbyRooms(self,W):
		# constant render distance of rooms in world
		REND_DIST = 3
		R = set()
		self.roomFinder(REND_DIST,self.currentroom,0,R,W)
		R.remove(self.currentroom)
		return R

	def renderedRooms(self,W):
		rooms = self.nearbyRooms(REND_DIST,W)
		rooms.add(self.currentroom)
		return rooms

	def changeRoom(self,newroom,P,W):
		self.prevroom.exit(P,W,self)
		self.prevroom = self.currentroom
		self.currentroom = newroom
		self.currentroom.enter(P,W,self)

# used to define all rooms in the world
class Room():
	def __init__(self,name,desc,exits,contents,occupants,effects):#,enter,exit):
		self.name = name
		self.desc = desc
		self.exits = exits
		self.contents = contents
		self.occupants = occupants
		self.effects = effects

	def __repr__(self):
		return "{}".format(self.name)

	def __str__(self):
		return "{}".format(self.name)

	# prints all the contents of the room in sentence form
	def describeContents(self):
		if len(self.contents) != 0:
			print("There is " + listItems(self.contents))

	# prints all the creatures in the room in sentence form
	def describeOccupants(self):
		if len(self.occupants) != 0:
			print("There is " + listItems(self.occupants))

	def addConnection(self,dir,loc):
		self.exits[dir] = loc

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
		self.contents.remove(I)

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
		return self.name < other.name

	def __eq__(self,other) :
		if isinstance(other, self.__class__):
			return self.__dict__ == other.__dict__
		else:
			return False

	def __hash__(self):
		return hash(frozenset(self.__dict__))

	def writeAttributes(self,fd):
		fd.write(f'"{self.name}", "{self.desc}", ')
		fd.write(f'{self.weight}, {self.durability}')

	# used to create a generic Weapon() if this item is used to attack something
	def improviseWeapon(self):
		#TODO: if item is too large/heavy, make it two-handed
		return Weapon(self.name,self.desc,self.weight,self.durability,minm(1,self.weight//4),0,0,0,False,"b")

	def describe(self):
		print("It's " + gprint("a",self.name,3,1), end="")
		print(self.desc)

	def Weight(self):
		return self.weight

	def Obtain(self,P,W,G):
		pass

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
		self.gear = {key: inv[gear[key]] if gear[key] != -1 else Empty() for key in gear}
		self.status = status
		# sort status effects by name, change 0 to 1 to sort by duration
		self.status.sort(key=lambda x: x[0])

		self.weapon = Empty()
		self.weapon2 = Empty()
		self.shield = Empty()
		self.shield2 = Empty()

		# these attributes remain unused in the Player subclass
		self.alive = True
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

	def writeAttributes(self,fd):
		fd.write(f'"{self.name}", "{self.desc}", ')
		fd.write(f'{self.hp}, {self.mp}, ')
		fd.write(f'[{self.STR},{self.SPD},{self.SKL},{self.STM},{self.CON},')
		fd.write(f'{self.CHA},{self.INT},{self.WIS},{self.FTH},{self.LCK}]')
		fd.write(f', {self.money}, ')

		if len(self.inv) != 0:	fd.write('\n\t')
		fd.write('[')
		for i in range(len(self.inv)):
			writeObj(fd,self.inv[i])
			if i != len(self.inv)-1:	fd.write(',\n\t')
		fd.write('], ')

		gearList = list(self.compressGear().items())
		if len(gearList) != 0:		fd.write('\n\t')
		fd.write('{')
		for k in range(len(gearList)):
			fd.write(f'"{gearList[k][0]}": {gearList[k][1]}')
			if k != len(gearList)-1:	fd.write(', ')

		fd.write('}, ')
		if len(self.status) != 0:	fd.write('\n\t')
		fd.write('[')
		statuslist = list(self.status)
		for j in range(len(statuslist)):
			fd.write(f'["{statuslist[j][0]}",{statuslist[j][1]}]')
			if j != len(statuslist)-1:	fd.write(', ')
		fd.write(']')

	# returns sum of the weight of all items in player inventory
	def invWeight(self):
		weight = 0
		for item in self.inv: weight += item.Weight()
		return weight

	# returns a list of names of all items in player inventory
	def invNames(self):
		return [item.name for item in self.inv]

	# just a function wrapper for functions that call contentNames on objects
	def contentNames(self):
		return self.invNames()

	# searches through inventory for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return None
	def inInv(self,term):
		for item in self.inv:
			if item.name == term:	return item
		return None

	# searches through gear for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return False
	def inGear(self,term):
		for slot in self.gear:
			if self.gear[slot].name == term:
				return self.gear[slot]
		return None

	# returns sum of the weight of all items in player gear
	def armorWeight(self):
		weight = 0
		for item in self.gear:
			if hasattr(self.gear[item], "weight"):
				weight += self.gear[item].Weight()
		return weight

	def describe(self):
		if hasattr(descname,self):
			print(f"It's {gprint('a',self.descname,3,1)}", end="")
		else:
			print(f"It's {gprint('a',self.name,3,1)}", end="")
		print(self.desc)

	def addItem(self,I):
		if self.invWeight() + I.Weight() > self.BRDN() * 2:
			return False
		if self.invWeight() + I.Weight() > self.BRDN():
			self.addCondition("hindered")
		insort(self.inv,I)
		return True

	def removeItem(self,I):
		if I in self.gear.values():
			self.unequip(I)
		self.inv.remove(I)
		if hasattr(I,"Drop") and callable(I.Drop):
			I.Drop(I)
		if self.invWeight() < self.BRDN():
			self.removeCondition("hindered")

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
				self.status.remove(condition)

	def addCondition(self,cond,stackable=False):
		# TODO: include stackability
		insort(self.status, cond)

	def removeCondition(self,cond,reqDuration=None):
		# removes all conditions of the same name
		for condition, duration in self.status:
			if condition == cond:
				if reqDuration == None or reqDuration == duration:
					self.status.remove(condition,duration)

	# these are creature stats that are determined dynamically with formulas
	# these formulas are difficult to read, check design document for details
	def ACCU(self): return 50 + 2*self.SKL + self.LCK + self.weapon.sleight
	def ATCK(self): return diceRoll(self.STR, self.weapon.might, 0)
	def ATHL(self): return self.STR + self.SKL + self.STM
	def ATSP(self): return self.SPD - minm(0,self.weapon.weight//4 - self.CON) - minm(0,self.weapon2.weight//4 - self.CON) - minm(0,self.shield.weight//4 - self.CON)
	def BRDN(self): return self.CON * self.STR * 4 + 60
	def CAST(self): return self.WIS + self.FTH + self.INT - minm(0,self.armorWeight()//4 - self.CON)
	def CRIT(self): return self.SKL + self.LCK + self.weapon.sharpness
	def CSSP(self): return self.WIS - minm(0,self.invWeight() - self.BRDN()) - minm(0,self.armorWeight()//4 - self.CON)
	def DCPT(self): return 2*self.CHA + self.INT
	def DFNS(self): return self.CON + self.armor()
	def ENDR(self): return 2*self.STM + self.CON
	def EVSN(self): return 2*self.ATSP() + self.LCK
	def INVS(self): return 2*self.INT + self.WIS
	def KNWL(self): return 2*self.INT + self.LCK
	def LOOT(self): return 2*self.LCK + self.FTH
	def MVMT(self): return self.SPD + self.STM + 10 - minm(0,self.invWeight() - self.BRDN()) - minm(0,self.armorWeight()//4 - self.CON)
	def MXHP(self): return self.level()*self.CON + self.STM
	def MXMP(self): return self.level()*self.WIS + self.STM
	def PRSD(self): return 2*self.CHA + self.WIS
	def RESC(self): return 2*self.FTH + self.STM
	def RITL(self): return 2*self.FTH + self.LCK
	def SLTH(self): return 2*self.SKL + self.INT - minm(0,self.invWeight() - self.BRDN())
	def SPLS(self): return 2*self.INT
	def TNKR(self): return 2*self.INT + self.SKL

	# returns sum of all protection values of all items in gear
	def armor(self):
		prot = 0
		for item in self.gear:
			if hasattr(self.gear[item], "prot"): prot += self.gear[item].prot
		return prot

	# called when a creature's hp hits 0
	def death(self,P,G):
		self.alive = False
		print("agh its... ded?")
		G.currentroom.occupants.remove(self)
		#drop some wealth or items
		P.gainxp(10)
		P.gainMoney(P.LOOT())

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takedmg(self,dmg,type,P,G):
		if(f"{type} vulnerability" in self.status):	dmg *= 2
		if(f"{type} resistance" in self.status):	dmg //= 2
		if(f"{type} immunity" in self.status):		dmg = 0
		print(f"Took {dmg} {dmgtypes[type]} damage")
		self.hp = minm(0, self.hp-dmg)	#player hp lowered to a minimum of 0
		if(self.hp == 0):
			self.death(P,G)

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
	def __init__(self,name,desc,hp,mp,traits,money,inv,gear,status,xp,rp):
		Creature.__init__(self,name,desc,hp,mp,traits,money,inv,gear,status)
		self.xp = xp
		self.rp = rp

	def writeAttributes(self,fd):
		super(Player,self).writeAttributes(fd)
		fd.write(", ")
		if len(self.status) != 0:	fd.write("\n\t")
		fd.write(f"{self.xp}, {self.rp}")

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
		# check if there's any auto-resurrect features
		print("You have died!")
		# ask to continue from checkpoint (last save)
		# or to load a different save
		# or to quit game

	# takes incoming damage, accounts for damage vulnerability or resistance
	def takedmg(self,dmg,type):
		if(f"{type} vulnerability" in self.status):	dmg *= 2
		if(f"{type} resistance" in self.status):	dmg /= 2
		if(f"{type} immunity" in self.status):		dmg = 0
		print(f"You took {dmg} {dmgtypes[type]} damage")
		self.hp = minm(0, self.hp-dmg)	#player hp lowered to a minimum of 0
		if(self.hp == 0):
			self.death()

	# heals player hp a given amount
	def heal(self,heal):
		if self.hp + heal > self.MXHP():
			heal = self.MXHP() - self.hp
		self.hp += heal
		print(f"You healed {heal} HP")
		return heal

	def addCondition(self,cond,msg="",stackable=False,):
		# TODO: include stackability
		insort(self.status, cond)
		if msg != "":	print(msg)
		print("You are " + cond)

	def removeCondition(self,cond,reqDuration=None):
		# removes all conditions of the same name
		for condition, duration in self.status:
			if condition == cond:
				if reqDuration == None or reqDuration == duration:
					self.status.remove(condition,duration)
		print("You are no longer " + cond)

	def obtainItem(self,I,S,W,G):
		if self.invWeight() + I.Weight() > self.BRDN() * 2:
			return False
		if self.invWeight() + I.Weight() > self.BRDN():
			self.addCondition("hindered","Your inventory is growing heavy.")
		insort(self.inv,I)
		S.removeItem(I)
		if hasattr(I, "Obtain") and callable(I.Obtain):
			I.Obtain(self,W,G)
		return True

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

	# if the item is armor, equip it, otherwise return False
	def equipArmor(self,I):
		if isinstance(I, Helm):		self.gear["helm"] = I
		elif isinstance(I, Body):	self.gear["body"] = I
		elif isinstance(I, Legs):	self.gear["pants"] = I
		else:	return False
		I.Equip(self)

	# finds the slot in which item resides, sets it to Empty()
	# calls the item's Unequip() method if it has one
	def unequip(self,I):
		gearslots = list(self.gear.keys())
		gearitems = list(self.gear.values())
		#finds the slot who's value matches the item, sets it to empty
		slot = gearslots[gearitems.index(I)]
		self.gear[slot] = Empty()
		self.assignWeaponAndShield()
		if hasattr(I, "Unequip") and callable(I.Unequip):
			I.Unequip(P)

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
		if hasattr(I,"Equip") and callable(I.Equip): I.Equip(self)

	def dualAttack(self,target,G):
		hit = minm(1,maxm(99, self.ACCU() - target.EVSN()))
		if diceRoll(1,100,0) <= hit:
			print()
			crit = True if diceRoll(1,100,0) <= self.CRIT() else False
			attack = self.ATCK()
			if crit:
				print("critical hit!")
				attack *= 2
			damage = minm(0, attack - target.DFNS())
			target.takedmg(damage, self.weapon2.type, self, G)
			if target.alive == False:
				return
		else:
			print("aw it missed")

	def attackCreature(self,target,G):
		n = minm(1, self.ATSP() // target.ATSP())
		print(f"{n} attacks:")
		for i in range(n):
			print(f"\n{ordinal(i+1)} attack")
			# what about if weapon is ranged?
			hit = minm(1,maxm(99, self.ACCU() - target.EVSN()))
			if diceRoll(1,100,0) <= hit:
				crit = diceRoll(1,100,0) <= self.CRIT()
				attack = self.ATCK()
				if crit:
					print("critical hit!")
					attack *= 2
				damage = minm(0, attack - target.DFNS())
				target.takedmg(damage, self.weapon.type, self, G)
				if target.alive == False:	return
			else:
				print("aw it missed")
			if self.weapon2 != Empty():	self.dualAttack(target,G)
			if target.alive == False:	return

	def attackItem(self,target,G):
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
		for cond, dur in self.status:
			if cond not in conditions:
				conditions.append(cond)
				durations.append(dur)

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
		if len(self.inv) == 0:	print("Inventory is empty")
		else:					columnPrint(self.invNames(),8,12)

	# prints player level, money, hp, mp, rp, and status effects
	def printStats(self):
		stats = [self.name, f"LV: {self.level()}", f"Ᵽ{self.money}", f"RP: {self.rp}", f"HP: {self.hp}/{self.MXHP()}", f"MP: {self.mp}/{self.MXMP()}"]
		columnPrint(stats,3,16)
		if len(self.status) != 0:
			self.printStatus()

	# for every item in player inventory, if its a weapon, print it
	def printWeapons(self):
		if len(self.weapons) == 0:
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

# almost identical to the item class, but fixtures cannot be removed from their initial location
class Fixture(Item):
	def __init__(self,name,desc,weight,durability):
		Item.__init__(self,name,desc,weight,durability)

class Weapon(Item):
	def __init__(self,name,desc,weight,durability,might,sleight,sharpness,range,twohanded,type):
		Item.__init__(self,name,desc,weight,durability)
		self.might = might
		self.sleight = sleight
		self.sharpness = sharpness
		self.range = range
		self.twohanded = bool(twohanded)
		self.type = type

	# weapon is stored as normal item data with an additional 4 ints at the end
	def writeAttributes(self, fd):
		super(Weapon,self).writeAttributes(fd)
		fd.write(f', {self.might}, {self.sleight}, {self.sharpness}, ')
		fd.write(f'{self.range}, {1 if self.twohanded else 0}, "{self.type}"')

	def print(self):
		print(f"{self.name} {self.might} {self.sleight}")
		print(f"{self.sharpness} { self.twohanded} {self.range}")


class Shield(Item):
	def __init__(self,name,desc,weight):
		Item.__init__(self,name,desc,weight)

class Armor(Item):
	def __init__(self,name,desc,weight):
		Item.__init__(self,name,desc,weight)

	def Equip(self,P):
		pass

	def Unequip(self,P):
		pass

class Head(Armor):
	def __init__(self,name,desc,weight):
		Armor.__init__(self,name,desc,weight)

class Body(Armor):
	def __init__(self,name,desc,weight):
		Item.__init__(self,name,desc,weight)

class Legs(Armor):
	def __init__(self,name,desc,weight):
		Armor.__init__(self,name,desc,weight)


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

def destroyItem(S,I):
	if isinstance(S,Player):	print(f"Your {I.name} is destroyed")
	else:						print(f"The {I.name} is destroyed")
	S.removeItem(I)

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
