# Effects.py
# This file contains all the functions which represent some "effect" in the game
# This file is dependent on Menu.py and is a dependency of PoPy.py

import Creatures
import Items
import Core
import Data




#######################
##  EFFECT FUNCTIONS ##
#######################


def applyAreaEffect(effect,root,condfunc=lambda x:True):
	objs = Core.objQuery(root,key=condfunc,d=3)
	for obj in objs:
		effect(obj)


def spawnObject(obj,room=None,silent=False):
	if room is None:
		room = Core.game.currentroom
	if type(obj) is str:
		if obj in Items.factory:
			obj = Items.factory[obj]()
		elif obj in Creatures.factory:
			obj = Creatures.factory[obj]()
		else:
			raise Exception(f"object name '{obj}' not in any factory")

	if isinstance(obj,Core.Creature):
		room.addCreature(obj)
	elif isinstance(obj,Core.Fixture):
		room.addFixture(obj)
	elif isinstance(obj,Core.Item):
		room.addItem(obj)
	if not Core.game.silent and not silent:
		Core.Print(f"{obj.nounPhrase('a',cap=1)} appeared!")
		Core.game.setPronouns(obj)
	return obj


def destroyObject(obj):
	if isinstance(obj,Core.Creature):
		obj.parent.removeCreature(obj)
	elif isinstance(obj,Core.Fixture):
		obj.parent.removeFixture(obj)
	elif isinstance(obj,Core.Item):
		obj.parent.removeItem(obj)
	if not Core.game.silent:
		Core.Print(f"{-obj} was destroyed.")


def increment(obj,attribute,num):
    if hasattr(obj, attribute):
        current_value = getattr(obj, attribute)
        if isinstance(current_value, int):
            setattr(obj, attribute, current_value + increment)
        else:
            raise TypeError(f"The attribute '{attribute}' is not an integer.")
    else:
        raise AttributeError(f"The object {obj} has no attribute '{attribute}'.")


def Launch(obj,speed,aim,launcher,target):
	obj = spawnObject(obj,silent=True).asProjectile()
	if target is Core.player:
		Core.Print(f"{obj.nounPhrase(det='A')} is launched at you!",color="o")
	else:
		Core.Print(f"{obj.nounPhrase(det='A')} is launched at {-target}")
	obj.Launch(speed,aim,launcher,target)



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
