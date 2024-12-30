# PoPy.py, Potions & Pythons by Ross Peene, 2022
# This file runs main() which loops, having the user and creatures take actions
# This file is dependent on Parser.py

import os

import Core
import Menu
import Parser




def main(skipIntro=False):
	# formatting the prompt window
	os.system("mode con: lines=9999")
	os.system("title Potions ^& Pythons")

	# run intro logo animation
	if not skipIntro: Menu.gameIntro()
	# instantiate global objects Player, World, Game
	Menu.mainMenu()
	if Core.game.quit: return
	# assign parents to objects, which specifies what they are contained in
	Core.assignParents()
	# eliminate any room connections which don't exist in the world dict
	Core.ensureWorldIntegrity()

	# describe the current room
	Core.game.startUp()
	# main input loop
	while True:
		Core.game.silent = False
		Core.game.whoseturn = Core.player

		# take user input until player successfully performs an action
		while not Parser.parse(): continue
		if Core.game.quit: return

		# creatures in current room's turn
		for creature in Core.game.currentroom.creatures:
			Core.game.whoseturn = creature
			creature.act()
			if Core.game.quit: return

		# creatures in nearby rooms' turn
		Core.game.silent = True
		for room in Core.game.nearbyRooms():
			for creature in room.creatures:
				Core.game.whoseturn = creature
				creature.act()
				if Core.game.quit: return

		# cleanup before looping
		Core.game.whoseturn = None
		# pass the time for all rooms and creatures
		Core.game.incrementTime()
		# remove dead creatures from room creatures
		Core.game.reapCreatures()
		# sort the creatures in each rendered room by their MVMT attribute
		Core.game.sortCreatures()
		if Core.game.quit: return


if __name__ == "__main__":
	main()


################################################################################

# CURRENT TASKS
	
# replace Empty object? with none

# add print which writes text letter by letter

# add "you're already there" when trying to go to current room
# improve 'go' with 'go to tunnel' for instance (filter out prepositions basically)
# add 'forward(s), ahead' to 'go' command
# add dialect processor to tritepool output?

# add basic time cycling, and clock items which tell you the hour
# add astronomical events based on the time cycling

# add basic equipment and clothing items
# fix/add Creature.isNaked or Player.isNaked

# restructure map and revise tests
	# add magic beans or food to pour stuff on
	# "drink from the fountain"
	# make a list of all possible uses and inputs for each action and systematically test them. Revise the world to accomodate them

# add some preliminary spells and add effects file
	# reevaluate effect functions, is there a way to reference a function by string?
	# how will amulet effects work??
	# add spells functions and fill in spells dict
	# added spell/effects tests

# add resilient error handling, for file I/O, maybe in action loop

# examine output grammar/statements for lower level actions (in case non-player creatures do actions, we dont want it to print the same msgs), alter print to use G.print which depends on silent

# behavior
	# design persons and person behavior all of the RP system?
	# figure out animal behavior
	# add monsters/monster behavior
	# creatures attacking?
	# improve attack tests
	# add creatures with many limbs (or can equip more than 2 weapons/shields)
	# figure out combat? attack items?

# add possession? (so you can say 'break goblin's sword', 'take his food')... these could be easily restructured as "break sword from goblin", "take food from him"

# sift through TODOs

# FLESH OUT MORE VERBS (and add items to go with them)
# add "insert the key into the lock"
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


################################################################################

# FUTURE IMPROVEMENTS

# fill out definitions more, change definitions of some things to be more expository and fantastical
# consider making objects hideable based on something other than weight
# add quicksave and autosave, possibly include recent save name in Game() class
# add signal handling: ctrl+s to save, ctrl+q to quit?
# add cooking/brewing/crafting/tinkering
# ^^^sharpening/smithing items?
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
#		body
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
