# Items.py
# This file contains the item classes used in the game
# This file is dependent on Core.py and is a dependency of Menu.py and Interpreter.py


from bisect import insort
from random import randint, choice,choices

import Effects
import Core
import Data




############################
## ITEM CLASS DEFINITIONS ##
############################


class Axe(Core.Weapon):
	# TODO: do something with this
	def cut(self):
		pass



class Bed(Core.Item):
	def traverse(self,traverser,dir=None,verb=None):
		if verb == "jump":
			Core.Print(traverser+f"jumps onto {-self}.")
			traverser.changePosture("crouch")
			self.occupy(traverser)
		if verb == None:
			verb = "lay"

		if traverser.platform is not self and self.occupy(traverser):
			displayVerb = "gets in" if verb == "lay" else f"{verb}s on"
			Core.Print(traverser+f"{displayVerb} {-self}.")
			if traverser is Core.player:
				Core.game.setPronouns(self)
		if traverser.platform is self:
			if verb in ("stand","crouch","sit","lay"):
				traverser.changePosture(verb)
			if traverser.posture() == "laying" and not traverser.hasStatus("cozy",-4):
				traverser.addStatus("cozy",-4)
		return True



class Bottle(Core.Item):
	def breaks(self):
		if self.id not in Core.game.itemRegistry:
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
			shard = Shard("glass shard","a sharp shard of glass",shardWeight,-1,"glass",
			{"shard"})
			parent.add(shard)
		self.destroy()
		return True



# Box is a container that can be opened and closed to hide contents and prevent passage
class Box(Core.Container):
	def __init__(self,name,desc,weight,durability,composition,items,closed=False,**kwargs):
		super().__init__(name,desc,weight,durability,composition,items,**kwargs)
		self.closed = closed

	def canPass(self,obj,silent=False):
		if self.closed:
			if not silent:
				Core.Print(f"{+self} is closed.")
			return False
		if self.Capacity() == -1:
			return True
		return obj.totalSize() <= self.Capacity()


	def enter(self,traverser):
		self.closed = False
		super().enter(traverser)


	def exit(self,traverser):
		self.closed = False
		super().exit(traverser)


	def examine(self,looker):
		if looker not in self.items:
			self.open(looker,silent=True)
		return super().examine(looker)


	# sets closed false, examine contents
	def open(self,opener,silent=False):
		if not self.closed:
			if not silent:
				opener.Print(f"{+self} is already open.")
			return False
		elif not silent:
			opener.Print(f"You open {-self}.")
		self.closed = False
		for elem in self.items:
			if isinstance(elem,Core.Creature):
				elem.removeStatus("hidden",-4)
		for occupant in self.occupants.copy():
			occupant.fall()
		if Core.player not in self.items and not silent:
			self.examine(opener)
		return True


	# sets closed to true
	def close(self,closer):
		self.closed = True
		closer.Print(f"You close {-self}.")
		for elem in self.items:
			if isinstance(elem,Core.Creature):
				elem.addStatus("hidden",-4)
		return True



# Controllers are generic Items that triggger an 'effect' upon some 'trigger' action
# triggers work as the method endpoints that run the effect ('use','touch','press',etc)
# the effect is a string that is executed when the trigger is called
class Controller(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,effect,triggers=None,
	**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.triggers = triggers if triggers else ["use"]
		self.effect = effect
		for trigger in self.triggers:
			f = lambda *args: self.Trigger(*args)
			setattr(self,trigger,f)


	### File I/O ###

	# don't save triggers functions to json
	def convertToJSON(self):
		jsonDict = super().convertToJSON()
		for trigger in self.triggers:
			del jsonDict[trigger]
		return jsonDict


	### Operation ###

	# triggers some effect using the effect string to call related function
	def Trigger(self,*args):
		exec(self.effect)



# Food heals the eater when consumed, then is removed from inventory
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
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",
		Core.min1(self.weight//4),0,0,0,"b")



class Fountain(Core.Fixture):
	def douse():
		pass


	def imbibe(self):
		Core.Print(f"You drink from {-self.name}.")



class Generator(Controller):
	def __init__(self,name,desc,weight,durability,composition,effect,charge,cap,rate,
	cost,**kwargs):
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
	def __init__(self,name,desc,weight,durability,composition,effect,on=False,delay=1,
	fuse=None,repeats=0,maxRepeats=1,toggle=False,reset=True,**kwargs):
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
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",
		Core.min1(self.weight//4)+1,2,0,0,"b")



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
		return super().examine(self,looker)


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


	def traverse(self,traverser,dir=None,verb=None):
		if self.locked:
			if self is traverser.parent:
				traverser.Print(f"You can't get out of {-self}. It's locked!")
			else:
				traverser.Print(f"You can't get in {-self}. It is locked.")
			return True
		else:
			return Box.traverse(self,traverser,dir=dir,verb=verb)



class Mouth(Core.Item):
	def asWeapon(self):
		return Core.Weapon(self.name,self.desc,self.weight,self.durability,"",
		Core.min1(self.weight//4),0,0,4,"p")



class Plash(Core.Container):

	WATER_SIZES = {
		"droplet":       2,
		"driblet":       4,
		"small puddle":  10,
		"puddle":        20,
		"large puddle":  30,
		"pool":          50,
	}

	@classmethod
	def Spill(cls,weight=None,name=None,composition="freshwater"):
		assert name is not None or weight is not None, \
		"Provide either name or weight"

		names = list(cls.WATER_SIZES.keys())
		limits = list(cls.WATER_SIZES.values())
		if name is not None:
			i = names.index(name)
			lo = limits[i-1] + 1 if i > 0 else 1
			weight = randint(lo,limits[i])
		else:
			name = next(n for n,hi in cls.WATER_SIZES.items() if weight <= hi)
		desc = f"a {name} of {composition}"
		return cls(name,desc,weight,composition,[])


	def __init__(self,name,desc,weight,composition,items,infinite=False,occupyprep="on",
	**kwargs):
		assert composition in Data.liquids
		super().__init__(name,desc,weight,-1,composition,items,fixed=True,**kwargs)
		self.occupyprep = occupyprep
		self.infinite = infinite
		self.aliases.append(self.composition)
		if any(comp for comp in ("freshwater","mudwater","saltwater")):
			self.aliases.append("water")


	def convertToJSON(self):
		jsonDict = Core.Container.convertToJSON(self)
		del jsonDict["fixed"]
		del jsonDict["durability"]
		return jsonDict


	def assignRefs(self,parent):
		super().assignRefs(parent)
		self.floor = self.parent.floor
		self.surfaces = (self.ceiling,self.walls,self.floor)


	@Core.Container.parent.setter
	def parent(self,value):
		Core.Container.parent.fset(self,value)
		if hasattr(value,'floor'):
			self.floor = value.floor
		else:
			self.floor = None
		if not hasattr(self,"ceiling"):
			self.ceiling = None
		if not hasattr(self,"walls"):
			self.walls = None
		self.surfaces = (self.ceiling,self.walls,self.floor)


	def canAdd(self,I,force=False):
		if I in (self,self.parent,None) or I in self.objTree():
			Core.Print("CANT ADD TO PLASH, OBJTREE")
			return False
		if I.hasStatus("waterwalking") and not force:
			Core.Print("CANT ADD TO PLASH, WATERWALKING")
			return False
		selfDensity = Data.densities.get(self.composition,1)
		itemDensity = Data.densities.get(I.composition,1)
		if itemDensity < selfDensity and not force:
			Core.Print("CANT ADD TO PLASH, DENSITY")
			return False
		# TODO: check if boat or buoyant?
		# if isinstance(I,Boat):
		# 	return False
		# case where Plash has infinite capacity. Imagine an endless puddle
		if self.Capacity() == -1:
			return True
		# case where Plash has nothing in it and not too small. Imagine a shallow puddle
		if len(self.items) == 0 and self.Size() >= I.Size() // 5 and self.Capacity() > 1:
			return True
		# case where Plash is full
		if self.itemsSize() + I.Size() > self.Capacity():
			Core.Print("CANT ADD TO PLASH, CAPACITY")
			return False
		return True


	def canSubmerse(self,creature):
		if creature.Size() < self.Capacity() // 2 or self.Capacity() == -1:
			return self.composition
		if self.parent.canSubmerse(creature):
			return self.parent.canSubmerse(creature)
		return None


	# return self.items. Don't include surfaces, because a plash's surface belong to 
	# its parent. having an obj's parent in its objTree would cause recursion problems
	def contents(self):
		cts = self.items
		return cts


	def consume(self,eater):
		return self.imbibe(eater)


	def disoccupy(self,occupant):
		if occupant not in self.occupants:
			return False
		super().disoccupy(occupant)
		self.replaceStatus(("wet",-4),("wet",21))


	def drain(self,quantity):
		assert quantity >= 0
		self.weight -= quantity
		# if Plash has a point at which it is infinite, then only lower to that 
		if self.infinite:
			self.weight = Core.minm(self.weight,self.infinite)
		else:
			self.weight = Core.min0(self.weight)

		if self.weight <= 0:
			for item in self.items:
				self.remove(item)
				if self.parent.canAdd(item):
					self.parent.add(item)
				else:
					item.displace()
			return self.destroy()

		for item in self.items:
			item.checkSubmersion()
		self.checkCapacity()


	# try to enter the Container, applying any relevant status effects
	def enter(self,traverser):
		if traverser in self:
			return False
		if self.Capacity() == -1 or self.Capacity() > self.Size():
			traverser.waitInput("It's deeper than it looks!")
		if super().enter(traverser):
			traverser.addStatus("wet",-4,stackable=True)
			traverser.checkSubmersion()
			return True
		return False


	# try to exit the Container, removing any relevant status effects
	def exit(self,traverser):
		Core.Print(f"REMOVING {traverser} FROM {self}")
		if traverser not in self:
			return False
		Core.Print("CALLING PLASH SUPER")
		return super().exit(traverser)


	def fill(self,quantity):
		assert quantity >= 0
		overflow = 0

		# store first because this will change after adding weight or overflowing
		parentVacancy = self.parent.vacancy() if self.parent else -1
		if quantity > parentVacancy and parentVacancy != -1:
			overflow = quantity - parentVacancy
			quantity = parentVacancy

		self.weight += quantity
		if overflow:
			Core.Print(f"{self.parent} overflows!")
			self.parent.add(self.Spill(weight=overflow))

		# astute readers will notice that the lines above would cause self.parent to become
		# full beyond capacity when you consider all of self's sibling objects;
		# so as self grows, randomly engulf siblings, the smaller the more likely to engulf
		# the more vacant space in self.parent, the less likely to engulf anything
		# note that when there is no vacancy left, we will definitely engulf something
		spaceToEngulf = quantity
		while spaceToEngulf > 0:
			vacancy = self.parent.vacancy() if self.parent else -1
			vacancy = self.Size() if vacancy == -1 else max(vacancy,0)

			# list must be recomputed every loop; engulfing one item may affect others
			parentItems = [None] + [i for i in self.parent.items if i is not self]
			if len(parentItems) <= 1:
				break
			engulfLikelihood = [vacancy] + [self.Size()//i.Size() for i in parentItems[1:]]
			engulfed = choices(parentItems,engulfLikelihood)[0]

			canAddAny = any(self.canAdd(i) for i in parentItems[1:])
			Core.Print("ENGULFING?", canAddAny, spaceToEngulf, engulfed, engulfed.Size() if engulfed else None)
			spaceToEngulf -= engulfed.Size() if engulfed else vacancy
			if engulfed and self.canAdd(engulfed):
				self.parent.remove(engulfed)
				self.add(engulfed)
				engulfed.checkSubmersion()
			# if we can't engulf any (for some reason), we must eject or destroy them
			elif engulfed and not canAddAny and getattr(self.parent,"closed",True):
				engulfed.destroy()
			elif engulfed and not canAddAny:
				engulfed.displace(self.parent)

		assert self.parent.vacancy == -1 or self.parent.vacancy() >= 0, \
		f"{+self.parent} has negative vacancy after filling {+self} with {quantity}."


	def imbibe(self,drinker):
		Core.Print(f"You drink from {-self}.")
		self.taste(drinker)

		if not self.infinite:
			self.weight -= 3	
		if self.weight <= 0:
			self.Print(f"{+self} becomes empty.")
			return self.destroy()


	def merge(self,other):
		if other.composition != self.composition:
			return False
		if other.weight > self.weight:
			return self.replace(other.merge(self))

		# self.infinite = other.infinite
		if other.Capacity() == -1:
			self.capacity = -1
		elif self.Capacity() != -1:
			self.capacity = self.Capacity() + other.Capacity()
		self.weight += other.weight

		if not self.floor and other.floor:
			self.floor = other.floor
		if not self.walls and other.walls:
			self.walls = other.walls
		if not self.ceiling and other.ceiling:
			self.ceiling = other.ceiling
		self.surfaces = (self.ceiling,self.walls,self.floor)
		self.aliases = list(set(self.aliases + other.aliases))

		for item in other.items.copy():
			other.remove(item)
			self.add(item)
		return self


	def occupy(self,occupant):
		if occupant.hasStatus("waterwalking"):
			return super().occupy(occupant)
		# if self.canAdd(occupant):
		# 	return self.add(occupant)
		return False
		# if super().occupy(occupant):
		# 	occupant.addStatus("wet",-4)
		# 	return True


	def traverse(self,traverser,dir=None,verb=None):
		traverser.Print("TRAVERSING",self,dir,verb)
		if not self.canSubmerse(traverser):
			verb = "get"
		elif not traverser.canSwim() and traverser.anchor() and \
		traverser.anchor().composition not in Data.liquids:
			verb = "wade"
		else:
			verb = "swim"
		if verb == "swim" and not self.canSubmerse(traverser):
			traverser.Print(f"You can't swim in {-self}, it's too shallow.")
			return False

		if dir in Data.directions: dir = Data.directions[dir]
		if traverser in self.occupants:
			Core.Print(f"You can't, you are {traverser.position()}.")
			return False
		if dir == None:
			if len(set(self.links.values())) == 1:
				dir = list(self.links.keys())[0]
			else:
				msg = f"Which direction on the {self.name}?"
				dir = Core.Input(msg).lower()

		if dir == "down" and traverser in self:
			if traverser.hasStatus("submerged"):
				if "down" not in self.links:
					traverser.Print(f"You are already submerged in {-self}.")
					return False
				traverser.waitInput(f"You {verb} down.")
				return traverser.changeLocation(self.getNewLocation("down"))
			return traverser.Submerge()
		if dir == "up" and traverser in self:
			if not traverser.hasStatus("submerged"):
				traverser.Print(f"You are in {-self}, but not submerged.")
				return False
			return traverser.Emerge()
		if dir in ("out",self.exitprep):
			if self is traverser.parent or traverser in self.occupants:
				if traverser in self.occupants:
					traverser.Print(f"You get off {-self}.")
				else:
					traverser.Print(f"You get out of {-self}.")
				if self.parent is not Core.game.currentroom:
					traverser.waitInput()
				self.disoccupy(traverser)
				if traverser in self:
					traverser.changeLocation(self.parent)				
				return True
			else:
				traverser.Print(f"You're not in {-self}.",color="k")
				return False

		if traverser.parent is self or traverser in self.occupants:
			if dir in ("in","on",self.passprep):
				traverser.Print(f"You're already in {-self}.")
				return False
			if dir not in self.links:
				traverser.Print(f"{+self} does not go '{dir}'.")
				return False
			if not traverser.canSwim() and traverser.posture == "floating":
				traverser.Print(f"You can't go {dir}, you aren't able to swim!")
			
			newLoc = self.getNewLocation(dir)
			traverser.waitInput(f"You {verb} {dir}.")
			return traverser.changeLocation(newLoc)

		if dir not in ("in","on","through",self.passprep):
			traverser.Print(f"{+self} does not go {dir}.",color="k")
			return False
		dir = "in"
		if traverser.hasStatus("waterwalking"):
			traverser.Print(f"You are waterwalking.")
			dir = "on"

		if dir == "on" and verb != "swim" and self.occupy(traverser):
			if verb in ("lay","sit","crouch","stand"):
				traverser.changePosture(verb,silent=True)
			traverser.Print(f"You {verb} {dir} {-self}.")
			return True

		if not self.canAdd(traverser):
			traverser.Print(f"{+self} is too small to {-traverser} to {verb} {dir}.")
			return False

		if verb in ("lay","sit","crouch","stand"):
			traverser.changePosture(verb,silent=True)
		traverser.Print(f"You {verb} {dir} {-self}.")
		traverser.changeLocation(self)
		if traverser is Core.player:
			Core.game.setPronouns(self)
		return True



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
	def __init__(self,name,desc,weight,durability,composition,effect,offEffect,on=False,
	toggle=True,**kwargs):
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
	def __init__(self,name,desc,weight,composition,links,difficulty,passprep=None,
	**kwargs):
		super().__init__(name,desc,weight,composition,links,passprep=passprep,**kwargs)
		self.difficulty = difficulty
		if passprep is None:
			self.passprep = "on" if self.getDefaultDir() in ("up","down") else "across"


	def traverse(self,traverser,dir=None,verb=None):
		if dir in Data.directions: dir = Data.directions[dir]
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
		elif traverser.hasStatus("clingfast") and dir in ("up","down"): verb = "crawl"
		elif traverser is Core.player.riding: verb = "ride"
		elif verb is None and dir in ("up","down"): verb = "climb"
		elif verb is None: verb = "jump"

		if traverser.riding:
			return self.traverse(traverser.riding,dir=dir)
		elif traverser.carrying and verb in ("climb","crawl"):
			traverser.Print(f"You can't climb, you are carrying {~traverser.carrying}.")
			return False
		if not self.canPass(traverser):
			traverser.Print(f"{+traverser} can't fit on {-self}.")
			return False

		traverser.waitInput(f"You {verb} {dir} {-self}.")

		if verb != "jump" or dir not in ("down","off") or traverser.hasAnyStatus("flying"):
			contest = Core.roll(traverser.ATHL()) - self.difficulty
			if contest > 0 or traverser.hasAnyStatus("clingfast","flying","submerged"):
				traverser.changeLocation(self.getNewLocation(dir))
				return True

		if "down" in self.links:
			traverser.fall(self.difficulty,room=self.getNewLocation("down"))
		else:
			traverser.fall(self.difficulty)
		return True


	def transfer(self,item):
		if isinstance(item,Core.Creature):
			return self.traverse(item,dir=self.getDefaultDir())

		if "down" in self.links:
			return item.fall(height=self.difficulty,room=self.links["down"])

		# item can't randomly go up
		dir = choice([dir for dir in self.links])
		if self.links[dir] == self.links.get("up",None):
			return item.fall()

		# Print(f"{+item} goes {self.passprep} {-self}.")
		item.changeLocation(self.getNewLocation(dir))


# Windows are passages that can only be opened by breaking them
# they have a view that looks at the destination when examined
class Window(Core.Passage):
	def __init__(self,name,desc,weight,composition,linkKeys,linkPort,closed=True,
	broken=False,view=None,passprep="through",**kwargs):
		links = {linkKey: linkPort for linkKey in linkKeys}
		super().__init__(name,desc,weight,composition,links,passprep=passprep,**kwargs)
		self.view = view
		if self.view is not None:
			assert self.view in self.links
		self.closed = closed
		if self.closed:
			self.passprep = "at"
		self.broken = broken


	def convertToJSON(self):
		jsonDict = Core.Passage.convertToJSON(self)
		jsonDict["linkKeys"] = list(jsonDict["links"].keys())
		jsonDict["linkPort"] = list(jsonDict["links"].values())[0]
		del jsonDict["links"]
		return jsonDict


	def canPass(self,obj,silent=False):
		if self.closed:
			if not silent:
				Core.Print(f"{+self} is closed.")
			return False
		if self.Capacity() == -1:
			return True
		return obj.totalSize() <= self.Capacity()


	# breaks the window, removes it from player inventory, and generates some shards
	def breaks(self):
		if self.id not in Core.game.itemRegistry:
			return False
		if self.broken:
			return False
		self.broken = True
		self.closed = False
		self.durability = -1
		self.passprep = "through"

		for portal in self.links.values():
			portal.breaks()

		self.printNearby(f"{+self} breaks.")
		if self.weight > 2 and self.composition == "glass":
			self.printNearby("Shards of glass scatter everywhere.",color="o")
		while self.weight > 2 and self.composition == "glass":
			shardWeight = randint(1,3)
			self.weight -= shardWeight
			shard = Shard("glass shard","a sharp shard of glass",shardWeight,-1,"glass",
			{"shard"})
			Core.game.currentroom.add(shard)
		for occupant in self.occupants.copy():
			occupant.fall(room=self.getNewLocation())
			self.disoccupy(occupant)
		if self.covering:
			self.covering.removeCover()
		return True


	def traverse(self,traverser,dir=None,verb="go"):
		if dir in Data.directions: dir = Data.directions[dir]
		if self.closed:
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
			return self.traverse(traverser.riding,dir=dir)

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
			if self.closed:
				missile.collide(self)
			else:
				Core.Print(f"{+missile} goes {self.passprep} {-self}.")
				self.transfer(missile.asItem())
			return True
		return False


	def examine(self,looker):
		if self.view:
			looker.waitInput(f"You look through it...")
			view = self.getNewLocation(self.view)
			Core.Print(f"{view.desc}")
		return True



class Door(Window):
	def __init__(self,name,desc,weight,durability,composition,links,descname,closed=True,
	**kwargs):
		super().__init__(name,desc,weight,durability,composition,links,descname,**kwargs)
		self.descname = descname
		self.closed = closed


	# sets closed to False
	def open(self,opener):
		if self.closed:
			Core.Print(f"You open {-self}.")
			self.closed = False
		else:
			Core.Print(f"{+self} is already open.")


	# sets closed to True
	def close(self,closer):
		self.closed = True
		closer.Print(f"You close {-self}.")
		for elem in self.items:
			if isinstance(elem,Core.Creature):
				elem.addStatus("hidden",-4)
		return True


factory = {
	"black hole": lambda: Core.Item("black hole","A spherical vortex of darkness.",10000,-1,"void"),
	"blue potion": lambda: Potion("blue potion", "A bubbling blue liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	"bottle": lambda: Bottle("bottle","An empty glass bottle",6,3,"glass",["glass","glass bottle"]),
	"coffee": lambda: Potion("bottle of coffee","A bottle of frothy dark brown liquid.",10,3,"glass",["coffee","espresso","bottle"],1),
	"compass": lambda: Core.Compass("compass","A plain steel compass with a red needle.",2,10,"steel",rarity=2,plural="compasses"),
	"green potion": lambda: Potion("green potion", "A bubbling green liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	"iron ingot": lambda: Core.Item("iron ingot","A solid bar of iron.",20,200,"iron",["ingot","bar","iron"]),
	"puddle": lambda: Plash("puddle","A small puddle of murky water.",randint(2,10),"water",[]),
	"red potion": lambda: Potion("red potion", "A bubbling red liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	"shard": lambda: Shard("glass shard","A small glass shard.",2,1,"glass",["shard"])
}
