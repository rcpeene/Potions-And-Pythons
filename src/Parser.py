# Parser.py
# This file contains the code to parse user input and execute player actions
# This file is dependent on Menu.py and is a dependency of PoPy.py

# It consists of three main parts;
# 1. Parsing functions	(functions to parse user input)
# 2. Action functions	(action, shortaction, cheat functions called by parse())
# 3. Action dicts		(dictionaries used to call action functions from)

import sys
from random import choice

import Data
import Core
import Menu
import Items
import Creatures
import Effects


#######################
## PARSING FUNCTIONS ##
#######################


# this is used to disambiguate user input...
# when the object name given is not specific enough
# takes the object name and list of matching objects
# prints the list of objects with entry 'tags' to help the user distinguish them
# will return when user cancels or when they select an object by name or number
def chooseObject(name,objects):
	if objects is None or len(objects) == 0:
		return None
	if len(objects) == 1:
		return objects[0]
	Core.game.print()
	while True:
		for n,object in enumerate(objects):
			strname = object.stringName(det=False)
			label = ""
			if isinstance(object,Core.Creature):
				if not object.isAlive():
					label += f" (dead)"
				else:
					label += f" ({object.hp} hp)"
			if not isinstance(object.parent,(Core.Room,Core.Player)):
				label += f" ({object.parent.name})"
			if object in Core.player.gear.values():
				label += " (equipped)"
			elif object in Core.player.invSet():
				label += " (Inventory)"
			Core.game.print(f"{n+1}. {strname}{label}")

		Core.game.print(f"\nWhich {name}?")
		choice = Core.game.input("> ").lower()
		if choice == "": continue
		if choice in Data.cancels: return None
		break

	try:
		return objects[int(choice)-1]
	except:
		for obj in objects:
			if choice == obj.stringName(det=False).lower():
				return obj
	Core.game.print("That is not one of the options.")
	return None


# return an object in player inv or room based on player input
# gets a list of potential objects whose name matches the given user input term
# queryPlayer and queryRoom indicate which places to look for matching objects
# roomD and playerD are the 'degree' of the query.
# Look at Core.py objQuery for details on query degree
def findObjFromTerm(term,queryType="both",filter=None,roomD=1,playerD=2,reqParent=None,silent=False):
	matches = []

	if queryType == "player" or queryType == "both":
		matches += Core.player.nameQuery(term,d=playerD)
	if queryType == "room" or queryType == "both":
		matches += Core.game.nameQueryRoom(term,d=roomD)

	if filter:
		matches = [match for match in matches if filter(match)]
	if reqParent:
		matches = [match for match in matches if Core.nameMatch(reqParent, match.parent)]

	if len(matches) == 0:
		suffix = ""
		if not silent:
			if reqParent:
				det = "an" if reqParent[0] in Data.vowels else "a"
				suffix += f" in {det} '{reqParent}'"
			if queryType == "player":
				suffix += " in your Inventory"
			elif queryType == "room":
				suffix += " here"
			Core.game.print(f"There is no '{term}'{suffix}.")
		return None
	elif len(matches) == 1:
		return matches[0]
	else:
		return chooseObject(term,matches)


# checks if a noun refers to a room, an object in the world or on the player...
# or an action verb, an in-game definition or a miscellaneous expression
def isMeaningful(noun):
	if noun in Core.world or \
	noun in actions or \
	noun in Data.definitions or \
	noun in Data.miscexpressions or \
	noun in Data.hellos or \
	noun in Data.goodbyes or \
	noun in Data.prepositions or \
	Core.player.nameQuery(noun) or \
	Core.game.inWorld(noun):
		return True
	return False


# combines multiple words into single terms that appear to be a meaningful term
# returns the command after any relevant words are joined into one term
# ex. ["attack","green","snake"] -> ["attack","green snake"]
# this algorithm favors the meaningful terms which contain the most words
def nounify(command):
	# i is the index of the starting word
	i = 0
	while i < len(command):
		# j is the index of the ending word
		j = i+1
		while j < len(command):
			possibleNoun = " ".join(command[i:j+1])
			if isMeaningful(possibleNoun):
				# replace elements with joined term element
				command[i:j+1] = [possibleNoun]
			else:
				j += 1
		i += 1
	return command


# iterates over the command list and splits compound words into separate words
def decompose(command):
	i = 0
	while i < len(command):
		word = command[i]
		if word in Data.compounds:
			newwords = Data.compounds[word]
			command[i:i+1] = newwords
		else:
			i += 1
	return command


# if the term is a given pronoun, returns the name of the object which...
# matches the pronoun in the Game class. Intended to return a "best guess"
def replacePronoun(term):
	obj = None
	if term == "it":
		obj = Core.game.it
	elif term in {"she","her"}:
		obj = Core.game.she
	elif term in {"he","him"}:
		obj = Core.game.he
	elif term in {"they","them"}:
		obj = Core.game.they
	if obj == None:
		return term
	return obj.stringName(det=False)


# validates user input and processes into into a command form usable by parse(),
# namely, it returns a list of words without capitals, symbols, or articles
# the last step, nounify(), joins words that may only be meaningful as one term
def processCmd(prompt,storeRawCmd=False):
	rawcommand = Core.game.input(prompt + "\n> ")
	# take input until input has any non-whitespace characters in it
	while not any(i not in "\t " for i in rawcommand):
		rawcommand = Core.game.input("> ")
	# for convenience, save raw command in game object
	if storeRawCmd:
		Core.game.lastRawCommand = rawcommand.split()

	# lowercase-ify the sentence command, copy it excluding symbols
	purecommand = "".join([i for i in rawcommand.lower() if i not in Data.symbols])
	# copy command, delimited by spaces, into a list of words excluding articles
	listcommand = [i for i in purecommand.split() if i not in Data.articles]
	# combine certain words if they appear to make one noun term
	finalcommand = nounify(listcommand)
	# split compound words that ought to be two separate words for parsing
	finalcommand = decompose(finalcommand)
	return finalcommand


def getNoun(prompt):
	return " ".join(processCmd(prompt))


def parseWithoutVerb(prompt,preps):
	dobj = None
	iobj = None
	prep = None
	cmdInput = processCmd(prompt)

	# iterates through the input and assigns...
	# terms based on their position relative to the other terms present
	for term in cmdInput:
		# preposition is defined if the term is a known preposition
		if term in Data.prepositions and prep == None:
			prep = term
		# direct object is defined if prep and dobj havent been found yet
		elif prep == None and dobj == None:
			dobj = term
		# indirect object is defined if a prep or dobj has been found
		else:
			iobj = term

	dobj = replacePronoun(dobj)
	iobj = replacePronoun(iobj)

	return dobj,iobj,prep


# called in parse() when a command fails, it simply recurs parse(), and...
# prints a helpful message if user has provided invalid input 3 or more times
# n is the number of times parse() has recurred
def promptHelp(msg,n):
	if msg != "":
		Core.game.print(msg)
	if n >= 2:
		Core.game.print("Enter 'help' for a list of commands.")
	if n > 32:
		return False	# prevent stack overflow from repeated bad input
	return parse(n+1)	# ask again


# the primary input parsing function for the game
# its purpose is to parse command grammar and call the related action function
# it is called on infinite loop until it returns True
# it returns True only when the player successfully takes an action in the game
# n denotes how many times parse has recurred
def parse(n=0):
	command = processCmd("\n\nWhat will you do?",storeRawCmd=True)
	if len(command) == 0:
		return promptHelp("Command not understood.",n)
	verb = command[0]	# verb is always first word
	dobj = None			# values are None by default, they may remain None
	iobj = None
	prep = None

	# handle cases with special verb commands
	if verb in cheatcodes.keys():
		return cheatcodes[verb](Core.game.lastRawCommand)
	elif verb in Data.hellos:
		return Hello()
	elif verb in Data.goodbyes:
		return Goodbye()
	elif verb in shortactions or verb in Data.traits + Data.abilities:
		# 'cast' may be a stat command or a regular action
		if verb != "cast" or len(command) == 1:
			if len(command) != 1:
				return promptHelp(f"The '{verb}' command can only be one word.",n)
			if verb == "here":
				return Core.game.currentroom.describe()
			if verb in Data.abilities:
				return Core.player.printAbility(verb.upper())
			if verb in Data.traits:
				return Core.player.printTraits(verb.upper())
			return shortactions[verb](Core.player)
	elif verb not in actions:
		return promptHelp(f"'{verb}' is not a valid verb",n)

	# iterates through the command (skips the verb) and assigns...
	# terms based on their position relative to the other terms present
	for term in command[1:]:
		# preposition is defined if the term is a known preposition
		if term in Data.prepositions and prep == None:
			prep = term
		# direct object is defined if prep and dobj havent been found yet
		elif prep == None and dobj == None:
			dobj = term
		# indirect object is defined if a prep or dobj has been found
		elif iobj == None:
			iobj = term

	dobj = replacePronoun(dobj)
	iobj = replacePronoun(iobj)

	# this line calls the action function using the 'actions' dict
	actionCompleted = actions[verb](dobj,iobj,prep)
	# if action was not completed for some reason, recur
	if actionCompleted == False:
		return promptHelp("",n)
	# if action didn't take any time, return False
	if actionCompleted == None:
		return False
	return True




##########################################
## CHEATCODES AND DEV COMMAND FUNCTIONS ##
##########################################

def Evaluate(command):
	if len(command) < 2:
		Core.game.print("Error: No code given")
		return
	code = " ".join(command[1:])
	try:
		Core.game.print(eval(code))
	except Exception as e:
		Core.game.print("Error: Code was unable to be executed.")
		Core.game.print(e)


def Execute(command):
	if len(command) < 2:
		Core.game.print("Error: No code given")
		return
	code = " ".join(command[1:])
	try:
		exec(code)
	except Exception as e:
		Core.game.print("Error: Code was unable to be executed.")
		Core.game.print(e)


def Expell(command):
	if len(command) < 2:
		Core.game.print("Error: no condition given")
		return
	condname = " ".join(command[1:])
	Core.player.removeCondition(condname)


def Get(command):
	if len(command) < 2:
		Core.game.print("Error: No object name given")
		return
	objname = command[1].lower()
	attrname = ( " ".join(command[2:]) ).lower()

	if objname in {"p","player","my"}: obj = Core.player
	elif objname in {"g","game"}: obj = Core.game
	elif objname in {"here","room"}: obj = Core.game.currentroom
	elif objname in {"w","world"}: obj = Core.world
	elif objname in Core.world: obj = Core.world[objname]
	else: obj = findObjFromTerm(objname,playerD=3,roomD=3)
	if obj == None:
		Core.game.print("Error: Object not found")
		return

	if len(command) < 3:
		Core.game.print(obj)
	else:
		try:
			Core.game.print(getattr(obj,attrname))
		except:
			Core.game.print("Error: Attribute does not exist")


def Imbue(command):
	if len(command) < 2:
		Core.game.print("Error: No status condition given")
		return
	if len(command) < 3:
		duration = -2
		condname = " ".join(command[1:])
	else:
		condname = " ".join(command[1:-1])
		try:
			duration = int(command[-1])
		except:
			Core.game.print("Error: Duration not number")
			return


	Core.player.addCondition(condname,duration)


def Learn(command):
	try:
		Core.player.gainxp(int(command[1]))
	except:
		Core.game.print("Error: Value not number")


def Mode(command):
	try:
		Core.game.mode = int(command[1])
		Core.game.print("Mode set to " + str(Core.game.mode))
	except:
		Core.game.print("Error: Value not number")


def Pypot(command):
	try:
		money = int(command[1])
		Core.player.money = Core.player.money + money
		if Core.player.money < 0:
			Core.player.money = 0
		Core.game.print(f"You now have {Core.player.money} money.")
	except:
		Core.game.print("Error: Value not number")


def Set(command):
	if len(command) < 2:
		Core.game.print("Error: No object name given")
		return
	if len(command) < 3:
		Core.game.print("Error: No attribute name given")
		return
	if len(command) < 4:
		Core.game.print("Error: No value given")
		return

	objname = command[1].lower()
	attrname = command[2]
	value = " ".join(command[3:])
	try: value = int(value)
	except: pass

	if objname in {"p","player","my"}: obj = Core.player
	elif objname in {"g","game"}: obj = Core.game
	elif objname in {"here","room"}: obj = Core.game.currentroom
	elif objname in {"w","world"}: obj = Core.world
	else: obj = findObjFromTerm(command[1],playerD=3,roomD=3)

	setattr(obj,attrname,value)


def Spawn(command):
	if len(command) < 2:
		Core.game.print("Error: no object given")
	try:
		obj = eval(" ".join(command[1:]))
	except Exception as e:
		Core.game.print("Error: Object could not be instantiated:")
		Core.game.print(e)
		return False
	if not (isinstance(obj,Core.Creature) or isinstance(obj,Core.Item)):
		Core.game.print("Could not instantiate game object")
	Effects.spawnObject(Core.game.currentroom,obj)


def Teleport(command):
	if len(command) < 2:
		Core.game.print("Error: no location given")
		return
	location = " ".join(command[1:])
	if location in Core.world:
		Core.game.changeRoom(Core.world[location])
	else:
		Core.game.print("Location not in world")


def Test(command):
	Core.game.print(Core.player)
	return True


def Warp(command):
	if len(command) < 2:
		Core.game.print("Error: no warp value given")
		return
	try:
		t = int(command[1])
	except:
		Core.game.print("Value not number")
	Core.game.passTime(t)


def Zap(command):
	if len(command) < 2:
		Core.game.print("Error: no object given")
		return
	objname = " ".join(command[1:])
	key = lambda obj: Core.nameMatch(objname, obj)
	matches = Core.game.queryRooms(key=key)
	zappedObjects = 0
	for obj in matches:
		if isinstance(obj,Core.Item):
			obj.Break()
		elif isinstance(obj,Core.Creature):
			obj.death()
	Core.game.print(f"Zapped objects: {len(matches)}")
	Core.game.reapCreatures()




#######################################
## SHORTACTION AND RELATED FUNCTIONS ##
#######################################


def Cry(*args): Core.game.print("A single tear sheds from your eye.")
def Dance(*args): Core.game.print("You bust down a boogie.")

def Examples(*args):
	Core.clearScreen()
	Core.game.print(Data.examples)
	Core.game.input()
	Core.waitKbInput()
	Core.clearScreen()

def Goodbye(*args): Core.game.print(Core.capWords(choice(list(Data.goodbyes)),c=1))

def Hello(*args): Core.game.print(Core.capWords(choice(list(Data.hellos)),c=1))

def Help(*args):
	Core.clearScreen()
	Core.game.print("\nSingle-Word Commands")
	shortcommands = sorted(tuple(shortactions.keys()) + Data.traits + Data.abilities)
	Core.columnPrint(shortcommands,12,10)
	Core.game.print("\nVerb Commands (Does not include cheat codes and secret commands)")
	Core.columnPrint(actions.keys(),12,10)
	Core.game.print("\nDuring the game, type 'info' for information on the game and how to play.")
	Core.waitKbInput()
	Core.clearScreen()


def Info(*args):
	Core.clearScreen()
	Core.game.print(Data.gameinfo)
	Core.game.input()
	Core.waitKbInput()
	Core.clearScreen()


def Laugh(*args): Core.game.print('"HAHAHAHAHA!"')


def Quit(*args):
	if Core.yesno("Are you sure you want to quit? (Anything unsaved will be lost)"):
		Core.game.quit = True
		return True

def Save(*args): Menu.saveGame()
def Shout(*args): Core.game.print('"AHHHHHHHHHH"')
def Sing(*args): Core.game.print('"Falalalaaaa"')
def Time(*args): Core.game.print("Time:", Core.game.time)
def Yawn(*args): Core.game.print("This is no time for slumber!")




##################################
## ACTION AND RELATED FUNCTIONS ##
##################################


def Attack(dobj,iobj,prep,target=None,weapon=None,weapon2=None):
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False

	if iobj == None:
		if len(Core.player.weapons()) == 0:
			iobj = "fist"
		elif Core.player.gear["right"] == Core.Empty() and Core.player.gear["left"] == Core.Empty():
			iobj = getNoun("What will you attack with?")
			if iobj in Data.cancels: return False

	# assigning weapons based on input and what is in player's hand
	if weapon == None and weapon2 != None:
		weapon, weapon2 = weapon2, None
	if iobj in {"fist","hand"}:
		Core.player.unequip(Core.player.gear["right"])
		weapon = Items.Hand("your hand","",[],"",4,-1,[])
	if iobj in {"foot","leg"}:
		weapon = Items.Foot("your foot","",[],"",6,-1,[])
	if iobj in {"mouth","teeth"}:
		weapon = Items.Mouth("your mouth","",[],"",4,-1,[])
	if iobj != None:
		if weapon == None:
			weapon = Core.player.inGear(iobj)
		if weapon == None:
			weapons = Core.player.inInv(iobj)
			if len(weapons) == 0: Core.game.print(f"There is no '{iobj}' in your Inventory.")
			elif len(weapons) == 1: weapon = weapons[0]
			else: weapon = chooseObject(iobj,weapons)
			if weapon == None: return False
	else:
		if Core.player.gear["right"] != Core.Empty():
			weapon = Core.player.gear["right"]
		elif Core.player.gear["left"] != Core.Empty():
			weapon = Core.player.gear["right"]

	if target == None:
		if dobj == None: dobj = getNoun("What will you attack?")
		if dobj in Data.cancels: return False
		if dobj in {"myself","me"}: target = Core.player
		else: target = findObjFromTerm(dobj,"room")
		if target == None: return False
	Core.game.setPronouns(target)

	stowed = False
	if isinstance(weapon,(Items.Foot,Items.Mouth)):
		stowed = True
		stowedweapons = (Core.player.weapon, Core.player.weapon2)
	if not isinstance(weapon,Core.Weapon):
		weapon = weapon.improviseWeapon()
	Core.player.weapon = weapon

	Core.game.print(f"\nYou attack {target.stringName(definite=True)} with {Core.player.weapon.name}.")
	if isinstance(target,Core.Creature): Core.player.attackCreature(target)
	elif isinstance(target,Core.Item): Core.player.attackItem(target)
	if stowed: Core.player.weapon,Core.player.weapon2 = stowedweapons
	return True


def Bite(dobj,iobj,prep):
	if prep != None:
		Core.game.print("Command not understood.")
	if dobj == None:
		dobj = getNoun("What do you want to bite?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	if Core.hasMethod(I,"Eat"):
		I.Eat()
		return True
	else:
		return Attack(dobj,"mouth",prep,target=I)

	# TODO: if u add the ability to "bite" items, maybe actually damage them...
	# if their durability is low enough or smth. Maybe append the item's...
	# description to include "it has a bite taken out of it"
	# perhaps if player swallows something inedible, take damage?


def Break(dobj,iobj,prep):
	# TODO: potentially just redirect this func to attack, idk
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to break?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Break"):
		Core.game.print(f"You can't break the {I.name}.")
		return False
	if I.Break():
		return True
	else:
		return False


# this is not intended to be called directly from Parse
# but rather from the Take action function
def CarryCreature(creature):
	# TODO: identify a way to link carrier to carried without remove carried creature from Room.creatures
	if not isinstance(creature,Core.Creature):
		Core.game.print(f"You can't carry the {creature.name}")
		return False

	Core.game.print(f"You try to pick up {creature.stringName(definite=True)}.")
	
	if not creature.isAlive():
		Core.player.Carry(creature)
	elif creature.Restrain(Core.player):
		Core.game.print(f"You succesfully restrain {creature.stringName(definite=True)}!")
		Core.player.Carry(creature)
	else:
		Core.game.print(f"You fail to restrain {creature.stringName(definite=True)}!")
		return True
	Core.game.print(f"You are carrying {creature.stringName(definite=True)}.")
	return True


def Cast(dobj,iobj,prep):
	if prep not in {"at","on","onto","upon",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What spell will you cast?")
		if dobj in Data.cancels: return False
	if dobj not in Core.player.spells:
		Core.game.print(f"You don't know a spell called '{dobj}'.")
		return False
	if dobj not in Effects.spells:
		# this shouldn't happen
		Core.game.print("That spell doesn't exist.")
		return False

	target = None
	if prep != None:
		if iobj == None:
			iobj = getNoun(f"What will you cast upon?")
			if iobj in Data.cancels: return False
		target = findObjFromTerm(iobj,"room")

	return Effects.spells[dobj](target)


def Catch(dobj,iobj,prep):
	Core.game.print("catching")


# TODO:
# def Climb(dobj,iobj,prep):
# 	Core.game.print("climbing")


def Close(dobj,iobj,prep):
	if prep != None:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you close?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not hasattr(I,"open"):
		Core.game.print(f"The {I.name} doesn't close.")
		return False
	if not I.open:
		Core.game.print(f"The {I.name} is already closed.")
		return False
	if Core.hasMethod(I,"Close"):
		I.Close()
	else:
		I.open = False
		Core.game.print(f"You close the {I.name}.")
	return True


def Craft(dobj,iobj,prep):
	Core.game.print("crafting")


def Crawl(dobj,iobj,prep):
	if prep in {"behind","below","beneath","under",None}:
		return Crouch(dobj,iobj,prep)
	if prep in {"in","inside","into","through"}:
		Crouch(None,None,None)
		return Go(dobj,iobj,prep)


def Cross(dobj,iobj,prep):
	Core.game.print("crossing")


def Crouch(dobj,iobj,prep):
	if prep not in {"behind","below","beneath","inside","under",None}:
		Core.game.print("Command not understood.")
		return False

	if dobj != None:
		dobj = iobj
	if dobj != None:
		return Hide(dobj,iobj,prep)

	Core.player.addCondition("crouched",-3)
	return True


def Cut(dobj,iobj,prep):
	Core.game.print("cuting")


def Define(dobj,iobj,prep):
	if iobj != None or prep != None:
		Core.game.print("Can only define one word at once.")
		return False
	if dobj == None:
		dobj = getNoun("What term would you like defined?")
		if dobj in Data.cancels: return False

	if dobj in Data.definitions:
		Core.game.print("\n"+Data.definitions[dobj])
		return True
	elif Core.game.inWorld(dobj):
		return Look(dobj,iobj,prep)
	elif dobj == Core.player.name.lower():
		Core.game.print(f"\n{Core.player.name}\nThat is you!")
		return True
	Core.game.print(f"'{dobj}' is unknown")
	return False


def Describe(dobj,iobj,prep):
	if iobj != None or prep != None:
		Core.game.print("Can only describe one thing at once.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to be described?")
		if dobj in Data.cancels: return False

	if dobj == Core.game.currentroom.name or dobj in {"room","here"}:
		D = Core.game.currentroom
	else:
		D = findObjFromTerm(dobj)
	if D == None: return False
	Core.game.setPronouns(D)

	D.describe()
	return True


def Do(dobj,iobj,prep):
	Core.game.print("doing")


def Dodge(dobj,iobj,prep):
	Core.game.print("dodgeing")


def Doff(dobj,iobj,prep):
	if prep != None:
		Core.game.print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to doff?")
		if dobj in Data.cancels: return False

	I = Core.player.inGear(dobj)
	if I == None or not isinstance(I,Core.Armor):
		Core.game.print(f"You aren't wearing a '{dobj}'.")
		return False
	Core.game.setPronouns(I)

	Core.player.unequip(I)
	Core.game.print(f"You doff your {I.name}.")
	return True


def Don(dobj,iobj,prep):
	if prep != None:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to don?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"player")
	if I == None: return False
	Core.game.setPronouns(I)

	if not isinstance(I,Core.Armor):
		Core.game.print(f"You cannot wear your {I.name}.")
		return False
	if I in Core.player.gear.values():
		Core.game.print(f"You are already wearing your {I.name}.")
		return False

	if not Core.player.equipArmor(I):
		return False
	Core.game.print(f"You don your {I.name}.")
	return True


def Drink(dobj,iobj,prep):
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to drink?.")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Drink"):
		Core.game.print(f"You can't drink the {I.name}.")
		return False
	I.Drink()
	return True


def Drop(dobj,iobj,prep,I=None,R=None):
	if prep not in {"down",None}:
		return Put(dobj,iobj,prep)
	if dobj == None and I == None:
		dobj = getNoun("What will you drop?.")
		if dobj in Data.cancels: return False

	if I == None: I = findObjFromTerm(dobj,"player")
	if I == None: return False
	Core.game.setPronouns(I)

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	I.parent.removeItem(I)
	if isinstance(I, Core.Creature):
		Core.game.print(f"You drop {I.stringName(definite=True)}")
		Core.game.currentroom.addCreature(I)
	else:
		Core.game.print(f"You drop your {I.name}")
		Core.game.currentroom.addItem(I)
	return True


def Dump(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","out","upon",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you dump?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"player")
	if I == None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Pour"):
		return Pour(dobj,iobj,prep,I=I)
	else:
		return Drop(dobj,iobj,prep,I=I)


def Eat(dobj,iobj,prep):
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to eat?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Eat"):
		Core.game.print(f"You can't eat the {I.name}.")
		return False
	I.Eat()
	return True


def Enter(dobj,iobj,prep):
	if dobj == None and "in" in Core.game.currentroom.exits:
		return Go("in",iobj,prep)
	return Go(dobj,iobj,prep)


def Equip(dobj,iobj,prep):
	if prep != None:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to equip?")
		if dobj in Data.cancels:
			return False

	matches = Core.player.inInv(dobj)
	if len(matches) == 0:
		Core.game.print(f"There is no {dobj} in your Inventory")
	I = chooseObject(dobj,matches)
	if I == None: 
		return False
	Core.game.setPronouns(I)

	if I in Core.player.gear.values():
		Core.game.print(f"Your {I.name} is already equipped.")
		return False
	# if item is armor, equip it as armor, otherwise, equip it in hand
	if isinstance(I,Core.Armor):
		Core.player.equipArmor(I)
	else:
		Core.player.equipInHand(I)
	Core.game.print(f"You equip your {I.name}.")
	return True


def Escape(dobj,iobj,prep):
	Core.game.print("escapeing")


def Exit(dobj,iobj,prep):
	if dobj == None and "out" in Core.game.currentroom.exits:
		return Go("out",iobj,prep)
	return Go(dobj,iobj,prep)


def Feed(dobj,iobj,prep):
	Core.game.print("feeding")


def Fill(dobj,iobj,prep):
	Core.game.print("filling")


def Find(dobj,iobj,prep):
	Core.game.print("finding")


def Fish(dobj,iobj,prep):
	Core.game.print("fishing")


def Follow(dobj,iobj,prep):
	Core.game.print("following")


def Fuck(dobj,iobj,prep):
	Core.game.print("There's a time and place for everything, but not now.")


def Give(dobj,iobj,prep):
	Core.game.print("giveing")


# not called by Parse directly
# called when the user wants to go "up" or "down"
def GoVertical(dir,passage=None,dobj=None):
	if Core.player.hasCondition("flying"):
		newroom = Core.game.currentroom.allExits()[dir]
		Core.game.print(f"You fly {dir}!")
		return Core.game.changeRoom(Core.world[newroom])

	if passage == None and dobj != None:
		Core.game.print(f"There is no '{dobj}' to go {dir} here.")
		return False
	if passage == None:
		passagename = getNoun(f"What will you go {dir}?")
		passage = findObjFromTerm(passagename,"room")
	if passage == None:
		Core.game.print(f"There is no '{passagename}' to go {dir} here.")
		return False
	if Core.hasMethod(passage,"Traverse"):
		return passage.Traverse(dir)


# infers direction, destination, and passage (if they exist) from input terms
def assignGoTerms(dobj,iobj,prep):
	dir,dest,passage = None,None,None

	# assign dir
	if dobj in Data.directions.values(): dir = dobj
	elif iobj in Data.directions.values(): dir = iobj
	else: dir = prep

	# assign dest
	if dobj in Core.game.currentroom.allExits().values(): dest = dobj
	elif Core.nameMatch(dobj,Core.game.currentroom): dest = dobj
	if iobj in Core.game.currentroom.allExits().values(): dest = iobj
	elif Core.nameMatch(iobj,Core.game.currentroom): dest = iobj

	# assign passage
	if dobj != None: passage = findObjFromTerm(dobj,"room",silent=True)
	elif iobj != None: passage = findObjFromTerm(iobj,"room",silent=True)

	return dir,dest,passage


# parses user input to determine the intended direction, destination, and/or
# passage. Then calls either traverse or changeroom accordingly
def Go(dobj,iobj,prep):
	preps = {"down","through","to","toward","up","in","inside","into","on","onto","out",None}
	if (dobj,iobj,prep) == (None,None,None):
		dobj,iobj,prep = parseWithoutVerb("Where will you go?",preps)
	if dobj in Data.cancels: return False
	if dobj in ("back", "backward", "backwards"): dobj = Core.game.prevroom.name.lower()
	if dobj in ("ahead", "forward", "forwards"): dobj = getNoun("In which direction?")
	if dobj == None: dobj = iobj

	# if any terms are abbreviations for a direction, expand them
	dobj,iobj,prep = map(Core.expandDir,[dobj,iobj,prep])
	if prep not in preps:
		Core.game.print("Command not understood.")
		return False

	# get dir, dest, and passage and validate them
	dir,dest,passage = assignGoTerms(dobj,iobj,prep)
	if (dir,dest,passage) == (None,None,None):
		Core.game.print(f"There is no exit leading to a '{dobj}' here.")
		return False
	if Core.nameMatch(dest,Core.game.currentroom):
		Core.game.print(f"You are already there!")
		return False
	if dir == None:
		dir = Core.game.currentroom.getDirFromDest(dest)
	if (dest,passage) == (None,None):
		if dir in Core.game.currentroom.allExits():
			dest = Core.game.currentroom.allExits()[dir]
	if passage == None:
		passage = Core.game.currentroom.getPassageFromDir(dir)
	if (dest,passage) == (None,None):
		if dir != None and dir not in Core.game.currentroom.allExits():
			Core.game.print(f"There is no exit leading '{dir}' here.")
			return False

	# call one of three functions to actually change rooms
	# depends if they go normally, traverse a passage, or go vertically
	if dir == "up" or dir == "down":
		return GoVertical(dir,passage,dobj)
	# if just passage is given
	if passage != None:
		if not Core.hasMethod(passage,"Traverse"):
			Core.game.print(f"The {passage.name} cannot be traversed.")
			return False
		return passage.Traverse(dir)
	# if just dest given
	if dest != None:
		return Core.game.changeRoom(Core.world[dest])
	Core.game.print(f"There is no exit leading to a '{dobj}' here.")
	return False


def Hide(dobj,iobj,prep):
	if prep not in {"behind","below","beneath","inside","under",None}:
		Core.game.print("Command not understood.")
		return False

	if dobj == None: dobj = iobj
	if dobj == None:
		dobj = getNoun("What do you want to hide behind?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"room")
	if I == None: return False
	Core.game.setPronouns(I)

	if not isinstance(I,Core.Fixture) or I.weight < 50:
		Core.game.print(f"You can't hide behind {I.name}.")
		return False

	Core.player.addCondition("hiding",-3)
	return True


def Ignite(dobj,iobj,prep):
	Core.game.print("igniteing")


def Insert(dobj,iobj,prep):
	Core.game.print("inserting")


def Jump(dobj,iobj,prep):
	Core.game.print("jumping")


def Kick(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you kick?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"foot","with")


def Kill(dobj,iobj,prep):
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj in {"myself","me"}:
		if Core.yesno("Are you sure you want to kill yourself?"):
			Core.player.death()
			return True
		Core.game.print("Fwew, that was close!")
		return False
	return Attack(dobj,iobj,prep)


def Lick(dobj,iobj,prep):
	Core.game.print("licking")


def Light(dobj,iobj,prep):
	Core.game.print("lighting")


def Listen(dobj,iobj,prep):
	Core.game.print("listening")


def Lock(dobj,iobj,prep):
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False

	if dobj == None:
		dobj = getNoun("What will you lock?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Lock"):
		Core.game.print(f"The {I.name} doesn't lock.")
		return False

	if iobj == None:
		iobj = getNoun("What will you lock with?")
		if iobj in Data.cancels: return False
	K = findObjFromTerm(iobj,"player")
	if K == None: return False

	if not isinstance(K,Items.Key):
		Core.game.print(f"You can't lock with the {K.name}.")
		return False
	return I.Lock(K)


def Look(dobj,iobj,prep):
	if prep not in {"at","in","inside","into","on","through",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None: dobj = iobj
	if dobj == None:
		dobj = getNoun("What will you look at?")
		if dobj in Data.cancels: return False

	if dobj in {"around","here","room"} or dobj == Core.game.currentroom.name.lower():
		Core.game.currentroom.describe()
		return True
	if dobj in {"me","myself",Core.player.name}:
		Core.game.print(f"You are {Core.player.desc}")
		return True

	L = findObjFromTerm(dobj)
	if L == None: return False
	Core.game.setPronouns(L)

	L.describe()
	if Core.hasMethod(L,"Look"):
		L.Look()
	return True


def Mount(dobj,iobj,prep):
	Core.game.print("mounting")


def Move(dobj,iobj,prep):
	Core.game.print("moveing")


def Open(dobj,iobj,prep):
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you open?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Open"):
		Core.game.print(f"The {I.name} doesn't open.")
		return False
	if hasattr(I,"locked") and I.locked:
		Core.game.print(f"The {I.name} is locked")
		return False
	I.Open()
	return True


def Pet(dobj,iobj,prep):
	Core.game.print("peting")


def Play(dobj,iobj,prep):
	Core.game.print("playing")


def Point(dobj,iobj,prep):
	Core.game.print("pointing")


def Pour(dobj,iobj,prep,I=None):
	if prep not in {"in","into","inside","on","onto","out","upon",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you pour?")
		if dobj in Data.cancels: return False

	if I == None: I = findObjFromTerm(dobj,"player")
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Pour"):
		Core.game.print(f"You can't pour the {I.name}.")
		return False

	R = None
	if iobj != None and iobj not in {"floor","ground","here"}:
		R = findObjFromTerm(iobj)
		if R == None: return False

	if prep == None: prep = "on"
	if R != None: Core.game.print(f"You pour your {I.name} {prep} the {R.name}.")
	else: Core.game.print(f"You pour out your {I.name}.")
	I.Pour(R)
	return True


def Pray(dobj,iobj,prep):
	Core.game.print("praying")


def Press(dobj,iobj,prep):
	Core.game.print("pressing")


def Pull(dobj,iobj,prep):
	Core.game.print("pulling")


def Punch(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you punch?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"fist","with")


def Push(dobj,iobj,prep):
	Core.game.print("pushing")


def Put(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon","down",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you put?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"player")
	if I == None: return False
	Core.game.setPronouns(I)

	if iobj == None:
		iobj = getNoun(f"What will you put your {dobj} in?")
		if iobj in Data.cancels: return False

	if iobj in {"floor","ground","here"}:
		return Drop(dobj,iobj,prep,I=I)
	R = findObjFromTerm(iobj)
	if R == None: return False

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	if not Core.hasMethod(R,"addItem"):
		Core.game.print(f"You can't put the {I.name} {prep} the {R.name}.")
		return False
	
	idet = "your" if Core.player in I.ancestors() else "the"
	rdet = "your" if Core.player in R.ancestors() else "the"
	outprep = "on" if isinstance(R,Items.Table) else "in"
	if iobj == "here": Core.game.print(f"You put your {I.name} here.")
	else: Core.game.print(f"You put {idet} {I.name} {outprep} {rdet} {R.name}.")
	I.parent.removeItem(I)
	R.addItem(I)
	return True


def Release(dobj,iobj,prep):
	Core.game.print("releaseing")


def Rest(dobj,iobj,prep):
	Core.game.print("resting")


def Restrain(dobj,iobj,prep):
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False

	if dobj == None:
		dobj = getNoun("What will you restrain?")
		if dobj in Data.cancels: return False

	C = findObjFromTerm(dobj,"room")
	if C == None: return False
	Core.game.setPronouns(C)

	if not isinstance(C,Core.Creature):
		Core.game.print(f"You can't restrain the {C.name}.")
		return False

	I = None
	if iobj != None:
		I = findObjFromTerm(iobj,"player")
		if I == None: return False
		if not Core.hasMethod(I,"RestrainWith"):
			Core.game.print(f"You can't restrain with the {I.name}.")
			return False

	if not C.Restrain(Core.player,I):
		Core.game.print(f"You fail to restrain the {C.name}.")
		return False
	Core.game.print(f"You restrain the {C.name}.")
	return True


def Return(*args): 
	return Go(None, Core.game.prevroom.name.lower(), None)


def Ring(dobj,iobj,prep):
	Core.game.print("ringing")


def Rub(dobj,iobj,prep):
	Core.game.print("rubbing")


def Search(dobj,iobj,prep):
	Core.game.print("searching")


def Shoot(dobj,iobj,prep):
	Core.game.print("shooting")


def Shove(dobj,iobj,prep):
	Core.game.print("shoveing")


def Smell(dobj,iobj,prep):
	Core.game.print("smelling")


def Steal(dobj,iobj,prep,I=None):
	Core.game.print(f"stealing {dobj} {prep} {iobj}")


def Struggle(dobj,iobj,prep):
	Core.game.print("struggleing")


def Swim(dobj,iobj,prep):
	Core.game.print("swiming")


def Talk(dobj,iobj,prep):
	if prep not in {"at","into","to","toward","with",None}:
		Core.game.print("Command not understood.")
		return False

	if dobj == None: dobj = iobj
	if dobj == None:
		dobj = getNoun("Who do you want to talk to?")
		if dobj in Data.cancels: return False

	target = findObjFromTerm(dobj,"room")
	if target == None: 
		return False
	Core.game.setPronouns(target)

	if not hasattr(target,'Talk'):
		Core.game.print(f"There is no response...")
		return False

	target.Talk(Core.player,Core.game,Core.world)
	return True


def Throw(dobj,iobj,prep):
	Core.game.print("throwing")


def Tie(dobj,iobj,prep):
	Core.game.print("tieing")


# if an item is a container, take each of its contents before taking it
def TakeAllRecur(objToTake):
	takenAll = True
	takenAny = False
	if hasattr(objToTake, "contents"):
		# deep copy to prevent removing-while-iterating error
		contents = [obj for obj in objToTake.contents()]
		for content in contents:
			takenAny = TakeAllRecur(content) or takenAny

	parent = objToTake.parent
	count = parent.itemNames().count(objToTake.name)
	
	if parent is Core.game.currentroom: suffix = ""
	elif Core.player in objToTake.ancestors(): suffix = " from your " + parent.name
	else: suffix = " from the " + parent.name
	strname = objToTake.stringName(definite=(count==1))
	tookMsg = f"You take {strname}{suffix}."
	failMsg = f"You can't take the {objToTake.name}, your Inventory is too full."

	return Core.player.obtainItem(objToTake,tookMsg,failMsg) or takenAny


def TakeAll():
	if len(Core.game.currentroom.items) == 0:
		Core.game.print("There are no items to take.")
		return False
	takenAny = False
	for obj in [obj for obj in Core.game.currentroom.items]:
		takenAny = TakeAllRecur(obj) or takenAny
	return takenAny


def Take(dobj,iobj,prep):
	if prep not in {"from","in","inside","out","out of","up",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you take?")
		if dobj in Data.cancels: return False

	if dobj in {"all","everything","it all"}: return TakeAll()

	filt = lambda x: x.parent is not Core.player
	if iobj in ("here", "room"):
		obj = findObjFromTerm(dobj,"room",roomD=2,filter=filt)
	else:
		obj = findObjFromTerm(dobj,roomD=2,filter=filt,reqParent=iobj)
	if obj == None: return False
	Core.game.setPronouns(obj)

	if isinstance(obj,Core.Creature): return CarryCreature(obj)
	if not isinstance(obj,Core.Item) or isinstance(obj,Core.Fixture):
		Core.game.print(f"You can't take the {dobj}.")
		return False

	parent = obj.parent	
	# if it is in a non-player inventory, it will have to be stolen
	if any(isinstance(anc,Core.Creature) for anc in obj.ancestors()) and obj not in Core.player.invSet():
		return Steal(dobj,iobj,prep,I=obj)
	count = parent.itemNames().count(obj.name)

	if parent is Core.game.currentroom: suffix = ""
	elif Core.player in obj.ancestors(): suffix = " from your " + parent.name
	else: suffix = " from the " + parent.name
	strname = obj.stringName(definite=(count==1))
	tookMsg = f"You take {strname}{suffix}."
	failMsg = f"You can't take the {obj.name}, your Inventory is too full."

	return Core.player.obtainItem(obj,tookMsg,failMsg)


def Touch(dobj,iobj,prep):
	Core.game.print("touching")


def Trip(dobj,iobj,prep):
	Core.game.print("triping")


def Unequip(dobj,iobj,prep):
	if prep != None:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to unequip?")
		if dobj in Data.cancels: return False

	I = Core.player.inGear(dobj)
	if I == None:
		Core.game.print(f"You do not have a '{dobj}' equipped.")
		return False
	Core.game.setPronouns(I)

	Core.game.print(f"You unequip your {I.name}.")
	Core.player.unequip(I)
	return True


def Unlock(dobj,iobj,prep):
	if prep not in {"using","with",None}:
		Core.game.print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you unlock?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)
	if not Core.hasMethod(I,"Unlock"):
		Core.game.print(f"The {I.name} doesn't unlock.")
		return False

	if iobj == None:
		iobj = getNoun("What will you unlock with?")
		if iobj in Data.cancels: return False

	K = findObjFromTerm(iobj,"player")
	if K == None: return False

	if not isinstance(K,Items.Key):
		Core.game.print(f"You can't unlock with the {K.name}.")
		return False
	return I.Unlock(K)


def Untie(dobj,iobj,prep):
	Core.game.print("untieing")


def Use(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you use?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Use"):
		Core.game.print(f"You can't use the {I.name}.")
		return False
	I.Use()
	return True


def Wait(dobj,iobj,prep):
	Core.game.print("waiting")


def Wave(dobj,iobj,prep):
	Core.game.print("waveing")




##################################
## ACTION FUNCTION DICTIONARIES ##
##################################


cheatcodes = {
	"\\evl":Evaluate,
	"\\exe":Execute,
	"\\get":Get,
	"\\lrn":Learn,
	"\\mbu":Imbue,
	"\\mod":Mode,
	"\\pot":Pypot,
	"\\set":Set,
	"\\spn":Spawn,
	"\\tst":Test,
	"\\tpt":Teleport,
	"\\wrp":Warp,
	"\\xpl":Expell,
	"\\zap":Zap
}

# contains corresponding functions for all items in Data.shortverbs or stat commands
shortactions = {
"abilities":Core.Player.printAbility,
"back":Return,
"back up":Return,
"clear":Core.clearScreen,
"examples":Examples,
"gear":Core.Player.printGear,
"help":Help,
"hello":Hello,
"here":Core.game.currentroom.describe,
"hi":Hello,
"hp":Core.Player.printHP,
"info": Info,
"information": Info,
"inventory":Core.Player.printInv,
"inv":Core.Player.printInv,
"level":Core.Player.printLV,
"lv":Core.Player.printLV,
"money":Core.Player.printMoney,
"mp":Core.Player.printMP,
"quit":Quit,
"rp":Core.Player.printRP,
"save":Save,
"spells":Core.Player.printSpells,
"stats":Core.Player.printStats,
"status":Core.Player.printStatus,
"time":Time,
"traits":Core.Player.printTraits,
"weapons":Core.Player.printWeapons,
"xp":Core.Player.printXP,
"yawn":Yawn
}

actions = {
"attack":Attack,
"bite":Bite,
"break":Break,
"build":Craft,
"carry":Take,
"cast":Cast,
"catch":Catch,
"climb":Go,
"close":Close,
"craft":Craft,
"crawl":Crawl,
"create":Craft,
"cross":Cross,
"crouch":Crouch,
"cut":Cut,
"cry":Cry,
"dance":Dance,
"define":Define,
"describe":Describe,
"do":Do,
"dodge":Dodge,
"doff":Doff,
"don":Don,
"drink":Drink,
"drop":Drop,
"duck":Crouch,
"dump":Dump,
"dump out":Dump,
"eat":Eat,
"empty":Dump,
"enter":Enter,
"equip":Equip,
"escape":Escape,
"examine":Look,
"exit":Exit,
"feed":Feed,
"feel":Touch,
"fight":Attack,
"fill":Fill,
"find":Find,
"fish":Fish,
"follow":Follow,
"fuck":Fuck,
"get":Take,
"give":Give,
"go":Go,
"grab":Take,
"grapple":Take,
"head":Go,
"hear":Listen,
"hide":Hide,
"hit":Attack,
"ignite":Ignite,
"insert":Insert,
"jump":Jump,
"kick":Kick,
"kill":Kill,
"laugh":Laugh,
"lay":Crouch,
"leave":Exit,
"lick":Lick,
"light":Ignite,
"listen":Listen,
"lock":Lock,
"look":Look,
"make":Craft,
"mount":Mount,
"move":Move,
"obtain":Take,
"open":Open,
"pet":Pet,
"pick":Take,
"pick up":Take,
"place":Put,
"play":Play,
"point":Point,
"pour":Pour,
"pour out":Pour,
"pray":Pray,
"press":Press,
"pull":Pull,
"punch":Punch,
"push":Push,
"put":Put,
"put away":Unequip,
"put down":Drop,
"put on":Don,
"quaff":Drink,
"read":Look,
"release":Release,
"remove":Unequip,
"rest":Rest,
"restrain":Restrain,
"return":Return,
"ride":Mount,
"ring":Ring,
"rub":Rub,
"run":Go,
"scream":Shout,
"search":Search,
"set":Put,
"set down":Drop,
"shoot":Shoot,
"shout":Shout,
"shove":Shove,
"shut":Close,
"sing":Sing,
"slap":Punch,
"sleep":Rest,
"slice":Cut,
"smell":Smell,
"sneak":Crouch,
"sniff":Smell,
"speak":Talk,
"steal":Steal,
"stomp":Kick,
"stow":Unequip,
"strike":Attack,
"struggle":Struggle,
"swim":Swim,
"take":Take,
"take off":Doff,
"talk":Talk,
"taste":Lick,
"throw":Throw,
"tie":Tie,
"tinker":Craft,
"toss":Throw,
"touch":Touch,
"travel":Go,
"trip":Trip,
"unequip":Unequip,
"unlock":Unlock,
"untie":Untie,
"use":Use,
"view":Look,
"wait":Wait,
"walk":Go,
"wave":Wave,
"wear":Don,
"yell":Shout
}


# headbutt
# poke
# think
# show/reveal
# write
# remove clothing/strip
# draw/sheath/stow
# bow
# slap
# sit
# vomit?
# sniff
# grunt/moan/groan/roar/rawr/argh/snarl
# squirm -> struggle
# dive/jump/leap
# untie
# whip (attack)
# dress/undress/strip
# spit
# converse/communicate/discuss
# say hello -> hello
# sprint/run
# flick?
# insert (key) -> unlock
# lift -> carry
# mix/stir -> brew?
# greet -> wave or talk?
# scratch/itch
# knock/bang
# switch
# smoke
# weave/sew
# evade -> dodge
# stare/gaze -> look
# fart, burp
# pick -> a lock or a berry
# kiss/smooch
# shake?
# browse/peruse -> look
# pilfer -> steal
# swing (an item)
# ligma/sugma
# buy/pay/purchase, sell, trade
# embrace/hug
# stab/slash
# shave?
# swallow
# fly/float/hover? (rename the spell)
# pierce
# hump -> fuck
# curse/swear
# squat - > crouch
# pee/poop/shit on (soil your pants if they have them on)
# caress -> pet
# choke/strangle
# paint/draw
# carve/whittle
# chase -> follow?
# drive -> ride
# feed (food) -> give
# scale -> climb
# water -> pour on
# dig, bury
# rip, tear -> break
# reload?
# reel -> fish?
# cook/brew
# clean/sweep/mop/wipe?
# lay -> lay? (make own command?)
# chop -> slash -> atk
# chew -> eat
# strike -> ignite/hit
# lift -> carry
# kneel -> crouch
# lasso
# ask/inquire -> talk
# snuff/put out/blow out
# investigate -> examine -> look??
# sit
# stand
# backflip??
# row/steer (if not mounted -> ride, else -> go)
# stop, get off, dismount
# blow/breath
# clap
# snap
# observe/watch