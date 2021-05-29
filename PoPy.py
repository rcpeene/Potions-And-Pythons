# PoPy.py, Potions & Pythons by Ross Peene, 2021
# This file runs main() which loops, having the user and creatures take actions
# This file is dependent on Parser.py

from Parser import *

# note: some startup code is run in Parser.py before main is called
def main():
	while True:
		G.sortOccupants(W)

		# take user input until player successfully performs an action
		G.whoseturn = P
		while not parse(0):	continue

		# creatures in current room's turn
		for creature in G.currentroom.occupants:
			G.whoseturn = creature
			creature.act(P,G.currentroom,False)

		# creatures in nearby rooms' turn
		for room in G.nearbyRooms(W):
			for creature in room.occupants:
				G.whoseturn = creature
				creature.act(P,room,True)

		# pass the time after everyone has acted
		G.whoseturn = None
		G.incrementTime(P,W)

if __name__ == "__main__":
	main()



################################################################################

# CURRENT TASKS

# add "put on" and "take off" commands
# test input "go">"up">"the stairwell"
# really consider what attributes to give items. maybe give them a value and a size attribute.
# give passages complete "connections" rather than just directions, ie directions and destinations
# add hide/crouch/crawl
# test newest actions
# when creature die, make it so they drop items maybe? instead of to player inv?
# fix Go() when they dont have a compass
# examine output grammar/statements for lower level actions (in case non-player creatures do actions, we dont want it to print the same msgs)

# add carry/put down (HOW IS THIS GONNA WORK? does it equip the creature? while they are restraining is the player unable to do anything else?)
# organize method names in Core.py, jesus christ
# implement escape and exit actions
# add a wait command (cant wait with enemies nearby)
# there is a bug in equip where two of the same item can be equipped twice
# make menu look nice instead of reprinting everything
# add basic "cast" parsing
# add some preliminary spells and add effects file
# split creatures and objects into different files

# consider adding alternative names (this would change search funcs a lot)
# TODO: research using map() in python, and passing functions as arguments
# consider enter, exit functions in room
# reevaluate effect functions, is there a way to reference a function by string?
# how will amulet effects work??

# add Steal
# determine what can be hid behind
# add magic beans or food to pour stuff one
# "drink from the fountain"
# make a list of all possible uses and inputs for each action and systematically test them. Revise the world to accomodate them

# figure out animal behavior
# creatures attacking?
# add monsters/monster behavior
# figure out combat? attack items?

# add in armor and shields and protection and test them
# add range and ranged weapons???
# add new weapons
# more switches, levers, buttons
# ensure output is grammatically correct with creature names. (for npcs, instead of printing "the I.name" you must print just name)

# add object name disambiguation? (code asks "which sword will you use?"
# add object plural type? 'there is some bread' vs 'there is a bread'
# add object generalization (so you can say 'take potion' on the 'red potion')
# add possession? (so you can say 'break goblin's sword', 'take his food')... these could be easily restructured as "break sword from goblin", "take food from him"

# design persons and person behavior all of the RP system?
# FLESH OUT MORE VERBS (and add items to go with them)
# go into the cabin?

################################################################################

# FUTURE IMPROVEMENTS

# fill out definitions more
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




# interpret(verb,dobj,iobj,prep,preps,dobjSearch,iobjSearch,d1=0)
# 	if prep not in preps:
# 		print("not understood")
# 		return False
# 	if dobj == None: dobj = iobj
# 	if dobj == None: dobj = getNoun("What do you want to " + verb + "?")
# 	if dobj in cancels:
# 		return False
#
# 	if searchInv:
#
#
#
#
# func(dobj,iobj,prep):
# 	preps = {toward, none}
# 	I,R,prep = interpretSearch(dobj,iobj,prep,preps,dobjSearch,iobjSearch)
#
#
