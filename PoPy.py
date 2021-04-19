# PoPy.py, Potions & Pythons by Ross Peene, 2021
# This file runs main() which loops, having the user and creatures take actions
# This file is dependent on Parser.py

from Parser import *

# note: some startup code is run in Parser.py before main is called
def main():
	while True:
		# take user input until player successfully performs an action
		while not parse(getcmd(),0):	continue

		# creatures in current room's turn
		for creature in G.currentroom.occupants:
			creature.act(P,G.currentroom,False)

		# creatures in nearby rooms' turn
		for room in G.nearbyRooms(W):
			for creature in room.occupants:
				creature.act(P,room,True)

		# pass the time after everyone has acted
		G.incrementTime()

main()


# CURRENT TASKS:

# reevaluate effect functions, is there a way to reference a function by string?
# revise the way status effects are implemented, probably store them as a tuple containing the effect counter and a timer?
# how will amulet effects work??
# evaluate enter, exit functions in room

# figure out animal behavior
# creatures attacking?
# add monsters/monster behavior
# figure out combat? attack items?
# fix the fact that creatures can't die outside of the currentroom?

# add 'initiative order' for creature actions
# add time to verbs?

# add locking/unlocking items
# add Steal

# add in armor and shields and protection and test them
# add range and ranged weapons???
# add new weapons and TEST
# more switches, levers, buttons

# add "it" variable in G class? maybe ordered list of most recent items, starting with the last item player referred to, followed by last items which were referred to in output?

# add object name disambiguation?
# add object plural type? 'there is some bread' vs 'there is a bread'
# add object generalization (so you can say 'take potion' on the 'red potion')
# add possession? (so you can say 'break goblin's sword', 'take his food')

# design persons and person behavior all of the RP system?
# FLESH OUT MORE VERBS (and add items to go with them)
# go into the cabin?


# FUTURE IMPROVEMENTS

# fill out definitions more
# add status effects and their durations (can it work on items?)
# add quicksave and autosave, possibly include recent save name in Game() class
# add signal handling: ctrl+s to save, ctrl+q to quit?
# add cooking/brewing/crafting/tinkering
# ^^^sharpening/smithing items?
# add trading with npcs
# add spells
# add a world map/record visited rooms
# add a window which shows player stats/possible commands/instructions



# effects may include:
#
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
