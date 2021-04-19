# Objects.py
# This file contains the classes used in the game and the dicts to identify them
# This file is dependent on Core.py and is a dependency of Menu.py

# It consists of three main parts;
# 1. Class definitions		(all specific item and creature definitions)
# 2. Item dictionary		(used to identify item objects from strings)
# 3. Creature dictionary	(used to identify creature objects from strings)

from Core import *


#######################
## CLASS DEFINITIONS ##
#######################

class Bottle(Item):
	# breaks the bottle, removes it from player inventory, and randomly...
	# generates a number of shards between 1,5 into the room.
	def Break(self,P,G,S):
		print(f"The {self.name} breaks. Shards of glass scatter everywhere")
		S.removeItem(self)
		for i in range(randint(3,6)):	#randomly generates n shards between 3,6
			newShard = Shard("shard","a sharp shard of glass",1,-1)
			G.currentroom.addItem(newShard)

class Box(Item):
	def __init__(self,name,desc,weight,durability,open,contents):
		Item.__init__(self,name,desc,weight,durability)
		self.open = open
		self.contents = contents

	def writeAttributes(self,fd):
		super(Box,self).writeAttributes(fd)
		fd.write(f", {self.open}, ")
		if len(self.contents) != 0:	fd.write("\n\t")
		fd.write("[")
		for i in range(len(self.contents)):
			writeObj(fd,self.contents[i])
			if i != len(self.contents) - 1:	fd.write(",\n\t")
		fd.write("]")

	# takes a string, term, and searches the box's contents
	# if an item is found that matches term, return it, otherwise, return None
	def inContents(self,term):
		for item in self.contents:
			if item.name == term:	return item
		return None

	def contentNames(self):
		return [item.name for item in self.contents]

	def addItem(self,I):
		insort(self.contents,I)

	def removeItem(self,I):
		self.contents.remove(I)

	# sets open bool to true, prints its contents
	def Open(self):
		if self.open:
			print(f"The {self.name} is already open")
		else:
			print(f"You open the {self.name}")
			self.open = True
		if len(self.contents) == 0:
			print("It is empty")
		else:
			print("Inside there is " + listItems(self.contents))

	# sets open bool to false
	def Close(self):
		self.open = False
		print(f"You close the {self.name}")

	# the weight of a box is equal to its own weight + weights of its contents
	def Weight(self):
		w = self.weight
		for i in self.contents:	w += i.Weight()
		return w

	def Look(self):
		if len(self.contents) == 0:
			print("It is empty")
		else:
			print("Inside there is " + listItems(self.contents))


class Bread(Item):
	# heals 20 hp to the player, removes bread from inventory
	def Eat(self,P,G,S):
		print("You consume the bread")
		h = P.heal(20)
		S.removeItem(self)
		if h == 0:
			print("Yummy")

class Compass(Item):
	#???
	def Orient(self):
		print("Orienting you northward!")

class Controller(Item):
	def __init__(self,name,desc,weight,durability,effect):
		Item.__init__(self,name,desc,weight,durability)
		self.effect = effect

	# has an effect string which is used as a key in an 'effects' dict
	def writeAttributes(self,fd):
		super(Controller,self).writeAttributes(fd)
		fd.write(', "' + self.effect + '"')

	# triggers some effect using the effect string to call related function
	def Trigger(self,P,W,G):
		eval(self.effect)

	# using the controller triggers the effect
	def Use(self,P,W,G):	self.Trigger(P,W,G)

class Foot(Item):
	def improviseWeapon(self):
		return Weapon(self.name,self.desc,self.weight,self.durability,minm(1,self.weight//4),0,0,0,False,"b")

class Hand(Item):
	def improviseWeapon(self):
		return Weapon(self.name,self.desc,self.weight,self.durability,minm(1,self.weight//4),2,0,0,False,"b")

class Lockbox(Box):
	def __init__(self,name,desc,weight,durability,open,contents,locked):
		Box.__init__(self,name,desc,weight,durability,open,contents)
		self.locked = locked

	def writeAttributes(self,fd):
		super(Lockbox,self).writeAttributes(fd)
		fd.write(f", {self.locked}")

	# sets open bool to true, prints its contents
	def Open(self):
		if self.open:
			print(f"The {self.name} is already open")
		elif self.locked:
			print(f"The {self.name} is locked")
			return False
		else:
			print(f"You open the {self.name}")
			self.open = True
		if len(self.contents) == 0:
			print("It is empty")
		else:
			print("Inside there is " + listItems(self.contents))

	def Lock(self):
		pass

	def Unlock(self):
		pass

class Mouth(Item):
	def improviseWeapon(self):
		return Weapon(self.name,self.desc,self.weight,self.durability,minm(1,self.weight//4),0,0,4,False,"p")

class Potion(Bottle):
	# heals the player hp 1000, replaces potion with an empty bottle
	def Drink(self,P,G,S):
		print("You drink the potion")
		P.heal(1000)
		S.removeItem(self)
		P.addItem(Bottle("bottle","an empty glass bottle",3,3))

class Shard(Item):
	#???
	def Cut(self,P):
		print("[you cut something?]")

class Sign(Item):
	def __init__(self,name,desc,weight,durability,text):
		Item.__init__(self,name,desc,durability,weight)
		self.text = text

	def writeAttributes(self,fd):
		super(Sign,self).writeAttributes(fd)
		fd.write(', "' + self.text + '"')

	# prints the text on the sign in quotes
	def Look(self):
		print('\n"' + self.text + '"')

class Switch(Fixture):
	def __init__(self,name,desc,weight,durability,effect):
		Fixture.__init__(self,name,desc,weight,durability)
		self.effect = effect

	# has an effect string which is used as a key in an 'effects' dict
	def writeAttributes(self,fd):
		super(Switch,self).writeAttributes(fd)
		fd.write(', "' + self.effect + '"')

	# triggers some effect using the effect name to find related function
	def Trigger(self,P,W,G):
		eval(self.effect)

	# using the switch triggers the effect
	def Use(self,P,W,G):	self.Trigger(P,W,G)

class Sword(Weapon):
	def Cut(self,P):
		print("[you cut something?]")

class Table(Fixture):
	def __init__(self,name,desc,weight,durability,contents,descname):
		Item.__init__(self,name,desc,weight,durability)
		self.contents = contents
		self.descname = descname

	def writeAttributes(self,fd):
		super(Table,self).writeAttributes(fd)
		fd.write(',')
		if len(self.contents) != 0:	fd.write('\n\t')
		fd.write('[')
		for i in range(len(self.contents)):
			writeObj(fd,self.contents[i])
			if i != len(self.contents) - 1:	fd.write(',\n\t')
		fd.write(f'], "{self.descname}"')

	# takes a string, term, and searches the box's contents
	# if an item is found that matches term, return it, otherwise, return None
	def inContents(self,term):
		for item in self.contents:
			if item.name == term:	return item
		return None

	def contentNames(self):
		return [item.name for item in self.contents]

	def addItem(self,I):
		insort(self.contents,I)

	def removeItem(self,I):
		self.contents.remove(I)
		if len(self.contents) == 1:
			items = gprint("a",self.contents[0].name,4)
			self.descname = f"{self.name} with {items} on it"
		elif len(self.contents) == 0:
			self.descname = f"empty {self.name}"

	# the weight of a box is equal to its own weight + weights of its contents
	def Weight(self):
		w = self.weight
		for i in self.contents:	w += i.Weight()
		return w

	def describe(self):
		super(Table,self).describe()
		if len(self.contents) != 0:
			print("On it is " + listItems(self.contents))
		else:
			print("There is nothing on it")


#####################
## ITEM DICTIONARY ##
#####################

items = {
	"":Empty,
	"Bottle":Bottle,
	"Box":Box,
	"Bread":Bread,
	"Compass":Compass,
	"Controller":Controller,
	"Lockbox":Lockbox,
	"Potion":Potion,
	"Shard":Shard,
	"Sign":Sign,
	"Switch":Switch,
	"Sword":Sword,
	"Table":Table
}


#########################
## CREATURE DICTIONARY ##
#########################

creatures = {
	"Animal":Animal,
	"Creature":Creature,
	"Monster":Monster,
	"Person":Person
}
