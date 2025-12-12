# Items.py
# This file contains the item classes used in the game
# This file is dependent on Core.py and is a dependency of Menu.py and Interpreter.py


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
		return self.Traverse(layer)

	def Traverse(self,traverser,dir=None,verb=None):
		if verb == "jump":
			if self.occupy(traverser):
				if traverser is Core.player:
					Core.Print(f"You jump onto {-self}.")
				else:
					Core.Print(f"{+traverser} jumps onto {-self}.")
				traverser.changePosture("crouch")
			return True
		if traverser.platform is not self and self.occupy(traverser):
			if traverser is Core.player:
				Core.Print(f"You get in {-self}.")
			else:
				Core.Print(f"{+traverser} lies down on {-self}.")
		if traverser.platform is self:
			traverser.changePosture("lay")
			traverser.addStatus("cozy",-4)
			return True
		return False


class Bottle(Core.Item):
	def breaks(self):
		if self.id not in Core.game.objRegistry:
			return False
		parent = self.parent
		if self.durability == -1:
			if not Core.game.silent:
				Core.Print(f"{+self} cannot be broken.")
			return False
		self.Print(f"{+self} breaks.")
		if self.weight > 2 and self.composition == "glass":
			self.Print("Shards of glass scatter everywhere.",color="o")
		while self.weight > 1 and self.composition == "glass":
			shardWeight = randint(1,max(self.weight,4))
			self.weight -= shardWeight
			shard = Shard("glass shard","a sharp shard of glass",shardWeight,-1,"glass",{"shard"})
			parent.add(shard)
		self.destroy()
		return True



class Box(Core.Container):
	def __init__(self,name,desc,weight,durability,composition,items,open=False,**kwargs):
		super().__init__(name,desc,weight,durability,composition,items,**kwargs)
		self.open = open

	def enter(self,traverser):
		self.open = True
		super().enter(traverser)


	def exit(self,traverser):
		self.open = True
		super().exit(traverser)


	def examine(self,looker):
		if looker not in self.items:
			self.open = True
		return super().look(looker)


	# sets open bool to true, prints its items
	def open(self,opener,silent=False):
		if self.open:
			if not silent:
				opener.Print(f"{+self} is already open.")
			return False
		elif not silent:
			opener.Print(f"You open {-self}.")
		self.open = True
		for elem in self.items:
			if isinstance(elem,Core.Creature):
				elem.removeStatus("hidden",-4)
		for occupant in self.occupants.copy():
			occupant.fall()
		if Core.player not in self.items:
			self.look(opener)
		return True


	# sets open bool to false
	def close(self,closer):
		self.open = False
		closer.Print(f"You close {-self}.")
		for elem in self.items:
			if isinstance(elem,Core.Creature):
				elem.addStatus("hidden",-4)
		return True



class Controller(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,effect,triggers=None,**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.triggers = triggers if triggers else ["use"]
		self.effect = effect
		for trigger in self.triggers:
			f = lambda *args: self.Trigger(*args)
			setattr(self,trigger,f)


	### File I/O ###

	def convertToJSON(self):
		jsonDict = super().convertToJSON()
		for trigger in self.triggers:
			del jsonDict[trigger]
		return jsonDict


	### Operation ###

	# triggers some effect using the effect string to call related function
	def Trigger(self,*args):
		exec(self.effect)



class Food(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,heal,**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.heal = heal

	# heals hp to the player, removes food from inventory
	def consume(self,eater):
		if isinstance(eater,Core.Player):
			Core.Print(f"You consume {-self}.")
		else:
			Core.Print(f"{+eater} eats {-self}.")
		h = eater.heal(self.heal)
		eater.lastAte = Core.game.time
		if h == 0 and isinstance(eater,Core.Player):
			Core.Print("Yummy...")
		eater.checkHungry()
		self.destroy(self)



class Foot(Core.Item):
	def asWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.min1(self.weight//4),0,0,0,"b")



class Fountain(Core.Fixture):
	def douse():
		pass


	def imbibe(self):
		Core.Print(f"You drink from {-self.name}.")



class Generator(Controller):
	def __init__(self,name,desc,weight,durability,composition,effect,charge,cap,rate,cost,**kwargs):
		super().__init__(name,desc,weight,durability,composition,effect,**kwargs)
		self.charge = charge
		self.cap = cap
		self.rate = rate
		self.cost = cost


	def Trigger(self,*args):
		if self.charge > self.cost:
			self.charge -= self.cost
			eval(self.effect)
		else:
			self.Print("Nothing happened...")


	def passTime(self,t):
		super().passTime(t)
		self.charge += self.rate*t
		if self.charge > self.cap:
			self.charge = self.cap



class Timer(Controller):
	def __init__(self,name,desc,weight,durability,composition,effect,on=False,delay=1,fuse=None,repeats=0,maxRepeats=1,toggle=False,reset=True,**kwargs):
		super().__init__(name,desc,weight,durability,composition,effect,**kwargs)
		self.on = on
		# the 'length' of the fuse; time between triggers when turned on
		self.delay = delay
		# time left until next effect
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
			self.Print(f"{+self} turns off.")
			self.on = False
			return True
		if self.maxRepeats is not None and self.repeats > self.maxRepeats:
			self.Print("Nothing happens...")
			return False

		self.on = True
		self.Print(f"{+self} turns on.")


	def passTime(self,t):
		super().passTime(t)
		if self.maxRepeats is not None and self.repeats > self.maxRepeats:
			self.on = False
		if not self.on:
			return

		self.fuse -= 1
		if self.fuse <= 0:
			eval(self.effect)
			self.repeats += 1
			self.fuse = self.delay



class Hand(Core.Item):
	def asWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.min1(self.weight//4)+1,2,0,0,"b")



class Key(Core.Item):
	def lockWith(self,box):
		pass


	def unlockWith(self,box):
		pass



class Lockbox(Box):
	def __init__(self,name,desc,weight,durability,composition,keyids,locked,**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.keyids = keyids
		self.locked = locked


	### Operation ###

	# sets open bool to true, prints its items
	def open(self,opener):
		if self.locked:
			opener.Print(f"{+self} is locked.")
			return False
		return Box.open(self,opener)


	def examine(self,looker):
		if self.locked == True and Core.player not in self.items:
			looker.Print(f"{+self} is locked.")
			return False
		return Box.look(self,looker)


	def lock(self,locker,key):
		if self.locked:
			locker.Print(f"{+self} is already locked.")
			return False
		if key.id in self.keyids:
			self.locked = True
			locker.Print(f"You lock {-self}.")
			if Core.hasMethod(key,"unlockWith"):
				key.unlockWith(self)
			return True
		locker.Print(f"You can't lock {-self} with {-key}.")
		return True


	def unlock(self,unlocker,key):
		if not self.locked:
			unlocker.Print(f"{+self} is not locked.")
			return False
		if key.id in self.keyids:
			self.locked = False
			unlocker.Print(f"You unlock {-self}.")
			if Core.hasMethod(key,"lockWith"):
				key.lockWith(self)
			return True
		unlocker.Print(f"{+key} won't work!")
		return True


	def Traverse(self,traverser,dir=None,verb=None):
		if self.locked:
			if self is traverser.parent:
				traverser.Print(f"You can't get out of {-self}. It's locked!")
			else:
				traverser.Print(f"You can't get in {-self}. It is locked.")
			return True
		else:
			return Box.Traverse(self,traverser,dir=dir,verb=verb)



class Mouth(Core.Item):
	def asWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",Core.min1(self.weight//4),0,0,4,"p")



class Pool(Core.Fixture):
	def __init__(self,name,desc,weight,composition,finite=False,**kwargs):
		assert composition in Data.liquids
		super().__init__(name,desc,weight,composition,**kwargs)
		self.occupyprep = "in"
		self.finite = finite


	def canAdd(self,I):
		if self.occupantsSize() + I.Size() > self.Size():
			return False
		return True


	def disoccupy(self,occupant):
		if occupant not in self.occupants:
			return False
		super().disoccupy(occupant)
		occupant.addStatus("wet",21)
		occupant.removeStatus("wet",-4)


	def Traverse(self,traverser,dir=None,verb=None):

		# if self in traverser.objTree():
		# 	if traverser is Core.player:
		# 		Core.Print(f"You can't enter {-self}. It's within your Inventory.")
		# 	else:
		# 		Core.Print(f"{+traverser} can't enter {-self}. It's within {-traverser}'s Inventory.")
		# 	return False
		if traverser in self.occupants:
			Core.Print(f"You can't, you are {traverser.position()}.")
			return False

		if dir in ("out","outside"):
			if self is traverser.parent:
				if not self.open:
					self.open(traverser)
				Core.Print(f"You get out of {-self}.")
				if self.parent is not Core.game.currentroom:
					Core.waitInput()
				self.disoccupy(traverser)
				return True
			else:
				Core.Print(f"You're not in {-self}.",color="k")
				return False
		# if traverser.parent is self:
		# 	Core.Print(f"You're already in {-self}.")
		# 	return False
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

		traverser.Print(f"You {verb} {dir} {-self}.")
		self.occupy(traverser)
		traverser.addStatus("wet",-4)
		return True


	def consume(self,eater):
		return self.imbibe(eater)


	def imbibe(self,drinker):
		Core.Print(f"You drink from {-self}.")
		self.Taste(drinker)

		if self.finite:
			self.weight -= 3	
		if self.weight <= 0:
			self.Print(f"{+self} becomes empty.")
			return self.destroy()




class Potion(Bottle):
	# heals the player hp 1000, replaces potion with an empty bottle
	def imbibe(self,drinker):
		drinker.Print(f"You drink {-self}.")
		drinker.heal(1000)
		self.replace("bottle")

	# TODO: when breaking, spill potion out and then call bottle.Break

	def Pour(self,pourer,obj=None):
		if obj != None:
			if Core.hasMethod(obj,"Drench"):
				obj.Drench(self)
		self.replace("bottle")



class Shard(Core.Item):
	#???
	def Cut(self,P):
		# TODO: do something here?
		Core.Print("[you cut something?]")


	def Lick(self,licker):
		if self.composition in ("glass","bronze","iron","steel"):
			licker.Print("It tastes like... blood.")
			licker.takeDamage(3,"s")
			return True

		if self.composition in Data.tastes:
			licker.Print(Data.tastes[self.composition])
		if self.composition in Data.scents:
			licker.Print(Data.scents[self.composition].replace("scent","taste"))



class Sign(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,text,**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.text = text


	# prints the text on the sign in quotes
	def examine(self,looker):
		looker.Print(f'\n"{self.text}"',color='y')



class Switch(Controller):
	def __init__(self,name,desc,weight,durability,composition,effect,offEffect,on=False,toggle=True,**kwargs):
		super().__init__(name,desc,weight,durability,composition,effect,**kwargs)
		self.offEffect = offEffect
		self.on = on
		# whether or not it can be turned off after turn on
		self.toggle = toggle


	# triggers some effect using the effect name to find related function
	def Trigger(self):
		if self.on and not self.toggle:
			self.Print(f"{+self} is already on.")
			return False
		elif self.on:
			self.Print(f"{+self} turns off.")
			self.on = False
			eval(self.offEffect)
		else:
			self.Print(f"{+self} turns on.")
			self.on = True
			eval(self.effect)



class Sword(Core.Weapon):
	def Cut(self,cutter):
		# TODO: once again, do something with this?
		cutter.Print("[you cut something?]")



class Table(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)



class Wall(Core.Passage):
	def __init__(self,name,desc,weight,composition,links,difficulty,passprep=None,**kwargs):
		super().__init__(name,desc,weight,composition,links,passprep=passprep,**kwargs)
		self.difficulty = difficulty
		if passprep is None:
			self.passprep = "onto" if self.getDefaultDir() in ("up","down") else "across"


	def Traverse(self,traverser,dir=None,verb=None):
		if dir == None:
			if len(set(self.links.values())) == 1:
				dir = list(self.links.keys())[0]
			else:
				msg = f"Which direction on the {self.name}?"
				dir = Core.Input(msg).lower()
		if dir in Data.cancels:
			return False
		if dir == "over": dir = "across"
		if dir in Data.directions: dir = Data.directions[dir]
		if dir not in self.links:
			traverser.Print(f"{+self} does not go '{dir}'.")
			return False

		if traverser.hasStatus("flying") and verb is None: verb = "fly"
		elif traverser.hasStatus("clingfast") and dir in ("u","up","d","down"): verb = "crawl"
		elif traverser is Core.player.riding: verb = "ride"
		elif verb is None and dir in ("u","up","d","down"): verb = "climb"
		elif verb is None: verb = "jump"

		if traverser.riding:
			return self.Traverse(traverser.riding,dir=dir)
		if traverser.carrying and verb in ("climb","crawl"):
			traverser.Print(f"You can't climb, you are carrying {~traverser.carrying}.")
			return False
		if not self.canPass(traverser):
			traverser.Print(f"{+traverser} can't fit on {-self}.")
			return False

		traverser.waitInput(f"You {verb} {dir} {-self}.")

		if verb != "jump" or dir not in ("d","down","off") or traverser.hasAnyStatus("flying"):
			contest = Core.roll(traverser.ATHL()) - self.difficulty
			if contest > 0 or traverser.hasAnyStatus("clingfast","flying"):
				traverser.changeLocation(self.getNewLocation(dir))
				return True

		if "down" in self.links:
			traverser.fall(self.difficulty,room=self.getNewLocation("down"))
		else:
			traverser.fall(self.difficulty)
		return True


	def Transfer(self,item):
		if isinstance(item,Core.Creature):
			return self.Traverse(item,dir=self.getDefaultDir())

		if "down" in self.links:
			return item.fall(height=self.difficulty,room=self.links["down"])

		# item can't randomly go up
		dir = choice([dir for dir in self.links])
		if self.links[dir] == self.links.get("up",None):
			return item.fall()

		# Print(f"{+item} goes {self.passprep} {-self}.")	
		item.changeLocation(self.getNewLocation(dir))


class Window(Core.Passage):
	def __init__(self,name,desc,weight,composition,links,open=False,broken=False,view=None,passprep="through",**kwargs):
		super().__init__(name,desc,weight,composition,links,passprep=passprep,**kwargs)
		self.view = view
		if self.view is not None:
			assert self.view in self.links
		self.open = open
		if not self.open:
			self.passprep = "at"
		self.broken = broken


	# breaks the window, removes it from player inventory, and generates some shards
	def breaks(self):
		if self.id not in Core.game.itemRegistry:
			return False
		Core.Print(f"{+self} breaks.")
		self.broken = True
		self.open = True
		self.durability = -1
		self.passprep = "through"
		if self.weight > 2 and self.composition == "glass":
			self.Print("Shards of glass scatter everywhere.",color="o")
		while self.weight > 2 and self.composition == "glass":
			shardWeight = randint(1,3)
			self.weight -= shardWeight
			shard = Shard("glass shard","a sharp shard of glass",shardWeight,-1,"glass",{"shard"})
			Core.game.currentroom.add(shard)
		for occupant in self.occupants.copy():
			occupant.fall(room=self.getNewLocation())
			self.disoccupy(occupant)
		if self.covering:
			self.covering.removeCover()
		return True


	def Traverse(self,traverser,dir=None,verb="go"):
		if dir in Data.directions: dir = Data.directions[dir]
		if not (self.broken or self.open):
			traverser.Print(f"{+self} is closed.")
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
			traverser.Print(f"{+self} does not go '{dir}'.")
			return False

		if traverser.riding:
			return self.Traverse(traverser.riding,dir=dir)

		if not self.canPass(traverser):
			traverser.Print(f"{+traverser} can't fit through {-self}.")
			return False

		newloc = self.getNewLocation(dir)
		if not newloc.canAdd(traverser):
			traverser.Print(f"You can't enter {-self}. There's not enough room.")
			return False
		if traverser.hasStatus("flying"): verb = "fly"
		elif traverser is Core.player.riding: verb = "ride"
		traverser.waitInput(f"You {verb} {dir} {-self}.")
		traverser.changeLocation(newloc)
		return True


	def bombard(self,missile):
		assert isinstance(missile,Core.Projectile)
		if Core.roll(100) < Core.bound(missile.aim+self.Size()+10,1,99):
			if not self.open:
				missile.Collide(self)
			if self.open:
				Core.Print(f"{+missile} goes {self.passprep} {-self}.")
				self.Transfer(missile.asItem())
			return True
		return False


	def examine(self,looker):
		if self.view:
			looker.waitInput(f"You look through it...")
			Core.Print(f"{self.links[self.view].desc}")
		return True



class Door(Window):
	def __init__(self,name,desc,weight,durability,composition,links,descname,open=False,**kwargs):
		super().__init__(name,desc,weight,durability,composition,links,descname,**kwargs)
		self.descname = descname
		self.open = open


	# sets open bool to true, prints its items
	def open(self,opener):
		if self.open:
			Core.Print(f"{+self} is already open.")
		else:
			Core.Print(f"You open {-self}.")
			self.open = True



factory = {
	"black hole": lambda: Core.Item("black hole","A spherical vortex of darkness.",10000,-1,"void"),
	"blue potion": lambda: Potion("blue potion", "A bubbling blue liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	"bottle": lambda: Bottle("bottle","An empty glass bottle",6,3,"glass",["glass","glass bottle"]),
	"coffee": lambda: Potion("bottle of coffee","A bottle of frothy dark brown liquid.",10,3,"glass",["coffee","espresso","bottle"],1),
	"compass": lambda: Core.Compass("compass","A plain steel compass with a red arrow.",2,10,"steel",rarity=2,plural="compasses"),
	"green potion": lambda: Potion("green potion", "A bubbling green liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	'iron ingot': lambda: Core.Item("iron ingot","A solid bar of iron.",20,200,"iron",["ingot","bar","iron"]),
	"red potion": lambda: Potion("red potion", "A bubbling red liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	"shard": lambda: Shard("glass shard","A small glass shard.",2,1,"glass",["shard"])
}
