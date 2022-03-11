# Items.py
# This file contains the item classes used in the game
# This file is dependent on Core.py and is a dependency of Menu.py

import Core
import Data
from Core import *




############################
## ITEM CLASS DEFINITIONS ##
############################


class Bottle(Item):
	# breaks the bottle, removes it from player inventory, and randomly...
	# generates a number of shards between 1,5 into the room.
	def Break(self):
		print(f"The {self.name} breaks. Shards of glass scatter everywhere")
		self.parent.removeItem(self)
		for i in range(randint(3,6)):	#randomly generates n shards between 3,6
			newShard = Shard("shard","a sharp shard of glass",1,-1)
			self.parent.addItem(newShard)




class Box(Item):
	def __init__(self,name,desc,weight,durability,open,contents):
		Item.__init__(self,name,desc,weight,durability)
		self.open = open
		self.contents = contents



	### Operation ###

	# the weight of a box is equal to its own weight + weights of its contents
	def Weight(self):
		w = self.weight
		for i in self.contents:
			w += i.Weight()
		return w


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


	def Look(self):
		if len(self.contents) == 0:
			print("It is empty")
		else:
			self.open = True
			print("Inside there is " + listItems(self.contents))


	def addItem(self,I):
		insort(self.contents,I)
		I.parent = self


	def removeItem(self,I):
		self.contents.remove(I)



	### Getters ###

	# takes a string, term, and searches the box's contents
	# if an item is found that matches term, return it, otherwise, return None
	def inContents(self,term):
		for item in self.contents:
			if item.name == term:	return item
		return None


	def contentNames(self):
		return [item.name for item in self.contents]



class Bread(Item):
	# heals 20 hp to the player, removes bread from inventory
	def Eat(self):
		print("You consume the bread")
		h = Core.player.heal(20)
		self.parent.removeItem(self)
		if h == 0:
			print("Yummy")



class Controller(Item):
	def __init__(self,name,desc,weight,durability,effect):
		Item.__init__(self,name,desc,weight,durability)
		self.effect = effect


	# triggers some effect using the effect string to call related function
	def Trigger(self):
		eval(self.effect)


	# using the controller triggers the effect
	def Use(self):
		self.Trigger()




class Door(Fixture):
	def __init__(self,name,desc,weight,durability,open,connections):
		Fixture.__init__(self,name,desc,weight,durability)
		self.open = open
		# connection is a 4-tuple of the form:
		# (outDirection, outLocation, inDirection, inLocation)
		self.outconnection = connections[0]


	# sets open bool to true, triggers the effect
	def Open(self,Currentroom):
		if self.open:
			print(f"The {self.name} is already open")
		else:
			print(f"You open the {self.name}")
			self.open = True
		outdir = self.connections[0]
		outloc = self.connections[1]
		indir = self.connections[2]
		inloc = self.connections[3]
		Currentroom.addConection(outdir,outloc)
		Otherroom = Core.world[outloc]
		Otherroom.addConnection(indir,inloc)




class Foot(Item):
	def improviseWeapon(self):
		return Weapon(self.name,self.desc,self.weight,self.durability,Core.minm(1,self.weight//4),0,0,0,False,"b")



class Hand(Item):
	def improviseWeapon(self):
		return Weapon(self.name,self.desc,self.weight,self.durability,Core.minm(1,self.weight//4),2,0,0,False,"b")




class Key(Item):
	def __init__(self,name,desc,weight,durability,id):
		Item.__init__(self,name,desc,weight,durability)
		self.id = id


	def LockWith(self,box):
		pass


	def UnlockWith(self,box):
		pass



class Lockbox(Box):
	def __init__(self,name,desc,weight,durability,open,contents,keyids,locked):
		Box.__init__(self,name,desc,weight,durability,open,contents)
		self.keyids = keyids
		self.locked = locked



	### Operation ###

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


	def Look(self):
		if self.locked == True:
			print("It is locked")
		elif len(self.contents) == 0:
			print("It is empty")
		else:
			self.open = True
			print("Inside there is " + listItems(self.contents))


	def Lock(self,key):
		if I.locked:
			print(f"The {I.name} is already locked")
			return False
		if key.id in self.keyids:
			self.locked = True
			print(f"You lock the {self.name}")
			if Core.hasMethod(key,"UnlockWith"):
				key.UnlockWith(self)
			return True
		print(f"You can't lock the {self.name} with the {key.name}")
		return True


	def Unlock(self,key):
		if not self.locked:
			print(f"The {self.name} is not locked")
			return False
		if key.id in self.keyids:
			self.locked = False
			print(f"You unlock the {self.name}")
			if Core.hasMethod(key,"LockWith"):
				key.LockWith(self)
			return True
		print(f"The {key.name} won't work!")
		return True




class Mouth(Item):
	def improviseWeapon(self):
		return Weapon(self.name,self.desc,self.weight,self.durability,Core.minm(1,self.weight//4),0,0,4,False,"p")




class Potion(Bottle):
	# heals the player hp 1000, replaces potion with an empty bottle
	def Drink(self):
		print("You drink the potion")
		Core.player.heal(1000)
		self.parent.removeItem(self)
		Core.player.addItem(Bottle("bottle","an empty glass bottle",3,3))


	def Pour(self,obj=None):
		if obj != None:
			obj.Drench(self)
		self.parent.removeItem(self)
		Core.player.addItem(Bottle("bottle","an empty glass bottle",3,3))




class Shard(Item):
	#???
	def Cut(self,P):
		print("[you cut something?]")




class Sign(Item):
	def __init__(self,name,desc,weight,durability,text):
		Item.__init__(self,name,desc,durability,weight)
		self.text = text


	# prints the text on the sign in quotes
	def Look(self):
		print('\n"' + self.text + '"')




class Switch(Fixture):
	def __init__(self,name,desc,weight,durability,effect):
		Fixture.__init__(self,name,desc,weight,durability)
		self.effect = effect


	# triggers some effect using the effect name to find related function
	def Trigger(self):
		eval(self.effect)


	# using the switch triggers the effect
	def Use(self):
		self.Trigger()




class Sword(Weapon):
	def Cut(self):
		print("[you cut something?]")




class Table(Fixture):
	def __init__(self,name,desc,weight,durability,contents,descname):
		Fixture.__init__(self,name,desc,weight,durability)
		self.contents = contents
		self.descname = descname



	### Operation ###

	def addItem(self,I):
		insort(self.contents,I)
		I.parent = self


	def removeItem(self,I):
		self.contents.remove(I)
		if len(self.contents) == 1:
			items = Core.gprint("a",self.contents[0].name,4)
			self.descname = f"{self.name} with {items} on it"
		elif len(self.contents) == 0:
			self.descname = f"empty {self.name}"




	### Getters ###

	# the weight of a box is equal to its own weight + weights of its contents
	def Weight(self):
		w = self.weight
		for i in self.contents:	w += i.Weight()
		return w


	# takes a string, term, and searches the box's contents
	# if an item is found that matches term, return it, otherwise, return None
	def inContents(self,term):
		for item in self.contents:
			if item.name == term:	return item
		return None


	def contentNames(self):
		return [item.name for item in self.contents]




	### User Output ###

	def describe(self):
		print(self.descname)
		if len(self.contents) != 0:
			print("On it is " + listItems(self.contents))
		else:
			print("There is nothing on it")



class Wall(Passage):
	def __init__(self,name,desc,weight,durability,connections,descname,passprep,cr):
		Passage.__init__(self,name,desc,weight,durability,connections,descname,passprep)
		self.cr = cr


	def Traverse(self,dir=None):
		if dir == None:
			if len(self.connections) == 1:
				dir = list(self.connections.keys())[0]
			else:
				msg = f"Which direction will you go on the {self.name}?\n> "
				dir = input(msg).lower()
		if dir in Data.cancels:
			return False
		if dir not in self.connections:
			print(f"The {self.name} does not go '{dir}'")
			return False

		if Core.player.ATHL() < self.cr:
			print(f"You fall down the {self.name}!")
			if dir == "down":
				Core.game.changeRoom(W[self.connections["down"]])
			if not (Core.player.hasCondition("fly") or Core.player.hasCondition("feather fall")):
				Core.player.takeDamage(self.cr-Core.player.ATHL(),"b")
			return True

		print(f"You climb {dir} the {self.name}")
		Core.game.changeRoom(Core.world[self.connections[dir]])
		return True



#########################
## strToClass Function ##
#########################

# def strToClass(classname):
# 	if classname in globals():
# 		return globals()[classname]
# 	else:
# 		return None
