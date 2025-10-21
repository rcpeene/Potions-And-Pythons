# PoPy.py, Potions & Pythons by Ross Peene, 2022
# This file runs main() which loops, having the user and creatures take actions
# This file is dependent on Parser.py

import os
import sys
import traceback

import Core
import Menu
import Interpreter




def main(testing=False):
	# sleep(3)
	# formatting the prompt window
	# os.system("mode con: lines=32")
	os.system("title Potions ^& Pythons")
	os.system("color 0F")
	if "src" in os.getcwd(): os.chdir("..")

	if not testing:
		# run intro logo animation
		Menu.gameIntro()

		logger = Core.TeeLogger("./transcript.log")
		sys.stdin = logger
		sys.stdout = logger
		sys.stderr = logger

	# instantiate global objects Player, World, Game and run start-up
	Menu.mainMenu()

	# main input loop
	while True:
		try:
			if Core.game.quit: return Menu.quit()
			Core.game.silent = False
			Core.game.whoseturn = Core.player
			if not Core.player.isAlive(): 
				if not Menu.restart():
					return False
				continue

			# take user input until player successfully performs an action
			if not Core.player.hasStatus("asleep"):
				while not Interpreter.interpret(): continue
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
			if Core.game.time >= Core.game.lastsave+20: Menu.quickSave("autosave")
		except Exception as e:
			if testing: raise e
			Core.Print(f"\n\nAn error has occurred. The game will attempt to continue, but you may want to restart.\nThe error message is as follows:\n")
			traceback.print_exc()
			Core.waitInput("\nPress any key to continue...")
			# return Menu.quit()


if __name__ == "__main__":
	main()


################################################################################

# CURRENT TASKS


################################################################################

# BUG BACKLOG



################################################################################

# FUTURE IMPROVEMENTS

# test drinking an object when inv is full, see if bottle goes on ground
# hide/get in a body of water?
# try "jump in the pond"
# add "swim"
# handle bodies of water; what about fall dammage, being weighed down
# add magic beans or food to pour stuff on
# "drink from the pond"
# think about a broken water container or leaking/draining

# refactor drop into a creature method?
# make sure Touch method is called when player 'takes' an item (unless they use a hook or smth?)
# try to pull creature off of its mount?
# add Steal
# implement steal
	# "take bird from earl"

# readjust throw force formula; compare to BRDN (shouldn't be able to throw heavier than you can have in inv, or more than you can carry in hands?
# check if throwing a creature which has another riding it?
# knock stuff off of a table if it takes impact?
# add in projectile weapons?
# add range and ranged weapons???
# add in a whip or hook which is a projectile that allows you to grab an item?
# throw 'grappling hook' which creates a new passage?, throw up a cliff or across a gap
# consider how attacking with foot, head, mouth, hand, tail works

# add "in" operator to objects
# reorganize methods, capital or lowercase them based on if creature is subject or object
# add asserts to most class methods
# add better comments to methods

# color status conditions green/red in status display
# account for being restrained when doing stuff

# what if horse goes wild while riding it, doesn't obey your directions
# give passages a capacity limit, so a dragon can't fit through a doorway?

# add chopping tree
# add a "tree" item? item which can be climbed but isn't a passage
# add destroying objects with fire, burning creatures
# add a "torch" item which can be lit and put out, and lights up a dark room
# a "campfire" item which can be used to cook food and provide light
# if something is on fire (or other condition) when entering a room, say it

# try out using a creature as a weapon
# correctly factor DFNS into takeDamage (it should probably be in takeDamage method itself), but consider different damage source like collision and falling
# add fencing and wooden swords
# add in armor and shields and protection and test them
# add new weapons

# add turn order, so you aren't the first to move when you enter a room, makes MVMT more useful
	# allow moving multiple times if you have enough speed? (maybe max 5 for vs 1 for slowest creature)
# add time to verbs?
# add action queue to sort initiative among rooms
# add in "knockback"?, if you get hit on top of the cliff, have a chance to fall off?

# add room property which is description of directions ("look up", "look east", "look out", etc.)
# try "boom" effect. It will only effect current room/container (unless container breaks or is open?)
# restrict Read to readable objects?
# if describing something in own inventory, also print the lore tip in grey (or other color)
# make items have an invisibility property? but what about if a missed projectile hits something invisible?
# make player.aware(I) method, which instead of using currentroom, checks if I in player.surroundings.objTree
	# replace references to currentroom with player.parent when needed
	# include hiding ability?
	# you are hiding (if in one)

# add character creation/customization
# gender: male (+1 STR), female (+1 CHA), other (+1 LCK)
# build: slender (+2 SPD), medium (+2 DEX), heavy (+2 CON)
# age: youth (+3 STM), mature (+3 INT), aged (+3 WIS), elderly (+3 FTH)
# hair color: black, brown, blonde, red, grey, no hair 
	# (maybe just cosmetic or maybe affects something minor/dialogue)
# character always has purple eyes?

# sift through TODOs
# add basic equipment and clothing items
# restructure map and revise tests
# add a coin purse? which holds your money? required to collect money?
# make a list of all possible uses and inputs for each action and systematically test them. Revise the world to accomodate them
# implement escape/run away

# use both items and fixtures array to contain fixtures. Just use fixtures array to determine which ones not to list and query normally. remove fixtures mention property
# refactor Switch into just inheriting fixture and controller?
# add possession? (so you can say 'break goblin's sword', 'take his food')... these could be easily restructured as "break sword from goblin", "take food from him"
	# 'take goblins sword from him'

# fix/add Creature.isNaked or Player.isNaked
# add total traversal limit on dlog nodes?
# add link nodes and effect nodes to dialogue after all
	# for instance, continue conversation if a truesight person speaks to invisible player, or if a goddess spirit gives you blessing
	# maybe blessings actually would be the course of action of the NPC with which you speak... I guess, find a way to do that
# add dialect processor to tritepool output?

# fill out glossary more, change definitions of some things to be more expository and fantastical
# add knowledge/intelligence value for glossary, 
# player only knows something if the term is in their "knowledge" set or their KNWL fits the requirement
# perhaps don't allow crafting certain things without it in their glossary?
# or add items to glossary through trial and error in crafting?

# add in crafting recipes. Probably store this as a JSON?
# add cooking/brewing/crafting/tinkering
# ^^^sharpening/smithing items?
	# create system for 'recipes' with this

# behavior
	# implement creature.Go
		# make sure they can't go if they're riding something dead or occupying something
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

# FLESH OUT MORE VERBS (and add items to go with them)
# add "insert the key into the lock"
# add a wait command (cant wait with enemies nearby, cuz they could just kill you)
# more switches, levers, buttons
# add douse function

# add output effects to blessings and curses?
# slowness/swiftness already affects output speed
# perhaps brawniness makes text bold? weakness makes all lowercase?
# insanity -> make random words random colors? random prints like "You see a demon" Or weird whispering messages
# stupidity -> make text use dumb vocabulary? (would be difficult) (maybe remove any >6 word, replace with stuff and things)
# stupidity -> remove ability to see stats, remove glossary
# clumsiness -> trip randomly? jumping likely to fail, likely to drop stuff out of inventory, likely to fail crafting
# calamity -> ricochet always hits you, lightning strikes likely
# apathy might make all text white or light gray, perhaps you can't gain xp? make sensory information gone (taste, smell touch), makes sleeping much longer
# timidity make it not possible to meet new people?, don't do quest or colloquy
# illness, perhaps make it so that the player has random coughing fits or sneezes, heal half the rate?
# blind -> don't get a description of where you are, just a few hints (like "you feel grass under your feet"), 
	# just hearing creature sounds, 
	# some stuff like items breaking and taking damage you know
	# you can't see items in the room, but you can feel them if you search
	# maybe allow "feel something" and randomly select
	# during Go, just choose a random direction
# deaf -> bang doesn't affect you, and you can't talk to creatures


# add spells
# add some preliminary spells and add effects file
	# reevaluate effect functions, is there a way to reference a function by string?
	# how will amulet effects work??
	# add spells functions and fill in spells dict
	# added spell/effects tests

# add trading, buying, selling with npcs

# update design doc
# add signal handling: ctrl+s to save, ctrl+q to quit?
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


### TYPES OF FEEDBACK:
# 1. execution errors; Errors which stop the game from running
# 2. failure of intention; Errors where player input result is interpreted in an unreasonable manner, leading to unexpected/nonsensical consequences.
# 3. failure of information; Errors where the player is not given enough information about what happened making the game difficult to understand.
# 4. failures of action; Errors where the player has difficulty figuring out how to do what they want to do. The game tells them they can't do something they think they should be able to.
# 5. grammatical failures; Errors where the text output is ungrammatical or awkwardly phrased.
# 6. failure of verisimilitude; Errors where the game mechanics behave in ways that are consistent and reliable, but absurd or at odds with reality (allowing the fantasy elements of the game world).
# 7. lack of polish; Errors where the game mechanics are fully functional, but not as user-friendly or enjoyable as they could be.
# 8. lack of gameplay content; Errors where the game is missing mechanics/features that would enhance the player's experience.
# 9. narrative/lore shortcomings; Missing story or environment elements that detract from the game's immersion or storytelling. Things the world lacks that would make it more interesting.
# 10. any other feedback