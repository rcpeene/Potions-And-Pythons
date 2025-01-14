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
	Core.game.Print()
	for n,object in enumerate(objects):
		strname = object.stringName()
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

		Core.game.Print(f"{n+1}. {strname}{strLabel}")
	Core.game.Print(f"\nWhich {name}?")

	invalid_count = 0
	while True:
		choice = Core.game.Input("> ").lower()
		if choice == "": continue
		if choice in Data.cancels: return None

		try:
			return objects[int(choice)-1]
		except:
			for obj in objects:
				if choice == obj.stringName().lower():
					return obj
		Core.game.Print("That is not one of the options.")
		if invalid_count >= 3:
			Core.game.Print("Type 'cancel' to undo this action.")
		invalid_count += 1


# return an object in player inv or room based on player input
# gets a list of potential objects whose name matches the given user input term
# queryPlayer and queryRoom indicate which places to look for matching objects
# roomD and playerD are the 'degree' of the query.
# Look at Core.py objQuery for details on query degree
def findObjFromTerm(term,queryType="both",filter=None,roomD=1,playerD=2,reqParent=None,silent=False):
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
			Core.game.Print(f"There is no '{term}'{suffix}.")
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
	noun in shortactions or \
	noun in Data.definitions or \
	noun in Data.miscexpressions or \
	noun in Data.hellos or \
	noun in Data.goodbyes or \
	noun in Data.prepositions or \
	noun in Core.game.currentroom.exits.keys() or \
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
	if obj == None:
		return term
	return obj.stringName()


# validates user input and processes into into a command form usable by parse(),
# namely, it returns a list of words without capitals, symbols, or articles
# nounify() joins words that may only be meaningful as one term
def processCmd(prompt,storeRawCmd=False):
	rawcommand = Core.game.Input(prompt + "\n> ",low=False)
	# take input until input has any non-whitespace characters in it
	while not any(i not in "\t " for i in rawcommand):
		Core.flushInput()
		rawcommand = Core.game.Input("> ",low=False)
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
		Core.game.Print(msg)
	if n >= 2:
		Core.game.Print("Enter 'help' for a list of commands.")
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
				return Core.player.printTraits(verb)
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
		Core.game.Print("Error: No code given")
		return
	code = " ".join(command[1:])
	try:
		Core.game.Print(eval(code))
	except Exception as e:
		Core.game.Print("Error: Code was unable to be executed.")
		Core.game.Print(e)


def Execute(command):
	if len(command) < 2:
		Core.game.Print("Error: No code given")
		return
	code = " ".join(command[1:])
	try:
		exec(code)
	except Exception as e:
		Core.game.Print("Error: Code was unable to be executed.")
		Core.game.Print(e)


def Expell(command):
	if len(command) < 2:
		Core.game.Print("Error: no condition given")
		return
	condname = " ".join(command[1:])
	Core.player.removeCondition(condname)


def Get(command):
	if len(command) < 2:
		Core.game.Print("Error: No object name given")
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
	if obj == None:
		Core.game.Print("Error: Object not found")
		return
	
	if len(command) < 3:
		Core.game.Print(obj)
	else:
		try:
			Core.game.Print(getattr(obj,attrname))
		except:
			Core.game.Print("Error: Attribute does not exist")


def Imbue(command):
	if len(command) < 2:
		Core.game.Print("Error: No status condition given")
		return
	if len(command) < 3:
		duration = -2
		condname = " ".join(command[1:])
	else:
		condname = " ".join(command[1:-1])
		try:
			duration = int(command[-1])
		except:
			Core.game.Print("Error: Duration not number")
			return


	Core.player.addCondition(condname,duration)


def Learn(command):
	if len(command) < 2:
		Core.game.Print("Error: No xp value given")
		return
	try:
		Core.player.gainxp(int(command[1]))
	except:
		Core.game.Print(f"Error: Value not number {command[1]}")


def Mode(command):
	if len(command) < 2:
		Core.game.Print("Error: No mode value given")
		return
	try:
		Core.game.mode = int(command[1])
		Core.game.Print("Mode set to " + str(Core.game.mode))
	except:
		Core.game.Print(f"Error: Value not number {command[1]}")


def Pypot(command):
	if len(command) < 2:
		Core.game.Print("Error: No money value given")
		return
	try:
		money = int(command[1])
		Core.player.money = Core.player.money + money
		if Core.player.money < 0:
			Core.player.money = 0
		Core.game.Print(f"You now have {Core.player.money} money.")
	except:
		Core.game.Print("Error: Value not number")


def Set(command):
	if len(command) < 2:
		Core.game.Print("Error: No object name given")
		return
	if len(command) < 3:
		Core.game.Print("Error: No attribute name given")
		return
	if len(command) < 4:
		Core.game.Print("Error: No value given")
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

	if obj is None:
		Core.game.print(f"There is no {obj}")
		return False
	try:
		getattr(obj,attrname)
	except:
		Core.game.Print(f"{obj} has no attribute")
		return False
	print(f"Setting {obj}.{attrname} to {value}")
	setattr(obj,attrname,value)
	


def Spawn(command):
	if len(command) < 2:
		Core.game.Print("Error: no object given")
	try:
		obj = eval(" ".join(command[1:]))
	except Exception as e:
		Core.game.Print("Error: Object could not be instantiated:")
		Core.game.Print(e)
		return False
	if not (isinstance(obj,Core.Creature) or isinstance(obj,Core.Item)):
		Core.game.Print("Could not instantiate game object")
	Effects.spawnObject(Core.game.currentroom,obj)


def Teleport(command):
	if len(command) < 2:
		Core.game.Print("Error: no location given")
		return
	location = " ".join(command[1:])
	if location in Core.world:
		Core.player.changeRoom(Core.world[location])
	else:
		Core.game.Print("Location not in world")


def Test(command):
	Core.game.Print(Core.player)
	return True


def Warp(command):
	if len(command) < 2:
		Core.game.Print("Error: no warp value given")
		return
	try:
		t = int(command[1])
	except:
		Core.game.Print("Value not number")
		return
	Core.game.Print(f"Warping {t}")
	Core.game.passTime(t)
	Core.game.Print("Time: ", Core.game.time)
	Core.game.checkDaytime()
	Core.game.checkAstrology(update=True)


def Zap(command):
	if len(command) < 2:
		Core.game.Print("Error: no object given")
		return
	objname = " ".join(command[1:])
	key = lambda obj: Core.nameMatch(objname, obj)
	matches = Core.game.queryRooms(key=key)
	Core.game.Print(f"Zapped objects: {len(matches)}")
	for obj in matches:
		if isinstance(obj,Core.Item):
			obj.Break()
		elif isinstance(obj,Core.Creature):
			obj.death()




#######################################
## SHORTACTION AND RELATED FUNCTIONS ##
#######################################


def Cry(*args): Core.game.Print("A single tear sheds from your eye.")
def Dance(*args): Core.game.Print("You bust down a boogie.")

def Examples(*args):
	Core.clearScreen()
	Core.game.Print(Data.examples)
	Core.game.Input()
	Core.waitKbInput()
	Core.clearScreen()
	
def Exits(*args):
	exitText = []
	for key, val in Core.game.currentroom.allExits().items():
		Core.game.Print(f"{key}:	{val}")


def Goodbye(*args): Core.game.Print(Core.capWords(choice(list(Data.goodbyes)),c=1))

def Hello(*args): Core.game.Print(Core.capWords(choice(list(Data.hellos)),c=1))

def Help(*args):
	Core.flushInput()
	Core.clearScreen()
	Core.game.Print("\nSingle-Word Commands")
	shortcommands = sorted(tuple(shortactions.keys()) + Data.traits + Data.abilities)
	Core.columnPrint(shortcommands,12,10,printf=print)
	Core.game.Print("\nVerb Commands (Does not include cheat codes and secret commands)")
	Core.columnPrint(actions.keys(),12,10,printf=print)
	Core.game.Print("\nDuring the game, type 'info' for information on the game and how to play.")
	Core.waitKbInput()
	Core.clearScreen()


def Info(*args):
	Core.clearScreen()
	Core.game.Print(Data.gameinfo)
	Core.waitKbInput()
	Core.clearScreen()


def Laugh(*args): Core.game.Print('"HAHAHAHAHA!"')


def Quit(*args):
	if Core.yesno("Are you sure you want to quit? (Anything unsaved will be lost)"):
		Menu.quit()


def Shout(*args): Core.game.Print('"AHHHHHHHHHH"')
def Sing(*args): Core.game.Print('"Falalalaaaa"')
def Time(*args): Core.game.Print("Time:", Core.game.time)
def Yawn(*args): return Rest(None,None,None) if Core.yesno("Do you want to sleep?") else None




##################################
## ACTION AND RELATED FUNCTIONS ##
##################################


def Attack(dobj,iobj,prep,target=None,weapon=None,weapon2=None):
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False

	if iobj == None:
		if len(Core.player.weapons()) == 0:
			iobj = "fist"
		elif Core.player.gear["right"] == Core.EmptyGear() and Core.player.gear["left"] == Core.EmptyGear():
			iobj = getNoun("What will you attack with?")
			if iobj in Data.cancels: return False
	if iobj.startswith("my "):
		iobj = iobj[3:]

	# assigning weapons based on input and what is in player's hand
	if weapon == None and weapon2 != None:
		weapon, weapon2 = weapon2, None
	if iobj in ("fist","hand"):
		Core.player.unequip(Core.player.gear["right"])
		weapon = Items.Hand("your hand","",4,-1,None)
	if iobj in ("foot","leg"):
		weapon = Items.Foot("your foot","",6,-1,None)
	if iobj in ("mouth","teeth"):
		weapon = Items.Mouth("your mouth","",4,-1,None)
	if iobj != None:
		if weapon == None:
			weapon = Core.player.inGear(iobj)
		if weapon == None:
			weapons = Core.player.inInv(iobj)
			if len(weapons) == 0: Core.game.Print(f"There is no '{iobj}' in your Inventory.")
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
		if dobj in ("myself","me"): target = Core.player
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

	Core.game.Print(f"\nYou attack {target.stringName(det='the')} with {Core.player.weapon.name}.")
	if isinstance(target,Core.Creature): Core.player.attackCreature(target)
	elif isinstance(target,Core.Item): Core.player.attackItem(target)
	if stowed: Core.player.weapon,Core.player.weapon2 = stowedweapons
	return True


def Bite(dobj,iobj,prep):
	if prep != None:
		Core.game.Print("Command not understood.")
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
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to break?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Break"):
		Core.game.Print(f"You can't break the {I.name}.")
		return False
	if I.Break():
		return True
	else:
		return False


# this is not intended to be called directly from Parse
# but rather from the Take action function
def CarryCreature(creature):
	Core.game.setPronouns(creature)	
	carrying = Core.player.carrying
	
	if carrying:
		Core.game.Print(f"You're already carrying {carrying.stringName(det='the')}")
	if not isinstance(creature,Core.Creature):
		Core.game.Print(f"You can't carry {creature.stringName(det='the')}")
		return False

	Core.player.unequip(Core.player.gear["left"])
	Core.game.Print(f"You try to pick up {creature.stringName(det='the')}.")
	if not creature.Carry(Core.player):
		return False
	Core.game.Print(f"You are carrying {creature.stringName(det='the')}.")
	return True


def Cast(dobj,iobj,prep):
	if prep not in ("at","on","onto","upon",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What spell will you cast?")
		if dobj in Data.cancels: return False
	if dobj not in Core.player.spells:
		Core.game.Print(f"You don't know a spell called '{dobj}'.")
		return False
	if dobj not in Effects.spells:
		# this shouldn't happen
		Core.game.Print("That spell doesn't exist.")
		return False

	target = None
	if prep != None:
		if iobj == None:
			iobj = getNoun(f"What will you cast upon?")
			if iobj in Data.cancels: return False
		target = findObjFromTerm(iobj,"room")

	return Effects.spells[dobj](target)


def Catch(dobj,iobj,prep):
	Core.game.Print("catching")


# TODO:
# def Climb(dobj,iobj,prep):
# 	Core.game.Print("climbing")


def Close(dobj,iobj,prep):
	if prep != None:
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you close?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not hasattr(I,"open"):
		Core.game.Print(f"The {I.name} doesn't close.")
		return False
	if not I.open:
		Core.game.Print(f"The {I.name} is already closed.")
		return False
	if Core.hasMethod(I,"Close"):
		I.Close()
	else:
		I.open = False
		Core.game.Print(f"You close the {I.name}.")
	return True


def Craft(dobj,iobj,prep):
	Core.game.Print("crafting")


def Crawl(dobj,iobj,prep):
	if prep in ("behind","below","beneath","under",None):
		return Crouch(dobj,iobj,prep)
	if prep in ("in","inside","into","through"):
		Crouch(None,None,None)
		return Go(dobj,iobj,prep)


def Cross(dobj,iobj,prep):
	Core.game.Print("crossing")


def Crouch(dobj,iobj,prep):
	if prep not in ("behind","below","beneath","inside","under",None):
		Core.game.Print("Command not understood.")
		return False

	if dobj != None:
		dobj = iobj
	if dobj != None:
		return Hide(dobj,iobj,prep)

	Core.player.addCondition("crouched",-3)
	return True


def Cut(dobj,iobj,prep):
	Core.game.Print("cuting")


def Define(dobj,iobj,prep):
	if iobj != None or prep != None:
		Core.game.Print("Can only define one word at once.")
		return False
	if dobj == None:
		dobj = getNoun("What term would you like defined?")
		if dobj in Data.cancels: return False

	if dobj in Data.definitions:
		Core.game.Print("\n"+Data.definitions[dobj])
		return True
	elif Core.game.inWorld(dobj):
		return Look(dobj,iobj,prep)
	elif dobj == Core.player.name.lower():
		Core.game.Print(f"\n{Core.player.name}\nThat is you!")
		return True
	Core.game.Print(f"'{dobj}' is unknown")
	return False


def Describe(dobj,iobj,prep):
	if iobj != None or prep != None:
		Core.game.Print("Can only describe one thing at once.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to be described?")
		if dobj in Data.cancels: return False

	if dobj == Core.game.currentroom.name or dobj in ("room","here"):
		D = Core.game.currentroom
	else:
		D = findObjFromTerm(dobj)
	if D == None: return False
	Core.game.setPronouns(D)

	D.describe()
	return True


def Dismount(dobj,iobj,prep):
	if prep not in ("from","of","off","out","out of",None):
		Core.game.Print("Command not understood.")
		return False
	
	if Core.player.riding is None:
		print(f"You're not riding anything")
		return False

	if iobj != None:
		dobj = iobj
	if dobj != None:
		matches = Core.game.nameQueryRoom(dobj)
		if Core.player.riding not in matches:
			print(f"You're not riding a '{dobj}'")
			return False
	
	riding = Core.player.riding
	Core.game.setPronouns(riding)
	Core.game.Print(f"You dismount {riding.stringName(det='the')}.")	
	riding.rider = None
	Core.player.riding = None	
	return True


def Do(dobj,iobj,prep):
	Core.game.Print("doing")


def Dodge(dobj,iobj,prep):
	Core.game.Print("dodgeing")


def Doff(dobj,iobj,prep):
	if prep != None:
		Core.game.Print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to doff?")
		if dobj in Data.cancels: return False

	I = Core.player.inGear(dobj)
	if I == None or not isinstance(I,Core.Armor):
		Core.game.Print(f"You aren't wearing a '{dobj}'.")
		return False
	Core.game.setPronouns(I)

	Core.player.unequip(I)
	Core.game.Print(f"You doff your {I.name}.")
	return True


def Don(dobj,iobj,prep):
	if prep not in ("on","onto","over","to",None):
		Core.game.Print("Command not understood.")
		return False
	if prep == None:
		prep = "on"
	if dobj == None:
		dobj = getNoun("What do you want to don?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"player")
	if I == None: return False
	Core.game.setPronouns(I)

	if not isinstance(I,Core.Armor):
		Core.game.Print(f"You cannot wear your {I.name}.")
		return False
	if I in Core.player.gear.values():
		Core.game.Print(f"You are already wearing your {I.name}.")
		return False
	if iobj and iobj not in Core.player.gear: 
		Core.game.Print(f"You aren't able to equip to '{iobj}'.")
		return False
	if iobj not in I.slots and iobj != None:
		Core.game.Print(f"You cannot wear {I.stringName(det='the')} {prep} your {iobj}.")
		return False
	if not Core.player.equipArmor(I,iobj):
		return False
	Core.game.Print(f"You don your {I.name}.")
	return True


def Drink(dobj,iobj,prep):
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to drink?.")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Drink"):
		Core.game.Print(f"You can't drink the {I.name}.")
		return False
	I.Drink()
	return True


def Drop(dobj,iobj,prep,I=None):
	if prep not in ("down",None):
		return Put(dobj,iobj,prep)
	if dobj == None and I == None:
		dobj = getNoun("What will you drop?.")
		if dobj in Data.cancels: return False

	if I == None and Core.nameMatch(dobj, Core.player.carrying):
		I = Core.player.carrying
	if I == None: I = findObjFromTerm(dobj,"player")
	if I == None: return False
	Core.game.setPronouns(I)

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	if isinstance(I, Core.Creature):
		Core.player.removeCarry()
		Core.game.Print(f"You drop {I.stringName(det='the')}")
	else:
		I.parent.removeItem(I)
		Core.game.Print(f"You drop your {I.name}")
		Core.game.currentroom.addItem(I)
	return True


def Dump(dobj,iobj,prep):
	if prep not in ("in","into","inside","on","onto","out","upon",None):
		Core.game.Print("Command not understood.")
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
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to eat?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Eat"):
		Core.game.Print(f"You can't eat the {I.name}.")
		return False

	I.Eat(Core.player)
	return True


def Enter(dobj,iobj,prep):
	if dobj == None and "in" in Core.game.currentroom.exits:
		return Go("in",iobj,prep)
	return Go(dobj,iobj,prep)


def Equip(dobj,iobj,prep):
	if prep != None:
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to equip?")
		if dobj in Data.cancels:
			return False
	if dobj.startswith("my "):
		dobj = dobj[3:]


	matches = Core.player.inInv(dobj)
	if len(matches) == 0:
		Core.game.Print(f"There is no '{dobj}' in your Inventory")
	I = chooseObject(dobj,matches)
	if I == None: 
		return False
	Core.game.setPronouns(I)

	if I in Core.player.gear.values():
		Core.game.Print(f"Your {I.name} is already equipped.")
		return False
	# if item is armor, equip it as armor, otherwise, equip it in hand
	if isinstance(I,Core.Armor):
		Core.player.equipArmor(I)
	else:
		Core.player.equipInHand(I)
	Core.game.Print(f"You equip your {I.name}.")
	return True


def Escape(dobj,iobj,prep):
	Core.game.Print("escapeing")


def Exit(dobj,iobj,prep):
	if dobj == None and "out" in Core.game.currentroom.exits:
		return Go("out",iobj,prep)
	return Go(dobj,iobj,prep)


def Feed(dobj,iobj,prep):
	Core.game.Print("feeding")


def Fill(dobj,iobj,prep):
	Core.game.Print("filling")


def Find(dobj,iobj,prep):
	Core.game.Print("finding")


def Fish(dobj,iobj,prep):
	Core.game.Print("fishing")


def Follow(dobj,iobj,prep):
	Core.game.Print("following")


def Fuck(dobj,iobj,prep):
	Core.game.Print("There's a time and place for everything, but not now.")


def Give(dobj,iobj,prep):
	Core.game.Print("giveing")


# not called by Parse directly
# called when the user wants to go "up" or "down"
def GoVertical(dir,passage=None,dobj=None):
	if Core.player.hasCondition("flying") and not Core.player.riding:
		newroomname = Core.game.currentroom.allExits()[dir]
		Core.game.Print(f"You fly {dir}!")
		return Core.player.changeRoom(Core.world[newroomname])

	if passage == None and dobj != None:
		Core.game.Print(f"There is no '{dobj}' to go {dir} here.")
		return False
	if passage == None:
		passagename = getNoun(f"What will you go {dir}?")
		passage = findObjFromTerm(passagename,"room")
	if passage == None:
		Core.game.Print(f"There is no '{passagename}' to go {dir} here.")
		return False
	
	if Core.hasMethod(passage,"Traverse"):
		return passage.Traverse(Core.player,dir)


# infers direction, destination, and passage (if they exist) from input terms
def assignGoTerms(dobj,iobj,prep):
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
	elif dir == None: dir = prep

	# assign passage
	if dobj != None: passage = findObjFromTerm(dobj,"room",silent=True)
	elif iobj != None: passage = findObjFromTerm(iobj,"room",silent=True)

	return dir,dest,passage


# parses user input to determine the intended direction, destination, and/or
# passage. Then calls either traverse or changeroom accordingly
def Go(dobj,iobj,prep):
	# print(dobj,iobj,prep)
	preps = ("away","away from","down","through","to","toward","up","in","inside","into","on","onto","out",None)
	if prep in ("to", "toward", "away", "away from"):
		prep = None
	if (dobj,iobj,prep) == (None,None,None):
		dobj,iobj,prep = parseWithoutVerb("Where will you go?",preps)
	if dobj in Data.cancels: return False
	if dobj in ("back", "backward", "backwards"): dobj = Core.game.prevroom.name.lower()
	if dobj in ("ahead", "forward", "forwards"): dobj = getNoun("In which direction?")
	if dobj == None: dobj = iobj

	# if any terms are abbreviations for a direction, expand them
	dobj,iobj,prep = map(Core.expandDir,[dobj,iobj,prep])
	if prep not in preps or (dobj,iobj,prep) == (None,None,None):
		Core.game.Print("Command not understood.")
		return False

	# get dir, dest, and passage and validate them
	dir,dest,passage = assignGoTerms(dobj,iobj,prep)
	# print(dir,dest,passage)
	if (dir,dest,passage) == (None,None,None):
		Core.game.Print(f"There is no exit leading to a '{dobj}' here.")
		return False
	if Core.nameMatch(dest,Core.game.currentroom):
		Core.game.Print(f"You are already there!")
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
			Core.game.Print(f"There is no exit leading '{dir}' here.")
			return False

	# call one of three functions to actually change rooms
	# depends if they go normally, traverse a passage, or go vertically
	if dir in ("up","down"):
		return GoVertical(dir,passage,dobj)
	# if just passage is given
	if passage != None:
		if not Core.hasMethod(passage,"Traverse"):
			Core.game.Print(f"The {passage.name} cannot be traversed.")
			return False
		return passage.Traverse(Core.player,dir)
	# if just dest given
	if dest != None:
		return Core.player.changeRoom(Core.world[dest])
	Core.game.Print(f"There is no exit leading to a '{dobj}' here.")
	return False


def Hide(dobj,iobj,prep):
	if prep not in ("behind","below","beneath","inside","under",None):
		Core.game.Print("Command not understood.")
		return False

	if dobj == None: dobj = iobj
	if dobj == None:
		dobj = getNoun("What do you want to hide behind?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,"room")
	if I == None: return False
	Core.game.setPronouns(I)

	if not isinstance(I,Core.Fixture) or I.weight < 50:
		Core.game.Print(f"You can't hide behind {I.name}.")
		return False

	Core.player.addCondition("hiding",-3)
	return True


def Ignite(dobj,iobj,prep):
	Core.game.Print("igniteing")


def Insert(dobj,iobj,prep):
	Core.game.Print("inserting")


def Jump(dobj,iobj,prep):
	Core.game.Print("jumping")


def Kick(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you kick?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"foot","with")


def Kill(dobj,iobj,prep):
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj in ("myself","me"):
		if Core.yesno("Are you sure you want to kill yourself?"):
			Core.player.death()
			return True
		Core.game.Print("Fwew, that was close!")
		return False
	return Attack(dobj,iobj,prep)


def Lick(dobj,iobj,prep):
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to lick?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Lick"):
		return I.Lick(Core.player)
		
	if I.composition in Data.tastes:
		Core.game.Print(Data.tastes[I.composition])
	if I.composition in Data.scents:
		Core.game.Print(Data.scents[I.composition].replace("scent","taste"))
	return True


def Light(dobj,iobj,prep):
	Core.game.Print("lighting")


def Listen(dobj,iobj,prep):
	Core.game.Print("listening")


def Lock(dobj,iobj,prep):
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False

	if dobj == None:
		dobj = getNoun("What will you lock?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Lock"):
		Core.game.Print(f"The {I.name} doesn't lock.")
		return False

	if iobj == None:
		iobj = getNoun("What will you lock with?")
		if iobj in Data.cancels: return False
	K = findObjFromTerm(iobj,"player")
	if K == None: return False

	if not isinstance(K,Items.Key):
		Core.game.Print(f"You can't lock with the {K.name}.")
		return False
	return I.Lock(K)


def Look(dobj,iobj,prep):
	if prep not in ("at","in","inside","into","on","through",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None: dobj = iobj
	if dobj == None:
		dobj = getNoun("What will you look at?")
		if dobj in Data.cancels: return False

	if dobj in ("around","here","room") or dobj == Core.game.currentroom.name.lower():
		Core.game.currentroom.describe()
		return True
	if dobj in ("me","myself",Core.player.name):
		Core.game.Print(f"You are {Core.player.desc}")
		return True

	L = findObjFromTerm(dobj)
	if L == None: return False
	Core.game.setPronouns(L)

	L.describe()
	if Core.hasMethod(L,"Look"):
		L.Look()
	return True


def Mount(dobj,iobj,prep):
	if prep not in ("in","into","inside","on","onto","upon",None):
		Core.game.Print("Command not understood.")
		return False
	
	if Core.player.riding is not None:
		print(f"You're already riding {Core.player.riding.stringName()}")
		return False

	if dobj == None: dobj = iobj
	if dobj == None:
		dobj = getNoun("What will you mount?")
		if dobj in Data.cancels: return False

	C = findObjFromTerm(dobj,"room")
	if C == None: return False
	Core.game.setPronouns(C)
	
	if Core.player.Weight() > C.BRDN():
		Core.game.Print(f"You are too heavy to ride {C.stringName(det='the')}")
		return False
	C.Ride(Core.player)
	return True


def Open(dobj,iobj,prep):
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you open?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Open"):
		Core.game.Print(f"The {I.name} doesn't open.")
		return False
	if hasattr(I,"locked") and I.locked:
		Core.game.Print(f"The {I.name} is locked")
		return False
	I.Open()
	return True


def Pet(dobj,iobj,prep):
	Core.game.Print("peting")


def Play(dobj,iobj,prep):
	Core.game.Print("playing")


def Point(dobj,iobj,prep):
	Core.game.Print("pointing")


def Pour(dobj,iobj,prep,I=None):
	if prep not in ("in","into","inside","on","onto","out","upon",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you pour?")
		if dobj in Data.cancels: return False

	if I == None: I = findObjFromTerm(dobj,"player")
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Pour"):
		Core.game.Print(f"You can't pour the {I.name}.")
		return False

	R = None
	if iobj != None and iobj not in ("floor","ground"):
		R = findObjFromTerm(iobj)
		if R == None: return False

	if prep == None: prep = "on"
	if R != None: Core.game.Print(f"You pour your {I.name} {prep} the {R.name}.")
	else: Core.game.Print(f"You pour out your {I.name}.")
	I.Pour(R)
	return True


def Pray(dobj,iobj,prep):
	Core.game.Print("praying")


def Press(dobj,iobj,prep):
	Core.game.Print("pressing")


def Pull(dobj,iobj,prep):
	Core.game.Print("pulling")


def Punch(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you punch?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"fist","with")


def Push(dobj,iobj,prep):
	Core.game.Print("pushing")


def Put(dobj,iobj,prep):
	if prep not in ("in","into","inside","on","onto","upon","down",None):
		Core.game.Print("Command not understood.")
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

	if iobj in ("floor","ground","here"):
		return Drop(dobj,iobj,prep,I=I)
	R = findObjFromTerm(iobj)
	if R == None: return False

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	if not Core.hasMethod(R,"addItem"):
		Core.game.Print(f"You can't put the {I.name} {prep} the {R.name}.")
		return False
	
	idet = "your" if Core.player in I.ancestors() else 'the'
	rdet = "your" if Core.player in R.ancestors() else 'the'
	outprep = "on" if isinstance(R,Items.Table) else "in"
	if iobj == "here": Core.game.Print(f"You put your {I.name} here.")
	else: Core.game.Print(f"You put {idet} {I.name} {outprep} {rdet} {R.name}.")
	I.parent.removeItem(I)
	R.addItem(I)
	return True


def Quicksave():
	Menu.quickSave("quicksave")
	return parse()


def Release(dobj,iobj,prep):
	Core.game.Print("releaseing")


def Rest(dobj,iobj,prep):
	if prep not in ("behind","below","beneath","in","inside","into","on","onto","over","under","upon","using","with",None):
		Core.game.print("Commmand not understood")
		return False
	for condname in Data.conditionDmg.keys():
		if Core.player.hasCondition(condname):
			Core.game.Print(f"This is no time for slumber! You are {condname}.")
			return False

	if prep is None: prep = "on"
	if dobj == None: dobj = iobj
	if dobj == None: dobj = getNoun(f"What will you sleep {prep}?")
	if dobj in Data.cancels: return False
	if dobj in ("nothing","ground","floor","here","room"):
		I = None
	else:
		I = findObjFromTerm(dobj)
		if I == None and not Core.yesno("Would you like to sleep on the ground?"):
			return False

	if I == None:
		Core.game.Print("Your sleep will not be very restful...")
	if I != None:
		# TODO: add lay down here
		pass

	sleeptime = 90 + randint(1,20)
	Core.player.addCondition("asleep",sleeptime)
	Core.ellipsis(3)
	Core.game.silent=True
	return True


def Restrain(dobj,iobj,prep):
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False

	if dobj == None:
		dobj = getNoun("What will you restrain?")
		if dobj in Data.cancels: return False

	C = findObjFromTerm(dobj,"room")
	if C == None: return False
	Core.game.setPronouns(C)

	if not isinstance(C,Core.Creature):
		Core.game.Print(f"You can't restrain the {C.name}.")
		return False

	I = None
	if iobj != None:
		I = findObjFromTerm(iobj,"player")
		if I == None: return False
		if not Core.hasMethod(I,"RestrainWith"):
			Core.game.Print(f"You can't restrain with the {I.name}.")
			return False

	if "restrained" in C.status:
		Core.game.Print(f"{C.stringName(det='the')} is already restrained.")
	if not C.Restrain(Core.player,I):
		Core.game.Print(f"You fail to restrain the {C.name}.")
		return False
	Core.game.Print(f"You restrain the {C.name}.")
	return True


def Return(*args): 
	return Go(None, Core.game.prevroom.name.lower(), None)


def Ring(dobj,iobj,prep):
	Core.game.Print("ringing")


def Rub(dobj,iobj,prep):
	Core.game.Print("rubbing")


def Save(dobj,iobj,prep):
	Menu.saveGame(dobj)
	return parse()


def Search(dobj,iobj,prep):
	Core.game.Print("searching")


def Shoot(dobj,iobj,prep):
	Core.game.Print("shooting")


def Shove(dobj,iobj,prep):
	Core.game.Print("shoveing")


def Smell(dobj,iobj,prep):	
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to smell?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Smell"):
		return I.Smell(Core.player)
		
	if I.composition in Data.scents:
		Core.game.Print(Data.scents[I.composition])
	elif I.composition in Data.tastes:
		Core.game.Print(Data.tastes[I.composition].replace("taste","scent"))
	return True


def Steal(dobj,iobj,prep,I=None):
	Core.game.Print(f"stealing {dobj} {prep} {iobj}")


def Struggle(dobj,iobj,prep):
	Core.game.Print("struggleing")


def Swim(dobj,iobj,prep):
	Core.game.Print("swiming")


def Talk(dobj,iobj,prep):
	if prep not in ("at","into","to","toward","with",None):
		Core.game.Print("Command not understood.")
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
		Core.game.Print(f"There is no response...")
		return False

	target.Talk(Core.player,Core.game,Core.world)
	return True


def Throw(dobj,iobj,prep):
	Core.game.Print("throwing")


def Tie(dobj,iobj,prep):
	Core.game.Print("tieing")


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
	strname = objToTake.stringName(det='the' if count==1 else 'a')
	tookMsg = f"You take {strname}{suffix}."
	failMsg = f"You can't take the {objToTake.name}, your Inventory is too full."

	return Core.player.obtainItem(objToTake,tookMsg,failMsg) or takenAny


def TakeAll():
	if len(Core.game.currentroom.items) == 0:
		Core.game.Print("There are no items to take.")
		return False
	takenAny = False
	for obj in [obj for obj in Core.game.currentroom.items]:
		takenAny = TakeAllRecur(obj) or takenAny
	return takenAny


def Take(dobj,iobj,prep):
	if prep not in ("from","in","inside","out","out of","up",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you take?")
		if dobj in Data.cancels: return False

	if dobj in ("all","everything","it all"): return TakeAll()

	if iobj in ("here", "room"):
		obj = findObjFromTerm(dobj,"room",roomD=2)
	else:
		obj = findObjFromTerm(dobj,roomD=2,reqParent=iobj)
	if obj is None:
		return False
	if obj.parent is Core.player:
		Core.game.Print(f"You can't take from your own Inventory.")
		return False
	Core.game.setPronouns(obj)

	if isinstance(obj,Core.Creature): return CarryCreature(obj)
	if not isinstance(obj,Core.Item) or isinstance(obj,Core.Fixture):
		Core.game.Print(f"You can't take the {dobj}.")
		return False

	parent = obj.parent
	# if it is in a non-player inventory, it will have to be stolen
	if any(isinstance(anc,Core.Creature) for anc in obj.ancestors()) and obj not in Core.player.invSet():
		return Steal(dobj,iobj,prep,I=obj)
	count = parent.itemNames().count(obj.name)

	if parent is Core.game.currentroom: suffix = ""
	elif Core.player in obj.ancestors(): suffix = " from your " + parent.name
	else: suffix = " from the " + parent.name
	strname = obj.stringName(det='the' if count==1 else 'a')
	tookMsg = f"You take {strname}{suffix}."
	failMsg = f"You can't take the {obj.name}, your Inventory is too full."

	return Core.player.obtainItem(obj,tookMsg,failMsg)


def Touch(dobj,iobj,prep):
	Core.game.Print("touching")


def Trip(dobj,iobj,prep):
	Core.game.Print("triping")


def Unequip(dobj,iobj,prep):
	if prep != None:
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to unequip?")
		if dobj in Data.cancels: return False

	I = Core.player.inGear(dobj)
	if I == None:
		Core.game.Print(f"You do not have a '{dobj}' equipped.")
		return False
	Core.game.setPronouns(I)

	Core.game.Print(f"You unequip your {I.name}.")
	Core.player.unequip(I)
	return True


def Unlock(dobj,iobj,prep):
	if prep not in ("using","with",None):
		Core.game.Print("Command not understood.")
		return False
	if dobj == None:
		dobj = getNoun("What will you unlock?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)
	if not Core.hasMethod(I,"Unlock"):
		Core.game.Print(f"The {I.name} doesn't unlock.")
		return False

	if iobj == None:
		iobj = getNoun("What will you unlock with?")
		if iobj in Data.cancels: return False

	K = findObjFromTerm(iobj,"player")
	if K == None: return False

	if not isinstance(K,Items.Key):
		Core.game.Print(f"You can't unlock with the {K.name}.")
		return False
	return I.Unlock(K)


def Untie(dobj,iobj,prep):
	Core.game.Print("untieing")


def Use(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you use?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Use"):
		Core.game.Print(f"You can't use the {I.name}.")
		return False
	I.Use(Core.player)
	return True


def Wait(dobj,iobj,prep):
	Core.game.Print("waiting")


def Wave(dobj,iobj,prep):
	Core.game.Print("waveing")




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
"examples":Examples,
"exits":Exits,
"gear":Core.Player.printGear,
"help":Help,
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
"get up":Mount,
"give":Give,
"go":Go,
"go to sleep":Rest,
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
"let go": Drop,
"lick":Lick,
"light":Ignite,
"listen":Listen,
"lock":Lock,
"look":Look,
"make":Craft,
"mount":Mount,
"move":Go,
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
"proceed":Go,
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
"save":Save,
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
"slumber":Rest,
"smash":Break,
"smell":Smell,
"sneak":Crouch,
"sniff":Smell,
"snooze":Rest,
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
# squat - > crouch
# pee/poop/shit on (soil your pants if they have them on)
# caress, stroke -> pet
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
# stop
# blow/breath
# clap
# snap
# observe/watch
# capture (with a net?) -> take?
# loot/scavenge/forage/salvage/harvest