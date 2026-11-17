# Items.py
# This file contains the item classes used in the game
# This file is dependent on Core.py and is a dependency of Menu.py and Interpreter.py


from bisect import insort
from random import randint, choice,choices
from pathlib import Path

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
			action = f"jump onto {-self}."
			traverser.Print(traverser*action)
			traverser.printNearby(traverser+action)
			if traverser is Core.player or traverser in Core.player.anchors():
				Core.waitInput()
			traverser.changePosture("crouch")
			self.occupy(traverser)
		if verb == None:
			verb = "lay"

		if traverser.platform is not self and self.occupy(traverser):
			displayVerb = "get in" if verb == "lay" else f"{verb} on"
			action = f"{displayVerb} {-self}."
			traverser.Print(traverser*action)
			traverser.printNearby(traverser+action)
			if traverser is Core.player or traverser in Core.player.anchors():
				Core.waitInput()
			if traverser is Core.player:
				Core.game.setPronouns(self)
		if traverser.platform is self:
			if verb in ("stand","crouch","sit","lay"):
				traverser.changePosture(verb)
			if traverser.posture() == "laying" and \
			not traverser.hasStatus("cozy",reqSource=self.id):
				traverser.addStatus("cozy",source=self.id)
		return True



# Bottles are glass vessels; they shatter via Item.shatter when they break
class Bottle(Core.Item):
	pass



# Box is a container that can be opened and closed to hide contents and prevent passage
class Box(Core.Container):
	def __init__(self,name,desc,weight,durability,composition,items,closed=False,**kwargs):
		super().__init__(name,desc,weight,durability,composition,items,**kwargs)
		self.closed = closed


	# Boxes are hollow; size tracks weight directly rather than material density
	def Size(self):
		return Core.min1(self.weight)


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
		return super().enter(traverser)


	def exit(self,traverser):
		self.closed = False
		return super().exit(traverser)


	def examine(self,looker):
		if self.closed and looker not in self.items:
			return self.open(looker)
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
				elem.removeStatus("hidden",reqSource="CONTAINER")
		for occupant in self.occupants():
			occupant.fall()
		if Core.player not in self.items and not silent:
			self.examine(opener)
		return True


	# sets closed to true
	def close(self,closer):
		self.closed = True
		closer.Print(f"You close {-self}.")
		# creatures remain visible through a transparent closed Box
		if not self.material().transparent:
			for elem in self.items:
				if isinstance(elem,Core.Creature):
					elem.addStatus("hidden",source="CONTAINER")
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
	def __init__(self,name,desc,weight,durability,composition,skeletonId=0,**kwargs):
		# Zero is an ordinary key; negative IDs identify compatible skeleton-key locks.
		assert isinstance(skeletonId,int) and skeletonId <= 0
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.skeletonId = skeletonId


	def lockWith(self,box):
		pass


	def unlockWith(self,box):
		pass



class Lockbox(Box):
	def __init__(self,name,desc,weight,durability,composition,keyids,locked,**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		# Nonnegative IDs match Key.id; negative IDs match Key.skeletonId.
		self.keyids = keyids
		self.locked = locked


	# Validate ordinary key references while reserving negative IDs for skeleton keys.
	def validate(self):
		for keyid in self.keyids:
			if not isinstance(keyid,int):
				raise ValueError(f"Lock {self} has invalid key ID {keyid}")
			if keyid >= 0 and not isinstance(Core.game.itemRegistry.get(keyid),Key):
				raise ValueError(f"Lock {self} references unknown key ID {keyid}")
		return super().validate()


	### Operation ###

	# sets open bool to true, prints its items
	def open(self,opener,silent=False):
		if self.locked:
			if not silent:
				opener.Print(f"{+self} is locked.")
			return not silent
		return Box.open(self,opener,silent=silent)


	def examine(self,looker):
		if self.locked == True and Core.player not in self.items:
			looker.Print(f"{+self} is locked.")
			return False
		return super().examine(looker)


	# Lock with either the key's object ID or its enabled skeleton ID.
	def lock(self,locker,key):
		if self.locked:
			locker.Print(f"{+self} is already locked.")
			return False
		if key.id in self.keyids or key.skeletonId and key.skeletonId in self.keyids:
			self.locked = True
			locker.Print(f"You lock {-self}.")
			if Core.hasMethod(key,"unlockWith"):
				key.unlockWith(self)
			return True
		locker.Print(f"{+key} doesn't work!")
		return True


	# Unlock with either the key's object ID or its enabled skeleton ID.
	def unlock(self,unlocker,key):
		if not self.locked:
			unlocker.Print(f"{+self} is not locked.")
			return False
		if key.id in self.keyids or key.skeletonId and key.skeletonId in self.keyids:
			self.locked = False
			unlocker.Print(f"You unlock {-self}.")
			if Core.hasMethod(key,"lockWith"):
				key.lockWith(self)
			return True
		unlocker.Print(f"{+key} doesn't work!")
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



class Plash(Core.Portal):

	LIQUID_SIZES = {
		"droplet":       1,
		"driblet":       4,
		"small puddle":  10,
		"puddle":        20,
		"large puddle":  30,
		"small pool":    50,
		"pool":          100,
		"large pool":    200,
	}

	def __init__(self,weight,name=None,desc=None,composition="freshwater",infinite=False,
	occupyprep="on",links=None,capacity=None,**kwargs):
		assert Data.Material.get(composition).liquid
		if name is None:
			name = composition
		if desc is None:
			desc = f"Some {composition}." if name == composition else \
				f"A {name} of {composition}."
		super().__init__(name,desc,weight,-1,composition,links or {},
			capacity=capacity,passprep="in",fixed=True,**kwargs)
		self.occupyprep = occupyprep
		self.exitprep = "out"
		self.infinite = infinite
		self.aliases.append(self.composition)
		if self.composition in ("freshwater","mudwater","saltwater"):
			self.aliases.append("water")
		self.updateAliases()


	@property
	def floor(self):
		parentFloor = getattr(self.parent,"floor",None)
		return parentFloor if self.platform is parentFloor else None


	def convertToJSON(self,portalLinkIds=None):
		jsonDict = Core.Portal.convertToJSON(self,portalLinkIds)
		del jsonDict["fixed"]
		del jsonDict["durability"]
		del jsonDict["passprep"]
		del jsonDict["exitprep"]
		return jsonDict


	def validate(self):
		if isinstance(self.parent,Core.Room) and \
		self in self.parent.permanents and not self.infinite:
			raise ValueError(f"Permanent Plash {self} must be infinite")
		reservedDirs = {"in","on","out","through",self.passprep,self.exitprep}
		for direction in self.links:
			if direction in reservedDirs:
				raise ValueError(f"Plash {self} has reserved link direction {direction}")
		for obj in self.immersedObjects():
			if not self.canImmerse(obj):
				raise ValueError(f"Plash {self} cannot immerse {obj}")
		return super().validate()


	def Spill(self,weight=None,size=None):
		assert weight is not None or size is not None
		minimumWeight = self.infinite if self.infinite else 0
		if size is not None:
			assert size > 0
			targetSize = max(self.minimumSize(),self.Size()-size)
			targetWeight = minimumWeight if targetSize == 0 else \
				max(minimumWeight,self.maxWeightAtSize(targetSize))
			weight = self.weight - targetWeight

		assert weight > 0 and weight <= self.weight-minimumWeight
		if self.parent is not None:
			self.printNearby(f"{+self.parent} overflows with {self.composition}!")
			carrier = next((ancestor for ancestor in self.ancestors() \
				if isinstance(ancestor,Core.Creature)),None)
			if carrier is not None and \
			not carrier.hasStatus("wet",reqSource="IMMERSED") and \
			not carrier.hasStatus("wet",reqSource="SUBMERGED"):
				carrier.addStatus("wet",dur=21)
		composition = self.composition
		self.drain(weight)
		return Plash(weight,composition=composition)


	# amount of space plash has for immersing other objects
	# increase immersion allowance as the Plash's parent becomes more crowded
	# very low parent vacancy makes the plash contact others more easily
	# very high parent capacity makes the plash less sensitive to parent vacancy
	def immersionSpace(self,size=None,vacancy=None):
		size = self.Size() if size is None else size
		vacancy = self.parent.vacancy() if vacancy is None and self.parent else vacancy
		if self.parent is None or vacancy == -1:
			return size
		return self.parent.Capacity() * size // (size + vacancy)


	# return the whole percentage of a finite parent occupied by this Plash
	def fillPercent(self):
		if self.parent is None or self.parent.Capacity() == -1:
			return 0
		return 100 * self.Size() // self.parent.Capacity()


	# return whether this Plash can currently immerse a sibling object
	def canImmerse(self,obj):
		if obj is self:
			return False
		if obj.parent is not self.parent:
			return False
		return self.couldImmerse(obj)


	# return whether projected liquid size and parent vacancy could immerse obj
	def couldImmerse(self,obj,size=None,vacancy=None):
		if obj is self:
			return False
		size = self.Size() if size is None else size
		otherImmersed = [other for other in self.immersedObjects() if other is not obj]
		# plash can usually immerse at least one object even when theres little space available
		if not otherImmersed:
			return size >= obj.Size() // 10
		# if there are already immersed objects, check if adding obj would exceed immersion space
		return self.immersedSize(exclude=obj) + obj.Size() <= \
			self.immersionSpace(size=size,vacancy=vacancy)


	def canSubmerge(self,creature):
		deepEnough = self.Capacity() == -1 or \
			creature.Size() < self.Capacity() // 2
		return deepEnough or self.parent.canSubmerge(creature)


	def canEmerge(self,obj):
		if self.parent is None:
			return True
		if not self.canSubmerge(obj):
			return True
		if self.parent.vacancy() == -1:
			return True
		return self.parent.vacancy() > obj.Size() // 5


	# Replace aliases derived from quantity while preserving authored aliases.
	def updateAliases(self):
		sizeNames = set(self.LIQUID_SIZES)
		sizeWords = {name.split()[-1] for name in sizeNames}
		sizeAliases = sizeNames | \
			{f"{name} of {self.composition}" for name in sizeNames} | sizeWords
		# remove old size-based aliases
		self.aliases = [alias for alias in self.aliases if alias not in sizeAliases]
		# determine sizeName based on self weight
		sizeName = next((name for name,limit in self.LIQUID_SIZES.items() \
			if self.weight <= limit),list(self.LIQUID_SIZES)[-1])
		self.aliases.extend((sizeName,f"{sizeName} of {self.composition}",
			sizeName.split()[-1]))


	# return sibling objects currently immersed in this Plash
	def immersedObjects(self):
		if self.parent is None:
			return []
		objects = self.parent.spatialContents()
		objects = [obj for obj in objects if getattr(obj,"immersed",None) is self]
		return sorted(objects,key=lambda obj:obj.Size(),reverse=True)


	# Surface occupants are described by describeImmersed(), not inline with the Plash.
	def nounPhrase(self,det="",n=-1,plural=False,cap=0,includePosture=False):
		inContainer = isinstance(self.parent,Core.Container)
		sizeName = next((name for name,limit in self.LIQUID_SIZES.items() \
			if self.weight <= limit),list(self.LIQUID_SIZES)[-1])
		usesSizeName = inContainer or self.name == self.composition or \
			self.name in self.LIQUID_SIZES

		if det.lower() == "the":
			phrase = f"the {self.name}"
		elif inContainer and self.fillPercent() >= 10:
			phrase = f"some {self.name}" if det == "a" or n >= 1 else self.name
		elif usesSizeName:
			if n > 1:
				phrase = f"{n} {sizeName}s of {self.composition}"
			elif plural:
				phrase = f"{sizeName}s of {self.composition}"
			elif det == "a" or n == 1:
				phrase = f"a {sizeName} of {self.composition}"
			else:
				phrase = f"{sizeName} of {self.composition}"
		else:
			phrase = Core.GameObject.nounPhrase(self,det=det,n=n,plural=plural,
				includePosture=includePosture)
		if cap > 0:
			phrase = Core.capWords(phrase,c=cap)
		return phrase


	# describe visible objects whose spatial relationship is owned by this liquid
	def describeImmersed(self):
		def describeGroup(prefix,objects,includePosture=False):
			if not objects:
				return False
			if len(objects) > 3:
				Core.Print(f"There are many things {prefix.lower()}.")
				return True
			verb = "is" if len(objects) == 1 else "are"
			Core.Print(Core.listObjects(f"{prefix} {verb} ",objects,".",
				includePosture=includePosture))
			return True

		immersed = [obj for obj in self.immersedObjects() \
			if not obj.hasStatus("submerged")]
		# Dependents appear recursively in their anchor's noun phrase.
		roots = [obj for obj in immersed if obj.anchor() not in immersed]
		floating = [obj for obj in roots if obj.anchor() is None]
		anchored = [obj for obj in roots if obj.anchor() is not None]
		surface = [obj for obj in self.occupants() \
			if not obj.hasStatus("submerged")]
		reference = -self

		described = describeGroup(f"Floating in {reference}",floating)
		described = describeGroup(f"In {reference}",anchored,
			includePosture=True) or described
		surfaceReference = reference + ("'" if reference.endswith("s") else "'s")
		described = describeGroup(f"On {surfaceReference} surface",surface) or described
		if described:
			Core.describeCarrying(floating+anchored+surface)
		return described


	# reveal objects on the opposite side of the surface from the looker
	def examine(self,looker):
		belowSurface = looker.immersed is self and looker.hasStatus("submerged")
		immersed = self.immersedObjects()
		if belowSurface:
			visible = [obj for obj in immersed if not obj.hasStatus("submerged")]
			visible += self.occupants()
			direction = "Above"
		else:
			visible = [obj for obj in immersed if obj.hasStatus("submerged")]
			direction = "Under"
		roots = [obj for obj in visible if obj is not looker and \
			obj.anchor() not in visible]
		if not roots:
			return False
		verb = "appears" if len(roots) == 1 else "appear"
		looker.Print(Core.listObjects(
			f"{direction} the surface, there {verb} to be ",roots,"."))
		Core.describeCarrying(roots)
		return True


	# sum of sizes of immersed objects
	def immersedSize(self,exclude=None):
		return sum(obj.Size() for obj in self.immersedObjects() if obj is not exclude)


	# finite Plashes can be fully spilled; infinite ones retain their threshold size
	def minimumSize(self):
		if not self.infinite:
			return 0
		return Core.min1(self.infinite // self.density())


	def consume(self,eater):
		return self.imbibe(eater)


	def disoccupy(self,occupant):
		if occupant not in self.occupants():
			return False
		removed = super().disoccupy(occupant)
		self.transferStatus("wet","IMMERSED",None,21)
		return removed


	def destroy(self,silent=True):
		for obj in self.immersedObjects().copy():
			obj.unimmerse(silent=silent)
		return super().destroy(silent=silent)


	def drain(self,quantity):
		assert quantity >= 0
		self.weight -= quantity
		# if Plash has a point at which it is infinite, then only lower to that 
		if self.infinite:
			self.weight = max(self.weight,self.infinite)
		else:
			self.weight = Core.min0(self.weight)

		if self.weight <= 0:
			return self.destroy()
		self.updateAliases()

		for obj in self.immersedObjects().copy():
			obj.checkImmersion()


	# infinite plashes tend toward their threshold mass
	# finite plashes in a Room soak away after their despawn timer expires
	def passTime(self,t):
		assert not (self.infinite and self.despawnTimer is not None), \
			f"Infinite Plash {self} cannot have a despawnTimer"
		super().passTime(t)
		if self.infinite:
			if self.weight < self.infinite:
				self.fill(1)
			elif self.weight > self.infinite:
				self.drain(1)
			return
		if self.despawnTimer is not None and self.despawnTimer <= 0 and \
		isinstance(self.parent,Core.Room):
			self.drain(1)


	# a Plash lingers for as many moments as its weight when it lands in a Room
	def timeDespawn(self):
		self.despawnTimer = None if self.infinite else self.weight


	# immerse the traverser in this Plash
	def enter(self,traverser,verb=None):
		if traverser.parent is not self.parent:
			if self.parent in traverser.ancestors():
				traverser.Print(f"You need to get out of {-traverser.parent} first.")
			else:
				traverser.Print(f"You need to be in {-self.parent} first.")
			return False
		anchor = traverser.anchor()
		floor = getattr(self.parent,"floor",None)
		if anchor not in (None,floor):
			traverser.Print(f"You need to get off {-anchor} first.")
			return False
		requiredFluid = self.parent.requiredImmersion(traverser)
		if requiredFluid is not None and requiredFluid is not self:
			traverser.Print(f"There isn't enough space to get out of {-requiredFluid}.")
			return False
		if not self.canImmerse(traverser):
			traverser.Print(f"There isn't enough room in {-self}.")
			return False
		if self.Capacity() == -1 or self.Capacity() > self.Size():
			traverser.waitInput("It's deeper than it looks!")
		if self.canSubmerge(traverser) and \
		traverser.platform is getattr(self.parent,"floor",None):
			traverser.removePlatform()
		if verb is not None:
			action = "get" if traverser.anchor() is None and \
				verb in ("lay","sit","crouch","stand") else verb
			traverser.Print(traverser*f"{action} in {-self}.")
			traverser.printNearby(traverser+f"{action} in {-self}.")
			if traverser is Core.player or traverser in Core.player.anchors():
				Core.waitInput()
		return traverser.immerse(self)


	# remove the traverser from this Plash
	def exit(self,traverser):
		if traverser.immersed is not self:
			return False
		requiredFluid = self.parent.requiredImmersion(traverser)
		if requiredFluid is not None:
			traverser.Print(f"There isn't enough space to get out of {-requiredFluid}.")
			return False
		traverser.unimmerse()
		if traverser.anchor() is None:
			traverser.platform = traverser.floorSupport()
		return True


	# probabilistically immerse siblings overtaken by added liquid
	def engulf(self,quantity):
		spaceToEngulf = quantity
		while spaceToEngulf > 0:
			vacancy = self.parent.vacancy() if self.parent else -1
			vacancy = self.Size() if vacancy == -1 else vacancy
			floor = getattr(self.parent,"floor",None)
			objects = [obj for obj in self.parent.spatialContents() \
				if obj is not self and obj.anchor() in (None,floor)]
			objsToEngulf = [obj for obj in objects if obj.immersed is None and \
			self.canImmerse(obj)]
			grounded = [obj for obj in objsToEngulf if not obj.hasStatus("flying")]

			# engulf non flying objects first, only engulf flying objects if necessary
			if grounded:
				objsToEngulf = grounded
			elif vacancy > 0:
				break
			if not objsToEngulf:
				break

			# choose to engulf an object or not randomly based on size
			weights = [vacancy] + \
				[max(1,self.Size()//obj.Size()) for obj in objsToEngulf]
			engulfed = choices([None] + objsToEngulf,weights)[0]
			spaceToEngulf -= engulfed.Size() if engulfed else vacancy
			if engulfed:
				engulfed.immerse(self)


	def fill(self,quantity):
		assert quantity >= 0
		overflow = 0
		oldSize = self.Size()
		parentVacancy = self.parent.vacancy() if self.parent else -1
		if parentVacancy != -1:
			maxSize = oldSize + Core.min0(parentVacancy)
			# reverse of the floor division from weight to size
			maxWeight = self.maxWeightAtSize(maxSize)
			overflow = Core.min0(self.weight + quantity - maxWeight)
			quantity -= overflow

		self.weight += quantity
		self.updateAliases()
		quantitySize = self.Size() - oldSize
		if overflow:
			self.printNearby(f"{self.parent} overflows!")
			self.parent.spawn(Plash(overflow,composition=self.composition))

		# check if objects are immersed or unimmersed by the fill
		if quantitySize:
			objects = self.parent.spatialContents().copy() if self.parent else []
			for obj in objects:
				if obj is self:
					continue
				obj.checkImmersion()
			self.engulf(quantitySize)
		self.checkSize()


	def imbibe(self,drinker):
		Core.Print(f"You drink from {-self}.")
		self.taste(drinker)

		if not self.infinite:
			self.drain(3)


	def destroy(self,silent=True):
		for obj in self.immersedObjects().copy():
			obj.unimmerse()
		return super().destroy(silent=silent)


	def merge(self,other):
		return False
		if not isinstance(other,Plash):
			return False
		if other.composition != self.composition:
			return False
		if self.links or other.links:
			return False
		if other.weight > self.weight:
			return self.replace(other.merge(self))

		otherImmersed = other.immersedObjects().copy()
		if other.Capacity() == -1:
			self.capacity = -1
		elif self.capacity is not None and self.Capacity() != -1:
			self.capacity = self.Capacity() + other.Capacity()
		self.weight += other.weight
		self.updateAliases()
		self.infinite = self.infinite or other.infinite
		self.aliases = list(set(self.aliases + other.aliases))

		for obj in otherImmersed:
			obj.unimmerse()
			obj.immerse(self)
		return self


	def occupy(self,occupant,silent=False,actor=None):
		if occupant.hasStatus("waterwalking"):
			return Core.Item.occupy(self,occupant,silent=silent,actor=actor)
		return False


	# move to a specific parent and fluid while preserving compatible submersion
	def transferImmersed(self,traverser,destinationParent,destinationFluid):
		if not self.canPass(traverser):
			return False
		if destinationFluid is not destinationParent and \
		destinationFluid.parent is not destinationParent:
			return False
		if isinstance(traverser,Core.Creature):
			if not traverser.canChangeLocation(destinationParent,silent=True):
				return False
		elif not destinationParent.canAdd(traverser):
			return False
		if not destinationFluid.couldImmerse(traverser):
			return False

		with Core.game.deferStatusReports():
			isCreature = isinstance(traverser,Core.Creature)
			wasSubmerged = isCreature and traverser.hasStatus("submerged")
			changedLocation = traverser.changeLocation(destinationParent)
			if not changedLocation:
				return False
			if traverser.immersed is not destinationFluid and \
			destinationFluid.canImmerse(traverser):
				traverser.immerse(destinationFluid)
			if wasSubmerged and traverser.immersed is not None and \
			traverser.immersed.canSubmerge(traverser):
				if not traverser.hasStatus("submerged"):
					traverser.addStatus("submerged",source="IMMERSED",
						silent=True)
			return True


	def traverse(self,traverser,dir=None,verb=None):
		if traverser.riding:
			return self.traverse(traverser.riding,dir=dir,verb=verb)
		if dir in Data.directions: dir = Data.directions[dir]
		# store if already immersed in this object
		immersed = traverser.immersed is self
		if traverser.hasStatus("waterwalking") and not immersed and \
		(verb == "swim" or dir in self.links):
			traverser.Print("You can't swim while waterwalking.")
			return False
		if immersed and dir is None:
			if not self.links:
				dir = self.exitprep
			else:
				validDirs = set(self.links) | {self.exitprep}
				acceptKey = lambda inp: Core.expandDir(inp) \
					if Core.expandDir(inp) in validDirs else None
				dir = Core.InputLoop(f"Which direction will you go in {-self}?",
					acceptKey=acceptKey,
					refuseMsg=f"{+self} does not go that way.")
				if dir is None:
					return False

		# determine verb based on depth of liquid and swimming ability
		if verb is None:
			floorSupported = traverser.platform is getattr(self.parent,"floor",None)
			if not self.canSubmerge(traverser) and floorSupported:
				verb = "wade" if self.Capacity() > traverser.Size() else "stand"
			elif traverser.canSwim(self):
				verb = "swim"
			else:
				verb = "get"

		# submerging when already immersed
		if immersed and dir == "down":
			if not traverser.hasStatus("submerged"):
				return traverser.Submerge()
			if "down" not in self.links:
				traverser.Print(f"You are already submerged in {-self}.")
				return False

		# emerging when submerged
		if immersed and dir == "up":
			if traverser.hasStatus("submerged"):
				return traverser.Emerge()

		if immersed and dir in ("out",self.exitprep):
			action = f"get out of {-self}."
			traverser.Print(traverser*action)
			traverser.printNearby(traverser+action)
			return self.exit(traverser)

		if immersed and dir in self.links:
			if not traverser.canSwim(self):
				traverser.Print(f"You can't go {dir}, you aren't able to swim!")
				return False
			if not self.canPass(traverser):
				traverser.Print(f"You can't {verb} {dir}. {-self} is too shallow.")
				return False
			newLoc = self.getNewLocation(dir)
			if not traverser.canChangeLocation(newLoc):
				return False
			destination = self.links[dir]
			if not destination.couldImmerse(traverser):
				traverser.Print(f"You can't {verb} {dir}. There isn't enough {self.composition} that way.")
				return False
			action = f"{verb} {dir} through {-self}."
			traverser.Print(traverser*action)
			traverser.printNearby(traverser+action)
			if traverser is Core.player or traverser in Core.player.anchors():
				Core.waitInput()
			return self.transferImmersed(traverser,newLoc,destination)

		if immersed and dir in ("in","on","through",self.passprep):
			anchor = traverser.anchor()
			floor = getattr(self.parent,"floor",None)
			support = "" if anchor in (None,floor) else f" on {-anchor}"
			traverser.Print(f"You're already in {-self}{support}.")
			return False
		if immersed:
			traverser.Print(f"{+self} does not go {dir}.",color="k")
			return False
		if dir in self.links or dir in ("out",self.exitprep):
			traverser.Print(f"You're not in {-self}.",color="k")
			return False

		if dir not in ("in","on","through",self.passprep,None):
			traverser.Print(f"{+self} does not go {dir}.",color="k")
			return False
		dir = "in"
		if traverser.hasStatus("waterwalking"):
			traverser.Print(f"You are waterwalking.")
			dir = "on"

		if dir == "on" and verb != "swim" and self.occupy(traverser):
			if verb in ("lay","sit","crouch","stand"):
				traverser.changePosture(verb,silent=True)
			action = f"{verb} {dir} {-self}."
			traverser.Print(traverser*action)
			traverser.printNearby(traverser+action)
			if traverser is Core.player or traverser in Core.player.anchors():
				Core.waitInput()
			return True

		if not self.enter(traverser,verb=verb):
			return False

		if traverser.anchor() is not None and \
		verb in ("lay","sit","crouch","stand"):
			traverser.changePosture(verb,silent=True)
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

	def pour(self,obj=None):
		if obj is not None:
			if Core.hasMethod(obj,"drench"):
				obj.drench(self)
		self.replace("bottle")



class Sign(Core.Item):
	def __init__(self,name,desc,weight,durability,composition,text,**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.text = text


	# prints the text on the sign in single quotes
	def examine(self,looker):
		looker.Print(f"\n'{self.text}'",color='y')



class Painting(Sign):
	def __init__(self,name,desc,weight,durability,composition,filepath,**kwargs):
		kwargs.pop("text",None)
		artworkPath = Path(__file__).resolve().parent.parent / "gamedata" / "artwork"
		with open(artworkPath / filepath,"r",encoding="utf-8") as artworkFile:
			text = artworkFile.read()
		super().__init__(name,desc,weight,durability,composition,text,**kwargs)
		self.filepath = filepath


	def convertToJSON(self):
		jsonDict = super().convertToJSON()
		del jsonDict["text"]
		return jsonDict


	def examine(self,looker):
		Core.waitInput()
		Core.clearScreen()
		looker.Print(self.text,delay=0)
		Core.waitInput()
		Core.clearScreen()



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
		elif traverser.carrying() and verb in ("climb","crawl"):
			traverser.Print(Core.listObjects("You can't climb, you are carrying ",
			traverser.carrying(),"."))
			return False
		if not self.canPass(traverser):
			msg = f"{+traverser} can't fit on {-self}."
			traverser.Print(msg)
			if traverser in Core.player.anchors():
				traverser.printNearby(msg)
			return False
		newLoc = self.getNewLocation(dir)
		if not traverser.canChangeLocation(newLoc):
			return False

		action = f"{verb} {dir} {-self}."
		traverser.Print(traverser*action)
		traverser.printNearby(traverser+action)
		if traverser is Core.player or traverser in Core.player.anchors():
			Core.waitInput()

		if verb != "jump" or dir not in ("down","off") or traverser.hasStatus("flying"):
			contest = Core.roll(traverser.ATHL()) - self.difficulty
			if contest > 0 or traverser.hasStatus(("clingfast","flying","submerged")):
				traverser.changeLocation(newLoc)
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


	def convertToJSON(self,portalLinkIds=None):
		jsonDict = Core.Passage.convertToJSON(self,portalLinkIds)
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
			shard = Core.Shard("glass",shardWeight)
			Core.game.spawn(shard,Core.game.currentroom)
		for occupant in self.occupants():
			occupant.fall(room=self.getNewLocation())
			self.disoccupy(occupant)
		self.clearCovering()
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
			msg = f"{+traverser} can't fit through {-self}."
			traverser.Print(msg)
			if traverser in Core.player.anchors():
				traverser.printNearby(msg)
			return False

		newloc = self.getNewLocation(dir)
		if not traverser.canChangeLocation(newloc):
			return False
		if traverser.hasStatus("flying"): verb = "fly"
		elif traverser is Core.player.riding: verb = "ride"
		action = f"{verb} {dir} {-self}."
		traverser.Print(traverser*action)
		traverser.printNearby(traverser+action)
		if traverser is Core.player or traverser in Core.player.anchors():
			Core.waitInput()
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
		return True


factory = {
	"black hole": lambda: Core.Item("black hole","A spherical vortex of darkness.",10000,-1,"void"),
	"blue potion": lambda: Potion("blue potion", "A bubbling blue liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	"bottle": lambda: Bottle("bottle","An empty glass bottle",6,3,"glass",["glass","glass bottle"]),
	"coffee": lambda: Potion("bottle of coffee","A bottle of frothy dark brown liquid.",10,3,"glass",["coffee","espresso","bottle"],1),
	"compass": lambda: Core.Compass("compass","A plain steel compass with a red needle.",2,10,"steel",rarity=2,plural="compasses"),
	"green potion": lambda: Potion("green potion", "A bubbling green liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	"iron ingot": lambda: Core.Item("iron ingot","A solid bar of iron.",20,200,"iron",["ingot","bar","iron"]),
	"puddle": lambda: Plash(randint(2,10),name="puddle",
		desc="A small puddle of murky water.",composition="water"),
	"red potion": lambda: Potion("red potion", "A bubbling red liquid in a glass bottle.",10,3,"glass",["bottle","glass","potion"],2),
	"shard": lambda: Core.Shard("glass",2)
}
