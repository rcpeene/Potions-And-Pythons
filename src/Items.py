# Items.py
# This file contains the item classes used in the game
# This file is dependent on Core.py and is a dependency of Menu.py


from bisect import insort
from random import randint

import Core
import Data




############################
## ITEM CLASS DEFINITIONS ##
############################


class Axe(Core.Weapon):
	def Cut(self):
		print("[you cut something?]")




class Bottle(Core.Item):
	# breaks the bottle, removes it from player inventory, and randomly...
	# generates a number of shards between 1,5 into the room.
	def Break(self):
		print(f"The {self.name} breaks. Shards of glass scatter everywhere.")
		self.parent.removeItem(self)
		#randomly generates n shards between 3,6
		for _ in range(randint(3,6)):
			shard = Shard("shard","a sharp shard of glass",[],"shards",1,-1,[])
			self.parent.addItem(shard)
		return True




class Box(Core.Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,open,items):
		Core.Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.open = open
		self.items = items



	### Operation ###

	# sets open bool to true, prints its items
	def Open(self):
		if self.open:
			print(f"The {self.name} is already open.")
		else:
			print(f"You open the {self.name}.")
			self.open = True
		self.Look()

	# sets open bool to false
	def Close(self):
		self.open = False
		print(f"You close the {self.name}.")


	def Look(self):
		if len(self.items) == 0:
			print("It is empty.")
		else:
			self.open = True
			print(f"Inside there is {Core.listObjects(self.items)}.")


	def Break(self):
		if self.durability == -1:
			if not game.silent:
				print(f"The {self.name} cannot be broken.")
			return False
		print(f"The {self.name} breaks.")
		self.parent.removeItem(self)
		# drop things it contains into parent
		for item in self.items:
			self.parent.addItem(item)
		return True


	def addItem(self,I):
		# ensure only one bunch of Gold exists here
		if isinstance(I,Core.Pylars):
			for item in self.items:
				if isinstance(item,Core.Pylars):
					item.merge(I)
					return

		insort(self.items,I)
		I.parent = self


	def removeItem(self,I):
		self.items.remove(I)



	### Getters ###

	# the weight of a box is equal to its own weight + weights of its items
	def Weight(self):
		w = self.weight
		for i in self.items:
			w += i.Weight()
		return w


	def itemNames(self):
		return [item.name for item in self.items]




class Controller(Core.Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,effect):
		Core.Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.effect = effect


	# triggers some effect using the effect string to call related function
	def Trigger(self):
		eval(self.effect)


	# using the controller triggers the effect
	def Use(self):
		self.Trigger()




class Door(Core.Fixture):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,mention,open,connections):
		Core.Fixture.__init__(self,name,desc,aliases,plural,weight,durability,status,mention)
		self.open = open
		# connection is a 4-tuple of the form:
		# (outDirection, outLocation, inDirection, inLocation)
		self.outconnection = connections[0]


	# sets open bool to true, triggers the effect
	def Open(self,Currentroom):
		if self.open:
			print(f"The {self.name} is already open.")
		else:
			print(f"You open the {self.name}.")
			self.open = True
		outdir = self.connections[0]
		outloc = self.connections[1]
		indir = self.connections[2]
		inloc = self.connections[3]
		Currentroom.addConection(outdir,outloc)
		Otherroom = Core.world[outloc]
		Otherroom.addConnection(indir,inloc)




class Food(Core.Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,heal):
		Core.Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.heal = heal

	# heals 'heal' hp to the player, removes food from inventory
	def Eat(self):
		print(f"You consume the {self.name}.")
		h = Core.player.heal(self.heal)
		self.parent.removeItem(self)
		if h == 0:
			print("Yummy...")




class Foot(Core.Item):
	def improviseWeapon(self):
		return Core.Weapon(self.name,self.desc,self.aliases,self.plural,self.weight,self.durability,[],Core.minm(1,self.weight//4),0,0,0,False,"b")




class Fountain(Core.Fixture):
	def Douse():
		pass


	def Drink(self):
		print(f"You drink from the {self.name}.")




class Generator(Controller):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,effect,charge,capacity,rate,cost):
		Core.Controller.__init__(self,name,desc,aliases,plural,weight,durability,status,effect)
		self.charge = charge
		self.capacity = capacity
		self.rate = rate
		self.cost = cost


	def Trigger(self):
		if charge > cost:
			charge -= cost
			eval(self.effect)
		if not Core.game.silent:
			print("Nothing happened...")


	def passTime(self):
		self.charge += self.rate
		if self.charge > self.capacity:
			self.charge = self.capacity
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




class Hand(Core.Item):
	def improviseWeapon(self):
		return Core.Weapon(self.name,self.desc,self.aliases,self.plural,self.weight,self.durability,[],Core.minm(1,self.weight//4)+1,2,0,0,False,"b")




class Key(Core.Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,id):
		Core.Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.id = id


	def LockWith(self,box):
		pass


	def UnlockWith(self,box):
		pass




class Lockbox(Box):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,open,items,keyids,locked):
		Box.__init__(self,name,desc,aliases,plural,weight,durability,status,open,items)
		self.keyids = keyids
		self.locked = locked



	### Operation ###

	# sets open bool to true, prints its items
	def Open(self):
		if self.open:
			print(f"The {self.name} is already open.")
		elif self.locked:
			print(f"The {self.name} is locked.")
			return False
		else:
			print(f"You open the {self.name}.")
			self.open = True
		if len(self.items) == 0:
			print("It is empty.")
		else:
			print(f"Inside there is {Core.listObjects(self.items)}.")


	def Look(self):
		if self.locked == True:
			print("It is locked.")
		elif len(self.items) == 0:
			print("It is empty.")
		else:
			self.open = True
			print(f"Inside there is {Core.listObjects(self.items)}.")


	def Lock(self,key):
		if I.locked:
			print(f"The {I.name} is already locked.")
			return False
		if key.id in self.keyids:
			self.locked = True
			print(f"You lock the {self.name}.")
			if Core.hasMethod(key,"UnlockWith"):
				key.UnlockWith(self)
			return True
		print(f"You can't lock the {self.name} with the {key.name}.")
		return True


	def Unlock(self,key):
		if not self.locked:
			print(f"The {self.name} is not locked.")
			return False
		if key.id in self.keyids:
			self.locked = False
			print(f"You unlock the {self.name}.")
			if Core.hasMethod(key,"LockWith"):
				key.LockWith(self)
			return True
		print(f"The {key.name} won't work!")
		return True




class Mouth(Core.Item):
	def improviseWeapon(self):
		return Core.Weapon(self.name,self.desc,self.aliases,self.plural,self.weight,self.durability,[],Core.minm(1,self.weight//4),0,0,4,False,"p")




class Potion(Bottle):
	# heals the player hp 1000, replaces potion with an empty bottle
	def Drink(self):
		print(f"You drink the {self.name}.")
		Core.player.heal(1000)
		self.parent.removeItem(self)
		Core.player.addItem(Bottle("bottle","an empty glass bottle",[],"",3,3,[]))


	def Pour(self,obj=None):
		if obj != None:
			if Core.hasMethod(obj,"Drench"):
				obj.Drench(self)
		self.parent.removeItem(self)
		Core.player.addItem(Bottle("bottle","an empty glass bottle",[],"bottles",3,3,[]))




class Shard(Core.Item):
	#???
	def Cut(self,P):
		print("[you cut something?]")




class Sign(Core.Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,text):
		Core.Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.text = text


	# prints the text on the sign in quotes
	def Look(self):
		print(f'\n"{self.text}"')




class Switch(Core.Fixture):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,mention,effect):
		Core.Fixture.__init__(self,name,desc,aliases,plural,weight,durability,status,mention)
		self.effect = effect


	# triggers some effect using the effect name to find related function
	def Trigger(self):
		eval(self.effect)


	# using the switch triggers the effect
	def Use(self):
		self.Trigger()




class Sword(Core.Weapon):
	def Cut(self):
		print("[you cut something?]")




class Table(Core.Item):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,items,descname):
		Core.Item.__init__(self,name,desc,aliases,plural,weight,durability,status)
		self.items = items
		self.descname = descname



	### Operation ###

	def Break(self):
		if self.durability == -1:
			if not game.silent:
				print(f"The {self.name} cannot be broken.")
			return False
		print(f"The {self.name} breaks.")
		self.parent.removeItem(self)
		# drop things it contains into parent
		if self.items:
			print(f"It's contents fall onto the ground.")
		for item in self.items:
			self.parent.addItem(item)
		return True


	def addItem(self,I):
		# ensure only one bunch of Gold exists here
		if isinstance(I,Core.Pylars):
			for item in self.items:
				if isinstance(item,Core.Pylars):
					item.merge(I)
					return

		insort(self.items,I)
		I.parent = self
		if len(self.items) == 1:
			itemName = self.items[0].stringName()
			self.descname = f"{self.name} with {itemName} on it"
		elif len(self.items) > 1:
			self.descname = f"{self.name} with items on it"


	def removeItem(self,I):
		self.items.remove(I)
		if len(self.items) == 1:
			itemName = self.items[0].stringName()
			self.descname = f"{self.name} with {itemName} on it"
		elif len(self.items) == 0:
			self.descname = f"empty {self.name}"




	### Getters ###

	# the weight of a box is equal to its own weight + weights of its items
	def Weight(self):
		w = self.weight
		for i in self.items:
			w += i.Weight()
		return w


	def itemNames(self):
		return [item.name for item in self.items]




	### User Output ###

	def describe(self):
		print(f"It's {self.stringName()}.")
		if len(self.items) != 0:
			print(f"On it is {Core.listObjects(self.items)}.")
		else:
			print("There is nothing on it.")




class Wall(Core.Passage):
	def __init__(self,name,desc,aliases,plural,weight,durability,status,connections,descname,passprep,cr):
		Core.Passage.__init__(self,name,desc,aliases,plural,weight,durability,status,connections,descname,passprep)
		self.cr = cr


	def Traverse(self,dir=None):
		if dir == None:
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

		if Core.player.ATHL() < self.cr:
			print(f"You fall down the {self.name}!")
			if dir == "down":
				Core.game.changeRoom(W[self.connections["down"]])
			if not (Core.player.hasCondition("fly") or Core.player.hasCondition("feather fall")):
				Core.player.takeDamage(self.cr-Core.player.ATHL(),"b")
			return True

		print(f"You climb {dir} the {self.name}.")
		Core.game.changeRoom(Core.world[self.connections[dir]])
		return True
