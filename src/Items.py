# Items.py
# This file contains the item classes used in the game
# This file is dependent on Core.py and is a dependency of Menu.py


from bisect import insort
from random import randint

import Effects
import Core
import Data




############################
## ITEM CLASS DEFINITIONS ##
############################


class Axe(Core.Weapon):
	def Cut(self):
		Core.game.Print("[you cut something?]")




class Bed(Core.Item):
	def Lay(self,layer):
		layer.addCondition("cozy",-3)
		return True
	
	def Sit(self,sitter):
		return True



class Bottle(Core.Item):
	# breaks the bottle, removes it from player inventory, and randomly...
	# generates a number of shards between 1,5 into the room.
	def Break(self):
		Core.game.Print(f"The {self.name} breaks. Shards of glass scatter everywhere.")
		self.parent.removeItem(self)
		# randomly generates n shards between 3,6
		for _ in range(randint(3,6)):
			shard = Shard("glass shard","a sharp shard of glass","glass",1,-1)
			Core.game.currentroom.addItem(shard)
		return True




class Box(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,open,items,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.open = open
		self.items = items



	### Operation ###

	# sets open bool to true, prints its items
	def Open(self):
		if self.open:
			Core.game.Print(f"The {self.name} is already open.")
		else:
			Core.game.Print(f"You open the {self.name}.")
			self.open = True
		self.Look()

	# sets open bool to false
	def Close(self):
		self.open = False
		Core.game.Print(f"You close the {self.name}.")


	def Look(self):
		if len(self.items) == 0:
			Core.game.Print("It is empty.")
		else:
			self.open = True
			Core.game.Print(f"Inside there is {Core.listObjects(self.items)}.")
			Core.game.setPronouns(self.items[-1])
		return True


	def Break(self):
		if self.durability == -1:
			if not Core.game.silent:
				Core.game.Print(f"The {self.name} cannot be broken.")
			return False
		Core.game.Print(f"The {self.name} breaks.")
		self.parent.removeItem(self)
		# drop things it contains into parent
		for item in self.items:
			self.parent.addItem(item)
		return True


	def addItem(self,I):
		# ensure only one bunch of Gold exists here
		if isinstance(I,Core.Serpens):
			for item in self.items:
				if isinstance(item,Core.Serpens):
					item.merge(I)
					return

		insort(self.items,I)
		I.parent = self
		I.despawnTimer = None


	def removeItem(self,I):
		self.items.remove(I)



	### Getters ###

	# the weight of a box is equal to its own weight + weights of its items
	def Weight(self):
		w = self.weight
		for i in self.items:
			w += i.Weight()
		return w

	
	def contents(self):
		return self.items


	def itemNames(self):
		return [item.name for item in self.items]




class Controller(Core.Item):
	def __init__(self,name,desc,weight,durability,triggers,effect,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,**kwargs)
		self.triggers = triggers if triggers else ["Use"]
		self.effect = effect
		for trigger in self.triggers:
			f = lambda *args: self.Trigger(trigger,*args)
			setattr(self,trigger,f)


	### File I/O ###

	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		for trigger in self.triggers:
			del jsonDict[trigger]
		jsonDict = {"__class__":self.__class__.__name__, **jsonDict}
		return jsonDict


	### Operation ###

	# triggers some effect using the effect string to call related function
	def Trigger(self,*args):
		exec(self.effect)




class Door(Core.Fixture):
	def __init__(self,name,desc,weight,durability,composition,mention,open,connections,**kwargs):
		Core.Fixture.__init__(self,name,desc,weight,durability,composition,mention,**kwargs)
		self.open = open
		# connection is a 4-tuple of the form:
		# (outDirection, outLocation, inDirection, inLocation)
		self.outconnection = connections[0]


	# sets open bool to true, triggers the effect
	def Open(self,Currentroom):
		if self.open:
			Core.game.Print(f"The {self.name} is already open.")
		else:
			Core.game.Print(f"You open the {self.name}.")
			self.open = True
		outdir = self.connections[0]
		outloc = self.connections[1]
		indir = self.connections[2]
		inloc = self.connections[3]
		Currentroom.addConection(outdir,outloc)
		Otherroom = Core.world[outloc]
		Otherroom.addConnection(indir,inloc)




class Food(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,heal,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.heal = heal

	# heals 'heal' hp to the player, removes food from inventory
	def Eat(self,eater):
		if isinstance(eater,Core.Player):
			Core.game.Print(f"You consume {-self}.")
		else:
			Core.game.Print(f"{+eater} eats {-self}.")
		h = eater.heal(self.heal)
		eater.lastAte = Core.game.time
		if h == 0 and isinstance(eater,Core.Player):
			Core.game.Print("Yummy...")
		eater.checkHungry()
		self.parent.removeItem(self)




class Foot(Core.Item):
	def improviseWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.minm(1,self.weight//4),0,0,0,"b")




class Fountain(Core.Fixture):
	def Douse():
		pass


	def Drink(self):
		Core.game.Print(f"You drink from the {self.name}.")




class Generator(Controller):
	def __init__(self,name,desc,weight,durability,composition,effect,charge,capacity,rate,cost,**kwargs):
		Core.Controller.__init__(self,name,desc,weight,durability,composition,effect,**kwargs)
		self.charge = charge
		self.capacity = capacity
		self.rate = rate
		self.cost = cost


	def Trigger(self):
		if charge > self.cost:
			charge -= self.cost
			eval(self.effect)
		if not Core.game.silent:
			Core.game.Print("Nothing happened...")


	def passTime(self,t):
		Controller.passTime(self,t)
		self.charge += self.rate*t
		if self.charge > self.capacity:
			self.charge = self.capacity




class Hand(Core.Item):
	def improviseWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.minm(1,self.weight//4)+1,2,0,0,"b")




class Key(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,id,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.id = id


	def LockWith(self,box):
		pass


	def UnlockWith(self,box):
		pass




class Lockbox(Box):
	def __init__(self,name,desc,weight,durability,composition,open,items,keyids,locked,**kwargs):
		Box.__init__(self,name,desc,weight,durability,composition,open,items,**kwargs)
		self.keyids = keyids
		self.locked = locked



	### Operation ###

	# sets open bool to true, prints its items
	def Open(self):
		if self.open:
			Core.game.Print(f"The {self.name} is already open.")
		elif self.locked:
			Core.game.Print(f"The {self.name} is locked.")
			return False
		else:
			Core.game.Print(f"You open the {self.name}.")
			self.open = True
		self.Look()
		return True


	def Look(self):
		if self.locked == True:
			Core.game.Print("It is locked.")
		elif len(self.items) == 0:
			Core.game.Print("It is empty.")
		else:
			self.open = True
			Core.game.Print(f"Inside there is {Core.listObjects(self.items)}.")
			Core.game.setPronouns(self.items[-1])


	def Lock(self,key):
		if self.locked:
			Core.game.Print(f"The {self.name} is already locked.")
			return False
		if key.id in self.keyids:
			self.locked = True
			Core.game.Print(f"You lock the {self.name}.")
			if Core.hasMethod(key,"UnlockWith"):
				key.UnlockWith(self)
			return True
		Core.game.Print(f"You can't lock the {self.name} with the {key.name}.")
		return True


	def Unlock(self,key):
		if not self.locked:
			Core.game.Print(f"The {self.name} is not locked.")
			return False
		if key.id in self.keyids:
			self.locked = False
			Core.game.Print(f"You unlock the {self.name}.")
			if Core.hasMethod(key,"LockWith"):
				key.LockWith(self)
			return True
		Core.game.Print(f"The {key.name} won't work!")
		return True




class Mouth(Core.Item):
	def improviseWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.minm(1,self.weight//4),0,0,4,"p")




class Potion(Bottle):

	# heals the player hp 1000, replaces potion with an empty bottle
	def Drink(self):
		Core.game.Print(f"You drink the {self.name}.")
		Core.player.heal(1000)
		self.parent.removeItem(self)
		Core.player.addItem()


	def Pour(self,obj=None):
		if obj != None:
			if Core.hasMethod(obj,"Drench"):
				obj.Drench(self)
		self.parent.removeItem(self)
		Core.player.addItem(factory["bottle"]())




class Shard(Core.Item):
	#???
	def Cut(self,P):
		Core.game.Print("[you cut something?]")

	
	def Lick(self,licker):
		if self.composition in ("glass","bronze","iron","steel"):
			Core.game.Print("It tastes like... blood.")
			licker.takeDamage(3,"s")
			return True

		if self.composition in Data.tastes:
			Core.game.Print(Data.tastes[self.composition])
		if self.composition in Data.scents:
			Core.game.Print(Data.scents[self.composition].replace("scent","taste"))



class Sign(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,text,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.text = text


	# prints the text on the sign in quotes
	def Look(self):
		Core.game.Print(f'\n"{self.text}"')




class Switch(Core.Fixture):
	def __init__(self,name,desc,weight,durability,composition,mention,effect,**kwargs):
		Core.Fixture.__init__(self,name,desc,weight,durability,composition,mention,**kwargs)
		self.effect = effect


	# triggers some effect using the effect name to find related function
	def Trigger(self):
		eval(self.effect)


	# using the switch triggers the effect
	def Use(self):
		self.Trigger()




class Sword(Core.Weapon):
	def Cut(self):
		Core.game.Print("[you cut something?]")




class Table(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,items,descname,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.items = items
		self.descname = descname



	### Operation ###

	def Break(self):
		if self.durability == -1:
			if not Core.game.silent:
				Core.game.Print(f"The {self.name} cannot be broken.")
			return False
		Core.game.Print(f"The {self.name} breaks.")
		self.parent.removeItem(self)
		# drop things it contains into parent
		if self.items:
			Core.game.Print(f"It's contents fall onto the ground.")
		for item in self.items:
			self.parent.addItem(item)
		return True


	def addItem(self,I):
		# ensure only one bunch of Gold exists here
		if isinstance(I,Core.Serpens):
			for item in self.items:
				if isinstance(item,Core.Serpens):
					item.merge(I)
					return

		insort(self.items,I)
		I.parent = self
		I.despawnTimer = None

		if len(self.items) == 1:
			self.descname = f"{self.name} with {~self.items[0]} on it"
		elif len(self.items) > 1:
			self.descname = f"{self.name} with things on it"


	def removeItem(self,I):
		self.items.remove(I)
		if len(self.items) == 1:
			self.descname = f"{self.name} with {~self.items[0]} on it"
		elif len(self.items) == 0:
			self.descname = f"{self.name}"




	### Getters ###

	# the weight of a box is equal to its own weight + weights of its items
	def Weight(self):
		w = self.weight
		for i in self.items:
			w += i.Weight()
		return w


	def itemNames(self):
		return [item.name for item in self.items]


	def contents(self):
		return self.items



	### User Output ###

	def describe(self):
		Core.game.Print(f"It's {~self}.")
		if len(self.items) != 0:
			Core.game.Print(f"On it is {Core.listObjects(self.items)}.")
		else:
			Core.game.Print("There is nothing on it.")




class Wall(Core.Passage):
	def __init__(self,name,desc,weight,durability,composition,connections,descname,difficulty,**kwargs):
		Core.Passage.__init__(self,name,desc,weight,durability,composition,connections,descname,**kwargs)
		self.difficulty = difficulty


	def Traverse(self,traverser,dir=None,verb="climb"):
		if dir == None:
			if len(set(self.connections.values())) == 1:
				dir = list(self.connections.keys())[0]
			else:
				msg = f"Which direction will you go on the {self.name}?\n> "
				dir = input(msg).lower()
		if dir in Data.cancels:
			return False
		if dir not in self.connections:
			Core.game.Print(f"The {self.name} does not go '{dir}'.")
			return False

		if traverser.riding:
			return self.Traverse(traverser.riding,dir=dir)
		if traverser.carrying:
			Core.game.Print(f"You can't climb, you are carrying {~traverser.carrying}")
			return False

		if traverser.hasCondition("clingfast"): verb = "crawl"
		elif traverser.hasCondition("flying"): verb = "fly"
		elif traverser is Core.player.riding: verb = "ride"
		Core.game.Print(f"You {verb} {dir} {-self}.")

		if traverser.ATHL() >= self.difficulty or traverser.hasAnyCondition("clingfast","flying"):
			traverser.changeRoom(Core.world[self.connections[dir]])
			return True

		Core.game.Print(f"You fall!")
		if "down" in self.connections:
			traverser.changeRoom(Core.world[self.connections["down"]])
		if not traverser.hasAnyCondition("fly","fleetfooted"):
			traverser.takeDamage(self.difficulty-traverser.ATHL(),"b")
		return True



factory = {
	"bottle": lambda: Bottle("bottle","an empty glass bottle",3,3,"glass"),
	"coffee": lambda: Potion("bottle of coffee","A bottle of dark brown foamy liquid",4,3,"glass",aliases=["coffee","espresso","bottle"]),
	"red potion": lambda: Potion("red potion", "A bubbling red liquid in a glass bottle",4,3,"glass",aliases=["potion"]),
	"blue potion": lambda: Potion("blue potion", "A bubbling blue liquid in a glass bottle",4,3,"glass",aliases=["potion"]),
	"green potion": lambda: Potion("green potion", "A bubbling green liquid in a glass bottle",4,3,"glass",aliases=["potion"])
}
