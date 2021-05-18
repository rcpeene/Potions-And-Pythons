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
		while not parse(getCmd(),0):	continue

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

# get all action funcs on same page with returning true or false

# then hide/crouch/crawl
# then grab/carry
# add a wait command (cant wait with enemies nearby)

# add room status conditions
# when creature die, make it so they drop items maybe? instead of to player inv?
# fix Go() when they dont have a compass
# consider adding alternative names (this would change search funcs a lot)

# TODO: research using map() in python, and passing functions as arguments
# reevaluate effect functions, is there a way to reference a function by string?
# evaluate enter, exit functions in room

# how will amulet effects work??

# add magic beans or food to pour stuff one
# "drink from the fountain"
# add locking/unlocking items
#
# figure out animal behavior
# creatures attacking?
# add monsters/monster behavior
# figure out combat? attack items?
# add Steal

# there is a bug in equip where two of the same item can be equipped twice

# add in armor and shields and protection and test them
# add range and ranged weapons???
# add new weapons and TEST
# more switches, levers, buttons

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



# commands to take for going up:
# "go up the cliff"
# "climb up the cliff"
# "climb the cliff"
# "scale the cliff?"
#
# "walk up the stairs"
# "walk the stairs"
# "go up the stairs"
#
# "crawl into the hole"
# "climb up the wall"
#
# "swim into the river"
# swim in the fountain"
# swim in the pond"
# "swim north"
#
# Room has connection {"up": "some other room"}
# when player goes "up":
# if player can fly: just changeRoom to above room
# else:
# 	need to know what things in the room lead up
# 	"what will you go up?"
# 	could be stairs, cliff, ladder
# 	call Ascend() function with specified object
# 		if obj requires climbing, call obj.climb(currentroom)
# 		else, just changeRoom to above room



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


# status effects are tuples of the form (name, duration)
# where duration is an integer representing the number of time units remaining
# a duration of -1 means the effect lasts until removed
# a duration of -2 means the effect was imbued from being in a room and it lasts until it is no longer afflicted again




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
#
