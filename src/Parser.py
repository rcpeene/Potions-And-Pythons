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


def chooseObject(name,objects):
	print()
	while True:
		for n,object in enumerate(objects):
			entry = object.name
			if isinstance(object,Core.Creature):
				entry += f"	({object.hp} hp)"
			elif isinstance(object.parent,Core.Player):
				entry += "	(inv)"
			elif not isinstance(object.parent,Core.Room):
				entry += f"	({object.parent.name})"
			print(f"{n+1}. {entry}")

		print(f"\nWhich {name}?")
		choice = input("\n> ").lower()
		if choice == "": continue
		if choice in Data.cancels: return None
		break

	try:
		return objects[int(choice)-1]
	except:
		for obj in objects:
			if choice == obj.name.lower():
				return obj
	print("That is not one of the options")
	return None


def findObjFromTerm(term,searchPlayer,searchRoom,roomD=1,playerD=2,reqParent=None,silent=False):
	matches = []
	if searchPlayer:
		matches += Core.player.inInv(term)
	if searchRoom:
		matches += Core.game.currentroom.search(term,d=roomD,reqParent=reqParent)

	if len(matches) == 0:
		if not silent:
			if searchRoom and searchPlayer:
				print(f"There is no '{term}'")
			elif searchPlayer:
				print(f"There is no '{term}' in your Inventory")
			elif searchRoom:
				print(f"There is no '{term}' here")
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
	Core.player.search(noun) or \
	Core.game.inWorld(noun):
		return True
	return False


# recursively inspects the command, which is a list of words, starting at i
# combines multiple words into single terms that appear to be a meaningful term
# returns the command after any relevant words are joined into one term
# ex. ["attack","green","snake"] -> ["attack","green snake"]
# this algorithm favors the meaningful terms which contain the most words
def nounify(command,i):
	# base case when end of command is reached
	if i >= len(command)-1:
		return command
	# the possible noun begins as the word at i (subsequent words will be added)
	possibleNoun = command[i]
	j = i+1
	while j < len(command):
		# possibleNoun is all words between i and j joined
		possibleNoun += ' '+command[j]
		# if new term refers to a rendered object, a location, or a game term:
		if isMeaningful(possibleNoun):
			# combine words into one element and recur
			del command[i:j+1]
			command.insert(i,possibleNoun)
			return nounify(command,i)
		j += 1
	return nounify(command,i+1)


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
		return None
	return obj.name


# validates user input and processes into into a command form usable by parse(),
# namely, it returns a list of words without capitals, symbols, or articles
# the last step, nounify(), joins words that may only be meaningful as one term
def processCmd(prompt,storeRawCmd=False):
	rawcommand = input("\n" + prompt + "\n> ")
	# take input until input has any non-whitespace characters in it
	while not any(i not in "\t " for i in rawcommand):
		rawcommand = input("> ")
	# for convenience, save raw command in game object
	if storeRawCmd:
		Core.game.lastRawCommand = rawcommand.split()

	# lowercase-ify the sentence command, copy it excluding symbols
	purecommand = "".join([i for i in rawcommand.lower() if i not in Data.symbols])
	# copy command, delimited by spaces, into a list of words excluding articles
	listcommand = [i for i in purecommand.split() if i not in Data.articles]
	# finally, combine certain words if they appear to make one noun term
	finalcommand = nounify(listcommand,0)
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

	if dobj in Data.pronouns:
		dobj = replacePronoun(dobj)
	if iobj in Data.pronouns:
		iobj = replacePronoun(iobj)

	return dobj,iobj,prep


# called in parse() when a command fails, it simply recurs parse(), and...
# prints a helpful message if user has provided invalid input 3 or more times
# n is the number of times parse() has recurred
def promptHelp(msg,n):
	if msg != "":
		print(msg)
	if n >= 2:
		print("Enter 'help' for a list of commands")
	if n > 32:
		return False	# prevent stack overflow from repeated bad input
	return parse(n+1)	# ask again


# the primary input parsing function for the game
# its purpose is to parse command grammar and call the related action function
# it is called by main() with processCmd() as its first argument
# it is called on infinite loop until it returns True
# it returns True only when the player successfully takes an action in the game
# n denotes how many times parse has recurred
def parse(n=0):
	command = processCmd("What will you do?",storeRawCmd=True)
	if len(command) == 0:
		return promptHelp("Command not understood",n)
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
	elif verb in Data.shortverbs or verb in Data.statcommands:
		if len(command) != 1:
			return promptHelp(f"The '{verb}' command can only be one word",n)
		if verb.upper() in Data.abilities:
			return Core.player.printAbility(verb.upper())
		if verb in Data.statcommands:
			return shortactions[verb](Core.player)
		if verb == "here":
			return Core.game.currentroom.describe()
		return shortactions[verb]()
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

	if dobj in Data.pronouns:
		dobj = replacePronoun(dobj)
	if iobj in Data.pronouns:
		iobj = replacePronoun(iobj)

	# this line calls the action function using the 'actions' dict
	actionCompleted = actions[verb](dobj,iobj,prep)
	# if action was instant, loop for another command
	if verb in Data.instantactions:
		return False
	# if action was not completed for some reason, recur
	if not actionCompleted:
		return promptHelp("",n)
	return True




##########################################
## CHEATCODES AND DEV COMMAND FUNCTIONS ##
##########################################


def Exe(command):
	if len(command) < 2:
		print("Error: No code given")
		return
	code = " ".join(command[1:])
	try:
		exec(code)
	except Exception as e:
		print("Error: Code was unable to be executed:")
		print(e)


def Get(command):
	if len(command) < 2:
		print("Error: No object name given")
		return
	if len(command) < 3:
		print("Error: No attribute name given")
		return
	objname = command[1].lower()
	attrname = ( " ".join(command[2:]) ).lower()

	if objname in {"p","player","my"}: obj = Core.player
	elif objname in {"g","game"}: obj = Core.game
	elif objname in {"here","room"}: obj = Core.game.currentroom
	elif objname in {"w","world"}: obj = Core.world
	elif objname in Core.world: obj = Core.world[objname]
	else: obj = findObjFromTerm(objname,True,True,playerD=3,roomD=3)
	if obj == None:
		print("Error: Object not found")
		return

	try:
		print(getattr(obj,attrname))
	except:
		print("Error: Attribute does not exist")


def Learn(command):
	try:
		Core.player.gainxp(int(command[1]))
	except:
		print("Error: Value not number")


def Mode(command):
	try:
		Core.game.mode = int(command[1])
		print("Mode set to " + str(Core.game.mode))
	except:
		print("Error: Value not number")


def Pypot(command):
	try:
		money = int(command[1])
		Core.player.money = Core.player.money + money
		if Core.player.money < 0:
			Core.player.money = 0
		print(f"You now have {Core.player.money} money")
	except:
		print("Error: Value not number")


def Set(command):
	if len(command) < 2:
		print("Error: No object name given")
		return
	if len(command) < 3:
		print("Error: No attribute name given")
		return
	if len(command) < 4:
		print("Error: No value given")
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
	else: obj = findObjFromTerm(command[1],True,True,playerD=3,roomD=3)

	setattr(obj,attrString,val)


def Teleport(command):
	if len(command) < 2:
		print("Not enough arguments")
		return
	location = " ".join(command[1:])
	if location in Core.world:
		Core.game.changeRoom(Core.world[location])
	else:
		print("Location not in world")


def Test(command):
	print(Core.player)
	return True


def Warp(command):
	try:
		Core.game.time += int(command[1])
	except:
		print("Value not number")


def Zap(command):
	objname = " ".join(command[1:])
	allObjects = Core.game.getAllObjects()
	zappedObjects = 0
	for obj in allObjects:
		if objname.lower() == obj.name.lower():
			if isinstance(obj,Core.Item):
				obj.Break()
			elif isinstance(obj,Core.Creature):
				obj.death()
			zappedObjects += 1
	print("Zapped objects: " + str(zappedObjects))




#######################################
## SHORTACTION AND RELATED FUNCTIONS ##
#######################################


def Cry(): print("A single tear sheds from your eye")
def Dance(): print("You bust down a boogie")

def Examples():
	Core.clearScreen()
	print(Data.examples)
	input()
	Core.clearScreen()

def Goodbye(): print(Core.capWords(choice(list(Data.goodbyes)),n=1))

def Hello(): print(Core.capWords(choice(list(Data.hellos)),n=1))

def Help():
	Core.clearScreen()
	print("\nPlayer Statistics Commands")
	Core.columnPrint(Data.statcommands,12,10)
	print("\nOther Single-Word Commands")
	Core.columnPrint(Data.shortverbs,12,10)
	print("\nVerb Commands (Does not include cheat codes and secret commands)")
	Core.columnPrint(Data.verbs,12,10)
	print("\nDuring the game, type 'info' for information on the game and how to play")
	input()
	Core.clearScreen()


def Info():
	Core.clearScreen()
	print(Data.gameinfo)
	input()
	Core.clearScreen()


def Laugh(): print('"HAHAHAHAHA!"')


def Quit():
	if Core.yesno("Are you sure you want to quit? (Anything unsaved will be lost)"):
		Core.game.quit = True
		return True


#go to previous room
def Return(): return Go(None, Core.game.prevroom.name.lower(), None)
def Save(): Menu.saveGame()
def Shout(): print('"AHHHHHHHHHH"')
def Sing(): print('"Falalalaaaa"')
def Time(): print("Time:", Core.game.time)
def Yawn(): print("This is no time for slumber!")




##################################
## ACTION AND RELATED FUNCTIONS ##
##################################


def Attack(dobj,iobj,prep,target=None,weapon=None):
	if prep not in {"with","using",None}:
		print("Command not understood")
		return False

	if iobj == None:
		if len(Core.player.weapons()) == 0:
			iobj = "fist"
		elif Core.player.gear["right"] == Empty() and Core.player.gear["left"] == Empty():
			iobj = getNoun("What will you attack with?")
			if iobj in Data.cancels: return False

	if weapon == None:
		weapon = Core.player.weapon
	if iobj != None and weapon == Core.Empty():
		weapon = Core.player.inGear(iobj)
		if weapon == None:
			weapon = Core.player.inInv(iobj)
		if iobj in {"fist","hand"}:
			weapon = Items.Hand("your hand","",[],"",4,-1,[])
		if iobj in {"foot","leg"}:
			weapon = Items.Foot("your foot","",[],"",8,-1,[])
		if iobj in {"mouth","teeth"}:
			weapon = Items.Mouth("your mouth","",[],"",4,-1,[])
		if weapon == None:
			print(f"There is no '{iobj}' in your Inventory")
			return False

	if target == None:
		if dobj == None: dobj = getNoun("What will you attack?")
		if dobj in Data.cancels: return False
		if dobj in {"myself","me"}: target = Core.player
		else: target = findObjFromTerm(dobj,False,True)
		if target == None: return False
	Core.game.setPronouns(target)

	stowed = False
	if isinstance(weapon,(Items.Hand,Items.Foot,Items.Mouth)):
		stowedweapons = Core.player.weapon,Core.player.weapon2
		Core.player.weapon,Core.player.weapon2 = weapon.improviseWeapon(),Core.Empty()
		stowed = True
	elif weapon not in Core.player.gear.values():
		Core.player.equipInHand(weapon)

	print(f"\nYou attack the {target.name} with {Core.player.weapon.name}")
	if isinstance(target,Core.Creature):
		Core.player.attackCreature(target)
	elif isinstance(target,Core.Item):
		Core.player.attackItem(target)
	if stowed:
		Core.player.weapon,Core.player.weapon2 = stowedweapons
	return True


def Bite(dobj,iobj,prep):
	if prep not in {"with","using",None}:
		print("Command not understood")
	if dobj == None:
		dobj = getNoun("What do you want to bite?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
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
	if prep not in {"with",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to break?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Break"):
		print("You can't break the " + I.name)
		return False
	I.Break()
	return True


# this is not intended to be called directly from Parse
# but rather from the Take action function
def CarryCreature(creature):
	# TODO: identify a way to link carrier to carried without remove carried creature from Room.creatures
	if not isinstance(creature,Core.Creature):
		print(f"You can't carry the {creature.name}")
		return False

	print(f"You try to pick up the {creature.name}")
	if creature.Restrain(Core.player):
		Core.player.Carry(creature)
		print(f"You successfully carry the {creature.name}!")
		return True
	else:
		print(f"You fail to restrain the {creature.name}!")
		return True


def Cast(dobj,iobj,prep):
	if prep not in {"at","on","onto","upon",}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What spell will you cast?")
		if dobj in Data.cancels: return False
	if dobj not in Core.player.spells:
		print("You don't know a spell called " + dobj)
		return False
	if dobj not in spells:
		# this shouldn't happen
		print("That spell doesn't exist")
		return False

	return Effects.spells[dobj](iobj)


def Catch(dobj,iobj,prep):
	print("catching")


# TODO:
# def Climb(dobj,iobj,prep):
# 	print("climbing")


def Close(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you close?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
	if I == None: return False
	Core.game.setPronouns(I)

	if not hasattr(I,"open"):
		print(f"The {I.name} doesn't close")
		return False
	if not I.open:
		print(f"The {I.name} is already closed")
		return False
	if Core.hasMethod(I,"Close"):
		I.Close()
	else:
		I.open = False
		print("You close the " + I.name)
	return True


def Craft(dobj,iobj,prep):
	print("crafting")


def Crawl(dobj,iobj,prep):
	if prep in {"behind","below","beneath","under",None}:
		return Crouch(dobj,iobj,prep)
	if prep in {"in","inside","into","through"}:
		Crouch(None,None,None)
		return Go(dobj,iobj,prep)


def Cross(dobj,iobj,prep):
	print("crossing")


def Crouch(dobj,iobj,prep):
	if prep not in {"behind","below","beneath","inside","under",None}:
		print("Command not understood")
		return False

	if dobj != None:
		dobj = iobj
	if dobj != None:
		return Hide(dobj,iobj,prep)

	Core.player.addCondition("crouched",-3)
	return True


def Cut(dobj,iobj,prep):
	print("cuting")


def Define(dobj,iobj,prep):
	if iobj != None or prep != None:
		print("Can only define one word at once")
		return False
	if dobj == None:
		dobj = getNoun("What term would you like defined?")
		if dobj in Data.cancels: return False

	if dobj in Data.definitions:
		print("\n"+Data.definitions[dobj])
		return True
	elif Core.game.inWorld(dobj):
		return Look(dobj,iobj,prep)
	elif dobj == Core.player.name.lower():
		print(f"\n{Core.player.name}\nThat is you!")
		return True
	print(f"'{dobj}' is unknown")
	return False


def Describe(dobj,iobj,prep):
	if iobj != None or prep != None:
		print("Can only describe one thing at once")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to be described?")
		if dobj in Data.cancels: return False

	if dobj == Core.game.currentroom.name or dobj in {"room","here"}:
		D = Core.game.currentroom
	else:
		D = findObjFromTerm(dobj,True,True)
	if D == None: return False
	Core.game.setPronouns(D)

	D.describe()
	return True


def Do(dobj,iobj,prep):
	print("doing")


def Dodge(dobj,iobj,prep):
	print("dodgeing")


def Doff(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to doff?")
		if dobj in Data.cancels: return False

	I = Core.player.inGear(dobj)
	if I == None or not isinstance(I,Core.Armor):
		print(f"You aren't wearing a '{dobj}'")
		return False
	Core.game.setPronouns(I)

	Core.player.unequip(I)
	print(f"You doff your {I.name}")
	return True


def Don(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to don?")
		if dobj in Data.cancels: return False

	I = Core.player.inInv(dobj)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False

	if not isinstance(I,Core.Armor):
		print(f"You cannot wear your {I.name}")
		return False
	if I in Core.player.gear.values():
		print(f"You are already wearing your {I.name}")
		return False
	Core.game.setPronouns(I)

	if not Core.player.equipArmor(I):
		return False
	print(f"You don your {I.name}")
	return True


def Drink(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to drink?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Drink"):
		print("You can't drink the " + I.name)
		return False
	I.Drink()
	return True


def Drop(dobj,iobj,prep,I=None,R=None):
	if prep not in {"down",None}:
		return Put(dobj,iobj,prep)
	if dobj == None and I == None:
		dobj = getNoun("What will you drop?")
		if dobj in Data.cancels: return False

	if I == None: I = findObjFromTerm(dobj,True,False)
	if I == None: return False
	Core.game.setPronouns(I)

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	print("You drop your " + I.name)
	I.parent.removeItem(I)
	Core.game.currentroom.addItem(I)
	return True


def Dump(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you dump?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,False)
	if I == None: return False
	Core.game.setPronouns(I)

	if Core.hasMethod(I,"Pour"):
		return Pour(dobj,iobj,prep,I=I)
	else:
		return Drop(dobj,iobj,prep,I=I)


def Eat(dobj,iobj,prep):
	if prep not in {"with",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to eat?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Eat"):
		print("You can't eat the " + I.name)
		return False
	I.Eat()
	return True


def Enter(dobj,iobj,prep):
	if dobj == None and "in" in Core.game.currentroom.exits:
		return Go("in",iobj,prep)
	return Go(dobj,iobj,prep)


def Equip(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to equip?")
		if dobj in Data.cancels:
			return False

	I = findObjFromTerm(dobj,True,False)
	if I == None: return False
	Core.game.setPronouns(I)

	if Core.player.inGear(dobj) and Core.player.invNames(lower=True).count(dobj) == 1:
		print(f"Your {dobj} is already equipped")
		return False
	# if item is armor, equip it as armor, otherwise, equip it in hand
	if isinstance(I,Core.Armor):
		Core.player.equipArmor(I)
	else:
		Core.player.equipInHand(I)
	print(f"You equip your {I.name}")
	return True


def Escape(dobj,iobj,prep):
	print("escapeing")


def Exit(dobj,iobj,prep):
	if dobj == None and "out" in Core.game.currentroom.exits:
		return Go("out",iobj,prep)
	return Go(dobj,iobj,prep)


def Feed(dobj,iobj,prep):
	print("feeding")


def Fill(dobj,iobj,prep):
	print("filling")


def Find(dobj,iobj,prep):
	print("finding")


def Fish(dobj,iobj,prep):
	print("fishing")


def Follow(dobj,iobj,prep):
	print("following")


def Fuck(dobj,iobj,prep):
	print("There's a time and place for everything, but not now")


def Give(dobj,iobj,prep):
	print("giveing")


# not called by Parse directly
# called when the user wants to go "up" or "down"
def GoVertical(dir,passage=None,dobj=None):
	if Core.player.hasCondition("flying"):
		newroom = Core.game.currentroom.allExits()[dir]
		print(f"You fly {dir}!")
		return Core.game.changeRoom(Core.world[newroom])

	if passage == None and dobj != None:
		print(f"There is no '{dobj}' to go {dir} here")
		return False
	if passage == None:
		passagename = getNoun(f"What will you go {dir}?")
		passage = findObjFromTerm(passagename,False,True)
	if passage == None:
		print(f"There is no '{passagename}' to go {dir} here")
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
	if iobj in Core.game.currentroom.allExits().values(): dest = iobj

	# assign passage
	if dobj != None: passage = findObjFromTerm(dobj,False,True,silent=True)
	elif iobj != None: passage = findObjFromTerm(iobj,False,True,silent=True)

	return dir,dest,passage


# parses user input to determine the intended direction, destination, and/or... # passage. Then calls either traverse or changeroom accordingly
def Go(dobj,iobj,prep):
	preps = {"down","through","to","toward","up","in","into","on","onto","out",None}
	if (dobj,iobj,prep) == (None,None,None):
		dobj,iobj,prep = parseWithoutVerb("Where will you go?",preps)
	if dobj in Data.cancels: return False
	if dobj == "back": dobj = Core.game.prevroom.name.lower()
	if dobj == None: dobj = iobj

	# if any terms are abbreviations for a direction, expand them
	dobj,iobj,prep = map(Core.expandDir,[dobj,iobj,prep])
	if prep not in preps:
		print("Command not understood")
		return False

	# get dir, dest, and passage and validate them
	dir,dest,passage = assignGoTerms(dobj,iobj,prep)
	if dir != None and dir not in Core.game.currentroom.allExits():
		print(f"There is no exit leading '{dir}' here")
		return False
	if (dir,dest,passage) == (None,None,None):
		print(f"There is no exit leading to a '{dobj}' here")
		return False
	if dir == None:
		dir = Core.game.currentroom.getDirFromDest(dest)
	if (dest,passage) == (None,None):
		dest = Core.game.currentroom.allExits()[dir]
	if passage == None:
		passage = Core.game.currentroom.getPassageFromDir(dir)

	# call one of three functions to actually change rooms
	# depends if they go normally, traverse a passage, or go vertically
	if dir == "up" or dir == "down":
		return GoVertical(dir,passage,dobj)
	# if just passage is given
	if passage != None:
		if not Core.hasMethod(passage,"Traverse"):
			print(f"The {passage.name} cannot be traversed")
			return False
		return passage.Traverse(dir)
	# if just dest given
	if dest != None:
		return Core.game.changeRoom(Core.world[dest])
	print(f"There is no exit leading to a '{dobj}' here")
	return False


def Hide(dobj,iobj,prep):
	if prep not in {"behind","below","beneath","inside","under",None}:
		print("Command not understood")
		return False

	if dobj == None: dobj = iobj
	if dobj == None:
		dobj = getNoun("What do you want to hide behind?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,False,True)
	if I == None: return False
	Core.game.setPronouns(I)

	if not isinstance(I,Core.Fixture) or I.weight < 50:
		print("You can't hide behind " + I.name)
		return False

	Core.player.addCondition("hiding",-3)
	return True


def Ignite(dobj,iobj,prep):
	print("igniteing")


def Insert(dobj,iobj,prep):
	print("inserting")


def Jump(dobj,iobj,prep):
	print("jumping")


def Kick(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you kick?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"foot","with")


def Kill(dobj,iobj,prep):
	if prep not in {"with","using",None}:
		print("Command not understood")
		return False
	if dobj in {"myself","me"}:
		if Core.yesno("Are you sure you want to kill yourself?"):
			Core.player.death()
			return True
		print("Fwew, that was close!")
		return False
	return Attack(dobj,iobj,prep)


def Lick(dobj,iobj,prep):
	print("licking")


def Light(dobj,iobj,prep):
	print("lighting")


def Listen(dobj,iobj,prep):
	print("listening")


def Lock(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False

	if dobj == None:
		dobj = getNoun("What will you lock?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Lock"):
		print(f"The {I.name} doesn't lock")
		return False

	if iobj == None:
		iobj = getNoun("What will you lock with?")
		if iobj in Data.cancels: return False
	K = findObjFromTerm(dobj,True,False)
	if K == None: return False

	if not isinstance(K,Items.Key):
		print(f"You can't lock with the {K.name}")
		return False
	return I.Lock(K)


def Look(dobj,iobj,prep):
	if prep not in {"at","in","inside","into","on","through",None}:
		print("Command not understood")
		return False
	if dobj == None: dobj = iobj
	if dobj == None:
		dobj = getNoun("What will you look at?")
		if dobj in Data.cancels: return False

	if dobj in {"around","here","room"} or dobj == Game.currentroom.name.lower():
		Core.game.currentroom.describe()
		return True
	if dobj in {"me","myself",Core.player.name}:
		print("You are " + Core.player.desc)
		return True

	L = findObjFromTerm(dobj,True,True)
	if L == None: return False
	Core.game.setPronouns(L)

	L.describe()
	if Core.hasMethod(L,"Look"):
		L.Look()
	return True


def Mount(dobj,iobj,prep):
	print("mounting")


def Move(dobj,iobj,prep):
	print("moveing")


def Open(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you open?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Open"):
		print(f"The {I.name} doesn't open")
		return False
	if hasattr(I,"locked") and I.locked:
		print(f"The {I.name} is locked")
		return False
	I.Open()
	return True


def Pet(dobj,iobj,prep):
	print("peting")


def Play(dobj,iobj,prep):
	print("playing")


def Point(dobj,iobj,prep):
	print("pointing")


def Pour(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you pour?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,False)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Pour"):
		print(f"You can't pour the {I.name}")
		return False

	R = None
	if iobj != None and iobj not in {"floor","ground","here"}:
		R = findObjFromTerm(iobj,True,True)
		if R == None: return False

	if prep == None: prep = "on"
	if R != None: print(f"You pour your {I.name} {prep} the {R.name}")
	else: print(f"You pour out your {I.name}")
	I.Pour(R)
	return True


def Pray(dobj,iobj,prep):
	print("praying")


def Press(dobj,iobj,prep):
	print("pressing")


def Pull(dobj,iobj,prep):
	print("pulling")


def Punch(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you punch?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"fist","with")


def Push(dobj,iobj,prep):
	print("pushing")


def Put(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon","down",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you put?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,False)
	if I == None: return False
	Core.game.setPronouns(I)

	if iobj == None:
		iobj = getNoun(f"What will you put your {dobj} in?")
		if iobj in Data.cancels: return False

	if iobj in {"floor","ground","here"}:
		return Drop(dobj,iobj,prep,I=I)
	R = findObjFromTerm(iobj,True,True)
	if R == None: return False

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	if not Core.hasMethod(I,"addItem"):
		print(f"You can't put the {I.name} {prep} the {R.name}")
		return False

	outprep = "on" if isinstance(R,Items.Table) else "in"
	if iobj == "here": print(f"You put your {I.name} here")
	else: print(f"You put your {I.name} {outprep} the {R.name}")
	I.parent.removeItem(I)
	R.addItem(I)
	return True


def Release(dobj,iobj,prep):
	print("releaseing")


# TODO:
# def Remove(dobj,iobj,prep):
# 	print("removeing")


def Rest(dobj,iobj,prep):
	print("resting")


def Restrain(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False

	if dobj == None:
		dobj = getNoun("What will you restrain?")
		if dobj in Data.cancels: return False

	C = findObjFromTerm(dobj,False,True)
	if C == None: return False
	Core.game.setPronouns(C)

	if not isinstance(C,Core.Creature):
		print(f"You can't restrain the {C.name}")
		return False

	I = None
	if iobj != None:
		I = findObjFromTerm(dobj,True,False)
		if I == None: return False
		if not Core.hasMethod(I,"RestrainWith"):
			print(f"You can't restrain with the {I.name}")
			return False

	if not C.Restrain(Core.player,I):
		print(f"You fail to restrain the {C.name}")
		return False
	print(f"You restrain the {C.name}")
	return True


def Ring(dobj,iobj,prep):
	print("ringing")


def Rub(dobj,iobj,prep):
	print("rubbing")


def Search(dobj,iobj,prep):
	print("searching")


def Shoot(dobj,iobj,prep):
	print("shooting")


def Shove(dobj,iobj,prep):
	print("shoveing")


def Smell(dobj,iobj,prep):
	print("smelling")


def Steal(dobj,iobj,prep,I=None):
	print(f"stealing {dobj} {prep} {iobj}")


def Struggle(dobj,iobj,prep):
	print("struggleing")


def Swim(dobj,iobj,prep):
	print("swiming")


def Talk(dobj,iobj,prep):
	print("talking")


def Throw(dobj,iobj,prep):
	print("throwing")


def Tie(dobj,iobj,prep):
	print("tieing")


def TakeAll():
	takenAnything = False
	# deep copy to prevent deleting-while-iterating error
	items = [item for item in Core.game.currentroom.items]
	for obj in items:
		count = obj.parent.itemNames().count(obj.name)
		msg = f"You take {obj.stringName(definite=(count==1))}"

		taken = Core.player.obtainItem(obj,msg)
		takenAnything = taken or takenAnything

	return takenAnything


def Take(dobj,iobj,prep):
	if prep not in {"from","in","inside","up",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you take?")
		if dobj in Data.cancels: return False

	if dobj in {"all","everything","it all"}: return TakeAll()

	matches = Core.game.currentroom.search(dobj,d=2,reqParent=iobj)
	if len(matches) == 0:
		if prep in {None,"up"}: print(f"There is no '{dobj}' here")
		else: print(f"There is no '{dobj}' in a '{iobj}' here")
		return False
	elif len(matches) == 1: obj = matches[0]
	else: obj = chooseObject(dobj,matches)
	if obj == None: return False
	Core.game.setPronouns(obj)

	if isinstance(obj,Core.Creature): return CarryCreature(obj)
	if not isinstance(obj,Core.Item) or isinstance(obj,Core.Fixture):
		print("You can't take the " + dobj)
		return False

	parent = obj.parent
	if parent is Core.player:
		print("You can't take from your own Inventory")
		return False
	if any(isinstance(anc,Core.Creature) for anc in obj.ancestors()):
		return Steal(dobj,iobj,prep,I=obj)
	count = parent.itemNames().count(obj.name)

	if parent is Core.game.currentroom: suffix = ""
	elif Core.player in obj.ancestors(): suffix = " from your " + parent.name
	else: suffix = " from the " + parent.name
	strname = obj.stringName(definite=(count==1))
	msg = f"You take {strname}{suffix}"

	return Core.player.obtainItem(obj,msg)


def Touch(dobj,iobj,prep):
	print("touching")


def Trip(dobj,iobj,prep):
	print("triping")


def Unequip(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to unequip?")
		if dobj in Data.cancels: return False

	I = Core.player.inGear(dobj)
	if I == None:
		print(f"You do not have a '{dobj}' equipped")
		return False
	Core.game.setPronouns(I)

	print(f"You unequip your {I.name}")
	Core.player.unequip(I)
	return True


def Unlock(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you unlock?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
	if I == None: return False
	Core.game.setPronouns(I)
	if not Core.hasMethod(I,"Unlock"):
		print(f"The {I.name} doesn't unlock")
		return False

	if iobj == None:
		iobj = getNoun("What will you unlock with?")
		if iobj in Data.cancels: return False

	K = findObjFromTerm(dobj,True,False)
	if K == None: return False

	if not isinstance(K,Items.Key):
		print(f"You can't unlock with the {K.name}")
		return False
	return I.Unlock(K)


def Untie(dobj,iobj,prep):
	print("untieing")


def Use(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you use?")
		if dobj in Data.cancels: return False

	I = findObjFromTerm(dobj,True,True)
	if I == None: return False
	Core.game.setPronouns(I)

	if not Core.hasMethod(I,"Use"):
		print(f"You can't use the {I.name}")
		return False
	I.Use()
	return True


def Wait(dobj,iobj,prep):
	print("waiting")


def Wave(dobj,iobj,prep):
	print("waveing")




##################################
## ACTION FUNCTION DICTIONARIES ##
##################################


cheatcodes = {
	"\\exe":Exe,
	"\\get":Get,
	"\\lrn":Learn,
	"\\mod":Mode,
	"\\pot":Pypot,
	"\\set":Set,
	"\\tst":Test,
	"\\tpt":Teleport,
	"\\wrp":Warp,
	"\\zap":Zap
}

# contains corresponding functions for all items in Data.shortverbs and Data.statcommands
shortactions = {
"abilities":Core.Player.printAbilities,
"back":Return,
"clear":Core.clearScreen,
"cry":Cry,
"dance":Dance,
"examples":Examples,
"gear":Core.Player.printGear,
"hi":Hello,
"hello":Hello,
"help":Help,
"hp":Core.Player.printHP,
"info": Info,
"information": Info,
"inventory":Core.Player.printInv,
"inv":Core.Player.printInv,
"laugh":Laugh,
"level":Core.Player.printLV,
"lv":Core.Player.printLV,
"money":Core.Player.printMoney,
"mp":Core.Player.printMP,
"quit":Quit,
"return":Return,
"rp":Core.Player.printRP,
"save":Save,
"scream":Shout,
"shout":Shout,
"sing":Sing,
"stats":Core.Player.printStats,
"status":Core.Player.printStatus,
"time":Time,
"traits":Core.Player.printTraits,
"weapons":Core.Player.printWeapons,
"xp":Core.Player.printXP,
"yell":Shout,
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
"pray":Pray,
"press":Press,
"pull":Pull,
"punch":Punch,
"push":Push,
"put":Put,
"put down":Drop,
"put on":Don,
"quaff":Drink,
"read":Look,
"release":Release,
"remove":Unequip,
"rest":Rest,
"restrain":Restrain,
"ride":Mount,
"ring":Ring,
"rub":Rub,
"run":Go,
"search":Search,
"set":Put,
"set down":Drop,
"shoot":Shoot,
"shove":Shove,
"shut":Close,
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
"wear":Don
}
