# Effects.py
# This file contains all the functions which represent some "effect" in the game
# This file is dependent on Menu.py and is a dependency of PoPy.py

import Creatures
import Items
import Core
import Data




#######################
#####################
##  EFFECT HELPERS ##
#####################

# resolve an effect argument that may reference a game object:
# an object passes through unchanged, an int is looked up as an object ID,
# and a missing/unknown ID yields None (the effect should fizzle gracefully)
def resolveObj(x):
	if isinstance(x,int):
		return Core.game.itemRegistry.get(x)
	return x


# resolve an effect argument that should yield a Room:
# a Room passes through, a str is looked up as a room name, and any other
# object yields the room that ultimately contains it (None if unrooted)
def resolveRoom(x):
	if isinstance(x,Core.Room):
		return x
	if isinstance(x,str):
		return Core.world.get(x)
	if x is None:
		return None
	room = x.ancestors()[-1] if x.ancestors() else None
	return room if isinstance(room,Core.Room) else None


# normalize authored effect descriptors to a canonical tuple of descriptors:
# a bare descriptor (lone eval string or single (name, *args) sequence) is
# wrapped; an eval string may not appear inside a collection
def wrapEffectDescriptors(descriptors):
	if isinstance(descriptors,str):
		return (descriptors,)
	if isinstance(descriptors,(tuple,list)) and descriptors and \
	isinstance(descriptors[0],str):
		return (tuple(descriptors),)
	assert all(not isinstance(d,str) for d in descriptors), \
		"eval strings must be authored alone, not inside collections"
	return tuple(tuple(d) for d in descriptors)


def applyAreaEffect(effect,root,condfunc=lambda x:True):
	objs = Core.objQuery(root,key=condfunc,d=3)
	for obj in objs:
		effect(obj)


def spawnObject(obj,parent=None,silent=False):
	if parent is None:
		parent = Core.game.currentroom
	obj = Core.game.spawn(obj,parent)

	if not obj:
		Core.Print("It failed...")
		return False
	if not Core.game.silent and not silent:
		obj.printNearby(f"{obj.nounPhrase('a',cap=1)} appeared!")
		Core.game.setPronouns(obj)
	return obj


def destroyObject(obj):
	obj.destroy(silent=True)
	if not Core.game.silent:
		Core.Print(f"{-obj} was destroyed.")



#######################
## EFFECT PRIMITIVES ##
#######################

# primitives all share the same context prefix:
# actor = who is responsible, source = the object carrying the effect,
# target = what the effect acts on; remaining args are authored
# target resolution: an authored ref wins (fizzle if it resolves to nothing),
# else the runtime target, else the primitive's own fallback:
# creature effects -> actor, area -> source.parent, room -> source.room()


# convert an effect call's source into the entry's recorded source:
# None stays None (no identifiable carrier), a cause-code string or bare id
# passes through, and a game object contributes its id
def originId(source):
	if source is None or isinstance(source,(int,str)):
		return source
	return source.id


# add a status to a room itself: the authored room name if given, else the
# target if it is a Room, else the room containing the source; fizzles if no
# room resolves. Distinct from areaStatus, which stamps current occupants
def addRoomStatus(actor,source,target,name,duration=None,room=None):
	if room is not None:
		room = resolveRoom(room)
	elif isinstance(target,Core.Room):
		room = target
	else:
		room = resolveRoom(source)
	if room is None:
		return False
	return room.addStatus(name,originId(source),duration)


# add a status to every creature in the target area (or the area
# surrounding the source)
def areaCreatureStatus(actor,source,target,name,duration=None):
	area = target if target is not None else \
		(source.parent if source is not None else None)
	if area is None:
		return False
	srcId = originId(source)
	applyAreaEffect(lambda obj: obj.addStatus(name,srcId,duration),area,
		condfunc=lambda obj: isinstance(obj,Core.Creature))
	return True


# damage everything in the target area (or the area surrounding the source)
def areaDamage(actor,source,target,amount,dmgtype):
	area = target if target is not None else \
		(source.parent if source is not None else None)
	if area is None:
		return False
	applyAreaEffect(lambda obj: obj.takeDamage(amount,dmgtype),area)
	return True


# add a status to every item (excluding creatures) in the target area (or
# the area surrounding the source)
def areaItemStatus(actor,source,target,name,duration=None):
	area = target if target is not None else \
		(source.parent if source is not None else None)
	if area is None:
		return False
	srcId = originId(source)
	applyAreaEffect(lambda obj: obj.addStatus(name,srcId,duration),area,
		condfunc=lambda obj: not isinstance(obj,Core.Creature))
	return True


# add a status to every object in the target area (or the area
# surrounding the source)
def areaStatus(actor,source,target,name,duration=None):
	area = target if target is not None else \
		(source.parent if source is not None else None)
	if area is None:
		return False
	srcId = originId(source)
	applyAreaEffect(lambda obj: obj.addStatus(name,srcId,duration),area)
	return True


# wake the target (actor if none) from sleep; wellRested if sleep completed
def awaken(actor,source,target,wellRested=False):
	if target is None:
		target = actor
	if Core.hasMethod(target,"awaken"):
		target.awaken(wellRested=wellRested)
	return True


# bind a status to the target (actor if none): stripped by the derived
# inverse when the source departs/dies (idempotent: re-binding refreshes)
# returns whether the binding is in effect after the call
def bindStatus(actor,source,target,name,duration=None):
	if target is None:
		target = actor
	srcId = originId(source)
	target.addStatus(name,srcId,duration)
	return target.getStatusEntry(name,srcId) is not None


def damage(actor,source,target,amount,dmgtype):
	if target is None:
		target = actor
	return target.takeDamage(amount,dmgtype)


# the source bursts apart, destroying it and damaging its surroundings
# force defaults to the source's volatility times its weight
def explode(actor,source,target,dmgtype="f",amount=None):
	area = target if target is not None else \
		(source.parent if source is not None else None)
	if area is None:
		return False
	if amount is None:
		amount = source.material().volatility * source.Weight()
	source.printNearby(f"{+source} explodes!",color="o")
	# break for shatter flavor where possible, then ensure the source is gone
	if Core.hasMethod(source,"breaks"):
		source.breaks()
	if Core.game.itemRegistry.get(source.id) is source:
		source.destroy(silent=True)
	applyAreaEffect(lambda obj: obj.takeDamage(amount,dmgtype),area)
	return True


# lift the target (actor if none) off the floor; a perch platform is kept
def Float(actor,source,target):
	if target is None:
		target = actor
	if target.platform is not None and Core.hasMethod(target,"removePlatform") \
	and target.platform is getattr(target.parent,"floor",None):
		target.removePlatform()
	return True


def heal(actor,source,target,amount):
	if target is None:
		target = actor
	return target.heal(amount)


# impart a status to the target (actor if none): free-standing, survives
# the source's departure or destruction; repeatable (two doses, two entries)
def impartStatus(actor,source,target,name,duration=None):
	if target is None:
		target = actor
	return target.addStatus(name,originId(source),duration)


# spawn a missile and launch it at the target
def launch(actor,source,target,missileName,speed,aim):
	missile = spawnObject(missileName,silent=True).asProjectile()
	adverb = ""
	p = "."
	if speed <= 5:
		adverb = "slowly"
	if speed >= 10:
		adverb = "rapidly"
	if target is Core.player:
		if adverb != "slowly":
			p = "!"
		Core.Print(f"{missile.nounPhrase(det='A')} is launched {adverb} at you{p}",
		color="o")
	else:
		Core.Print(f"{missile.nounPhrase(det='A')} is launched {adverb} at {-target}{p}")
	missile.launch(speed,aim,source,target)


# open a door/box/vessel; ref may be authored as an object id
def openTarget(actor,source,target,ref=None):
	if ref is not None:
		target = resolveObj(ref)
	if target is None or not Core.hasMethod(target,"open"):
		return False
	return target.open(actor)


# remove a status from a room itself; resolves its room like addRoomStatus
def removeRoomStatus(actor,source,target,name,room=None):
	if room is not None:
		room = resolveRoom(room)
	elif isinstance(target,Core.Room):
		room = target
	else:
		room = resolveRoom(source)
	if room is None:
		return False
	return room.removeStatus(name)


# remove status entries matching name (and optionally source/duration)
# from the target (actor if none)
# "*" matches anything; None matches unsourced / indefinite respectively
def removeStatus(actor,source,target,name="*",reqSource="*",reqDuration="*"):
	if target is None:
		target = actor
	return target.removeStatus(name,reqSource=reqSource,reqDuration=reqDuration)


# restore the target's magic points, up to its maximum
def resurge(actor,source,target,amount):
	if target is None:
		target = actor
	gain = min(amount,target.MXMP() - target.mp)
	if gain <= 0 or not target.isAlive():
		return 0
	target.mp += gain
	target.display()
	target.Print(f"You resurged {gain} MP.",color="g")
	return gain


# re-attribute a status entry on the target (actor if none) in place,
# changing its source and/or duration without any add/remove event
def transferStatus(actor,source,target,name,entrySource,newSource,newDur=None):
	if target is None:
		target = actor
	return target.transferStatus(name,entrySource,newSource,newDur)


# unlock a lock; ref may be authored as an object id (no key required;
# levers and spells unlock by force majeure)
def unlockTarget(actor,source,target,ref=None):
	if ref is not None:
		target = resolveObj(ref)
	if target is None or not getattr(target,"locked",False):
		return False
	target.locked = False
	target.printNearby(f"{+target} unlocks.")
	return True



#####################
## EFFECT REGISTRY ##
#####################

# maps effect names to their functions, so effects can be referenced by name
# in authored descriptor data (World.json, Material fields, save files)
# every function defined in this module above this line is included;
# functions imported from other modules are not
effects = {name: func for name,func in globals().items()
	if callable(func) and getattr(func,"__module__",None) == __name__}


# run authored effect descriptors (a collection or a single one alone)
# a tuple (effectName, *args) is dispatched through the effects registry with
# the (actor, source, target) context spliced in; a string is eval()'d
def evokeEffects(descriptors,actor,source,target=None):
	# a single bare descriptor is wrapped into a singleton collection
	descriptors = wrapEffectDescriptors(descriptors)
	for descriptor in descriptors:
		if isinstance(descriptor,str):
			eval(descriptor)
		else:
			name,*args = descriptor
			if name not in effects:
				raise ValueError(f"Unknown effect name '{name}'")
			effects[name](actor,source,target,*args)
	return len(descriptors) > 0


# validate all authored Material effect descriptors at import, so a typo'd
# effect name fails at startup instead of mid-game (materials are coded
# data, not world-authored: eval strings are not allowed in them)
for _material in Data.materials.values():
	for _trigger in ("consume","drench","touch","ignite","impact","expose",
	"onBreak"):
		for _descriptor in getattr(_material,_trigger):
			assert _descriptor[0] in effects, \
				f"Material '{_material.name}' {_trigger} references unknown " \
				f"effect '{_descriptor[0]}'"
	assert 0 <= _material.volatility <= 10, \
		f"Material '{_material.name}' volatility must be 0-10"
del _material, _trigger, _descriptor


# validate all authored StatusCondition cascade descriptors the same way
for _condition in Data.statusConditions.values():
	for _hook in ("onAdd","onGain","onRemove","onLoss","onTick","onExpire",
	"onBlock"):
		for _descriptor in getattr(_condition,_hook):
			assert _descriptor[0] in effects, \
				f"StatusCondition '{_condition.name}' {_hook} references " \
				f"unknown effect '{_descriptor[0]}'"
del _condition, _hook



spells = {}

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


# SPELL EFFECTS:
# Note: these are not specific spell ideas, but general things a spell could do, to outline ways to implement spells and what technical limitations there are
#
# add a status effect
# remove a status effect
# deal area damage/heal (to whole room)
# deal area damage/heal only to creatures which fit a condition
# deal target damage/heal
# improving weapon stats
# changing weapon damage type
# repair an item
#
# spawning item (temporary weapon, illusion projector, food, leomund chest)
# destroy item
# destroy all items that fit a condition
# unlock an item
# lock an item
# locate an item? in the world or nearby
# create a lasting room effect (like preventing entering an exiting, zero gravity, darkness)
# alter the terrain (affecting fixtures and passages)
# create a portal to somewhere (mansion, hut, another room) (permanent/temp)
# break an item
# ignite things
# freeze things
# acid melt things
# shock things
#
# spawning creature (familiar, magic sentry, dragon)
# summon an npc
# destroy creature
# read people's minds
# command a creature
# make a creature laugh/cry/sneeze
# attract animals/creatures
# disguising self
# attracts animals
# speak with animals/monsters
# communicate with npc at a distance?
# pause a creature in time? paralyze them maybe
# pause all creatures in time
# produce illusion of a creature (probably class creature)
# create a loud sound (alert creatures)
#
# resurrect a dead creature
# create a zombie
# teleport somewhere
# stop time everywhere (bool in game class)
#
#
# ^^^^^^^^^^^^
# for magical area effects, you could basically have a function which takes a list of objects (probably contents, occupants or both), an effects function, and an optional key as an argument.
#
# it essentially maps the magical effect function to every object in the given list that fits the key. if there is no key, it is applied to all things in the rooms list
