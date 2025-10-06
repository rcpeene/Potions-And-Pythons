# Items.py
# This file contains the item classes used in the game
# This file is dependent on Core.py and is a dependency of Menu.py


from bisect import insort
from random import randint, choice

import Effects
import Core
import Data




############################
## ITEM CLASS DEFINITIONS ##
############################


class Axe(Core.Weapon):
	# TODO: do something with this
	def Cut(self):
		Core.Print("[you cut something?]")



class Bed(Core.Item):
	def LayOn(self,layer):
		if layer.carrier is not self and self.Occupy(layer):
			if layer is Core.player:
				Core.Print(f"You get in {-self}.")
			else:
				Core.Print(f"{+layer} lies down on {-self}.")
		if layer.carrier is self:
			layer.Lay()
			layer.addCondition("cozy",-3)
			return True
		return False


	def Traverse(self,traverser,dir=None,verb=None):
		return self.LayOn(traverser)


class Bottle(Core.Item):
	# breaks the bottle, removes it from player inventory, and generates some shards
	def Break(self):
		if not super().Break():
			return False
		if self.weight > 2 and self.composition == "glass":
			Core.Print("Shards of glass scatter everywhere.",color="o")
		while self.weight > 2 and self.composition == "glass":
			shardWeight = randint(2,4)
			self.weight -= shardWeight
			shard = Shard("glass shard","a sharp shard of glass",shardWeight,-1,"glass",{"shard"})
			Core.game.currentroom.add(shard)
		return True 


class Box(Core.Portal):
	def __init__(self,name,desc,weight,durability,composition,open,capacity,items,passprep=None,**kwargs):
		Core.Portal.__init__(self,name,desc,weight,durability,composition,{},name,None,**kwargs)
		self.parent = None
		self.passprep = "in" if passprep is None else passprep
		self.links = {self.passprep:self}
		self.open = open
		self.capacity = capacity
		self.items = items


	### File I/O ###

	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		del jsonDict["links"]
		del jsonDict["descname"]
		return jsonDict


	### Operation ###

	def addCondition(self,name,dur,stackable=False):
		if Core.Item.addCondition(self,name,dur,stackable):
			for item in self.items:
				item.addCondition(name,dur,stackable)


	# sets open bool to true, prints its items
	def Open(self,opener):
		if self.open:
			opener.Print(f"{+self} is already open.")
		else:
			opener.Print(f"You open {-self}.")
		self.open = True
		for elem in self.items:
			if isinstance(elem,Core.Creature):
				elem.removeCondition("hidden",-3)
		if self.occupant:
			return self.occupant.Fall()
		if Core.player not in self.items:
			self.Look(opener)
		return True


	# sets open bool to false
	def Close(self):
		self.open = False
		Core.Print(f"You close {-self}.")
		for elem in self.items:
			if isinstance(elem,Core.Creature):
				elem.addCondition("hidden",-3)
		return True


	def Look(self,looker):
		if Core.player not in self.items:
			self.open = True
		# exclude player if they are inside the box
		displayItems = [item for item in self.items if item is not Core.player]
		if len(displayItems) == 0:
			text = "It is empty"
			if Core.player in self.items:
				text += ", apart from you"
			looker.Print(f"{text}.")
		else:
			looker.Print(f"Inside there is {Core.listObjects(displayItems)}.")
			Core.game.setPronouns(self.items[-1])
		return True


	def Break(self):
		if not super().Break():
			return False
		if len(self.items) > 0:
			Core.Print("Its contents spill out.")
		# drop things it contains into parent
		for item in self.items:
			if item is Core.player:
				Core.waitKbInput(f"You are no longer in {-self}.")
			item.changeLocation(self.parent)
		return True


	def Bombard(self,missile):
		assert isinstance(missile,Core.Projectile)
		if Core.diceRoll(1,100) < Core.bound(missile.aim+self.weight+10,1,99):
			if not self.open:
				Core.Print(f"{+self} is closed.")
				missile.Collide(self)
			elif missile.item.parent is self:
				missile.Collide(self)				
			elif not self.canAdd(missile):
				Core.Print(f"{+self} is too full.")
				missile.Collide(self)
			else:
				Core.Print(f"{+missile} goes into {-self}.")
				missile = missile.asItem()
				missile.changeLocation(self)
			return True
		return False


	def enter(self,traverser):
		self.links["out"] = self.parent
		if traverser in self.contents():
			return False
		self.open = True
		self.add(traverser)


	def exit(self,traverser):
		if traverser not in self.contents():
			return False
		self.open = True
		self.remove(traverser)
		traverser.removeCondition("hidden",-3)


	def Traverse(self,traverser,dir=None,verb=None):
		if self in traverser.objTree():
			if traverser is Core.player:
				Core.Print(f"You can't enter {-self}. It's within your Inventory.")
			else:
				Core.Print(f"{+traverser} can't enter {-self}. It's within {-traverser}'s Inventory.")
			return False
		if self.occupant is traverser:
			Core.Print(f"{+traverser} is {traverser.posture()} on {-self}.")
			return False

		if dir in ("out","outside","out of"):
			if self is traverser.parent:
				if not self.open:
					self.Open(traverser)
				Core.Print(f"You get out of {-self}.")
				if self.parent is not Core.game.currentroom:
					Core.waitKbInput()
				traverser.changeLocation(self.parent)
				return True
			else:
				Core.Print(f"You're not in {-self}.",color="k")
				return False
		if traverser.parent is self:
			Core.Print(f"You're already in {-self}.")
			return False
		if dir not in ("in","into","inside",None):
			Core.Print(f"{+self} does not go {dir}.",color="k")
			return False

		if dir is None:
			dir = "into"
		if verb is None:
			verb = "get"
		self.open = True
		if not self.canAdd(traverser):
			if traverser is Core.player:
				Core.Print(f"You can't enter {-self}. There's not enough room.")
			return False

		if not self.open:
			self.Open(traverser)
		if traverser is Core.player:
			Core.Print(f"You {verb} {dir} {-self}.")
		traverser.changeLocation(self)
		return True


	def add(self,I):
		# ensure only one bunch of Gold exists here
		if isinstance(I,Core.Serpens):
			for item in self.items:
				if isinstance(item,Core.Serpens):
					item.merge(I)
					return

		insort(self.items,I)
		I.parent = self
		I.nullDespawn()


	def remove(self,I):
		self.items.remove(I)


	def passTime(self,t):
		Core.Item.passTime(self,t)
		for I in self.items:
			I.passTime(t)


	def Fall(self,height=0,room=None):
		# contents might spill out if item breaks
		contents = self.contents().copy()
		Core.Item.Fall(self,height,room)
		for obj in contents:
			# TODO, revise how damage is mitigated here based on composition/durability?
			obj.takeDamage(height//3,"b")
		return True


	### Getters ###

	def itemsWeight(self):
		return sum(i.untetheredWeight() for i in self.items)


	# the weight of a box is equal to its own weight + weights of its items
	def Weight(self):
		return self.weight + self.itemsWeight()


	def space(self):
		return self.capacity - self.itemsWeight()


	def canAdd(self,I):
		return I.Weight() <= self.space() and self not in I.objTree()


	def contents(self):
		return self.items


	def itemNames(self):
		return [item.name for item in self.items]


	# get the links dict to use in the parent's allLinks method
	def getLinksForParent(self):
		return {self.passprep:self}



class Controller(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,triggers,effect,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.triggers = triggers if triggers else ["Use"]
		self.effect = effect
		for trigger in self.triggers:
			f = lambda *args: self.Trigger(*args)
			setattr(self,trigger,f)


	### File I/O ###

	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		for trigger in self.triggers:
			del jsonDict[trigger]
		return jsonDict


	### Operation ###

	# triggers some effect using the effect string to call related function
	def Trigger(self,*args):
		exec(self.effect)



class Food(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,heal,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.heal = heal

	# heals hp to the player, removes food from inventory
	def Eat(self,eater):
		if isinstance(eater,Core.Player):
			Core.Print(f"You consume {-self}.")
		else:
			Core.Print(f"{+eater} eats {-self}.")
		h = eater.heal(self.heal)
		eater.lastAte = Core.game.time
		if h == 0 and isinstance(eater,Core.Player):
			Core.Print("Yummy...")
		eater.checkHungry()
		self.parent.remove(self)



class Foot(Core.Item):
	def asWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.min1(self.weight//4),0,0,0,"b")



class Fountain(Core.Fixture):
	def Douse():
		pass


	def Drink(self):
		Core.Print(f"You drink from {-self.name}.")



class Generator(Controller):
	def __init__(self,name,desc,weight,durability,composition,effect,charge,cap,rate,cost,**kwargs):
		Core.Controller.__init__(self,name,desc,weight,durability,composition,effect,**kwargs)
		self.charge = charge
		self.cap = cap
		self.rate = rate
		self.cost = cost


	def Trigger(self,*args):
		if self.charge > self.cost:
			self.charge -= self.cost
			eval(self.effect)
		else:
			Core.Print("Nothing happened...")


	def passTime(self,t):
		Controller.passTime(self,t)
		self.charge += self.rate*t
		if self.charge > self.cap:
			self.charge = self.cap



class Timer(Controller):
	def __init__(self,name,desc,weight,durability,composition,on=False,delay=1,fuse=None,repeats=0,maxRepeats=1,toggle=False,reset=True,**kwargs):
		Controller.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.on = on
		# the 'length' of the fuse
		self.delay = delay
		# time until next trigger
		self.fuse = self.delay if fuse is None else fuse
		# number of times been triggered
		self.repeats = repeats
		# will stop after repeats reaches this
		self.maxRepeats = maxRepeats
		# whether or not it can be turned off after turn on
		self.toggle = toggle
		# whether or not repeats and fuse reset upon trigger
		self.reset = reset


	def Trigger(self,*args):
		if self.reset and not self.on:
			self.repeats = 0
			self.fuse = self.delay
		if self.toggle and self.on:
			Core.Print(f"{+self} turns off.")
			self.on = False
			return True
		if self.maxRepeats is not None and self.repeats > self.maxRepeats:
			return False

		self.on = True
		Core.Print(f"{+self} turns on.")


	def passTime(self,t):
		Controller.passTime(self,t)
		if not self.on:
			return

		if self.fuse <= 0:
			eval(self.effect)
			self.repeats += 1
			self.fuse = self.delay
		self.fuse -= 1



class Hand(Core.Item):
	def asWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.min1(self.weight//4)+1,2,0,0,"b")



class Key(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,id,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.id = id


	def LockWith(self,box):
		pass


	def UnlockWith(self,box):
		pass



class Lockbox(Box):
	def __init__(self,name,desc,weight,durability,composition,keyids,locked,**kwargs):
		Box.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.keyids = keyids
		self.locked = locked


	### Operation ###

	# sets open bool to true, prints its items
	def Open(self,opener):
		if self.locked:
			Core.Print(f"{+self} is locked.")
			return False
		return Box.Open(self,opener)


	def Look(self,looker):
		if self.locked == True and Core.player not in self.items:
			looker.Print(f"{+self} is locked.")
			return False
		return Box.Look(self,looker)


	def Lock(self,key):
		if self.locked:
			Core.Print(f"{+self} is already locked.")
			return False
		if key.id in self.keyids:
			self.locked = True
			Core.Print(f"You lock {-self}.")
			if Core.hasMethod(key,"UnlockWith"):
				key.UnlockWith(self)
			return True
		Core.Print(f"You can't lock {-self} with {-key}.")
		return True


	def Unlock(self,key):
		if not self.locked:
			Core.Print(f"{+self} is not locked.")
			return False
		if key.id in self.keyids:
			self.locked = False
			Core.Print(f"You unlock {-self}.")
			if Core.hasMethod(key,"LockWith"):
				key.LockWith(self)
			return True
		Core.Print(f"{+key} won't work!")
		return True


	def Traverse(self,traverser,dir=None,verb=None):
		if self.locked:
			if traverser is Core.player:
				if self is traverser.parent:
					Core.Print(f"You can't get out of {-self}. It's locked!")
				else:
					Core.Print(f"You can't get in {-self}. It is locked.")					
			return True
		else:
			return Box.Traverse(self,traverser,dir=dir,verb=verb)



class Mouth(Core.Item):
	def asWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.min1(self.weight//4),0,0,4,"p")



class Potion(Bottle):
	# heals the player hp 1000, replaces potion with an empty bottle
	def Drink(self):
		Core.Print(f"You drink {-self}.")
		Core.player.heal(1000)
		self.parent.remove(self)
		Core.player.add(factory["bottle"]())


	def Pour(self,obj=None):
		if obj != None:
			if Core.hasMethod(obj,"Drench"):
				obj.Drench(self)
		self.parent.remove(self)
		Core.player.add(factory["bottle"]())



class Shard(Core.Item):
	#???
	def Cut(self,P):
		# TODO: do something here?
		Core.Print("[you cut something?]")

	
	def Lick(self,licker):
		if self.composition in ("glass","bronze","iron","steel"):
			Core.Print("It tastes like... blood.")
			licker.takeDamage(3,"s")
			return True

		if self.composition in Data.tastes:
			Core.Print(Data.tastes[self.composition])
		if self.composition in Data.scents:
			Core.Print(Data.scents[self.composition].replace("scent","taste"))



class Sign(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,text,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.text = text


	# prints the text on the sign in quotes
	def Look(self,looker):
		Core.Print(f'\n"{self.text}"',color='y')



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
		# TODO: once again, do something with this?
		Core.Print("[you cut something?]")



class Table(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,items,descname,**kwargs):
		Core.Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.items = items
		self.descname = descname


	### Operation ###

	def Break(self):
		if not super().Break():
			return False
		# drop things it contains into parent
		if self.items:
			Core.Print(f"It's contents fall onto the ground.")
		for item in self.items:
			self.parent.add(item)
		return True


	def add(self,I):
		# ensure only one bunch of Gold exists here
		if isinstance(I,Core.Serpens):
			for item in self.items:
				if isinstance(item,Core.Serpens):
					item.merge(I)
					return

		insort(self.items,I)
		I.parent = self
		I.nullDespawn()

		if len(self.items) == 1:
			self.descname = f"{self.name} with {~self.items[0]} on it"
		elif len(self.items) > 1:
			self.descname = f"{self.name} with things on it"

		if self.itemsWeight() > self.durability*2:
			print(f"{+self} collapses under the weight.")
			self.Break()
		elif self.itemsWeight() > self.durability:
			Core.Print(f"{+self} creaks under the weight.")


	def remove(self,I):
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


	def itemsWeight(self):
		return sum(i.untetheredWeight() for i in self.items)


	def itemNames(self):
		return [item.name for item in self.items]


	def contents(self):
		return self.items


	def canAdd(self,I):
		return True


	### User Output ###

	def describe(self):
		Core.Print(f"It's {~self}.")
		if len(self.items) != 0:
			Core.Print(f"On it is {Core.listObjects(self.items)}.")
		else:
			Core.Print("There is nothing on it.")



class Wall(Core.Passage):
	def __init__(self,name,desc,weight,durability,composition,links,descname,difficulty,passprep="onto",**kwargs):
		Core.Passage.__init__(self,name,desc,weight,durability,composition,links,descname,passprep=passprep,**kwargs)
		self.difficulty = difficulty


	def Traverse(self,traverser,dir=None,verb="climb"):
		if dir == None:
			if len(set(self.links.values())) == 1:
				dir = list(self.links.keys())[0]
			else:
				msg = f"Which direction on the {self.name}?"
				dir = Core.Input(msg).lower()
		if dir in Data.cancels:
			return False
		if dir not in self.links:
			Core.Print(f"{+self} does not go '{dir}'.")
			return False

		if traverser.riding:
			return self.Traverse(traverser.riding,dir=dir)
		if traverser.carrying:
			Core.Print(f"You can't climb, you are carrying {~traverser.carrying}")
			return False

		if traverser.hasCondition("clingfast"): verb = "crawl"
		elif traverser.hasCondition("flying"): verb = "fly"
		elif traverser is Core.player.riding: verb = "ride"
		if traverser is Core.player:
			Core.waitKbInput(f"You {verb} {dir} {-self}.")

		if traverser.ATHL() >= self.difficulty or traverser.hasAnyCondition("clingfast","flying"):
			traverser.changeLocation(self.getNewLocation(dir))
			return True
		elif "down" in self.links:
			traverser.Fall(self.difficulty,room=self.getNewLocation("down"))
		else:
			traverser.Fall(self.difficulty)
		return True


	def Transfer(self,item):
		if isinstance(item,Core.Creature):
			return self.Traverse(item,dir=self.getDefaultDir())

		if "down" in self.links:
			return item.Fall(height=self.difficulty,room=self.links["down"])

		# item can't randomly go up
		dir = choice([dir for dir in self.links])
		if self.links[dir] == self.links.get("up",None):
			return item.Fall()

		# Print(f"{+item} goes {self.passprep} {-self}.")	
		item.changeLocation(self.links[dir])


class Window(Core.Passage):
	def __init__(self,name,desc,weight,durability,composition,links,descname,open=False,broken=False,view=None,passprep="through",**kwargs):
		Core.Passage.__init__(self,name,desc,weight,durability,composition,links,descname,passprep=passprep,**kwargs)
		self.descname = descname
		self.view = view
		if self.view is not None:
			assert self.view in self.links
		self.open = open
		if not self.open:
			self.passprep = "at"
		self.broken = broken


	# breaks the window, removes it from player inventory, and generates some shards
	def Break(self):
		Core.Print(f"{+self} breaks.")
		self.broken = True
		self.open = True
		self.durability = -1
		self.passprep = "through"
		if self.weight > 2 and self.composition == "glass":
			Core.Print("Shards of glass scatter everywhere.",color="o")
		while self.weight > 2 and self.composition == "glass":
			shardWeight = randint(2,4)
			self.weight -= shardWeight
			shard = Shard("glass shard","a sharp shard of glass",shardWeight,-1,"glass",{"shard"})
			Core.game.currentroom.add(shard)
		if self.occupant:
			occupant = self.occupant
			self.Disoccupy()
			occupant.Fall(room=self.getNewLocation())
		return True


	def Traverse(self,traverser,dir=None,verb="go"):
		if not (self.broken or self.open):
			Core.Print(f"{+self} is closed.")
			return False

		if dir == None:
			if len(set(self.links.values())) == 1:
				dir = list(self.links.keys())[0]
			else:
				msg = f"Which direction on the {self.name}?"
				dir = input(msg).lower()
		if dir in Data.cancels:
			return False
		if dir not in self.links:
			Core.Print(f"{+self} does not go '{dir}'.")
			return False

		if traverser.riding:
			return self.Traverse(traverser.riding,dir=dir)

		newloc = self.getNewLocation(dir)
		if not newloc.canAdd(traverser):
			if traverser is Core.player:
				Core.Print(f"You can't enter {-self}. There's not enough room.")
			return False
		if traverser.hasCondition("flying"): verb = "fly"
		elif traverser is Core.player.riding: verb = "ride"
		Core.Print(f"You {verb} {dir} {-self}.")
		traverser.changeLocation(newloc)
		return True


	def Bombard(self,missile):
		assert isinstance(missile,Core.Projectile)
		if Core.diceRoll(1,100) < Core.bound(missile.aim+self.weight+10,1,99):
			if not self.open:
				missile.Collide(self)
			if self.open:
				Core.Print(f"{+missile} goes {self.passprep} {-self}.")
				self.Transfer(missile.asItem())
			return True
		return False
	

	def Look(self,looker):
		if self.view:
			looker.waitKbInput(f"You look through it...")
			Core.Print(f"{self.links[self.view].desc}.")
		return True



class Door(Window):
	def __init__(self,name,desc,weight,durability,composition,links,descname,open=False,**kwargs):
		Window.__init__(self,name,desc,weight,durability,composition,links,descname,**kwargs)
		self.descname = descname
		self.open = open


	# sets open bool to true, prints its items
	def Open(self,opener):
		if self.open:
			Core.Print(f"{+self} is already open.")
		else:
			Core.Print(f"You open {-self}.")
			self.open = True



factory = {
	"blue potion": lambda: Potion("blue potion", "A bubbling blue liquid in a glass bottle",6,3,"glass",None,["potion"]),
	"bottle": lambda: Bottle("bottle","an empty glass bottle",6,3,"glass"),
	"coffee": lambda: Potion("bottle of coffee","A bottle of dark brown foamy liquid",6,3,"glass",None,["coffee","espresso","bottle"]),
	"green potion": lambda: Potion("green potion", "A bubbling green liquid in a glass bottle",6,3,"glass",None,["potion"]),
	"red potion": lambda: Potion("red potion", "A bubbling red liquid in a glass bottle",6,3,"glass",None,["potion"]),
	"shard": lambda: Shard("glass shard","a black glass shard",2,1,"glass",["shard"])
}
