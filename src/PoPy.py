# PoPy.py, Potions & Pythons by Ross Peene, 2022
# This file runs main() which loops, having the user and creatures take actions
# This file is dependent on Parser.py

import os

import Core
import Menu
import Parser




def main():
	# formatting the prompt window
	os.system("mode con:cols=130 lines=32")
	os.system("title Potions ^& Pythons")

	# run intro logo animation
	Menu.gameIntro()
	# instantiate global objects Player, World, Game
	Menu.mainMenu()
	if Core.game.quit == True:
		return
	# assign parents to objects, which specifies what they are contained in
	Core.assignParents()
	# eliminate any room connections which don't exist in the world dict
	Core.ensureWorldIntegrity()

	# describe the current room
	Core.game.startUp()
	# main input loop
	while True:
		Core.game.silent = False
		Core.game.activeroom = Core.game.currentroom
		Core.game.whoseturn = Core.player

		# take user input until player successfully performs an action
		while not Parser.parse(): continue
		if Core.game.quit: return

		# creatures in current room's turn
		Core.game.activeroom = Core.game.currentroom
		for creature in Core.game.currentroom.occupants:
			Core.game.whoseturn = creature
			creature.act()

		# creatures in nearby rooms' turn
		Core.game.silent = True
		for room in Core.game.nearbyRooms():
			Core.game.activeroom = room
			for creature in room.occupants:
				Core.game.whoseturn = creature
				creature.act()

		# cleanup before looping
		Core.game.activeroom = None
		Core.game.whoseturn = None
		# pass the time for all rooms and creatures
		Core.game.incrementTime()
		# remove dead Creatures from room occupants
		Core.game.reapOccupants()
		# sort the occupants in each rendered room by their MVMT attribute
		Core.game.sortOccupants()


if __name__ == "__main__":
	main()


################################################################################

# CURRENT TASKS

# give rooms a 'features' list which contains fixtures
# test making room names capital
# restructure map and revise tests, add attack tests
# add "insert the key into the lock"
# alter how take is done (maybe)
# add checkConditions method when updating skills

# flush input not working?? (should be fixed, but make sure)
# add douse function
# add some preliminary spells and add effects file
# consider enter, exit functions in room
# reevaluate effect functions, is there a way to reference a function by string?
# how will amulet effects work??

# remove game.activeroom? maybe?
# add carry/put down (HOW IS THIS GONNA WORK? does it equip the creature? while they are restraining is the player unable to do anything else?)
# try "pick him up"
# add Steal
# determine what can be hid behind

# add resilient error handling, for file I/O, maybe in action loop
# add a wait command (cant wait with enemies nearby, cuz they could just kill you)
# examine output grammar/statements for lower level actions (in case non-player creatures do actions, we dont want it to print the same msgs), alter print to use G.print which depends on silent

# adjust how taking and listing items works (eg allow for saying "take swords")
# consider adding alternative names (this would change search funcs a lot)

# there is a bug in equip where two of the same item can be equipped twice???
# implement escape and exit actions
# add magic beans or food to pour stuff on

# "drink from the fountain"
# make a list of all possible uses and inputs for each action and systematically test them. Revise the world to accomodate them

# figure out animal behavior
# creatures attacking?
# add monsters/monster behavior
# add creatures with many limbs (or can equip more than 2 weapons/shields)
# figure out combat? attack items?

# add in armor and shields and protection and test them
# add range and ranged weapons???
# add new weapons
# more switches, levers, buttons
# ensure output is grammatically correct with creature names. (for npcs, instead of printing "THE I.name" you must print just name)

# add object name disambiguation? (code asks "which sword will you use?"
# add object plural type? 'there is some bread' vs 'there is a bread'
# add object generalization (so you can say 'take potion' on the 'red potion')
# add possession? (so you can say 'break goblin's sword', 'take his food')... these could be easily restructured as "break sword from goblin", "take food from him"

# design persons and person behavior all of the RP system?
# FLESH OUT MORE VERBS (and add items to go with them)
# go into the cabin?

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
