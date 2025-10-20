# Interpreter.py
# This file contains the code to parse user input and execute player actions
# This file is dependent on Menu.py and is a dependency of PoPy.py

# It consists of three main parts;
# 1. Interpreter functions	(functions to interpret user input)
# 2. Action functions	(action, shortaction, cheat functions called by interpret())
# 3. Action dicts		(dictionaries used to call action functions from)

from random import choice,randint
import traceback
import sys
import gc

import Data
import Core
import Menu
import Items
import Creatures
import Effects


helpCounter = 0
commandQueue = []

###########################
## INTERPRETER FUNCTIONS ##
###########################


# this is used to disambiguate user input...
# when the object name given is not specific enough
# takes the object name and list of matching objects
# prints the list of objects with entry 'tags' to help the user distinguish them
# will return when user cancels or when they select an object by name or number
def chooseObject(name,objects,verb=None):
	if objects is None or len(objects) == 0:
		return None
	objects = list(set(objects))
	if len(objects) == 1:
		return objects[0]
	Core.Print()
	for n,obj in enumerate(objects):
		labels = []
		if isinstance(obj,Core.Creature):
			if not obj.isAlive():
				labels.append("dead")
			else:
				labels.append(f"{obj.hp} hp")
		if hasattr(obj,"parent"):
			if not isinstance(obj.parent,(type(None),Core.Room,Core.Player)):
				labels.append(obj.parent.name)
		if obj is Core.player:
			labels.append("you")
		elif isinstance(obj,Core.Room):
			labels.append("here")
		elif obj in (obj.parent.ceiling,obj.parent.walls,obj.parent.floor):
			labels.append(obj.parent.name.lower())
		elif obj is Core.player.carrying:
			labels.append("carrying")
		elif obj is Core.player.riding:
			labels.append("riding")
		elif obj in Core.player.gear.values():
			labels.append("equipped")
		elif obj in Core.player.objTree():
			labels.append("Inventory")
		elif getattr(obj,"determiner",None):
			labels.append(obj.determiner)

		strLabel = ""
		if len(labels) >= 1:
			for label in labels[:-1]:
				strLabel += label + ","
			strLabel = " (" + strLabel + labels[-1] + ")"

		Core.Print(f"{n+1}. {obj}{strLabel}",color="k")

	def acceptKey(inp):
		try:
			return objects[int(inp)-1]
		except:
			for obj in objects:
				if inp == obj.nounPhrase().lower():
					return obj

	prompt = f"\nWhich {name}{f' to {verb}' if verb else ''}?"
	choice = Core.InputLoop(prompt,acceptKey=acceptKey,refuseMsg="That is not one of the options.",color="k")
	return choice


# return an object in player inv or room based on player input
# gets a list of potential objects whose name matches the given user input term
# queryPlayer and queryRoom indicate which places to look for matching objects
# roomD and playerD are the 'degree' of the query.
# Look at Core.py objQuery for details on query degree
def findObject(term,verb=None,queryType="both",filter=None,roomD=1,playerD=2,reqParent=None,silent=False):
	if term is None and not silent and verb is not None:
		term = getNoun(f"What will you {verb}?")
	if term in Data.cancels or term is None or term == "nothing":
		return None

	# allows for users to describe objects they possess
	my = False
	if term.startswith("my "):
		term = term[3:]
		my = True

	matches = set()
	if queryType == "player" or queryType == "both":
		matches |= Core.player.nameQuery(term,d=playerD)
	if queryType == "room" or queryType == "both":
		matches |= Core.player.surroundings().nameQuery(term,d=roomD)

	if queryType == "player" and Core.nameMatch(term,Core.player.carrying):
		matches.add(Core.player.carrying)
	if term in ("me","myself","player","self"):
		matches.add(Core.player)
	if term in ("room",Core.game.currentroom.name):
		matches.add(Core.game.currentroom)
	if term in ("here","there"):
		matches.add(Core.player.parent)

	if filter:
		matches = {match for match in matches if filter(match)}
	if reqParent:
		matches = {match for match in matches if Core.nameMatch(reqParent, match.parent)}
	if my:
		matches = {match for match in matches if Core.player in match.ancestors() or match.determiner == "your"}

	if len(matches) > 1:
		return chooseObject(term,matches,verb)
	elif len(matches) == 1:
		return matches.pop()

	suffix = ""
	if not silent:
		if reqParent:
			det = "an" if reqParent[0] in Data.vowels else 'a'
			suffix += f" in {det} '{reqParent}'"
		if queryType == "player" or my:
			suffix += " in your Inventory"
		elif queryType == "room":
			suffix += " in your surroundings"
		if queryType in ("room","both") and roomD <= 1:
			suffix += " that you can see"
		Core.Print(f"There is no '{term}'{suffix}.",color="k")
	return None


def enforceVerbScope(verb,obj,permitAnchor=True,permitParent=False,permitSelf=False,permitDistance=False):
	parent = Core.player.parent
	if obj not in parent.objTree(includeSelf=True):
		Core.Print(f"You can't {verb} {-obj}, you're {parent.passprep} {-parent}.")
		return True
	if not permitAnchor and obj is Core.player.anchor():
		if obj in Core.player.parent.surfaces:
			Core.Print(f"You can't {verb} {-obj}.")
			return True
		Core.Print(f"You're {Core.player.position()}, you can't {verb} {obj.pronoun}.")
		return True
		# if obj is Core.player.rider: # TODO, what if a bird is 'riding' on your shoulder?
		# 	Core.Print(f"You can't {verb} {-obj}, {obj.pronoun} is on you.")
		# 	return True
	# sometimes parent is also anchor. In this case, permitAnchor takes precedence.
	if not permitParent and obj is parent:
		Core.Print(f"You can't {verb} {-obj}, you're {parent.passprep} {parent.pronoun}.")
		return True
	if not permitSelf and obj is Core.player:
		Core.Print(f"You can't {verb} yourself.")
		return True
	if not permitDistance:
		anchor = Core.player.anchor()
		if anchor in Core.player.parent.surfaces + (None,):
			anchor = Core.player.parent
		rec = f" Try jumping to {obj.pronoun}." if verb == "get on" else ""
		if obj not in anchor.objTree(includeSelf=True):
			Core.Print(f"You can't {verb} {-obj}, you're {Core.player.position()}.{rec}")
			return True

	if isinstance(obj,Core.Fixture) and Core.nameMatch("ceiling",obj):
		if Core.player.Size() < Core.player.parent.Size() // 2 and not Core.player.hasStatus("flying"):
			Core.Print(f"You can't {verb} {-obj}, it is too high.")
			return True


# checks if a noun refers to a room, an object in the world or on the player...
# or an action verb, an in-game definition or a miscellaneous expression
def isMeaningful(noun):
	if noun in Core.world or \
	noun in actions or \
	noun in statcommands or \
	noun in Data.glossary or \
	noun in Data.miscexpressions or \
	noun in Data.hellos or \
	noun in Data.goodbyes or \
	noun in Data.prepositions or \
	noun in Core.game.currentroom.links.keys() or \
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


# takes and validates user input
def read(prompt,storeRawCmd=False):
	Core.flushInput()
	rawcommand = Core.InputLock(prompt,low=False)
	# for convenience, save raw command in game object
	if storeRawCmd:
		Core.game.lastRawCommand = rawcommand.split()
	return rawcommand


# processes it into a command form usable by interpret(),
# returns a list of words without capitals, symbols, or articles
# nounify() joins words that may only be meaningful as one term
def tokenize(command):
	# allow for sequential commands separated by 'and'
	seqcommand = command.split(" and ")
	command = seqcommand[0]
	commandQueue.extend(seqcommand[1:])
	# lowercase-ify the sentence command, copy it excluding symbols
	purecommand = "".join([i for i in command if i not in Data.symbols]).lower()
	# split command into list of words, but combine words that seem to be single terms
	splitcommand = nounify(purecommand.split())	
	# split compound words that ought to be two separate words for parsing
	splitcommand = decompose(splitcommand)
	# remove articles and determiners (and other extraneous words)
	finalcommand = [word for word in splitcommand if word not in Data.articles]
	return finalcommand


def getNoun(prompt):
	return " ".join(tokenize(read(prompt)))


def parse(cmdInput):
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


# called in interpret() when a command fails, it simply recurs interpret(), and...
# prints a helpful message if user has provided invalid input 3 or more times
# n is the number of times interpret() has recurred
def promptHelp(msg):
	global helpCounter
	commandQueue.clear()
	if msg != "":
		Core.Print(msg,color="k")
	helpCounter += 1
	if helpCounter >= 3:
		Core.Print("Enter 'help' for instructions.",color="k")
	return False


def dispatchShortCommand(command,verb):
	# 'cast' may be a stat command or a regular action
	if verb != "cast" or len(command) == 1:
		if len(command) != 1:
			return promptHelp(f"The '{verb}' command can only be one word.")
		if verb == "here":
			return Core.player.parent.describe()
		if verb == "room":
			return Core.game.currentroom.describe()
		if verb in ("clear","cls"):
			return Core.clearScreen()
		if verb in Data.hellos:
			return Hello()
		if verb in Data.goodbyes:
			return Goodbye()
		if verb in Data.abilities:
			return Core.player.printAbility(verb.upper())
		if verb in Data.traits:
			return Core.player.printTraits(verb)
		if verb in Data.colors:
			return Core.Print(verb.title()+".", color=Data.colors[verb])
		return statcommands[verb](Core.player)


# the primary endpoint of the interpreter module
# its purpose is to parse and execute user input
# it is called on infinite loop until it returns True
# it returns True only when the player performs some action
def interpret():
	if not Core.player.isAlive():
		return True
	global helpCounter
	if commandQueue:
		queuedInput = commandQueue.pop(0)
		Core.waitInput("\n& " + "".join(queuedInput))
		command = tokenize(queuedInput)
	else:
		command = tokenize(read("\n\nWhat will you do?",storeRawCmd=True))
	if len(command) == 0:
		return promptHelp("Command not understood.")
	verb = command[0]	# verb is always first word

	# handle cases with special verb commands
	if verb in cheatcodes.keys():
		commandQueue.clear()
		Core.Print(verb,color='k')
		return cheatcodes[verb](Core.game.lastRawCommand)
	elif verb in shortcommands:
		return dispatchShortCommand(command,verb)
	elif verb not in actions:
		return promptHelp(f"'{verb}' is not a valid verb.")

	dobj,iobj,prep = parse(command[1:])
	# this line calls the action function using the 'actions' dict
	actionCompleted = actions[verb](dobj,iobj,prep)
	helpCounter = 0
	# if action didn't succeed, return False
	if not actionCompleted:
		commandQueue.clear()
		return False
	return True




##########################################
## CHEATCODES AND DEV COMMAND FUNCTIONS ##
##########################################

def Diagnostic(command):
	gc.collect()
	sizes = [sys.getsizeof(obj) for obj in Core.game.objRegistry.values()]
	sizes.extend([sys.getsizeof(obj) for obj in Core.world.values()])
	sizes.append(sys.getsizeof(Core.player))
	sizes.append(sys.getsizeof(Core.world))
	sizes.append(sys.getsizeof(Core.game))
	pythonsizes = [sys.getsizeof(obj) for obj in gc.get_objects()]

	objInfo = lambda objects: [(sys.getsizeof(obj),type(obj),repr(obj)[:50]) for obj in objects]

	gameObjects = list(Core.game.objRegistry.values()) + list(Core.world.values()) + [Core.player,Core.world,Core.game]
	gameObjInfo = objInfo(gameObjects)
	gameObjSizes = [info[0] for info in gameObjInfo]
	print(f"Number of objects in registry: {len(Core.game.objRegistry)}")
	print(f"Number of rooms in world: {len(Core.world)}")
	print(f"Game object sizes (min, avg, max): {min(gameObjSizes)}b, {sum(gameObjSizes)//len(gameObjSizes)}b, {max(gameObjSizes)}b")
	print(f"Largest game object: {max(gameObjInfo,key=lambda x:x[0])}")
	print(f"Memory used by game objects: {sum(gameObjSizes)}b")

	pyObjInfo = objInfo(gc.get_objects())
	pyObjSizes = [info[0] for info in pyObjInfo]
	print(f"Total number of python objects: {len(pyObjSizes)}")
	print(f"All python object sizes (min, avg, max): {min(pyObjSizes)}b, {sum(pyObjSizes)//len(pyObjSizes)}b, {max(pyObjSizes)}b")
	print(f"Largest python object: {max(pyObjInfo,key=lambda x:x[0])}")
	print(f"Approximate total memory usage: {sum(pyObjSizes)}b")


def Evaluate(command):
	if len(command) < 2:
		Core.Print("Error: No code given",color="k")
		return
	code = " ".join(command[1:])
	try:
		fo = findObject # for convenience when executing quick code
		Core.Print(eval(code))
	except Exception as e:
		Core.Print("Error: Code was unable to be executed.",color="k")
		Core.Print(traceback.format_exc(),color="k",delay=0)


def Execute(command):
	if len(command) < 2:
		Core.Print("Error: No code given",color="k")
		return
	code = " ".join(command[1:])
	try:
		fo = findObject # for convenience when executing quick code
		exec(code)
	except Exception as e:
		Core.Print("Error: Code was unable to be executed.",color="k")
		Core.Print(traceback.format_exc(),color="k",delay=0)


def Expell(command):
	if len(command) < 2:
		Core.Print("Error: no condition given",color="k")
		return
	condname = " ".join(command[1:])
	Core.player.removeStatus(condname)


def Fortify(command):
	obj = Core.player
	if len(command) > 1:
		objname = " ".join(command[1:])
		obj = findObject(objname,"fortify",playerD=3,roomD=3)
	if obj is None:
		Core.Print("Error: Object not found",color="k")
		return
	Core.Print(f"Fortifying {-obj}.",color="k")
	if Core.hasMethod(obj,"heal"):
		obj.heal(1000)
	if Core.hasMethod(obj,"resurge"):
		obj.resurge(1000)


def Get(command):
	if len(command) < 2:
		Core.Print("Error: No object name given",color="k")
		return

	objname = command[1].lower()
	if len(command) == 3:
		attrname = command[2]

	if objname in ("g","game"): obj = Core.game
	elif objname in ("w","world"): obj = Core.world
	elif objname in Core.world: obj = Core.world[objname]
	else: obj = findObject(objname,"get",playerD=3,roomD=3)
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


def Grow(command):
	val = 3
	obj = Core.player
	if len(command) == 2:
		objname = " ".join(command[1:])
		obj = findObject(objname,"grow",playerD=3,roomD=3)
	elif len(command) > 2:
		objname = " ".join(command[1:-1])
		obj = findObject(objname,"grow",playerD=3,roomD=3)
		val = int(command[-1])
	if obj is None:
		Core.Print("Error: Object not found",color="k")
		return
	if obj.weight * val > obj.parent.Size():
		Core.Print(f"{-obj} can't get any bigger.",color="k")
		return
	Core.Print(f"Growing {-obj}.",color="k")
	obj.weight = Core.min1(obj.weight * val)


def Honor(command):
	obj = Core.player
	if len(command) > 1:
		objname = " ".join(command[1:])
		obj = findObject(objname,"honor",playerD=3,roomD=3)
	if obj is None:
		Core.Print("Error: Object not found",color="k")
		return
	if Core.hasMethod(obj,"updateLove"):
		obj.updateLove(100)
	if Core.hasMethod(obj,"updateFear"):
		obj.updateFear(100)
	if Core.hasMethod(obj,"updateReputation"):
		obj.updateReputation(100)


def Imbue(command):
	objname = "self"
	duration = -2
	if len(command) < 2:
		Core.Print("Error: No status condition given",color="k")
		return
	if len(command) == 2:
		condname = command[1]
	elif len(command) == 3:
		condname = command[2]
		objname = command[1]
	else:
		condname = command[-2]
		duration = command[-1]	
		objname = " ".join(command[1:-2])

	obj = findObject(objname,"imbue",playerD=3,roomD=3)
	if obj is None:
		Core.Print("Error: Object not found",color="k")
		return

	try:
		duration = int(duration)
	except:
		Core.Print("Error: Duration not number",color="k")
		return

	obj.addStatus(condname,duration)


def Learn(command):
	if len(command) < 2:
		Core.Print("Error: No xp value given",color="k")
		return
	# try:
	Core.player.gainxp(int(command[1]))
	# except:
	# 	Core.Print(f"Error: Value not number {command[1]}",color="k")


def Lob(command):
	if len(command) < 2:
		Core.Print("Error: no object name given",color="k")
		return
	if len(command) < 3:
		Core.Print("Error: no target given",color="k")
		return

	prep = "at"
	objname = command[1].lower()
	# dir, dest, or passage
	path = " ".join(command[2:]).lower()
	missile = findObject(objname,"get",playerD=3,roomD=3)
	if missile is None:
		Core.Print("Error: Object not found",color="k")
		return

	if path in Data.directions:
		path = Data.directions[path]
	for dir, room in Core.game.currentroom.links.items():
		if path in (dir, room.name.lower()):
			target = room
			prep = "to"
			break
	else:
		target = findObject(path,"launch at",playerD=3,roomD=3)
	if target is None:
		Core.Print("Error: target not found",color="k")
		return False

	if getattr(missile,"carrier",None):
		missile.carrier.removeCarry(missile)
	if getattr(missile,"rider",None):
		missile.rider.removeRiding(missile)
	if getattr(missile,"platform",None):
		missile.platform.Disoccupy(missile)
	missile = missile.asProjectile()
	Core.Print(f"{+missile} is launched {prep} {-target}.",color="k")
	missile.Launch(50,100,None,target)


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
		money = Core.min0(money)
		Core.player.updateMoney(money)
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
	except:
		pass
	if value in ("true","True"): value = True
	if value in ("false","False"): value = False

	if objname in ("g","game"): obj = Core.game
	elif objname in ("w","world"): obj = Core.world
	else: obj = findObject(command[1],"set",playerD=3,roomD=3)

	if obj is None: return False
	try:
		getattr(obj,attrname)
	except:
		Core.Print(f"{obj} has no attribute {attrname}",color="k")
		return False
	if type(getattr(obj,attrname)) is int and type(value) is not int:
		Core.Print(f"Can't step {attrname} to {value}. Attribute {attrname} is an integer",color="k")
		return False
	Core.Print(f"Setting {obj}.{attrname} to {value}",color="k")
	setattr(obj,attrname,value)
	if isinstance(obj,Core.Creature):
		obj.checkStatus()


def Shrink(command):
	val = 3
	obj = Core.player
	if len(command) == 2:
		objname = " ".join(command[1:])
		obj = findObject(objname,"shrink",playerD=3,roomD=3)
	elif len(command) > 2:
		objname = " ".join(command[1:-1])
		obj = findObject(objname,"shrink",playerD=3,roomD=3)
		try:
			val = int(command[-1])
		except:
			Core.Print("Value not number",color="k")
			return
	if obj is None:
		Core.Print("Error: Object not found",color="k")
		return
	if obj.weight <= 1:
		Core.Print(f"{-obj} can't get any smaller.",color="k")
		return
	Core.Print(f"Shrinking {-obj}.",color="k")
	obj.weight = Core.min1(obj.weight // val)


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
	location = " ".join(command[1:]).lower()
	if location in Core.world:
		Core.player.Teleport(Core.world[location])
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
	if objname == "all":
		key = lambda x: not (isinstance(x,(Core.Player,Core.Fixture)) or Core.player in x.ancestors())
		matches = Core.player.surroundings().query(key=key,d=3)
	elif objname in ("me","myself","player","self"):
		matches = [Core.player]
	else:
		key = lambda obj: Core.nameMatch(objname, obj)
		matches = Core.game.queryRooms(key=key)
	# Core.Print(f"Zapped objects: {len(matches)}",color="k")
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
	Core.player.removeStatus("hidden",-3)
	Core.Print("You bust down a boogie.",color="m")


def Examples(*args):
	Core.clearScreen()
	Core.Print(Data.examples,color="k",delay=0.0001)
	Core.waitInput()
	Core.clearScreen()


def Exits(*args):
	for key, val in Core.player.parent.allLinks().items():
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
	shortcommands = sorted(tuple(key for key in statcommands.keys() if key not in Data.emoticons) + Data.traits + Data.abilities)
	Core.columnPrint(shortcommands,12,10,color="k")
	Core.Print("\nVerb Commands (Does not include cheat codes and secret commands)",color="k")
	Core.columnPrint(actions.keys(),12,10,color="k")
	Core.Print("\nDuring the game, type 'info' for information on the game and how to play.",color="k")
	Core.waitInput()
	Core.clearScreen()


def Laugh(*args):
	Core.Print('"HAHAHAHAHA!"',color="y")
	Core.player.removeStatus("hidden",-3)


def Quit(*args):
	if Core.yesno("Are you sure you want to quit? (Anything unsaved will be lost)",color="k",delay=0):
		Core.game.quit = True
		return True


def Shout(*args): 
	Core.Print('"AHHHHHHHHHH"',color="y")
	Core.player.removeStatus("hidden",-3)


def Sing(*args):
	Core.Print('"Falalalaaaa"',color="y")
	Core.player.removeStatus("hidden",-3)


def Smile(*args):
	Core.Print("You smile.")


def Time(*args):
	Core.Print("Time:",Core.game.time,color="k")


def Wink(*args):
	Core.Print("You wink!",color="m")


def Yawn(*args):
	return Sleep(None,None,None) if Core.yesno("Do you want to sleep?") else None




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
	if iobj is not None and iobj.startswith("my "):
		iobj = iobj[3:]

	# assigning weapons based on input and what is in player's hand
	if weapon is None and weapon2 is not None:
		weapon, weapon2 = weapon2, None
	if iobj in ("fist","hand"):
		Core.player.unequip("right")
		weapon = Items.Hand("hand","",4,-1,None)
	if iobj in ("foot","leg"):
		weapon = Items.Foot("foot","",6,-1,None)
	if iobj in ("mouth","teeth"):
		weapon = Items.Mouth("mouth","",4,-1,None)
	if iobj is not None:
		if weapon is None:
			_, weapon = Core.player.inGear(iobj)
		if weapon is None:
			weapons = Core.player.inInv(iobj)
			if len(weapons) == 0: Core.Print(f"There is no '{iobj}' in your Inventory.",color="k")
			elif len(weapons) == 1: weapon = weapons[0]
			else: weapon = chooseObject(iobj,weapons)
			if weapon is None: return False
	else:
		if Core.player.gear["right"] != Core.EmptyGear():
			weapon = Core.player.gear["right"]
		elif Core.player.gear["left"] != Core.EmptyGear():
			weapon = Core.player.gear["right"]

	if target is None:
		target = findObject(dobj,"attack","room")
		if target is None: return False
	# TODO: if weapon is ranged, then redirect to Shoot here
	Core.game.setPronouns(target)
	if enforceVerbScope("attack",target,permitParent=True,permitSelf=True): return False
	Core.player.removeStatus("hidden",-3)

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
	I = findObject(dobj,"bite")
	if I is None: return False
	if enforceVerbScope("bite",I): return False
	Core.game.setPronouns(I)
	if Core.hasMethod(I,"Eat"):
		I.Eat()
		return True
	else:
		return Attack(dobj,"mouth",prep,target=I)

	# make sure to add tasting it as well here
	# TODO: if u add the ability to "bite" items, maybe actually damage them...
	# if their durability is low enough or smth. Maybe append the item's...
	# description to include "it has a bite taken out of it"
	# perhaps if player swallows something inedible, take damage?


def Break(dobj,iobj,prep):
	# TODO: potentially just redirect this func to attack, idk
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")
	# TODO: maybe figure out times when you will just break, not attack?
	# for instance though, a window should be attacked
	I = findObject(dobj,"break")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("break",I): return False

	if not Core.hasMethod(I,"Break"):
		Core.Print(f"You can't break {-I}.")
		return False
	Core.Print(f"You try to break {-I}.")
	return Core.player.attackItem(I)


def Caress(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")
	# TODO: include iobj validation

	I = findObject(dobj,"caress")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("caress",I,allowSelf=True,allowParent=True): return False

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
	if enforceVerbScope("carry",creature): return False
	carrying = Core.player.carrying

	if carrying:
		Core.Print(f"You're already carrying {-carrying}.")
		if carrying is creature:
			return False
	if not isinstance(creature,Core.Creature):
		Core.Print(f"You can't carry {-creature}")
		return False

	Core.player.unequip("left")
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
		target = findObject(iobj,f"cast {prep}","room")
		if target is None:
			return False

	return Effects.spells[dobj](target)


def Catch(dobj,iobj,prep):
	Core.Print("catching")


def Climb(dobj,iobj,prep):
	if prep not in ("down","in","into","inside","on","onto","out","out of","under","up","upon",None):
		return promptHelp("Command not understood.")
	verbprep = "on" if prep is None else prep

	if dobj is None: dobj = iobj
	surfacesHere = (Core.player.parent,) + Core.player.parent.surfaces
	if any(Core.nameMatch(dobj,o) for o in surfacesHere):
		dobj = getNoun(f"What will you climb {verbprep} here?")
	M = findObject(dobj,f"climb {verbprep}","room")
	if M is None: return False
	Core.game.setPronouns(M)
	if enforceVerbScope(f"climb {verbprep}",M,permitParent=True): return False

	# prevents absurdity of climbing onto a small item
	if M.Size() < Core.player.Size() // 5:
		Core.Print(f"{+M} is too small to climb {prep}.")
		return False
	# TODO: handle 'climb out of here' in a normal room

	elif isinstance(M,Core.Portal):
		return M.Traverse(Core.player,dir=prep,verb="climb")
	elif prep in ("down","out","out of"):
		return Dismount(dobj,iobj,prep)
	else:
		return Mount(dobj,iobj,prep,M=M)


def Close(dobj,iobj,prep):
	if prep is not None:
		return promptHelp("Command not understood.")

	I = findObject(dobj,"close")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("close",I,permitParent=True): return False

	if not hasattr(I,"open"):
		Core.Print(f"{+I} doesn't close.")
		return False
	if not I.open:
		Core.Print(f"{+I} is already closed.")
		return False
	if Core.hasMethod(I,"Close"):
		I.Close(Core.player)
	else:
		I.open = False
		Core.Print(f"You close {-I}.")
	return True


def Craft(dobj,iobj,prep):
	Core.Print("crafting")


def Cross(dobj,iobj,prep):
	Core.Print("crossing")


def Crouch(dobj,iobj,prep):
	if prep not in ("at","behind","below","beneath","by","in","inside","into","near","on","onto","under","upon",None):
		return promptHelp("Command not understood.")
	if dobj is None:
		dobj = iobj

	if (dobj,prep) == (None,None):
		if Core.player.posture() == "crouching":
			Core.Print("You are already crouching.")
			return False

	if prep is not None and dobj is None:
		dobj = getNoun(f"What will you crouch {prep}?")
		if dobj in Data.cancels: return False
	elif prep is None and dobj is not None:
		prep = "on"

	if prep in ("at","by","near"):
		Core.Print("You are there.")
	elif prep in ("below","beneath","behind","under"):
		return Hide(dobj,iobj,prep,posture="crouch")
	elif prep in ("on","onto","upon","in","inside","into"):
		M = findObject(dobj,f"crouch {prep}","room")
		if M is None: return False
		Core.game.setPronouns(M)
		return Mount(dobj,iobj,prep,M=M,posture="crouch")
	else:
		Core.player.changePosture("crouch")
		return True


def Cut(dobj,iobj,prep):
	Core.Print("cuting")


def Define(dobj,iobj,prep):
	if iobj is not None or prep is not None:
		return promptHelp("Can only define one word at once.")
	if dobj is None:
		dobj = getNoun("What term would you like defined?")
		if dobj in Data.cancels: return False

	if dobj in Data.glossary:
		Core.Print("\n"+Data.glossary[dobj])
		return True
	elif Core.game.inWorld(dobj):
		return Look(dobj,iobj,prep)
	elif dobj == Core.player.name.lower():
		Core.Print(f"\n{Core.player.name}\nThat is you!")
		return True
	Core.Print(f"'{dobj}' is not in the glossary",color="k")
	return False


def Describe(dobj,iobj,prep):
	if iobj is not None or prep is not None:
		return promptHelp("Can only describe one thing at once.")

	D = findObject(dobj,"have described")
	if D is None: return False
	Core.game.setPronouns(D)

	D.describe()
	return True


def Dismount(dobj,iobj,prep,posture=None):
	if prep not in ("d","down","from","of","off","out","out of",None):
		return promptHelp("Command not understood.")

	if Core.player.anchor() in (None,Core.player.parent.floor):
		if Core.player.posture() != "standing":
			return Stand(None,None,None)
		return promptHelp(f"You're not on anything.")

	if iobj is not None:
		dobj = iobj
	if dobj is not None:
		if dobj.startswith("my "):
			dobj = dobj[3:]
		matches = Core.player.surroundings().nameQuery(dobj)
		if Core.player.anchor() not in matches:
			Core.Print(f"You're not on a '{dobj}'",color="k")
			return False

	Core.player.Dismount(posture=posture)
	Core.game.setPronouns(Core.player.riding)
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

	slot, I = Core.player.inGear(dobj)
	if I is None or not isinstance(I,Core.Armor):
		Core.Print(f"You aren't wearing a '{dobj}'.")
		return False
	Core.game.setPronouns(I)

	Core.Print(f"You doff your {I.name}.")
	Core.player.unequip(slot)
	return True


def Don(dobj,iobj,prep):
	if prep not in ("on","onto","over","to",None):
		return promptHelp("Command not understood.")

	if prep is None:
		prep = "on"
	I = findObject(dobj,"don","player")
	if I is None: return False
	Core.game.setPronouns(I)

	displayName = f"{-I}" if Core.player.carrying is I else f"your {I}"
	if not isinstance(I,Core.Armor):
		Core.Print(f"You cannot wear {displayName}.")
		return False
	if I in Core.player.gear.values():
		Core.Print(f"You are already wearing {displayName}.")
		return False
	if iobj and iobj not in Core.player.gear: 
		Core.Print(f"You aren't able to equip to '{iobj}'.")
		return False
	if iobj not in I.slots and iobj is not None:
		Core.Print(f"You cannot wear {-I} {prep} your {iobj}.")
		return False
	if not Core.player.equipArmor(I,iobj):
		return False
	Core.Print(f"You don {displayName}.")
	return True


def Drink(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	I = findObject(dobj,"drink")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("drink",I,permitAnchor=False): return False

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

	if I is None: I = findObject(dobj,"drop","player")
	if I is None: return False
	Core.game.setPronouns(I)

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	if iobj is not None:
		R = findObject(iobj,f"drop {prep}","room")
		if R is None: return False
		if enforceVerbScope(f"drop {prep}",R,permitParent=True): return False
		if isinstance(R,Core.Portal) and "down" in R.links:
			if getattr(R,"open",True):
				if isinstance(I,Core.Creature):
					Core.player.removeCarry(I)
				else:
					Core.player.remove(I)
					Core.player.parent.add(I)
				Core.Print(f"You drop {-I} {prep} {-R}.")
				return R.Transfer(I)
			else:
				Core.Print(f"{+R} is closed.")
				return False
		elif not Core.hasMethod(R,"add"):
			Core.Print(f"You can't drop {-I} {prep} {-R}.")
			return False

	if isinstance(I,Core.Creature):
		Core.player.removeCarry()
	elif not Core.player.parent.canAdd(I) and I not in Core.player.parent.contents():
		Core.Print(f"You can't drop {-I}. There's not enough room.")
		return False
	else:
		I.parent.remove(I)
		Core.Print(f"You drop {-I}.")
		Core.player.parent.add(I)
	return True


def Dump(dobj,iobj,prep):
	if prep not in ("in","into","inside","on","onto","out","upon",None):
		return promptHelp("Command not understood.")

	I = findObject(dobj,"dump","player")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("dump",I): return False

	if Core.hasMethod(I,"Pour"):
		return Pour(dobj,iobj,prep,I=I)
	else:
		return Drop(dobj,iobj,prep,I=I)


def Eat(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	I = findObject(dobj,"eat")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("eat",I,permitAnchor=False): return False

	if not isinstance(I,Items.Food):
		Core.Print(f"You can't eat {-I}.")
		return False

	I.Eat(Core.player)
	return True


def Enter(dobj,iobj,prep):
	return Go(dobj,iobj,"in")


def Equip(dobj,iobj,prep):
	if prep is not None:
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What would you like to equip?")
		if dobj in Data.cancels:
			return False
	if dobj.startswith("my "):
		dobj = dobj[3:]

	# uses inInv instead of findObject because we only want top level of inv tree
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
	if isinstance(Core.player.carrier, Items.Bed):
		if Core.nameMatch(dobj, Core.player.carrier):
			return Dismount(dobj,iobj,prep)
	if dobj is None and "out" in Core.player.parent.allDirs():
		return Go("out",iobj,prep)
	return Go(None,iobj,"out")


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
	I = findObject(dobj,"give","player")
	if I is None:
		return False
	if enforceVerbScope("give",I,permitAnchor=False): return False

	if iobj is None:
		iobj = getNoun("Who will you give to?")
		if iobj in Data.cancels:
			return False
	C = findObject(iobj,"room")
	if C is None:
		return False
	if enforceVerbScope("give to",C,permitAnchor=False): return False

	Core.game.setPronouns(C)
	if Core.hasMethod(C,"Give"):
		return C.Give(I)
	else:
		Core.Print(f"You can't give to {-C}")
		return False


# called when the user wants to go "up" or "down"
def GoVertical(dir,passage=None,dobj=None):
	assert (dir,passage) in Core.game.currentroom.allLinks()
	newroom = None
	if Core.player.hasStatus("flying") and not Core.player.riding:
		newroom = Core.game.currentroom.allLinks()[dir,passage]
		Core.waitInput(f"You fly {dir}!")
	if Core.player.riding and Core.player.riding.hasStatus("flying"):
		newroom = Core.game.currentroom.allLinks()[dir,passage]
		Core.waitInput(f"{+Core.player.riding} flies {dir}!")
	if newroom is not None:
		if passage is not None:
			return Core.player.changeLocation(passage.getNewLocation())
		return Core.player.changeLocation(newroom)

	hasUpPassage = any(d == "up" for (d,p) in Core.game.currentroom.allLinks() if p is not None)
	if passage is None and dir == "up" and dir in Core.game.currentroom.links:
		if Core.player.riding is None and not Core.player.hasStatus("flying"):
			goer = Core.player
		if Core.player.riding and not Core.player.riding.hasStatus("flying"):
			goer = Core.player.riding
		if hasUpPassage:
			dobj = getNoun("What will you go up?")
			passage = findObject(dobj,"go up","room")
			if passage is None:
				return False
		else:
			Core.Print(f"{+goer} can't go up,", (goer+"isn't flying.").lower())
			return False

	if passage is None and dir in Core.game.currentroom.links:
		return Core.player.changeLocation(Core.game.currentroom.links[dir])
	elif passage is None and dobj is not None:
		Core.Print(f"There is no '{dobj}' to go {dir} here.",color="k")
		return False
	elif passage is None:
		passage = findObject("",f"go {dir}","room")
		if passage is None:
			return False
	if Core.hasMethod(passage,"Traverse"):
		Core.game.setPronouns(passage)
		return passage.Traverse(Core.player,dir)
	else:
		Core.Print(f"{+passage} can't be traversed.")
		return False


# infers direction, destination, and passage (if they exist) from input terms
def parseGo(dobj,iobj,prep):
	dir,dest,passage = None,None,None
	parentLinks = Core.player.parent.allLinks(d=0)
	cancelledAction = False
	# print(dobj,iobj,prep)

	matchTerm = lambda t1, t2: t1 == t2
	matchObj = lambda t, obj: Core.nameMatch(t, obj)
	# look for any combination of input terms which matches a room's link
	# None is treated as a wildcard
	for (thisDir,thisPassage), thisDest in parentLinks.items():
		# print("=",thisDir,thisPassage,thisDest)
		for term in (dobj,iobj,prep):
			if term is None:
				continue
			if dir is None and matchTerm(term,thisDir):
				dir = thisDir
			elif passage is None and matchObj(term,thisPassage):
				passage = thisPassage
			elif dest is None and matchObj(term,thisDest):
				dest = thisDest

	# if a term is assigned by any of the following, it will fail during Go()
	# but its useful to have for printing fail outputs to user

	# assign dir if unassigned
	if dir is None and dobj in Data.directions.values(): dir = dobj
	elif dir is None and iobj in Data.directions.values(): dir = iobj
	elif dir is None: dir = prep

	# assign dest if unassigned
	if dest is None and Core.nameMatch(dobj,Core.player.parent): dest = Core.player.parent
	elif dest is None and Core.nameMatch(iobj,Core.player.parent): dest = Core.player.parent

	# assign passage if unassigned
	passages = []
	if not (dobj is None or matchTerm(dobj,dir) or matchObj(dobj,dest)) and passage is None:
		passages = Core.player.surroundings().nameQuery(dobj,d=1)
	elif not (iobj is None or matchTerm(iobj,dir) or matchObj(iobj,dest)) and passage is None:
		passages = Core.player.surroundings().nameQuery(iobj,d=1)
	if len(passages) == 1:
		passage = passages.pop()
	elif len(passages) > 1:
		passage = chooseObject("way",passages,"go")
		if passage is None:
			cancelledAction = True

	return dir,dest,passage,cancelledAction


# parses user input to determine the intended direction, destination, and/or
# passage. Then calls either traverse or changelocation accordingly
def Go(dobj,iobj,prep):
	if Core.player.platform != Core.player.parent.floor or Core.player.carrier:
		Core.Print(f"You can't go anywhere, you are {Core.player.position()}.")
		return False
	for cond in Data.immobileStatus:
		if Core.player.hasStatus(cond) and Core.player.riding is None:
			Core.Print(f"You can't go anywhere, you are {cond}.")
			return False
		if Core.player.riding is not None and Core.player.riding.hasStatus(cond):
			spurRec = f" Try to spur {Core.player.riding.pronoun}." if cond in ("laying","sitting") else ""
			Core.Print(f"You can't go anywhere, you are riding {-Core.player.riding} which is {cond}.{spurRec}")
			Core.game.setPronouns(Core.player.riding)
			return False

	preps = ("away","away from","down","through","to","toward","up","in","inside","into","on","onto","out",None)
	if prep in ("to", "toward", "away", "away from"):
		prep = None
	if (dobj,iobj,prep) == (None,None,None):
		dobj,iobj,prep = parse(tokenize(read("Where will you go?")))
	if dobj in Data.cancels: return False
	if dobj in ("back", "backward", "backwards"): dobj = Core.game.prevroom.name.lower()
	if dobj in ("ahead", "forward", "forwards"): dobj = getNoun("In which direction?")
	if dobj is None and iobj is not None: dobj,iobj = iobj,dobj

	# if any terms are abbreviations for a direction, expand them
	dobj,iobj,prep = map(Core.expandDir,[dobj,iobj,prep])
	if prep not in preps or (dobj,iobj,prep) == (None,None,None):
		return promptHelp("Command not understood.")

	locReminder = "" if Core.player.parent is Core.game.currentroom else f" You are in {~Core.player.parent}."
	# get dir, dest, and passage and validate them
	dir,dest,passage,cancelledAction = parseGo(dobj,iobj,prep)
	if cancelledAction:
		return False
	# print(dir,dest,passage)
	if (dir,dest,passage) == (None,None,None):
		Core.Print(f"There is no '{dobj}' here.{locReminder}",color="k")
		return False
	if dir is None and dest is not None:
		dir, passage = Core.player.parent.getDirPortalPair(dest.name.lower())
	# print(dir,dest,passage)
	if (dest,passage) == (None,None):
		if dir in Core.player.parent.links:
			if isinstance(Core.player.parent,Core.Room):
				dest = Core.player.parent.links[dir]
			else:
				passage = Core.player.parent
		if dir == "out" and len(Core.player.parent.allDests()) == 1:
			dir = None
			passage = list(Core.player.parent.allLinks().keys())[0][1]
			dest = list(Core.player.parent.allLinks().values())[0]
	# print(dir,dest,passage)
	if (dest,passage) == (None,None) and dir not in Core.player.parent.links:
		passages = Core.player.parent.getPortalsFromDir(dir)
		passage = chooseObject("way",passages,"go")
		# this means player cancelled the choice
		if len(passages) > 0 and passage is None:
			return False
	# print(dir,dest,passage)
	if (dest,passage) == (None,None):
		Core.Print(f"There is no exit leading '{dir}' here.{locReminder}",color="k")
		return False
	if passage is None and Core.player.parent is dest:
		Core.Print(f"You are already there!")
		return False

	# print(dir,dest,passage)
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
		return Core.player.changeLocation(dest)
	Core.Print(f"There is no exit leading to a '{dobj}' here.{locReminder}",color="k")
	return False


def Hide(dobj,iobj,prep,I=None,posture=None):
	if prep not in ("behind","below","beneath","in","inside","under",None):
		return promptHelp("Command not understood.")
	if prep is None: prep = "behind"
	if posture is None:
		posture = "crouch"

	if Core.player.riding is not None:
		Core.Print(f"You can't hide, you are riding {~Core.player.riding}")
		return False
	if isinstance(Core.player.carrier,Core.Creature):
		Core.Print(f"You can't hide, you are being carried by {~Core.player.carrier}")
		return False

	if dobj is None: dobj = iobj
	if I is None: I = findObject(dobj,f"hide {prep}","room")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope(f"hide {prep}",I,permitParent=True): return False

	if prep in ("in","inside"):
		if not isinstance(I,Items.Box):
			Core.Print(f"You can't get {prep} {-I}.")
			return False
		res = I.Traverse(Core.player)
		if I.open:
			I.Close(Core.player)
		return res

	return Core.player.Hide(I,posture=posture)


def Ignite(dobj,iobj,prep):
	Core.Print("igniteing")


def Insert(dobj,iobj,prep):
	Core.Print("inserting")


def JumpFrom(dobj,iobj,prep):
	print(dobj,iobj,prep)
	jpreps = ("across","around","behind","below","beneath","by","d","down","from","in",
		   "inside","into","near","off","on","onto","over","through","to","toward","u",
		   "under","up","upon",None)
	if prep not in jpreps:
		return promptHelp("Command not understood.")
	if Core.player.posture() not in ("standing","crouching") or not Core.player.anchor():
		Core.Print("You need to be standing to jump.")
		return False
	for cond in Data.immobileStatus:
		if Core.player.hasStatus(cond) and Core.player.riding is None:
			Core.Print(f"You can't jump, you are {cond}.")
			return False
	if dobj is not None and not Core.nameMatch(dobj,Core.player.anchor()):
		Core.Print(f"You're not on a '{dobj}'",color="k")
		return False
	newdobj = iobj
	if newdobj is None:
		newdobj = getNoun(f"What will you jump to?")
	return Jump(newdobj,None,"to")


def Jump(dobj,iobj,prep):
	jpreps = ("across","around","behind","below","beneath","by","d","down","from","in",
		   "inside","into","near","off","on","onto","over","through","to","toward","u",
		   "under","up","upon",None)
	if prep not in jpreps:
		return promptHelp("Command not understood.")
	for cond in Data.immobileStatus:
		if Core.player.hasStatus(cond) and Core.player.riding is None:
			Core.Print(f"You can't jump, you are {cond}.")
			return False
	if Core.player.posture() not in ("standing","crouching") or not Core.player.anchor():
		Core.Print("You need to be standing to jump.")
		return False

	jumpTo = None
	jumpFrom = Core.player.anchor()
	suffix = ""
	if prep == "from":
		# swap dobj and iobj if using 'from' prep
		return JumpFrom(iobj,dobj,prep)
	if dobj is None: dobj = iobj
	if prep in ("d","down","off"):
		if Core.player.anchor() not in (None,Core.player.parent.floor):
			if dobj is not None and not Core.nameMatch(dobj,Core.player.anchor()):
				Core.Print(f"You're not on a '{dobj}'",color="k")
				return False
			jumpTo = Core.player.parent.floor
			suffix = " down"
	elif prep in ("around","by","near","toward","u","up"):
		if dobj is not None:
			jumpTo = findObject(dobj,f"jump near","room")
			if jumpTo is None: return False	
			suffix = f" near {-jumpTo}"
	elif prep is None and dobj is None:
		jumpTo = Core.player.anchor()
	if jumpTo is None:
		if prep is None: prep = "on"
		jumpTo = findObject(dobj,f"jump {prep}","room")
		if jumpTo is None: return False
		if jumpTo is Core.player.anchor():
			Core.Print(f"You're already on {-jumpTo}.")
			return False
		suffix = f" {prep} {-jumpTo}"

	if prep in ("d","down","off") and jumpTo is Core.player.parent.floor:
		return Dismount(dobj,iobj,prep)
	if prep in ("across","d","down","off","over","through"):
		if Core.hasMethod(jumpTo,"Traverse"):
			return jumpTo.Traverse(Core.player,verb="jump")
		else:
			Core.Print(f"{+jumpTo} can't be traversed.")
			return False
	if prep in ("on","onto","upon"):
		if Core.hasMethod(jumpTo,"Traverse") and getattr(jumpTo,"open",True):
			return jumpTo.Traverse(Core.player,verb="jump")
	if prep in ("in","inside","into") and not Core.hasMethod(jumpTo,"Traverse"):
		Core.Print(f"You can't get {prep} {-jumpTo}.")
		return False

	jumpFromSize = jumpFrom.Size() if jumpFrom else 1
	jumpToSize = jumpTo.Size() if jumpTo else 1
	difficulty = Core.min1(20 - (jumpFromSize // 10) - (jumpToSize // 5))
	if jumpTo is jumpFrom: difficulty //= 2
	contest = Core.roll(Core.player.ATHL()) - difficulty
	Core.Print(f"You jump{suffix}!")
	if contest <= 0:
		return Core.player.Fall(max(3,abs(contest)//5))

	if prep in ("behind","below","beneath","under"):
		return Hide(dobj,iobj,prep,I=jumpTo,posture="crouch")
	if prep in ("in","inside","into","on","onto","to","upon"):
		return Mount(dobj,iobj,prep,M=jumpTo)
	return True


def Kick(dobj,iobj,prep):
	if dobj is None:
		dobj = getNoun("What will you kick?")
		if dobj in Data.cancels: return False
	return Attack(dobj,"foot","with")


def Kill(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	if dobj in ("me","myself","player","self"):
		if Core.yesno("Are you sure you want to kill yourself?",color="r"):
			Core.player.death()
			return True
		Core.Print("Fwew, that was close!")
		return False
	return Attack(dobj,iobj,prep)


def Lay(dobj,iobj,prep,M=None):
	if prep not in ("at","behind","below","beneath","by","in","inside","into","near","on","onto","under","upon",None):
		return promptHelp("Command not understood.")
	if dobj is None:
		dobj = iobj

	if (dobj,prep,M) == (None,None,None):
		if Core.player.posture() == "laying":
			Core.Print("You are already laying.")
			return False

	if prep is not None and dobj is None and M is None:
		dobj = getNoun(f"What will you lay {prep}?")
		if dobj in Data.cancels: return False
	elif prep is None and dobj is not None:
		prep = "on"

	if prep in ("at","by","near"):
		Core.Print("You are there.")
	elif prep in ("below","beneath","behind","under"):
		return Hide(dobj,iobj,prep,posture="lay")
	elif prep in ("on","onto","upon","in","inside","into"):
		if M is None: M = findObject(dobj,f"lay {prep}","room")
		if M is None: return False
		if M is Core.player.parent: M = Core.player.parent.floor
		Core.game.setPronouns(M)
		return Mount(dobj,iobj,prep,M=M,posture="lay")
	else:
		Core.player.changePosture("lay")
		return True


def Lick(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	I = findObject(dobj,"lick")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("lick",I,permitSelf=True,permitParent=True): return False

	if Core.hasMethod(I,"Lick"):
		return I.Lick(Core.player)
	if isinstance(I,Core.Room):
		Core.Print("You can't lick the air.")
		return False

	if I.composition in Data.tastes:
		Core.Print(Data.tastes[I.composition])
	if I.composition in Data.scents:
		Core.Print(Data.scents[I.composition].replace("scent","taste").replace("smelling","tasting"))
	return True


def Light(dobj,iobj,prep):
	Core.Print("lighting")


def Listen(dobj,iobj,prep):
	Core.Print("listening")


def Lock(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	I = findObject(dobj,"lock")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("lock",I,permitParent=True): return False

	if not Core.hasMethod(I,"Lock"):
		Core.Print(f"{+I} doesn't lock.")
		return False

	K = findObject(iobj,"lock with","player")
	if K is None: return False

	if not isinstance(K,Items.Key):
		Core.Print(f"You can't lock with {-K}.")
		return False
	return I.Lock(K)


def Look(dobj,iobj,prep):
	if prep not in ("around","at","down","in","inside","into","on","out","through","up",None):
		return promptHelp("Command not understood.")
	if prep is None: prep = "at"

	if dobj is None: dobj = iobj
	if dobj is None and prep not in ("around","down","up"):
		dobj = getNoun(f"What will you look {prep}?")
		if dobj in Data.cancels: return False

	if dobj in ("me","myself",Core.player.name):
		Core.Print(f"You are {Core.player.desc}")
		return True
	if dobj in ("sky","sun","moon","stars","aurora","auroras","meteor shower","eclipse","solar eclipse") or prep == "up":
		return Core.game.LookUp(dobj)
	elif prep == "around":
		L = Core.player.parent
	else:
		L = findObject(dobj,"look at")
		if L is None: return False

	Core.game.setPronouns(L)
	L.describe()
	if Core.hasMethod(L,"Look"):
		L.Look(Core.player)
	return True


def Mount(dobj,iobj,prep,M=None,posture=None):
	if posture not in ("stand","crouch","sit","lay",None):
		return promptHelp("Command not understood.")
	if prep not in ("in","into","inside","on","onto","to","up","upon",None):
		return promptHelp("Command not understood.")

	if dobj is None: dobj = iobj
	if M is None: M = findObject(dobj,"get on","room")
	if M is None: return False
	Core.game.setPronouns(M)
	# done before enforceVerbScope because it would prevent interaction with floor
	if isinstance(M,Core.Room) or M is Core.player.parent.floor:
		if Core.player.anchor() not in (None,Core.player.parent.floor):
			return Dismount(None,None,None,posture=posture)
	if enforceVerbScope("get on",M,permitParent=True):
		return False
	if M in Core.player.parent.surfaces and not Core.player.hasStatus("clingfast"):
		Core.Print(f"You can't get on {-M}.")
		return False

	if Core.hasMethod(M,"Ride"):
		# Core.player.removeStatus("hidden",-3) TODO: readd this?
		if posture is None:
			posture = "sit"

	# if "stand on snake" or something
	if posture in ("stand","crouch"):
		if M.Weight() < Core.player.Weight() // 5 or M.posture() == "laying":
			Core.player.changePosture(posture)
			return Attack(dobj,"foot","with",target=M)

	if prep in ("in","into","inside"):
		if not Core.hasMethod(M,"Traverse"):
			return Core.Print(f"{+M} cannot be traversed.")
		return M.Traverse(Core.player)

	if posture is None:
		posture = "stand"
	return Core.player.Mount(M,posture)


def Open(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	I = findObject(dobj,"open")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("open",I,permitParent=True): return False

	if Core.hasMethod(I,"Open"):
		return I.Open(Core.player)
	elif hasattr(I,"locked") and I.locked:
		Core.Print(f"{+I} is locked.")
		return False
	Core.Print(f"{+I} doesn't open.")
	return False


def Play(dobj,iobj,prep):
	Core.Print("playing")


def Point(dobj,iobj,prep):
	Core.Print("pointing")


def Pour(dobj,iobj,prep,I=None):
	if prep not in ("in","into","inside","on","onto","out","upon",None):
		return promptHelp("Command not understood.")

	if I is None: I = findObject(dobj,"pour","player")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("pour",I,permitParent=False): return False

	if not Core.hasMethod(I,"Pour"):
		Core.Print(f"You can't pour {-I}.")
		return False

	R = findObject(iobj,"pour on")
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

	I = findObject(dobj,"put","player")
	if I is None: return False
	Core.game.setPronouns(I)

	# if input was 'put item down'
	if prep == "down" and iobj is None:
		return Drop(dobj,None,prep,I=I)

	if iobj is None:
		iobj = getNoun(f"What will you put your {dobj} {prep}?")
		if iobj in Data.cancels: return False
	R = findObject(iobj,f"put {prep}")
	if R is None: return False
	if enforceVerbScope(f"put {prep}",R): return False
	if R is Core.player.parent or R is Core.player.parent.floor:
		return Drop(dobj,None,None,I=I)

	if isinstance(I,Core.Compass) and Core.player.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not Core.yesno(q):
			return False

	if isinstance(R,Core.Portal) and "down" in R.links:
		if getattr(R,"open",True):
			if isinstance(I,Core.Creature):
					Core.player.removeCarry(I)
			else:
				Core.player.remove(I)
				Core.player.parent.add(I)
			return R.Transfer(I)
		else:
			Core.Print(f"{+R} is closed.")
	elif not Core.hasMethod(R,"add"):
		Core.Print(f"You can't put {-I} {prep} {-R}.")
		return False
	elif not R.canAdd(I) and I not in R.contents():
		Core.Print(f"You can't put {-I} {prep} {-R}. There's not enough room.")
		return False

	idet = "your" if Core.player in I.ancestors() else 'the'
	rdet = "your" if Core.player in R.ancestors() else 'the'
	outprep = "on" if isinstance(R,Items.Table) else "in"
	if iobj == "here": Core.Print(f"You put your {I.name} here.")
	else: Core.Print(f"You put {idet} {I} {outprep} {rdet} {R}.")
	I.parent.remove(I)
	if I is Core.player.carrying:
		Core.player.removeCarry(silent=True)
	R.add(I)
	return True


def Quicksave(*args):
	Menu.quickSave("quicksave")
	Core.waitInput("Quicksaved.",color="k")
	return interpret()


def Release(dobj,iobj,prep):
	Core.Print("releaseing")


def Restrain(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	C = findObject(dobj,"restrain","room")
	if C is None: return False
	Core.game.setPronouns(C)
	if enforceVerbScope("restrain",C,permitParent=False): return False

	# TODO: can't restrain creature you're already riding??
	if not isinstance(C,Core.Creature):
		Core.Print(f"You can't restrain {-C}.")
		return False

	I = None
	if iobj is not None:
		I = findObject(iobj,"restrain with","player")
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

	I = findObject(dobj,"rub")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("rub",I): return False

	if Core.hasMethod(I,"Rub"):
		return I.Rub(Core.player)
	return Touch(dobj,iobj,prep)


def Save(dobj,iobj,prep):
	Menu.saveGame(dobj)
	return interpret()


def Search(dobj,iobj,prep):
	Core.Print("searching")


def Shoot(dobj,iobj,prep):
	Core.Print("shooting")


def Shove(dobj,iobj,prep):
	Core.Print("shoveing")


def Sit(dobj,iobj,prep):
	if prep not in ("at","behind","below","beneath","by","in","inside","into","near","on","onto","under","upon",None):
		return promptHelp("Command not understood.")
	if dobj is None:
		dobj = iobj

	if (dobj,prep) == (None,None):
		if Core.player.posture() == "sitting":
			Core.Print("You are already sitting.")
			return False

	if prep is not None and dobj is None:
		dobj = getNoun(f"What will you sit {prep}?")
		if dobj in Data.cancels: return False
	elif prep is None and dobj is not None:
		prep = "on"

	if prep in ("at","by","near"):
		Core.Print("You are there.")
	elif prep in ("below","beneath","behind","under"):
		return Hide(dobj,iobj,prep,posture="sit")
	elif prep in ("on","onto","upon","in","inside","into"):
		M = findObject(dobj,f"sit {prep}","room")
		if M is None: return False
		Core.game.setPronouns(M)
		return Mount(dobj,iobj,prep,M=M,posture="sit")
	else:
		Core.player.changePosture("sit")
		return True


def Sleep(dobj,iobj,prep):
	if prep not in ("behind","below","beneath","in","inside","into","on","onto","over","under","upon","using","with",None):
		return promptHelp("Commmand not understood")

	for condname in Data.conditionDmg.keys():
		if Core.player.hasStatus(condname):
			Core.Print(f"This is no time for slumber! You are {condname}.",color="o")
			return False

	if prep is None: prep = "on"
	if dobj is None: dobj = iobj

	if dobj is not None:
		I = findObject(dobj,f"sleep {prep}","room")
		if I is None and not Core.yesno("Would you like to sleep on the ground?"):
			return False
	else:
		I = Core.player.anchor()
		if I is Core.player.parent.floor and Core.player.parent.floor is not None:
			if not Core.yesno("Would you like to sleep on the ground?"):
				return False

	if not Core.player.hasStatus("laying"):
		Lay(dobj,iobj,"on",M=I)
	if not Core.player.hasStatus("laying"):
		Core.Print("You can't sleep, you're not laying down.")
		return False

	if not Core.player.hasStatus("cozy"):
		Core.waitInput("Your sleep will not be very restful...")

	sleeptime = 90 + randint(1,20)
	Core.player.addStatus("asleep",sleeptime)
	Core.ellipsis(sleeptime//30)
	Core.game.silent=True
	return True


def Smell(dobj,iobj,prep):	
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	# TODO: if blinded, randomly smell something in the room?
	I = findObject(dobj,"smell")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("smell",I,permitSelf=True,permitParent=True): return False

	if Core.hasMethod(I,"Smell"):
		return I.Smell(Core.player)

	if isinstance(I,Core.Room):
		I = I.floor
	if I is None:
		Core.Print("You smell nothing.")
		return True

	if I.composition in Data.scents:
		Core.Print(Data.scents[I.composition])
	if I.composition in Data.tastes:
		Core.Print(Data.tastes[I.composition].replace("taste","smell").replace("tasting","smelling"))
	return True


def Spur(dobj,iobj,prep):
	if prep not in ("at","on","to","upon",None):
		return promptHelp("Command not understood.")
	if dobj is None:
		dobj = getNoun("What will you spur?")
		if dobj in Data.cancels: return False
	M = findObject(dobj,"spur","room")
	if M is None: return False
	Core.game.setPronouns(M)
	if enforceVerbScope("spur",M): return False

	if M is not Core.player.riding:
		Core.Print(f"You are not riding {-M}.")
		return False
	if not isinstance(M,Core.Creature):
		Core.Print(f"You can't spur {-M}.")
		return False
	Core.Print(f"You spur {-M}.")
	if M.isFriendly():
		M.changePosture("stand")
	return True


def Stand(dobj,iobj,prep):
	if prep not in ("at","behind","below","beneath","by","in","inside","into","near","on","onto","upon",None):
		return promptHelp("Command not understood.")
	if dobj is None:
		dobj = iobj

	if (dobj,prep) == (None,None):
		if Core.player.posture() == "standing":
			Core.Print("You are already standing.")
			return False

	if prep is not None and dobj is None:
		dobj = getNoun(f"What will you stand {prep}?")
		if dobj in Data.cancels: return False
	elif prep is None and dobj is not None:
		prep = "on"

	if prep in ("at","by","near"):
		Core.Print("You are there.")
	elif prep in ("below","beneath","behind","under"):
		return Hide(dobj,iobj,prep,posture="stand")
	elif prep in ("on","onto","upon","in","inside","into"):
		M = findObject(dobj,f"stand {prep}","room")
		if M is None: return False
		Core.game.setPronouns(M)
		return Mount(dobj,iobj,prep,M=M,posture="stand")
	else:
		Core.player.changePosture("stand")
		return True


def Steal(dobj,iobj,prep,I=None):
	# TODO make sure to account for tethers
	Core.Print(f"stealing {dobj} {prep} {iobj}")


def Struggle(dobj,iobj,prep):
	Core.Print("struggleing")


def Swim(dobj,iobj,prep):
	Core.Print("swiming")


# if an item is a container, take each of its contents before taking it
def TakeAllRecur(objToTake):
	if objToTake is Core.player:
		return False
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

	if enforceVerbScope("take",objToTake,permitParent=False,permitAnchor=False): return False
	return Core.player.obtainItem(objToTake) or takenAny


def TakeAll(parent):
	if not hasattr(parent,"items"):
		Core.Print(f"{+parent} doesn't contain anything.")
		return False
	if len(parent.items) == 0:
		Core.Print("There are no items to take.")
		return False
	takenAny = False
	for obj in sorted(parent.items, key=lambda x: x.Weight()):
		takenAny = TakeAllRecur(obj) or takenAny
	return takenAny


def Take(dobj,iobj,prep):
	if prep in ("behind","below","beneath","under"):
		return Hide(dobj,iobj,prep)
	if prep not in ("from","in","inside","out","out of","up",None):
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What will you take?")
		if dobj in Data.cancels: return False

	if dobj in ("all","each","everything","it all"):
		# TODO: account for 'take everything from ground', so only take uncontained items
		if iobj is None:
			takeFrom = Core.player.parent
		else:
			takeFrom = findObject(iobj,"take from")
		return TakeAll(takeFrom)

	if iobj in ("here","room",None):
		objToTake = findObject(dobj,"take","room",roomD=2)
	else:
		objToTake = findObject(dobj,"take",roomD=2,reqParent=iobj)
	if objToTake is None:
		return False
	Core.game.setPronouns(objToTake)
	if enforceVerbScope("take",objToTake,permitAnchor=False): return False
	if objToTake.parent is Core.player:
		Core.Print(f"You can't take from your own Inventory.")
		return False
	if isinstance(objToTake,Core.Fixture):
		Core.Print(f"You can't take {-objToTake}.")
		return False
	if isinstance(objToTake,Core.Creature):
		return CarryCreature(objToTake)

	# if it is in a non-player inventory, it will have to be stolen
	if any(isinstance(anc,Core.Creature) for anc in objToTake.ancestors()) and objToTake not in Core.player.objTree():
		return Steal(dobj,iobj,prep,I=objToTake)

	return Core.player.obtainItem(objToTake)


def Talk(dobj,iobj,prep):
	if prep not in ("at","into","to","toward","with",None):
		return promptHelp("Command not understood.")

	if dobj is None: dobj = iobj
	if dobj is None:
		dobj = getNoun("Who do you want to talk to?")
		if dobj in Data.cancels: return False

	target = findObject(dobj,"talk to","room")
	if target is None: 
		return False
	Core.game.setPronouns(target)

	if not Core.hasMethod(target,'Talk'):
		Core.Print(f"There is no response...")
		return False

	target.Talk()
	return True


def Throw(dobj,iobj,prep,maxspeed=None):
	if prep not in ("at","down","in","into","off","on","onto","out","through","to","toward","up",None):
		return promptHelp("Command not understood.")
	if prep in ("to","toward"):
		maxspeed = 0
	verb = "toss" if maxspeed == 0 else "throw"

	if prep in ("down","up","in","out"):
		if iobj is None:
			iobj = prep
		prep = None
	if prep is None:
		prep = "at"
	I = findObject(dobj,"throw","player")
	if I is None: return False

	if iobj is None:
		iobj = getNoun(f"What will you {verb} {prep}?")
		if iobj in Data.cancels: return False
	dir = None
	if iobj.lower() in Core.game.currentroom.links.keys():
		T = Core.game.currentroom.links[iobj]
		dir = iobj
	elif Core.player.parent.getDirPortalPair(iobj)[0]:
		dir, T = Core.player.parent.getDirPortalPair(iobj)
	else:
		T = findObject(iobj,f"{verb} {prep}","room")
		if T is None: return False
		dirprep = getattr(T,"passprep","toward")
		dir = f"{dirprep} {-T}"
	if T is None:
		T = Core.player.parent
	if T is I:
		Core.Print(f"You can't {verb} {-I} at {I.reflexive()}.",color="k")
		return False
	if T is Core.player.parent or T is Core.player.parent.walls:
		dir = "forward"
	elif T is Core.player.parent.floor or T is Core.player.anchor():
		dir = "down"
	elif T is Core.player.parent.ceiling:
		dir = "up"

	if not Core.player.parent.canAdd(I) and I not in Core.player.parent.contents():
		Core.Print(f"You can't {verb} {-I}. There's not enough room.",color="k")
		return False

	Core.player.equipInHand(I,slot="left")
	Core.game.setPronouns(I)
	Core.Print(f"You {verb} {-I} {dir}.")
	Core.player.Throw(I,T,maxspeed=maxspeed)
	return True


# throw at a tree, window, goblin, pit
# throw a rock, sword, black potion, bird, goblin
# toss into a basket? like basketball?


def Tie(dobj,iobj,prep):
	Core.Print("tieing")


def Toss(dobj,iobj,prep):
	return Throw(dobj,iobj,prep,maxspeed=0)


def Touch(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	I = findObject(dobj,"touch")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("touch",I,permitParent=True,permitSelf=True): return False

	if Core.hasMethod(I,"Touch"):
		return I.Touch(Core.player)

	if I.composition in Data.textures:
		Core.Print(Data.textures[I.composition])
	return True


def Trip(dobj,iobj,prep):
	Core.Print("triping")


def Try(dobj,iobj,prep):
	Core.Print("Do or do not. There is no try.")
	return False


def Unequip(dobj,iobj,prep):
	if prep is not None:
		return promptHelp("Command not understood.")

	if dobj is None:
		dobj = getNoun("What would you like to unequip?")
		if dobj in Data.cancels: return False

	slot, I = Core.player.inGear(dobj)
	if I is None:
		Core.Print(f"You do not have a '{dobj}' equipped.",color="k")
		return False
	Core.game.setPronouns(I)
	Core.player.unequip(slot)
	return True


def Unlock(dobj,iobj,prep):
	if prep not in ("using","with",None):
		return promptHelp("Command not understood.")

	I = findObject(dobj,"unlock")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("unlock",I,permitParent=True): return False

	if not Core.hasMethod(I,"Unlock"):
		Core.Print(f"{+I} doesn't unlock.")
		return False
	K = findObject(iobj,"unlock with","player")
	if K is None: return False

	if not isinstance(K,Items.Key):
		Core.Print(f"You can't unlock with {-K}.")
		return False
	return I.Unlock(K)


def Untie(dobj,iobj,prep):
	Core.Print("untieing")


def Use(dobj,iobj,prep):
	I = findObject(dobj,"use")
	if I is None: return False
	Core.game.setPronouns(I)
	if enforceVerbScope("use",I,permitParent=True): return False

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
	"\\dgn":Diagnostic,
	"\\evl":Evaluate,
	"\\exe":Execute,
	"\\get":Get,
	"\\grw":Grow,
	"\\ing":Honor,
	"\\lrn":Learn,
	"\\lob":Lob,
	"\\mbu":Imbue,
	"\\mod":Mode,
	"\\pot":Pypot,
	"\\set":Set,
	"\\shk":Shrink,
	"\\spn":Spawn,
	"\\tst":Test,
	"\\tpt":Teleport,
	"\\wrp":Warp,
	"\\xpl":Expell,
	"\\zap":Zap,
	"\x02":Honor,  # Ctrl-B ☻
	"\x04":lambda x: None, # Ctrl-D ♦ (reserved for future use)
	"\x05":lambda x: Zap(["","all"]),  # Ctrl-E ♣
	"\x10":lambda x: Learn(["",100]), # Ctrl-P ►
	"\x11":lambda x: Fortify([""]), # Ctrl-Q ◄
	"\x12":lambda x: None,  # Ctrl-R ↕ (reserved for future use)
	"\x13":Quicksave,  # Ctrl-S ‼
	"\x14": lambda x: None,  # Ctrl-T ¶ (reserved for future use) 
	"\x15":lambda x: Pypot(["",10000]),  # Ctrl-U §
	"\x17":lambda x: Imbue(["","flying"]), # Ctrl-W ↨
	"\x18":Grow, # Ctrl-X ↑
	"\x19":Shrink, # Ctrl-Y ↓
}

# contains corresponding functions for all items in Data.shortverbs or stat commands
statcommands = {
"abilities":Core.Player.printAbility,
"back":Return,
"back up":Return,
"carrying":Core.Player.printCarrying,
"commands":Commands,
"examples":Examples,
"exits":Exits,
"gear":Core.Player.printGear,
"help":Menu.gameInfo,
"hello":Hello,
"here":Core.game.currentroom.describe,
"hi":Hello,
"hp":Core.Player.printHP,
"info": Menu.gameInfo,
"information": Menu.gameInfo,
"inv":Core.Player.printInv,
"inventory":Core.Player.printInv,
"level":Core.Player.printLV,
"lv":Core.Player.printLV,
"money":Core.Player.printMoney,
"mp":Core.Player.printMP,
"pos":Core.Player.printPosition,
"position":Core.Player.printPosition,
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
"yawn":Yawn,
":)": Smile,
":(": Cry,
":d": Laugh,
":p": Sing,
";)": Wink,
":o": Shout,
}

shortcommands = (list(statcommands.keys()) +
					list(Data.colors.keys()) +
					list(Data.shortactions) +
					list(Data.traits) +
					list(Data.abilities) +
					list(Data.hellos) +
					list(Data.goodbyes)
				)

actions = {
"attack":Attack,
"bite":Bite,
"break":Break,
"build":Craft,
"caress":Caress,
"carry":Take,
"cast":Cast,
"catch":Catch,
"climb":Climb,
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
"drive":Spur,
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
"fall asleep":Sleep,
"feed":Feed,
"feel":Touch,
"fight":Attack,
"fill":Fill,
"find":Find,
"fish":Fish,
"follow":Follow,
"fuck":Fuck,
"get":Take,
"get in":Enter,
"get into":Enter,
"get inside":Enter,
"get down":Dismount,
"get off":Dismount,
"get on":Mount,
"get out":Exit,
"get out of":Exit,
"get up":Dismount,
"give":Give,
"go":Go,
"go to sleep":Sleep,
"grab":Take,
"grapple":Take,
"hand":Give,
"have sex":Fuck,
"head":Go,
"hear":Listen,
"hide":Hide,
"hit":Attack,
"ignite":Ignite,
"insert":Insert,
"jump":Jump,
"jump down from":JumpFrom,
"jump from":JumpFrom,
"jump to":Jump,
"jump up":Jump,
"kick":Kick,
"kill":Kill,
"laugh":Laugh,
"lay":Lay,
"lay down":Lay,
"leap": Jump,
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
"make love":Fuck,
"mount":Mount,
"move":Go,
"nap":Sleep,
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
"rest":Sleep,
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
"sleep":Sleep,
"slice":Cut,
"slumber":Sleep,
"smash":Break,
"smell":Smell,
"sneak":Crouch,
"sniff":Smell,
"snooze":Sleep,
"speak":Talk,
"spur":Spur,
"squat":Crouch,
"stand":Stand,
"stand up":Stand,
"steal":Steal,
"step":Stand,
"stomp":Kick,
"stow":Unequip,
"strike":Attack,
"stroke":Caress,
"struggle":Struggle,
"swim":Swim,
"take":Take,
"take a bite":Bite,
"take a drink":Drink,
# "take a dump":Poop,
# "take a leak":Pee,
"take a nap":Sleep,
# "take a piss":Pee,
"take a seat":Sit,
# "take a shit":Poop,
"take a sip":Lick,
"take a step":Go,
"take a swim":Swim,
"take a walk":Go,
"take cover":Hide,
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
# flick/tap
# knock/bang
# sip -> drink or lick?
# insert (key) -> unlock
# lift -> carry
# mix/stir -> brew?
# greet -> wave or talk?
# scratch/itch
# switch
# stop (stop him, stop hiding, stop riding, stop running, etc)
# smoke
# weave/sew
# guard/shield/block/protect/cover
# meditate
# evade -> dodge
# stare/gaze -> look
# fart, burp
# pick -> a lock or a berry
# step on
# kiss/smooch
# shake? (shake hands?)
# browse/peruse -> look
# roll (in the mud?)
# pilfer -> steal
# swing (an item)
# ligma/sugma
# buy/pay/purchase, sell, trade
# embrace/hug
# stab/slash
# shave?
# swallow
# fly/float/hover? (rename the spell, or if already flying, just redirect to go)
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
# chop -> slash -> attack
# chew -> eat
# strike -> ignite/hit
# lift -> carry
# kneel -> crouch
# lasso
# ask/inquire -> talk
# snuff/put out/blow out
# investigate -> examine -> look??
# flip/backflip??
# row/steer (if not mounted -> ride, else -> go)
# stop
# blow/breath
# clap
# snap
# observe/watch
# capture (with a net?) -> take?
# loot/scavenge/forage/salvage/harvest/pluck