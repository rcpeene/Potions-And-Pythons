# Effects.py
# This file contaisn all the functions which represent some "effect" in the game
# This file is dependent on Menu.py and is a dependency of PoPy.py

from Core import *



#######################
##  EFFECT FUNCTIONS ##
#######################

# changes global game mode from 1 to 0 or 0 to 1
def changeMode(G):
	print("Ring!")
	G.mode = 1 if G.mode == 0 else 0

def changeTime(G,t):
	G.time = t

def setStat(C,attrString,val):
	# try:
	attr = getattr(C,attrString)
	# except:
	# 	print("Attribute does not exist")
	# 	return
	if isinstance(attr,int):
		try:
			val = int(val)
		except:
			print("Invalid value type")
			return
	setattr(C,attrString,val)

def changeStat(C,attr,diff):
	try:
		attr = getattr(P,attr)
	except:
		print("Attribute does not exist")
		return
	setattr(C,attr,attr+val)

def addCondition(A,cond):
	A.addCondition(cond)

def removeCondition(A,cond):
	A.removeCondition(cond)

# spawns an item in the room
def spawnItem(G,I):
	print(f"A {I.name} appears in front of you!")
	G.currentroom.addItem(I)

# def destroyItem(S,I):
# 	if isinstance(S,Player):	print(f"Your {I.name} is destroyed")
# 	else:						print(f"The {I.name} is destroyed")
# 	S.removeItem(I)

def destroyItemsByType(R,Type,d=0,msg=""):
	#TODO: make this work efficiently
	items = objTreeToSet(S,d=d)
	for item in items:
		if isinstance(item,Type):
			S,I = objSearch(item.name,R,d=d,reqSource=True)
			S.removeItem(I)
	if msg != "":
		print(msg)


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
