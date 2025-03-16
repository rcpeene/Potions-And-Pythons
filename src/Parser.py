# Parser.py
# This file contains the code to parse user input and execute player actions
# This file is dependent on Menu.py and is a dependency of PoPy.py

# It consists of three main parts;
# 1. Parsing functions	(functions to parse user input)
# 2. Action functions	(action, shortaction, cheat functions called by parse())
# 3. Action dicts		(dictionaries used to call action functions from)

from random import choice,randint

import Data
import Core
import Menu
import Items
import Creatures
import Effects


helpCounter = 0

#######################
## PARSING FUNCTIONS ##
#######################


# this is used to disambiguate user input...
# when the object name given is not specific enough
# takes the object name and list of matching objects
# prints the list of objects with entry 'tags' to help the user distinguish them
# will return when user cancels or when they select an object by name or number
def chooseObject(name,objects,verb=None):
	if objects is None or len(objects) == 0:
		return None
	if len(objects) == 1:
		return objects[0]
	Core.Print()
	for n,object in enumerate(objects):
		labels = []
		if isinstance(object,Core.Creature):
			if not object.isAlive():
				labels.append("dead")
			else:
				labels.append(f"{object.hp} hp")
		if not isinstance(object.parent,(Core.Room,Core.Player)):
			labels.append(object.parent.name)
		if object in Core.player.gear.values():
			labels.append("equipped")
		elif object in Core.player.invSet():
			labels.append("Inventory")
		elif object.determiner:
			labels.append(object.determiner)
		
		strLabel = ""
		if len(labels) >= 1:
			for label in labels[:-1]:
				strLabel += label + ","
			strLabel = " (" + strLabel + labels[-1] + ")"

		Core.Print(f"{n+1}. {object}{strLabel}",color="k")
	verb = f" to {verb}" if verb else ""
	Core.Print(f"\nWhich {name}{verb}?",color="k")

	invalid_count = 0
	while True:
		choice = Core.Input().lower()
		if choice == "": continue
		if choice in Data.cancels: return None

		try:
			return objects[int(choice)-1]
		except:
			for obj in objects:
				if choice == obj.nounPhrase().lower():
					return obj
		Core.Print("That is not one of the options.",color="k")
		if invalid_count >= 3:
			Core.Print("Type 'cancel' to undo this action.",color="k")
		invalid_count += 1


# return an object in player inv or room based on player input
# gets a list of potential objects whose name matches the given user input term
# queryPlayer and queryRoom indicate which places to look for matching objects
# roomD and playerD are the 'degree' of the query.
# Look at Core.py objQuery for details on query degree
def findObjFromTerm(term,queryType="both",verb=None,filter=None,roomD=1,playerD=2,reqParent=None,silent=False):
	# allows for users to describe objects they possess
	my = False
	if term.startswith("my "):
		term = term[3:]
		my = True

	matches = []
	if queryType == "player" or queryType == "both":
		matches += Core.player.nameQuery(term,d=playerD)
	if queryType == "room" or queryType == "both":
		matches += Core.game.nameQueryRoom(term,d=roomD)

	if filter:
		matches = [match for match in matches if filter(match)]
	if reqParent:
		matches = [match for match in matches if Core.nameMatch(reqParent, match.parent)]
	if my:
		matches = [match for match in matches if Core.player in match.ancestors() or match.determiner == "your"]

	if len(matches) == 0:
		suffix = ""
		if not silent:
			if reqParent:
				det = "an" if reqParent[0] in Data.vowels else 'a'
				suffix += f" in {det} '{reqParent}'"
			if queryType == "player" or my:
				suffix += " in your Inventory"
			elif queryType == "room":
				suffix += " here"
			Core.Print(f"There is no '{term}'{suffix}.",color="k")
		return None
	elif len(matches) == 1:
		return matches[0]
	else:
		return chooseObject(term,matches,verb)


# checks if a noun refers to a room, an object in the world or on the player...
# or an action verb, an in-game definition or a miscellaneous expression
def isMeaningful(noun):
	if noun in Core.world or \
	noun in actions or \
	noun in shortactions or \
	noun in Data.definitions or \
	noun in Data.miscexpressions or \
	noun in Data.hellos or \
	noun in Data.goodbyes or \
	noun in Data.prepositions or \
	noun in Core.game.currentroom.exits.keys() or \
	noun in Items.factory or \
	noun in Creatures.factory or \
	Core.game.inWorld(noun) or \
	Core.player.nameQuery(noun):
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
			if isMeaningful(possibleNoun) or command[i] == "my":
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
	elif term in ("she","her"):
		obj = Core.game.she
	elif term in ("he","him"):
		obj = Core.game.he
	elif term in ("they","them"):
		obj = Core.game.they
	if obj is None:
		return term
	return obj.nounPhrase()


# validates user input and processes into into a command form usable by parse(),
# namely, it returns a list of words without capitals, symbols, or articles
# nounify() joins words that may only be meaningful as one term
def processCmd(prompt,storeRawCmd=False):
	rawcommand = Core.Input(prompt,low=False)
	# take input until input has any non-whitespace characters in it
	while not any(i not in "\t " for i in rawcommand):
		Core.flushInput()
		rawcommand = Core.Input("",cue="> ",low=False)
	# for convenience, save raw command in game object
	if storeRawCmd:
		Core.game.lastRawCommand = rawcommand.split()

	# lowercase-ify the sentence command, copy it excluding symbols
	purecommand = "".join([i for i in rawcommand if i not in Data.symbols]).lower()
	# split command into list of words, but combine words that seem to be single terms
	splitcommand = nounify(purecommand.split())	
	# split compound words that ought to be two separate words for parsing
	splitcommand = decompose(splitcommand)
	# remove articles and determiners (and other extraneous words)
	finalcommand = [word for word in splitcommand if word not in Data.articles]
	return finalcommand


def getNoun(prompt):
	return " ".join(processCmd(prompt))


def parseWithoutVerb(cmdInput):
	dobj = None
	iobj = None
	prep = None

	# iterates through the input and assigns...
	# terms based on their position relative to the other terms present
	for term in cmdInput:
		# preposition is defined if the term is a known preposition
		if term in Data.prepositions and prep is None:
			prep = term
		# direct object is defined if prep and dobj havent been found yet
		elif prep is None and dobj is None:
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
def promptHelp(msg):
	global helpCounter
	if msg != "":
		Core.Print(msg,color="k")
	helpCounter += 1
	if helpCounter >= 3:
		Core.Print("Enter 'help' for instructions.",color="k")
	return False


# the primary input parsing function for the game
# its purpose is to parse command grammar and call the related action function
# it is called on infinite loop until it returns True
# it returns True only when the player successfully takes an action in the game
# n denotes how many times parse has recurred
def parse():
	global helpCounter
	command = processCmd("\n\nWhat will you do?",storeRawCmd=True)
	if len(command) == 0:
		return promptHelp("Command not understood.")
	verb = command[0]	# verb is always first word

	# handle cases with special verb commands
	if verb in cheatcodes.keys():
		return cheatcodes[verb](Core.game.lastRawCommand)
	elif verb in Data.hellos:
		return Hello()
	elif verb in Data.goodbyes:
		return Goodbye()
	elif verb in shortactions or verb in Data.traits + Data.abilities or verb in Data.colors:
		# 'cast' may be a stat command or a regular action
		if verb != "cast" or len(command) == 1:
			if len(command) != 1:
				return promptHelp(f"The '{verb}' command can only be one word.")
			if verb == "here":
				return Core.game.currentroom.describe()
			if verb in Data.abilities:
				return Core.player.printAbility(verb.upper())
			if verb in Data.traits:
				return Core.player.printTraits(verb)
			if verb in Data.colors:
				return Core.Print(verb.title()+".", color=Data.colors[verb])
			return shortactions[verb](Core.player)
	elif verb not in actions:
		return promptHelp(f"'{verb}' is not a valid verb")

	dobj,iobj,prep = parseWithoutVerb(command[1:])
	# this line calls the action function using the 'actions' dict
	actionCompleted = actions[verb](dobj,iobj,prep)
	helpCounter = 0
	# if action didn't take any time, return False
	if actionCompleted is None:
		return False
	return True




##########################################
## CHEATCODES AND DEV COMMAND FUNCTIONS ##
##########################################

def Evaluate(command):
	if len(command) < 2:
		Core.Print("Error: No code given",color="k")
		return
	code = " ".join(command[1:])
	try:
		Core.Print(eval(code))
	except Exception as e:
		Core.Print("Error: Code was unable to be executed.",color="k")
		Core.Print(e)


def Execute(command):
	if len(command) < 2:
		Core.Print("Error: No code given",color="k")
		return
	code = " ".join(command[1:])
	try:
		exec(code)
	except Exception as e:
		Core.Print("Error: Code was unable to be executed.",color="k")
		Core.Print(e)


def Expell(command):
	if len(command) < 2:
		Core.Print("Error: no condition given",color="k")
		return
	condname = " ".join(command[1:])
	Core.player.removeCondition(condname)


def Get(command):
	if len(command) < 2:
		Core.Print("Error: No object name given",color="k")
		return

	objname = command[1].lower()
	if len(command) == 3:
		attrname = command[2]

	if objname in ("p","player","my","self"): obj = Core.player
	elif objname in ("g","game"): obj = Core.game
	elif objname in ("here","room"): obj = Core.game.currentroom
	elif objname in ("w","world"): obj = Core.world
	elif objname in Core.world: obj = Core.world[objname]
	else: obj = findObjFromTerm(objname,playerD=3,roomD=3)
	if obj is None:
		Core.Print("Error: Object not found",color="k")
		return
	
	if len(command) < 3:
		Core.Print(obj,color="k")
	else:
		try:
			Core.Print(getattr(obj,attrname),color="k")
		except:
			Core.Print("Error: Attribute does not exist",color="k")


def Imbue(command):
	if len(command) < 2:
		Core.Print("Error: No status condition given",color="k")
		return
	if len(command) < 3:
		duration = -2
		condname = " ".join(command[1:])
	else:
		condname = " ".join(command[1:-1])
		try:
			duration = int(command[-1])
		except:
			Core.Print("Error: Duration not number",color="k")
			return


	Core.player.addCondition(condname,duration)


def Learn(command):
	if len(command) < 2:
		Core.Print("Error: No xp value given",color="k")
		return
	try:
		Core.player.gainxp(int(command[1]))
	except:
		Core.Print(f"Error: Value not number {command[1]}",color="k")


def Mode(command):
	if len(command) < 2:
		Core.Print("Error: No mode value given",color="k")
		return
	try:
		Core.game.mode = int(command[1])
		Core.Print("Mode set to " + str(Core.game.mode),color="k")
	except:
		Core.Print(f"Error: Value not number {command[1]}",color="k")


def Pypot(command):
	if len(command) < 2:
		Core.Print("Error: No money value given",color="k")
		return
	try:
		money = int(command[1])
		Core.player.money = Core.player.money + money
		if Core.player.money < 0:
			Core.player.money = 0
		Core.Print(f"You now have {Core.player.money} money.",color="k")
	except:
		Core.Print("Error: Value not number",color="k")


def Set(command):
	if len(command) < 2:
		Core.Print("Error: No object name given",color="k")
		return
	if len(command) < 3:
		Core.Print("Error: No attribute name given",color="k")
		return
	if len(command) < 4:
		Core.Print("Error: No value given",color="k")
		return

	objname = command[1].lower()
	attrname = command[2]
	value = " ".join(command[3:])
	try: value = int(value)
	except: pass

	if objname in ("p","player","my","self"): obj = Core.player
	elif objname in ("g","game"): obj = Core.game
	elif objname in ("here","room"): obj = Core.game.currentroom
	elif objname in ("w","world"): obj = Core.world
	else: obj = findObjFromTerm(command[1],playerD=3,roomD=3)

	if obj is None: return False
	try:
		getattr(obj,attrname)
	except:
		Core.Print(f"{obj} has no attribute",color="k")
		return False
	Core.Print(f"Setting {obj}.{attrname} to {value}",color="k")
	setattr(obj,attrname,value)
	


def Spawn(command):
	if len(command) < 2:
		Core.Print("Error: no object given",color="k")
	objname = " ".join(command[1:])
	if objname in Creatures.factory or objname in Items.factory:
		obj = objname
	else:
		try:
			obj = eval(objname)
			if not (isinstance(obj,Core.Creature) or isinstance(obj,Core.Item)):
				raise TypeError
		except Exception as e:
			Core.Print("Error: Object could not be instantiated:",color="k")
			Core.Print(e,color="k")
			return False
	Effects.spawnObject(obj)


def Teleport(command):
	if len(command) < 2:
		Core.Print("Error: no location given",color="k")
		return
	location = " ".join(command[1:])
	if location in Core.world:
		Core.player.changeRoom(Core.world[location])
	else:
		Core.Print("Location not in world",color="k")


def Test(command):
	Core.Print(Core.player,color="k")
	return True


def Warp(command):
	if len(command) < 2:
		Core.Print("Error: no warp value given",color="k")
		return
	try:
		t = int(command[1])
	except:
		Core.Print("Value not number",color="k")
		return
	Core.game.silent = True
	Core.Print(f"Warping {t}",color="k")
	Core.game.passTime(t)
	Core.Print("Time: ", Core.game.time,color="k")


def Zap(command):
	if len(command) < 2:
		Core.Print("Error: no object given",color="k")
		return
	objname = " ".join(command[1:])
	key = lambda obj: Core.nameMatch(objname, obj)
	matches = Core.game.queryRooms(key=key)
	Core.Print(f"Zapped objects: {len(matches)}",color="k")
	for obj in matches:
		if isinstance(obj,Core.Item):
			obj.Break()
		elif isinstance(obj,Core.Creature):
			obj.death()




#######################################
## SHORTACTION AND RELATED FUNCTIONS ##
#######################################


def Cry(*args): Core.Print("A single tear sheds from your eye.")


def Dance(*args):
	Core.player.removeCondition("hiding",-3)
	Core.Print("You bust down a boogie.",color="m")


def Examples(*args):
	Core.clearScreen()
	Core.Print(Data.examples,color="k")
	Core.waitKbInput()
	Core.clearScreen()


def Exits(*args):
	exitText = []
	for key, val in Core.game.currentroom.allExits().items():
		Core.Print(f"{key}:	{val}",color="k")


def Goodbye(*args):
	goodbye = choice(list(Data.goodbyes))
	Core.Print(f'"{goodbye.title()}"',color="y")


def Hello(*args):
	hello = choice(list(Data.hellos))
	Core.Print(f'"{hello.title()}"',color="y")


def Commands(*args):
	Core.flushInput()
	Core.clearScreen()
	Core.Print("Short Commands (May only be one word)",color="k")
	shortcommands = sorted(tuple(shortactions.keys()) + Data.traits + Data.abilities)
	Core.columnPrint(shortcommands,12,10,delay=0,color="k")
	Core.Print("\nVerb Commands (Does not include cheat codes and secret commands)",color="k")
	Core.columnPrint(actions.keys(),12,10,delay=0,color="k")
	Core.Print("\nDuring the game, type 'info' for information on the game and how to play.",color="k")
	Core.waitKbInput()
	Core.clearScreen()


def Info(*args):
	Core.clearScreen()
	Core.Print(Data.gameinfo,color="k")
	Core.waitKbInput()
	Core.clearScreen()


def Laugh(*args):
	Core.Print('"HAHAHAHAHA!"',color="y")
	Core.player.removeCondition("hiding",-3)


def Quit(*args):
	if Core.yesno("Are you sure you want to quit? (Anything unsaved will be lost)",color="k"):
		Core.game.quit = True
		return True


def Shout(*args): 
	Core.Print('"AHHHHHHHHHH"',color="y")
	Core.player.removeCondition("hiding",-3)


def Sing(*args):
	Core.Print('"Falalalaaaa"',color="y")
	Core.player.removeCondition("hiding",-3)


def Time(*args): Core.Print("Time:",Core.game.time,color="k")


def Yawn(*args): return Rest(None,None,None) if Core.yesno("Do you want to sleep?") else None




##################################
## ACTION AND RELATED FUNCTIONS ##
##################################


def Attack(dobj,iobj,prep,target=None,weapon=None,weapon2=None):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if iobj is None:
		if len(Core.player.weapons()) == 0:
			iobj = "fist"
		elif Core.player.gear["right"] == Core.EmptyGear() and Core.player.gear["left"] == Core.EmptyGear():
			iobj = getNoun("What will you attack with?")
			if iobj in Data.cancels: return False
	if iobj.startswith("my "):
		iobj = iobj[3:]

	# assigning weapons based on input and what is in player's hand
	if weapon is None and weapon2 is not None:
		weapon, weapon2 = weapon2, None
	if iobj in ("fist","hand"):
		Core.player.unequip(Core.player.gear["right"])
		weapon = Items.Hand("your hand","",4,-1,None)
	if iobj in ("foot","leg"):
		weapon = Items.Foot("your foot","",6,-1,None)
	if iobj in ("mouth","teeth"):
		weapon = Items.Mouth("your mouth","",4,-1,None)
	if iobj is not None:
		if weapon is None:
			weapon = Core.player.inGear(iobj)
		if weapon is None:
			weapons = Core.player.inInv(iobj)
			if len(weapons) == 0: Core.Print(f"There is no '{iobj}' in your Inventory.",color="k")
			elif len(weapons) == 1: weapon = weapons[0]
			else: weapon = chooseObject(iobj,weapons)
			if weapon is None: return False
	else:
		if Core.player.gear["right"] != Core.Empty():
			weapon = Core.player.gear["right"]
		elif Core.player.gear["left"] != Core.Empty():
			weapon = Core.player.gear["right"]

	if target is None:
		if dobj is None: dobj = getNoun("What will you attack?")
		if dobj in Data.cancels: return False
		if dobj in ("myself","me"): target = Core.player
		else: target = findObjFromTerm(dobj,"room")
		if target is None: return False
	Core.game.setPronouns(target)
	Core.player.removeCondition("hiding",-3)

	stowed = False
	if isinstance(weapon,(Items.Foot,Items.Mouth)):
		stowed = True
		stowedweapons = (Core.player.weapon, Core.player.weapon2)
	if not isinstance(weapon,Core.Weapon):
		weapon = weapon.asWeapon()
	Core.player.weapon = weapon

	Core.Print(f"You attack {-target} with your {Core.player.weapon}.",color="o")
	if isinstance(target,Core.Creature): Core.player.attackCreature(target)
	elif isinstance(target,Core.Item): Core.player.attackItem(target)
	if stowed: Core.player.weapon,Core.player.weapon2 = stowedweapons
	return True


def Bite(dobj,iobj,prep):
	if prep is not None:
		return promptHelp("Command not understood.")
	if dobj is None:
		dobj = getNoun("What do you want to bite?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
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
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")
	if dobj is None:
		dobj = getNoun("What do you want to break?")
		if dobj in Data.cancels: return False

	# TODO: maybe figure out times when you will just break, not attack?
	# for instance though, a window should be attacked
	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Break"):
		Core.Print(f"You can't break {-I}.")
		return False
	Core.Print(f"You try to break {-I}.")
	return Core.player.attackItem(I)


def Caress(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What do you want to caress?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Caress"):
		return I.Caress(Core.player)
	if Core.hasMethod(I,"Touch"):
		return I.Touch(Core.player)
		
	if I.composition in Data.textures:
		Core.Print(Data.textures[I.composition])
	return True


# this is not intended to be called directly from Parse
# but rather from the Take action function
def CarryCreature(creature):
	Core.game.setPronouns(creature)	
	carrying = Core.player.carrying
	
	if carrying:
		Core.Print(f"You're already carrying {-carrying}")
	if not isinstance(creature,Core.Creature):
		Core.Print(f"You can't carry {-creature}")
		return False

	Core.player.unequip(Core.player.gear["left"])
	Core.Print(f"You try to pick up {-creature}.",color="o")
	if not creature.Carry(Core.player):
		return False
	Core.Print(f"You are carrying {-creature}.")
	return True


def Cast(dobj,iobj,prep):
	if prep not in ("at","on","onto","upon",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What spell will you cast?")
		if dobj in Data.cancels: return False
	if dobj not in Core.player.spells:
		Core.Print(f"You don't know a spell called '{dobj}'.",color="k")
		return False
	if dobj not in Effects.spells:
		# this shouldn't happen
		Core.Print("That spell doesn't exist.",color="k")
		return False

	target = None
	if prep is not None:
		if iobj is None:
			iobj = getNoun(f"What will you cast upon?")
			if iobj in Data.cancels: return False
		target = findObjFromTerm(iobj,"room")

	return Effects.spells[dobj](target)


def Catch(dobj,iobj,prep):
	Core.Print("catching")


# TODO:
# def Climb(dobj,iobj,prep):
# 	Core.Print("climbing")


def Close(dobj,iobj,prep):
	if prep is not None:
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you close?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if not hasattr(I,"open"):
		Core.Print(f"{+I} doesn't close.")
		return False
	if not I.open:
		Core.Print(f"{+I} is already closed.")
		return False
	if Core.hasMethod(I,"Close"):
		I.Close()
	else:
		I.open = False
		Core.Print(f"You close {-I}.")
	return True


def Craft(dobj,iobj,prep):
	Core.Print("crafting")


def Cross(dobj,iobj,prep):
	Core.Print("crossing")


def Crouch(dobj,iobj,prep):
	if prep not in ("behind","below","beneath","inside","under",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = iobj
	if dobj is not None:
		if not Hide(dobj,iobj,prep):
			return False

	Core.player.Crouch()
	return True


def Cut(dobj,iobj,prep):
	Core.Print("cuting")


def Define(dobj,iobj,prep):
	if iobj is not None or prep is not None:
		return promptHelp("Can only define one word at once.")
	if dobj is None:
		dobj = getNoun("What term would you like defined?")
		if dobj in Data.cancels: return False

	if dobj in Data.definitions:
		Core.Print("\n"+Data.definitions[dobj])
		return True
	elif Core.game.inWorld(dobj):
		return Look(dobj,iobj,prep)
	elif dobj == Core.player.name.lower():
		Core.Print(f"\n{Core.player.name}\nThat is you!")
		return True
	Core.Print(f"'{dobj}' is unknown",color="k")
	return False


def Describe(dobj,iobj,prep):
	if iobj is not None or prep is not None:
		return promptHelp("Can only describe one thing at once.")
	if dobj is None:
		dobj = getNoun("What would you like described?")
		if dobj in Data.cancels: return False

	if dobj == Core.game.currentroom.name or dobj in ("room","here"):
		D = Core.game.currentroom
	else:
		D = findObjFromTerm(dobj)
	if D is None: return False
	Core.game.setPronouns(D)

	D.describe()
	return True


def Dismount(dobj,iobj,prep):
	if prep not in ("from","of","off","out","out of",None):
		return promptHelp("Command not understood.")

	if Core.player.riding is None:
		return promptHelp(f"You're not riding anything")

	if iobj is not None:
		dobj = iobj
	if dobj is not None:
		matches = Core.game.nameQueryRoom(dobj)
		if Core.player.riding not in matches:
			Core.Print(f"You're not riding a '{dobj}'",color="k")
			return False
	
	riding = Core.player.riding
	Core.game.setPronouns(riding)
	Core.Print(f"You dismount {-riding}.")	
	riding.rider = None
	Core.player.riding = None
	Core.player.removeCondition("sitting")
	return True


def Do(dobj,iobj,prep):
	Core.Print("doing")


def Dodge(dobj,iobj,prep):
	Core.Print("dodgeing")


def Doff(dobj,iobj,prep):
	if prep is not None:
		return promptHelp("Command not understood")
	if dobj is None:
		dobj = getNoun("What do you want to doff?")
		if dobj in Data.cancels: return False

	I = Core.player.inGear(dobj)
	if I is None or not isinstance(I,Core.Armor):
		Core.Print(f"You aren't wearing a '{dobj}'.")
		return False
	Core.game.setPronouns(I)

	Core.player.unequip(I)
	Core.Print(f"You doff your {I.name}.")
	return True


def Don(dobj,iobj,prep):
	if prep not in ("on","onto","over","to",None):
		return promptHelp("Command not understood.")

	if prep is None:
		prep = "on"
	if dobj is None:
		dobj = getNoun("What do you want to don?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"player")
	if I is None: return False
	Core.game.setPronouns(I)

	if not isinstance(I,Core.Armor):
		Core.Print(f"You cannot wear your {I}.")
		return False
	if I in Core.player.gear.values():
		Core.Print(f"You are already wearing your {I}.")
		return False
	if iobj and iobj not in Core.player.gear: 
		Core.Print(f"You aren't able to equip to '{iobj}'.")
		return False
	if iobj not in I.slots and iobj is not None:
		Core.Print(f"You cannot wear {-I} {prep} your {iobj}.")
		return False
	if not Core.player.equipArmor(I,iobj):
		return False
	Core.Print(f"You don your {I}.")
	return True


def Drink(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What do you want to drink?.")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Drink"):
		Core.Print(f"You can't drink {-I}.")
		return False
	I.Drink()
	return True


def Drop(dobj,iobj,prep,I=None):
	if prep not in ("down","into","off",None):
		return Put(dobj,iobj,prep)
	if prep is None:
		prep = "down"
	if dobj is None and I is None:
		dobj = getNoun("What will you drop?")
		if dobj in Data.cancels: return False

	if I is None and Core.nameMatch(dobj, Core.player.carrying):
		I = Core.player.carrying
	if I is None: I = findObjFromTerm(dobj,"player")
	if I is None: return False
	Core.game.setPronouns(I)

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	if iobj is not None:
		R = findObjFromTerm(iobj,"room")
		if R is None: return False
		if isinstance(R,Core.Passage) and "down" in R.connections:
			if getattr(R,"open",True):
				Core.player.removeItem(I)
				Core.game.currentroom.addItem(I)
				return R.Transfer(I)
			else:
				Core.Print(f"{+R} is closed.")
				return False
		elif not Core.hasMethod(R,"addItem"):
			Core.Print(f"You can't drop {-I} {prep} {-R}.")
			return False

	if isinstance(I, Core.Creature):
		Core.player.removeCarry()
		Core.Print(f"You drop {-I}.")
	else:
		I.parent.removeItem(I)
		Core.Print(f"You drop {-I}.")
		Core.game.currentroom.addItem(I)
	return True


def Dump(dobj,iobj,prep):
	if prep not in ("in","into","inside","on","onto","out","upon",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you dump?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"player")
	if I is None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Pour"):
		return Pour(dobj,iobj,prep,I=I)
	else:
		return Drop(dobj,iobj,prep,I=I)


def Eat(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What do you want to eat?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Eat"):
		Core.Print(f"You can't eat {-I}.")
		return False

	I.Eat(Core.player)
	return True


def Enter(dobj,iobj,prep):
	if dobj is None and "in" in Core.game.currentroom.exits:
		return Go("in",iobj,prep)
	return Go(dobj,iobj,prep)


def Equip(dobj,iobj,prep):
	if prep is not None:
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What would you like to equip?")
		if dobj in Data.cancels:
			return False
	if dobj.startswith("my "):
		dobj = dobj[3:]


	matches = Core.player.inInv(dobj)
	if len(matches) == 0:
		Core.Print(f"There is no '{dobj}' in your Inventory",color="k")
	I = chooseObject(dobj,matches)
	if I is None: 
		return False
	Core.game.setPronouns(I)

	if I in Core.player.gear.values():
		Core.Print(f"Your {I} is already equipped.")
		return False
	# if item is armor, equip it as armor, otherwise, equip it in hand
	if isinstance(I,Core.Armor):
		Core.player.equipArmor(I)
	else:
		Core.player.equipInHand(I)
	Core.Print(f"You equip your {I}.")
	return True


def Escape(dobj,iobj,prep):
	Core.Print("escapeing")


def Exit(dobj,iobj,prep):
	if dobj is None and "out" in Core.game.currentroom.exits:
		return Go("out",iobj,prep)
	return Go(dobj,iobj,prep)


def Feed(dobj,iobj,prep):
	Core.Print("feeding")


def Fill(dobj,iobj,prep):
	Core.Print("filling")


def Find(dobj,iobj,prep):
	Core.Print("finding")


def Fish(dobj,iobj,prep):
	Core.Print("fishing")


def Follow(dobj,iobj,prep):
	Core.Print("following")


def Fuck(dobj,iobj,prep):
	Core.Print("There's a time and place for everything, but not now.")


def Give(dobj,iobj,prep):
	if prep not in ("to","over",None):
		return promptHelp("Command not understood.")

	if prep is None:
		dobj,iobj = iobj,dobj
	if dobj is None:
		dobj = getNoun("What will you give?")
		if dobj in Data.cancels:
			return False
	I = findObjFromTerm(dobj,"player")
	if I is None:
		return False

	if iobj is None:
		iobj = getNoun("Who will you give to?")
		if iobj in Data.cancels:
			return False
	C = findObjFromTerm(iobj,"room")
	if C is None:
		return False
	
	if Core.hasMethod(C,"Give"):
		return C.Give(I)
	else:
		Core.Print(f"You can't give to {-C}")
		return False


# not called by Parse directly
# called when the user wants to go "up" or "down"
def GoVertical(dir,passage=None,dobj=None):
	if Core.player.hasCondition("flying") and not Core.player.riding:
		newroomname = Core.game.currentroom.allExits()[dir]
		Core.Print(f"You fly {dir}!")
		return Core.player.changeRoom(Core.world[newroomname])

	if passage is None and dobj is not None:
		Core.Print(f"There is no '{dobj}' to go {dir} here.",color="k")
		return False
	if passage is None:
		passagename = getNoun(f"What will you go {dir}?")
		passage = findObjFromTerm(passagename,"room")
	if passage is None:
		Core.Print(f"There is no '{passagename}' to go {dir} here.",color="k")
		return False
	
	if Core.hasMethod(passage,"Traverse"):
		return passage.Traverse(Core.player,dir)


# infers direction, destination, and passage (if they exist) from input terms
def parseGoTerms(dobj,iobj,prep):
	dir,dest,passage = None,None,None

	# assign dest
	if dobj in Core.game.currentroom.allExits().values(): dest = dobj
	elif Core.nameMatch(dobj,Core.game.currentroom): dest = dobj
	if iobj in Core.game.currentroom.allExits().values(): dest = iobj
	elif Core.nameMatch(iobj,Core.game.currentroom): dest = iobj

	# assign dir
	if dobj in Data.directions.values(): dir = dobj
	elif iobj in Data.directions.values(): dir = iobj
	elif dobj in Core.game.currentroom.allExits().keys(): dir = dobj
	elif iobj in Core.game.currentroom.allExits().keys(): dir = dobj
	elif dir is None: dir = prep

	# assign passage
	if dobj is not None: passage = findObjFromTerm(dobj,"room",silent=True)
	elif iobj is not None: passage = findObjFromTerm(iobj,"room",silent=True)

	return dir,dest,passage


# parses user input to determine the intended direction, destination, and/or
# passage. Then calls either traverse or changeroom accordingly
def Go(dobj,iobj,prep):
	for cond in ("sitting","laying"):
		if Core.player.hasCondition(cond) and Core.player.riding is None:
			Core.Print(f"You can't go, you are {cond}.")
			return False

	preps = ("away","away from","down","through","to","toward","up","in","inside","into","on","onto","out",None)
	if prep in ("to", "toward", "away", "away from"):
		prep = None
	if (dobj,iobj,prep) == (None,None,None):
		dobj,iobj,prep = parseWithoutVerb(processCmd("Where will you go?"))
	if dobj in Data.cancels: return False
	if dobj in ("back", "backward", "backwards"): dobj = Core.game.prevroom.name.lower()
	if dobj in ("ahead", "forward", "forwards"): dobj = getNoun("In which direction?")
	if dobj is None: dobj = iobj

	# if any terms are abbreviations for a direction, expand them
	dobj,iobj,prep = map(Core.expandDir,[dobj,iobj,prep])
	if prep not in preps or (dobj,iobj,prep) == (None,None,None):
		return promptHelp("Command not understood.")


	# get dir, dest, and passage and validate them
	dir,dest,passage = parseGoTerms(dobj,iobj,prep)
	if (dir,dest,passage) == (None,None,None):
		Core.Print(f"There is no exit leading to a '{dobj}' here.",color="k")
		return False
	if dir is None:
		dir = Core.game.currentroom.getDirFromDest(dest)
	if (dest,passage) == (None,None):
		if dir in Core.game.currentroom.allExits():
			dest = Core.game.currentroom.allExits()[dir]
	if passage is None and dir not in Core.game.currentroom.exits:
		passage = Core.game.currentroom.getPassageFromDir(dir)
	if (dest,passage) == (None,None):
		if dir is not None and dir not in Core.game.currentroom.allExits():
			Core.Print(f"There is no exit leading '{dir}' here.",color="k")
			return False
	if passage is None and Core.nameMatch(dest,Core.game.currentroom):
		Core.Print(f"You are already there!")
		return False

	Core.player.removeCondition("hiding",-3)
	# call one of three functions to actually change rooms
	# depends if they go normally, traverse a passage, or go vertically
	if dir in ("up","down"):
		return GoVertical(dir,passage,dobj)
	# if just passage is given
	if passage is not None:
		if not Core.hasMethod(passage,"Traverse"):
			Core.Print(f"{+passage} cannot be traversed.")
			return False
		return passage.Traverse(Core.player,dir)
	# if just dest given
	if dest is not None:
		return Core.player.changeRoom(Core.world[dest])
	Core.Print(f"There is no exit leading to a '{dobj}' here.",color="k")
	return False


def Hide(dobj,iobj,prep):
	if prep not in ("behind","below","beneath","inside","under",None):
		return promptHelp("Command not understood.")

	riding = Core.player.riding
	if riding is not None:
		Core.Print(f"You can't hide, you are riding {~riding}")
		return False

	if dobj is None: dobj = iobj
	if dobj is None:
		dobj = getNoun("What do you want to hide behind?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"room")
	if I is None: return False
	Core.game.setPronouns(I)

	if I.weight < Core.player.weight:
		Core.Print(f"You can't hide behind {I.name}.")
		return False

	if Core.hasMethod(I,"HideBehind"):
		I.HideBehind(Core.player)
	Core.player.addCondition("hiding",-3)
	return True


def Ignite(dobj,iobj,prep):
	Core.Print("igniteing")


def Insert(dobj,iobj,prep):
	Core.Print("inserting")


def Jump(dobj,iobj,prep):
	Core.Print("jumping")
	return True


def Kick(dobj,iobj,prep):
	if dobj is None:
		dobj = getNoun("What will you kick?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"foot","with")


def Kill(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj in ("myself","me"):
		if Core.yesno("Are you sure you want to kill yourself?",color="r"):
			Core.player.death()
			return True
		Core.Print("Fwew, that was close!")
		return False
	return Attack(dobj,iobj,prep)


def Lay(dobj,iobj,prep):
	if prep not in ("behind","below","beneath","in","inside","on","onto","under","upon",None):
		return promptHelp("Command not understood.")


	if dobj is None:
		dobj = iobj
	if dobj is not None and prep in ("behind","below","beneath","inside","under"):
		if not Hide(dobj,iobj,prep):
			return False

	if Core.player.hasCondition("laying"):
		Core.Print("You are already laying.")
		return False

	if dobj is None and prep is not None:
		dobj = getNoun("What will you lay on?")
		if dobj in Data.cancels:
			return False
	if dobj in ("nothing","ground","floor","here","room"):
		dobj = None
	if dobj is not None:
		R = findObjFromTerm(dobj)
		if Core.hasMethod(R,"Lay"):
			Core.player.Lay()
			R.Lay(Core.player)
		else:
			Core.Print(f"You can't lay on {-R}.")
			return False

	Core.player.Lay()
	return True


def Lick(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What do you want to lick?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Lick"):
		return I.lick(Core.player)

	if I.composition in Data.tastes:
		Core.Print(Data.tastes[I.composition])
	if I.composition in Data.scents:
		Core.Print(Data.scents[I.composition].replace("scent","taste"))
	return True


def Light(dobj,iobj,prep):
	Core.Print("lighting")


def Listen(dobj,iobj,prep):
	Core.Print("listening")


def Lock(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you lock?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Lock"):
		Core.Print(f"{+I} doesn't lock.")
		return False

	if iobj is None:
		iobj = getNoun("What will you lock with?")
		if iobj in Data.cancels: return False
	K = findObjFromTerm(iobj,"player")
	if K is None: return False

	if not isinstance(K,Items.Key):
		Core.Print(f"You can't lock with {-K}.")
		return False
	return I.Lock(K)


def Look(dobj,iobj,prep):
	# TODO: add "look up", so they can look at sky or ceiling
	if prep not in ("at","in","inside","into","on","through",None):
		return promptHelp("Command not understood.")

	if dobj is None: dobj = iobj
	if dobj is None:
		dobj = getNoun("What will you look at?")
		if dobj in Data.cancels: return False

	if dobj in ("around","here","room") or dobj == Core.game.currentroom.name.lower():
		Core.game.currentroom.describe()
		return True
	if dobj in ("me","myself",Core.player.name):
		Core.Print(f"You are {Core.player.desc}")
		return True
	if dobj in ("down","ground"):
		Core.Print("Not much to see on the ground at your feet.")
		return True
	# TODO: Add something room specific if they look up or down?
	if dobj in ("up","sky","sun","moon","stars","aurora","auroras","meteor shower","eclipse","solar eclipse"):
		return Core.game.LookUp(dobj)

	L = findObjFromTerm(dobj)
	if L is None: return False
	Core.game.setPronouns(L)

	L.describe()
	if Core.hasMethod(L,"Look"):
		L.Look()
	return True


def Mount(dobj,iobj,prep):
	if prep not in ("in","into","inside","on","onto","upon",None):
		return promptHelp("Command not understood.")

	if Core.player.riding is not None:
		Core.Print(f"You're already riding {~Core.player.riding}")
		return False

	if dobj is None: dobj = iobj
	if dobj is None:
		dobj = getNoun("What will you mount?")
		if dobj in Data.cancels: return False

	C = findObjFromTerm(dobj,"room")
	if C is None: return False
	Core.game.setPronouns(C)
	
	if Core.player.Weight() > C.BRDN():
		Core.Print(f"You are too heavy to ride {-C}")
		return False

	Core.player.removeCondition("hiding",-3)
	if C.Ride(Core.player):
		Core.player.Sit()
	return True


def Open(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you open?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Open"):
		Core.Print(f"{+I} doesn't open.")
		return False
	if hasattr(I,"locked") and I.locked:
		Core.Print(f"{+I} is locked")
		return False
	I.Open()
	return True


def Play(dobj,iobj,prep):
	Core.Print("playing")


def Point(dobj,iobj,prep):
	Core.Print("pointing")


def Pour(dobj,iobj,prep,I=None):
	if prep not in ("in","into","inside","on","onto","out","upon",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you pour?")
		if dobj in Data.cancels: return False

	if I is None: I = findObjFromTerm(dobj,"player")
	if I is None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Pour"):
		Core.Print(f"You can't pour {-I}.")
		return False

	R = None
	if iobj is not None and iobj not in ("floor","ground"):
		R = findObjFromTerm(iobj)
		if R is None: return False

	if prep is None: prep = "on"
	if R is not None: Core.Print(f"You pour {-I} {prep} {-R}.")
	else: Core.Print(f"You pour out {-I}.")
	I.Pour(R)
	return True


def Pray(dobj,iobj,prep):
	Core.Print("praying")


def Press(dobj,iobj,prep):
	Core.Print("pressing")


def Pull(dobj,iobj,prep):
	# accomodate "pull the door", "pull the weeds"
	Core.Print("pulling")


def Punch(dobj,iobj,prep):
	if dobj is None:
		dobj = getNoun("What will you punch?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"fist","with")


def Push(dobj,iobj,prep):
	Core.Print("pushing")


def Put(dobj,iobj,prep):
	if prep not in ("in","into","inside","on","onto","upon","down",None):
		return promptHelp("Command not understood.")

	if prep is None:
		prep = "into"
	if dobj is None:
		dobj = getNoun("What will you put?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"player")
	if I is None: return False
	Core.game.setPronouns(I)

	if iobj is None:
		iobj = getNoun(f"What will you put your {dobj} in?")
		if iobj in Data.cancels: return False

	if iobj in ("floor","ground","here"):
		return Drop(dobj,iobj,prep,I=I)
	R = findObjFromTerm(iobj)
	if R is None: return False

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	if isinstance(R,Core.Passage) and "down" in R.connections:
		if getattr(R,"open",True):
			Core.player.removeItem(I)
			Core.game.currentroom.addItem(I)
			return R.Transfer(I)
		else:
			Core.Print(f"{+R} is closed.")
	elif not Core.hasMethod(R,"addItem"):
		Core.Print(f"You can't put {-I} {prep} {-R}.")
		return False
	
	idet = "your" if Core.player in I.ancestors() else 'the'
	rdet = "your" if Core.player in R.ancestors() else 'the'
	outprep = "on" if isinstance(R,Items.Table) else "in"
	if iobj == "here": Core.Print(f"You put your {I.name} here.")
	else: Core.Print(f"You put {idet} {I} {outprep} {rdet} {R}.")
	I.parent.removeItem(I)
	R.addItem(I)
	return True


def Quicksave(*args):
	Menu.quickSave("quicksave")
	Core.waitKbInput("Quicksaved.",color="k")
	return parse()


def Release(dobj,iobj,prep):
	Core.Print("releaseing")


def Rest(dobj,iobj,prep):
	if prep not in ("behind","below","beneath","in","inside","into","on","onto","over","under","upon","using","with",None):
		return promptHelp("Commmand not understood")

	for condname in Data.conditionDmg.keys():
		if Core.player.hasCondition(condname):
			Core.Print(f"This is no time for slumber! You are {condname}.",color="o")
			return False

	if prep is None: prep = "on"
	if dobj is None: dobj = iobj

	if not Core.player.hasCondition("laying"):
		if dobj is None: dobj = getNoun(f"What will you sleep {prep}?")
		if dobj in Data.cancels: return False
		if dobj in ("nothing","ground","floor","here","room"):
			I = None
		else:
			I = findObjFromTerm(dobj)
			if I is None and not Core.yesno("Would you like to sleep on the ground?"):
				return False
		Lay(dobj,iobj,"on")

	if not Core.player.hasCondition("cozy"):
		Core.Print("Your sleep will not be very restful...")

	sleeptime = 90 + randint(1,20)
	Core.player.addCondition("asleep",sleeptime)
	Core.ellipsis()
	Core.game.silent=True
	return True


def Restrain(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you restrain?")
		if dobj in Data.cancels: return False

	C = findObjFromTerm(dobj,"room")
	if C is None: return False
	Core.game.setPronouns(C)

	if not isinstance(C,Core.Creature):
		Core.Print(f"You can't restrain {-C}.")
		return False

	I = None
	if iobj is not None:
		I = findObjFromTerm(iobj,"player")
		if I is None: return False
		if not Core.hasMethod(I,"RestrainWith"):
			Core.Print(f"You can't restrain with {-I}.")
			return False

	if "restrained" in C.status:
		Core.Print(f"{-C} is already restrained.")
	Core.Print(f"You try to restrain {-C}",color="o")
	if not C.Restrain(Core.player,I):
		return False
	return True


def Return(*args): 
	return Go(None, Core.game.prevroom.name.lower(), None)


def Ring(dobj,iobj,prep):
	Core.Print("ringing")


def Rub(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What do you want to rub?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Rub"):
		return I.Rub(Core.player)
	return Touch(dobj,iobj,prep)


def Save(dobj,iobj,prep):
	Menu.saveGame(dobj)
	return parse()


def Search(dobj,iobj,prep):
	Core.Print("searching")


def Shoot(dobj,iobj,prep):
	Core.Print("shooting")


def Shove(dobj,iobj,prep):
	Core.Print("shoveing")


def Sit(dobj,iobj,prep):
	if prep not in ("below","beneath","in","inside","on","onto","under","upon",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = iobj

	if Core.player.hasCondition("sitting"):
		Core.Print("You are already sitting.")
		return False

	if dobj is None and prep is not None:
		dobj = getNoun("What will you sit on?")
		if dobj in Data.cancels:
			return False
	if dobj in ("nothing","ground","floor","here","room"):
		dobj = None
	if dobj is not None:
		R = findObjFromTerm(dobj)
		if Core.hasMethod(R,"Sit"):
			Core.player.Sit()
			R.Sit(Core.player)
		else:
			Core.Print(f"You can't sit on {-R}.")
			return False

	Core.player.Sit()
	return True


def Smell(dobj,iobj,prep):	
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What do you want to smell?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Smell"):
		return I.Smell(Core.player)
		
	if I.composition in Data.scents:
		Core.Print(Data.scents[I.composition])
	elif I.composition in Data.tastes:
		Core.Print(Data.tastes[I.composition].replace("taste","smell"))
	return True


def Stand(dobj,iobj,prep):
	if prep not in ("at","behind","below","beneath","by","in","inside","near","on","onto","upon",None):
		return promptHelp("Command not understood.")

	Core.player.removeCondition("cozy",-3)
	Core.player.removeCondition("laying")
	Core.player.removeCondition("crouching")
	Core.player.removeCondition("sitting")

	if prep is None:
		if dobj is None: 
			dobj = iobj
		if dobj is not None:
			M = findObjFromTerm(dobj)
			Mount(dobj,iobj,prep)
	elif prep in ("at","by","near"):
		Core.Print("You are there.")
	elif prep == "behind":
		Hide(dobj,iobj,prep)
	elif prep in ("below","beneath","under"):
		pass
	elif prep in ("in","inside"):
		pass
	elif prep in ("on","onto","upon"):
		pass
	return True


def Steal(dobj,iobj,prep,I=None):
	Core.Print(f"stealing {dobj} {prep} {iobj}")


def Struggle(dobj,iobj,prep):
	Core.Print("struggleing")


def Swim(dobj,iobj,prep):
	Core.Print("swiming")


# if an item is a container, take each of its contents before taking it
def TakeAllRecur(objToTake):
	takenAny = False
	if hasattr(objToTake, "contents"):
		contents = sorted(objToTake.contents(), key=lambda x: x.Weight())
		for content in contents:
			takenAny = TakeAllRecur(content) or takenAny

	parent = objToTake.parent
	count = parent.itemNames().count(objToTake.name)
	
	if parent is Core.game.currentroom: suffix = ""
	elif Core.player in objToTake.ancestors(): suffix = " from your " + parent.name
	else: suffix = f" from {-parent}"
	strname = objToTake.nounPhrase('the' if count==1 else 'a')
	tookMsg = f"You take {strname}{suffix}."
	failMsg = f"You can't take {-objToTake}, your Inventory is too full."

	return Core.player.obtainItem(objToTake,tookMsg,failMsg) or takenAny


def TakeAll():
	if len(Core.game.currentroom.items) == 0:
		Core.Print("There are no items to take.")
		return False
	takenAny = False
	for obj in sorted(Core.game.currentroom.items, key=lambda x: x.Weight()):
		takenAny = TakeAllRecur(obj) or takenAny
	return takenAny


def Take(dobj,iobj,prep):
	if prep not in ("from","in","inside","out","out of","up",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you take?")
		if dobj in Data.cancels: return False

	if dobj in ("all","everything","it all"): return TakeAll()

	if iobj in ("here", "room", None):
		objToTake = findObjFromTerm(dobj,"room",roomD=2)
	else:
		objToTake = findObjFromTerm(dobj,roomD=2,reqParent=iobj)
	if objToTake is None:
		return False
	Core.game.setPronouns(objToTake)
	if objToTake.parent is Core.player:
		Core.Print(f"You can't take from your own Inventory.")
		return False

	if isinstance(objToTake,Core.Creature): 
		return CarryCreature(objToTake)
	if isinstance(objToTake,Core.Fixture):
		Core.Print(f"You can't take {objToTake}.")
		return False

	parent = objToTake.parent
	# if it is in a non-player inventory, it will have to be stolen
	if any(isinstance(anc,Core.Creature) for anc in objToTake.ancestors()) and objToTake not in Core.player.invSet():
		return Steal(dobj,iobj,prep,I=objToTake)
	count = parent.itemNames().count(objToTake.name)

	if parent is Core.game.currentroom: suffix = ""
	elif Core.player in objToTake.ancestors(): suffix = " from your " + parent.name
	else: suffix = f" from {-parent}"
	strname = objToTake.nounPhrase('the' if count==1 else 'a')
	tookMsg = f"You take {strname}{suffix}."
	failMsg = f"You can't take {-objToTake}, your Inventory is too full."

	return Core.player.obtainItem(objToTake,tookMsg,failMsg)


def Talk(dobj,iobj,prep):
	if prep not in ("at","into","to","toward","with",None):
		return promptHelp("Command not understood.")

	if dobj is None: dobj = iobj
	if dobj is None:
		dobj = getNoun("Who do you want to talk to?")
		if dobj in Data.cancels: return False

	target = findObjFromTerm(dobj,"room")
	if target is None: 
		return False
	Core.game.setPronouns(target)

	if not Core.hasMethod(target,'Talk'):
		Core.Print(f"There is no response...")
		return False

	target.Talk()
	return True


def Throw(dobj,iobj,prep):
	if prep not in ("at","down","into","off","on","onto","out","through","to","toward","up",None):
		return promptHelp("Command not understood.")
	if prep in ("to","toward"):
		return Toss(dobj,iobj,prep)
	
	if prep in ("down","up") and iobj is None:
		iobj = prep
	if dobj is None:
		dobj = getNoun("What do you want to throw?")
		if dobj in Data.cancels: return False
	I = findObjFromTerm(dobj,"player","throw")
	if I is None: return False

	if iobj is None:
		iobj = getNoun("What will you throw at?")
		if iobj in Data.cancels: return False
	dir = None
	if iobj in ("down","floor","ground","here","room","up"):
		T = Core.game.currentroom
		dir = "up" if iobj == "up" else "down"
	elif iobj.lower() in Core.game.currentroom.exits.keys():
		T = Core.world[Core.game.currentroom.exits[iobj]]
		dir = iobj
	elif iobj in Core.game.currentroom.exits.values():
		T = Core.world[iobj]
		dir = Core.getDirFromDest(T)
	else:
		T = findObjFromTerm(iobj,"room",f"throw {prep}")
		if T is None: return False
		dirprep = getattr(T,"passprep","toward")
		dir = f"{dirprep} {-T}"
	
	Core.Print(f"You throw {-I} {dir}.")
	Core.game.setPronouns(I)
	return Core.player.Throw(I,T)
# throw at a tree, window, goblin, pit
# throw a rock, sword, black potion, bird, goblin
# toss into a basket? like basketball?


def Tie(dobj,iobj,prep):
	Core.Print("tieing")


def Toss(dobj,iobj,prep):
	if prep not in ("at","down","into","off","on","onto","out","through","to","toward","up",None):
		return promptHelp("Command not understood.")

	if prep in ("down","up") and iobj is None:
		iobj = prep
	if dobj is None:
		dobj = getNoun("What do you want to toss?")
		if dobj in Data.cancels: return False
	I = findObjFromTerm(dobj,"player")
	if I is None: return False

	if iobj is None:
		iobj = getNoun("What will you toss to?")
		if iobj in Data.cancels: return False
	dir = None
	if iobj in ("down","floor","ground","here","room","up"):
		T = Core.game.currentroom
		dir = "up" if iobj == "up" else "down"
	elif iobj.lower() in Core.game.currentroom.exits.keys():
		T = Core.world[Core.game.currentroom.exits[iobj]]
		dir = iobj
	elif iobj in Core.game.currentroom.exits.values():
		T = Core.world[iobj]
		dir = Core.getDirFromDest(T)
	else:
		T = findObjFromTerm(iobj)
		if T is None: return False
		dirprep = getattr(T,"passprep","toward")
		dir = f"{dirprep} {-T}"
	
	Core.Print(f"You toss {-I} {dir}.")
	Core.game.setPronouns(I)
	return Core.player.Throw(I,T,0)


def Touch(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What do you want to touch?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Touch"):
		return I.Touch(Core.player)
		
	if I.composition in Data.textures:
		Core.Print(Data.textures[I.composition])
	return True


def Trip(dobj,iobj,prep):
	Core.Print("triping")


def Try(dobj,iobj,prep):
	Core.Print("Do or do not. There is no 'try'.")
	return False


def Unequip(dobj,iobj,prep):
	if prep is not None:
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What would you like to unequip?")
		if dobj in Data.cancels: return False

	I = Core.player.inGear(dobj)
	if I is None:
		Core.Print(f"You do not have a '{dobj}' equipped.",color="k")
		return False
	Core.game.setPronouns(I)

	Core.Print(f"You unequip your {I.name}.")
	Core.player.unequip(I)
	return True


def Unlock(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you unlock?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)
	if not Core.hasMethod(I,"Unlock"):
		Core.Print(f"{+I} doesn't unlock.")
		return False

	if iobj is None:
		iobj = getNoun("What will you unlock with?")
		if iobj in Data.cancels: return False

	K = findObjFromTerm(iobj,"player")
	if K is None: return False

	if not isinstance(K,Items.Key):
		Core.Print(f"You can't unlock with {-K}.")
		return False
	return I.Unlock(K)


def Untie(dobj,iobj,prep):
	Core.Print("untieing")


def Use(dobj,iobj,prep):
	if dobj is None:
		dobj = getNoun("What will you use?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I is None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Use"):
		Core.Print(f"You can't use {-I}.")
		return False
	Core.Print(f"You use {-I}.")
	I.Use(Core.player)
	return True


def Wait(dobj,iobj,prep):
	Core.Print("You wait...")
	return True


def Wave(dobj,iobj,prep):
	Core.Print("waveing")




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
"commands":Commands,
"examples":Examples,
"exits":Exits,
"gear":Core.Player.printGear,
"help":Info,
"hello":Hello,
"here":Core.game.currentroom.describe,
"hi":Hello,
"hp":Core.Player.printHP,
"info": Info,
"information": Info,
"inv":Core.Player.printInv,
"inventory":Core.Player.printInv,
"level":Core.Player.printLV,
"lv":Core.Player.printLV,
"money":Core.Player.printMoney,
"mp":Core.Player.printMP,
"quit":Quit,
"riding":Core.Player.printRiding,
"rp":Core.Player.printRP,
"spells":Core.Player.printSpells,
"stats":Core.Player.printStats,
"status":Core.Player.printStatus,
"time":Time,
"traits":Core.Player.printTraits,
"verbs":Commands,
"weapons":Core.Player.printWeapons,
"xp":Core.Player.printXP,
"yawn":Yawn
}

actions = {
"attack":Attack,
"bite":Bite,
"break":Break,
"build":Craft,
"caress":Caress,
"carry":Take,
"cast":Cast,
"catch":Catch,
"climb":Go,
"close":Close,
"craft":Craft,
"crawl":Crouch,
"create":Craft,
"cross":Cross,
"crouch":Crouch,
"cut":Cut,
"cry":Cry,
"dance":Dance,
"define":Define,
"describe":Describe,
"dismount":Dismount,
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
"fall asleep":Rest,
"feed":Feed,
"feel":Touch,
"fight":Attack,
"fill":Fill,
"find":Find,
"fish":Fish,
"follow":Follow,
"fuck":Fuck,
"get":Take,
"get down":Dismount,
"get off":Dismount,
"get on":Mount,
"get up":Stand,
"give":Give,
"go":Go,
"go to sleep":Rest,
"grab":Take,
"grapple":Take,
"hand":Give,
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
"lay":Lay,
"lay down":Lay,
"leave":Exit,
"let go": Drop,
"lick":Lick,
"lie down":Lay,
"light":Ignite,
"listen":Listen,
"lock":Lock,
"look":Look,
"lounge":Lay,
"make":Craft,
"mount":Mount,
"move":Go,
"obtain":Take,
"offer":Give,
"open":Open,
"pet":Caress,
"pick":Take,
"pick up":Take,
"place":Put,
"play":Play,
"point":Point,
"pour":Pour,
"pour out":Pour,
"pray":Pray,
"press":Press,
"proceed":Go,
"pull":Pull,
"punch":Punch,
"push":Push,
"put":Put,
"put away":Unequip,
"put down":Drop,
"put on":Don,
"quaff":Drink,
"quicksave":Quicksave,
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
"save":Save,
"scream":Shout,
"search":Search,
"set":Put,
"set down":Drop,
"shoot":Shoot,
"shout":Shout,
"shove":Shove,
"shut":Close,
"sit":Sit,
"sit down":Sit,
"sit up":Sit,
"sing":Sing,
"slap":Punch,
"sleep":Rest,
"slice":Cut,
"slumber":Rest,
"smash":Break,
"smell":Smell,
"sneak":Crouch,
"sniff":Smell,
"snooze":Rest,
"speak":Talk,
"squat":Crouch,
"stand":Stand,
"stand up":Stand,
"steal":Steal,
"stomp":Kick,
"stow":Unequip,
"strike":Attack,
"stroke":Caress,
"struggle":Struggle,
"swim":Swim,
"take":Take,
"take off":Doff,
"talk":Talk,
"taste":Lick,
"throw":Throw,
"tie":Tie,
"tinker":Craft,
"toss":Toss,
"touch":Touch,
"travel":Go,
"trip":Trip,
"try":Try,
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
# remove clothing/strip
# show/reveal
# think
# write
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
# activate/turn [on]
# deactivate/turn [off]
# dress/undress/strip
# spit
# ponder (the orb, to see future?)
# douse,drench -> reverse of pour on?
# converse/communicate/discuss
# say hello -> hello
# sprint/run
# flick?
# sip -> drink or lick?
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
# pee/poop/shit on (soil your pants if they have them on)
# choke/strangle
# paint/draw
# carve/whittle/hew
# chase -> follow?
# drive -> ride
# feed (food) -> give
# scale -> climb
# water,splash -> pour on
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
# stop
# blow/breath
# clap
# snap
# observe/watch
# capture (with a net?) -> take?
# loot/scavenge/forage/salvage/harvest/pluck