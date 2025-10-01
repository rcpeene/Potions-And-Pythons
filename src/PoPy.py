# PoPy.py, Potions & Pythons by Ross Peene, 2022
# This file runs main() which loops, having the user and creatures take actions
# This file is dependent on Parser.py

import os
import sys

import Core
import Menu
import Parser




def main(testing=False):
	# formatting the prompt window
	# os.system("mode con: lines=32")
	os.system("title Potions ^& Pythons")
	os.system("color 0F")
	if "src" in os.getcwd(): os.chdir("..")

	if not testing:
		logger = Core.TeeLogger("./transcript.log")
		sys.stdin = logger
		sys.stdout = logger
		sys.stderr = logger

		# run intro logo animation
		Menu.gameIntro()

	# instantiate global objects Player, World, Game and run start-up
	Menu.mainMenu()

	# main input loop
	while True:
		if Core.game.quit: return Menu.quit()
		Core.game.silent = False
		Core.game.whoseturn = Core.player
		if not Core.player.isAlive(): 
			if not Menu.restart():
				return False
			continue

		# take user input until player successfully performs an action
		if not Core.player.hasCondition("asleep"):
			while not Parser.parse(): continue
		if Core.game.quit: return Menu.quit()

		# creatures in current room's turn
		for creature in Core.game.currentroom.allCreatures():
			if not Core.player.isAlive(): continue
			Core.game.whoseturn = creature
			creature.act()

		# creatures in nearby rooms' turn
		Core.game.silent = True
		for room in Core.game.nearbyRooms():
			for creature in room.allCreatures():
				if not Core.player.isAlive(): continue
				Core.game.whoseturn = creature
				creature.act()

		if not Core.player.isAlive(): continue
		# cleanup before looping
		Core.game.whoseturn = None
		# pass the time for all rooms and creatures
		Core.game.passTime()

		if not Core.player.isAlive(): continue
		# save game every so often just in case
		if Core.game.time >= Core.game.lastsave+10: Menu.quickSave("autosave")


if __name__ == "__main__":
	main()


################################################################################

# CURRENT TASKS

# add ability to go into containers
	# continue stand func with stand on and stand in
		# try "get on bed", redirect Mounting an obj to stand
# readjust throw force formula; compare to BRDN (shouldn't be able to throw heavier than you can have in inv, or more than you can carry in hands?
# check if throwing a creature which has another riding it?
# handle "get on" to mount or get on a table (wb get on table while on a horse?)
# refactor drop into a creature method?
# make player.aware(I) method, which instead of using currentroom, checks if I in player.surroundings.objTree
	# replace references to currentroom with player.parent when needed
	# include hiding ability?
	# you are hiding (if in one)

# add "in" operator to objects

# "you attack the goblin with your your hand!" is what shows up on attack
# fix obtaining money problem, think about other objects which won't go into inv upon obtaining
# add "look up" as valid. Should look at sky if not in a room?
	# add room property which is description of directions ("look up", "look east", "look out", etc.)
# correctly factor DFNS into takeDamage (it should probably be in takeDamage method itself), but consider different damage source like collision and falling
# try out using a creature as a weapon
# knock stuff off of a table if it takes impact?
# add in projectile weapons?
# add in a whip or hook which is a projectile that allows you to grab an item?
# throw 'grappling hook' which creates a new passage?, throw up a cliff or across a gap
# add turn order, so you aren't the first to move when you enter a room, makes MVMT more useful
# if something is on fire (or other condition) when entering a room, say it
# what if the tree at "big tree" is destroyed? Some contingency to reset/alter the room?
# what if horse goes wild while riding it, doesn't obey your directions
# give passages a capacity limit, so a dragon can't fit through a doorway?
# create linked passages? if a window breaks on one side, it should break the other way too
# add "climb" and "swim"
# "jump off cliff"
# add chopping tree
# add fencing and wooden swords
# add dull method to weapons, add blunt weapons which cant be sharpened?
# try "boom" effect. It will only effect current room/container (unless container breaks or is open?)
# restrict Read to readable objects?
# if describing something in own inventory, also print the lore tip in grey (or other color)
# use both items and fixtures array to contain fixtures. Just use fixtures array to determine which ones not to list and query normally. remove fixtures mention property
# refactor Switch into just inheriting fixture and controller?
# handle bodies of water; what about fall dammage, being wieghed down and following
# try to pull creature off of its mount?
# make items have an invisibility property? but what about if a missed projectile hits something invisible?
# add in crafting recipes. Probably store this as a JSON?
# add in "knockback"?, if you get hit on top of the cliff, have a chance to fall off?

# add basic equipment and clothing items
# make sure Touch method is called when player 'takes' an item (unless they use a hook or smth?)
# fix/add Creature.isNaked or Player.isNaked
# add link nodes and effect nodes to dialogue after all
	# for instance, continue conversation if a truesight person speaks to invisible player, or if a goddess spirit gives you blessing
	# maybe blessings actually would be the course of action of the NPC with which you speak... I guess, find a way to do that

# restructure map and revise tests
	# add magic beans or food to pour stuff on
	# "drink from the fountain"
	# make a list of all possible uses and inputs for each action and systematically test them. Revise the world to accomodate them
# add asserts to most class methods
# add better comments to methods
# skim/update design doc

# add total traversal limit on dlog nodes?
# behavior
	# add Escape to creature behavior. Make sure that if they escape a container thats in an inventory, to put them in the room??
	# make fear lowered by taking damage on player's turn, but make love go down if player does something they don't like (like restraining them)
	# create system for behavior 'regimens'
	# make sure creatures can see/select targets from open containers as well
	# design persons and person behavior all of the RP system?
	# add reactions to being healed or being attacked
	# figure out animal behavior
	# add monsters/monster behavior
	# creatures attacking?
	# improve attack tests
	# add creatures with many limbs (or can equip more than 2 weapons/shields)
	# figure out combat? attack items?
# examine output grammar/statements for lower level actions (in case non-player creatures do actions, we dont want it to print the same msgs), alter print to use G.print which depends on silent

# add portal object, which is basically a passage that isn't a fixture, (but still can't be taken?)
# add dialect processor to tritepool output?
# add possession? (so you can say 'break goblin's sword', 'take his food')... these could be easily restructured as "break sword from goblin", "take food from him"
# add a coin purse? which holds your money? required to collect money?

# sift through TODOs

# FLESH OUT MORE VERBS (and add items to go with them)
# add "insert the key into the lock"
	# allow restful sleep if resting by a fire?
	# implement escape
	# add a wait command (cant wait with enemies nearby, cuz they could just kill you)
	# add in armor and shields and protection and test them
	# add range and ranged weapons???
	# add new weapons
	# more switches, levers, buttons
	# add douse function
	# add carry/put down (HOW IS THIS GONNA WORK? does it equip the creature? while they are restraining is the player unable to do anything else?)
	# try "pick him up"
	# add Steal
	# determine what can be hid behind

# add some preliminary spells and add effects file
	# reevaluate effect functions, is there a way to reference a function by string?
	# how will amulet effects work??
	# add spells functions and fill in spells dict
	# added spell/effects tests


################################################################################

# FUTURE IMPROVEMENTS

# fill out definitions more, change definitions of some things to be more expository and fantastical
# consider making objects hideable based on something other than weight
# add quicksave and autosave, possibly include recent save name in Game() class
# add signal handling: ctrl+s to save, ctrl+q to quit?
# add cooking/brewing/crafting/tinkering
# ^^^sharpening/smithing items?
	# create system for 'recipes' with this
# add trading with npcs
# add spells
# add action queue to sort initiative among rooms
# add time to verbs?
# add a world map/record visited rooms
# add a window which shows player stats/possible commands/instructions

################################################################################



# OVERVIEW OF ITEM CLASSES AND SUBCLASSES:

# item
#	armor
#		helm
#		torso
#		legs
# 	bottle
#		potion
# 	box
#		lockbox
# 	compass
# 	controller
# 	door
# 	hand
# 	fixture
#		switch
#		table
# 	food
#		bread
#		etc other edible items
# 	foot
# 	mouth
# 	shard
#	shield
# 	weapon
#		sword
#		axe
#		polearm
#		club
