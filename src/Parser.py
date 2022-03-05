# Parser.py
# This file contains the code to parse user input and execute player actions
# This file is dependent on Menu.py and is a dependency of PoPy.py

# It consists of four main parts;
# 1. Game startup		(call main menu and instantiate global objects P, W, G)
# 2. Parsing functions	(functions to parse user input)
# 3. Action functions	(action, shortaction, cheat functions called by parse())
# 4. Action dicts		(dictionaries used to call action functions from)

from Menu import *



##################
## GAME STARTUP ##
##################

# formatting the prompt window
os.system("mode con:cols=128 lines=32")
os.system("title Potions ^& Pythons")

# import pygetwindow
# win = pygetwindow.getWindowsWithTitle('Potions & Pythons')[0]
# win.size = (128*8, 32*16) #128 x 32 tiles of 8 x 16 pixels


# run intro logo animation
gameIntro()
# print("\n"*64 + logo)

# mainMenu instantiates global objects Player, World, Game
P, W, G = mainMenu()



#######################
## PARSING FUNCTIONS ##
#######################

# checks if a noun refers to a room, an object in the world or on the player...
# or an action verb, an in-game definition or a miscellaneous expression
def isMeaningful(noun):
	if noun in W or \
	noun in actions or \
	noun in definitions or \
	noun in miscexpressions or \
	P.search(noun) or \
	G.inWorld(noun,W):
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
	if term == "it":				obj = G.it
	elif term in {"she","her"}:		obj = G.she
	elif term in {"he","him"}:		obj = G.he
	elif term in {"they","them"}:	obj = G.they
	if obj == None:					return None
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
	if storeRawCmd:	G.lastRawCommand = rawcommand.split()

	# lowercase-ify the sentence command, copy it excluding symbols
	purecommand = "".join([i for i in rawcommand.lower() if i not in symbols])
	# copy command, delimited by spaces, into a list of words excluding articles
	listcommand = [i for i in purecommand.split() if i not in articles]
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
		if term in prepositions and prep == None:	prep = term
		# direct object is defined if prep and dobj havent been found yet
		elif prep == None and dobj == None:			dobj = term
		# indirect object is defined if a prep or dobj has been found
		else:										iobj = term

	if dobj in pronouns:	dobj = replacePronoun(dobj)
	if iobj in pronouns:	iobj = replacePronoun(iobj)

	return dobj,iobj,prep

# called in parse() when a command fails, it simply recurs parse(), and...
# prints a helpful message if user has provided invalid input 3 or more times
# n is the number of times parse() has recurred
def promptHelp(msg,n):
	if msg != "":	print(msg)
	if n >= 2:	print("Enter 'help' for a list of commands")
	if n > 32:	return False	# prevent stack overflow from repeated bad input
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
		return cheatcodes[verb](G.lastRawCommand)
	elif verb in shortverbs or verb in statcommands:
		if len(command) != 1:
			return promptHelp(f"The '{verb}' command can only be one word",n)
		if verb.upper() in abilities:
			return P.printAbility(verb.upper())
		return shortactions[verb]()
	elif verb not in actions:
		return promptHelp(f"'{verb}' is not a valid verb",n)

	# iterates through the command (skips the verb) and assigns...
	# terms based on their position relative to the other terms present
	for term in command[1:]:
		# preposition is defined if the term is a known preposition
		if term in prepositions and prep == None:	prep = term
		# direct object is defined if prep and dobj havent been found yet
		elif prep == None and dobj == None:			dobj = term
		# indirect object is defined if a prep or dobj has been found
		elif iobj == None:							iobj = term

	if dobj in pronouns:	dobj = replacePronoun(dobj)
	if iobj in pronouns:	iobj = replacePronoun(iobj)

	# this line calls the action function using the 'actions' dict
	actionCompleted = actions[verb](dobj,iobj,prep)
	# if action was instant, loop for another command
	if verb in instantactions:	return False
	# if action was not completed for some reason, recur
	if not actionCompleted:		return promptHelp("",n)
	return True



##########################################
## CHEATCODES AND DEV COMMAND FUNCTIONS ##
##########################################

def Get(command):
	objname = command[1].lower()
	if objname in {"p","player","my"}:
		obj = P
	elif objname in {"g","game"}:
		obj = G
	elif objname in {"here","room"}:
		obj = G.currentroom
	elif objname in {"w","world"}:
		obj = W
	else:
		obj = objSearch(objname,G.currentroom,d=3)
	if obj == None:
		try: obj = W[objname]
		except:	pass
	if obj == None:
		print("Object not found")
		return
	try:
		attrString = command[2]
		print(getattr(obj,attrString))
	except:
		print("Attribute does not exist")

def Learn(command):
	try:	P.gainxp(int(command[1]))
	except:	print("Value not number")

def Mode(command):
	try:
		G.mode = int(command[1])
		print("Mode set to " + str(G.mode))
	except:
		print("Value not number")

def Pypot(command):
	try:	P.money = P.money + int(command[1])
	except:	print("Value not number")

def Set(command):
	if command[1] in {"p","player"}:
		obj = P
	else:
		obj = objSearch(command[1],G.currentroom,d=3)
	attrString = command[2]
	val = command[3]
	setStat(obj,attrString,val)

def Teleport(command):
	location = command[1]
	if location in W:	G.changeRoom(W[location],P,W)
	else:				print("Location not in world")

def Test(command):
	for i in range(10):
		print("hello" + str(i))
		if kbInput():
			clearScreen()
			flushInput()
			return
		sleep(1)
		# clearScreen()
	return True

def Warp(command):
	try:	G.time += int(command[1])
	except:	print("Value not number")

def Zap(command):
	objname = " ".join(command[1:])
	allObjects = G.getAllObjects(W)
	zappedObjects = 0
	for obj in allObjects:
		if objname.lower() == obj.name.lower():
			if isinstance(obj,Item):
				obj.Break(P,G)
			elif isinstance(obj,Creature):
				obj.death(P,G,W)
			zappedObjects += 1
	print("Zapped objects: " + str(zappedObjects))



#######################################
## SHORTACTION AND RELATED FUNCTIONS ##
#######################################

def Cry(): print("A single tear sheds from your eye")
def Dance(): print("You bust down a boogie")
def Examples(): print("\n"*64 + examples)

def Help():
	clearScreen()
	print("\nPlayer Statistics Commands")
	columnPrint(statcommands,10,10)
	print("\nOther Single-Word Commands")
	columnPrint(shortverbs,10,10)
	print("\nVerb Commands (Does not include cheat codes and secret commands)")
	columnPrint(verbs,10,10)
	print("\nType 'info' for information on the game and how to play")
	input()
	clearScreen()

def Info():
	print("\n"*64 + gameinfo)
	input()
	clearScreen()

def Laugh(): print("HAHAHAHAHA!")
def Quit():
	if yesno("Are you sure you want to quit? (Anything unsaved will be lost)"):
		sys.exit()
def Return(): return Go(None, G.prevroom.name, None) #go to previous room
def Save(): saveGame(P,W,G)
def Shout(): print("AHHHHHHHHHH")
def Sing(): print("Falalalaaaa")
def Time(): print("Time:", G.time)
def Yawn():	print("This is no time for slumber!")



##################################
## ACTION AND RELATED FUNCTIONS ##
##################################

def Attack(dobj,iobj,prep):
	if prep not in {"with","using",None}:
		print("Command not understood")
		return False

	if iobj == None:
		if len(P.weapons()) == 0:
			iobj = "fist"
		elif P.gear["right"] == Empty() and P.gear["left"] == Empty():
			iobj = getNoun("What will you attack with?")
			if iobj in cancels:	return False
	weapon = P.weapon
	if iobj != None:
		weapon = P.inGear(iobj)
		if weapon == None:	weapon = P.inInv(iobj)
		if iobj in {"fist","hand"}:		weapon = Hand("your hand","",4,-1)
		if iobj in {"foot","leg"}:		weapon = Foot("your foot","",8,-1)
		if iobj in {"mouth","teeth"}:	weapon = Mouth("your mouth","",4,-1)
		if weapon == None:
			print(f"There is no '{iobj}' in your inventory")
			return False

	if dobj == None:	dobj = getNoun("What will you attack?")
	if dobj in cancels:	return False
	target = G.currentroom.inOccupants(dobj)
	if target == None:	target = G.currentroom.inContents(dobj)
	if dobj in {"myself","me"}: target = P
	if target == None:
		print(f"There is no '{dobj}' here")
		return False

	if iobj in {"fist","hand","foot","leg","mouth","teeth"}:
		stowedweapons = P.weapon,P.weapon2
		P.weapon,P.weapon2 = weapon.improviseWeapon(),Empty()
	elif weapon not in P.gear.values():
		P.equipInHand(weapon)

	G.setPronouns(target)
	print(f"\nYou attack the {target.name} with {P.weapon.name}")
	if isinstance(target,Creature):		P.attackCreature(target,G,W)
	elif isinstance(target,Item):		P.attackItem(target,G,W)
	if iobj in {"fist","hand","foot","leg"}:
		P.weapon,P.weapon2 = stowedweapons
	return True


def Bite(dobj,iobj,prep):
	if prep not in {"with","using",None}:
		print("Command not understood")
	if dobj == None:
		dobj = getNoun("What do you want to bite?")
		if dobj in cancels:
			return False

	I = G.currentroom.search(dobj)
	if I == None:	I = P.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False
	if hasMethod(I,"Eat"):
		return Eat(dobj,iobj,prep)
	else:
		return Attack(dobj,"mouth",prep)

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
		if dobj in cancels:
			return False

	I = P.search(dobj)
	if I == None:	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Break"):
		print("You can't break the " + I.name)
		return False
	I.Break(P,G)
	return True

def Carry(dobj,iobj,prep):
	# TODO: identify a way to link carrier to carried without remove carried creature from Room.creatures
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to carry?")
		if dobj in cancels:
			return False

	I = G.currentroom.search(dobj)
	if I == None: I = P.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False
	G.setPronouns(I)

	if isinstance(I,Item):
		return Take(dobj,iobj,prep)
	if not isinstance(I,Creature):
		print(f"You can't carry the {dobj}")
		return False

	print(f"You try to pick up the {dobj}")
	if Restrain(dobj,iobj,prep):
		return I.Carry(P)

def Cast(dobj,iobj,prep):
	if prep not in {"at","on","onto","upon",}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What spell will you cast?")
		if dobj in cancels:
			return False
	if dobj not in P.spells:
		print("You don't know a spell called " + dobj)
		return False
	if dobj not in spells:
		# this shouldn't happen
		print("That spell doesn't exist")
		return False

	return spells[dobj](P,W,G,iobj)


def Catch(dobj,iobj,prep):
	print("catching")

# def Climb(dobj,iobj,prep):
# 	print("climbing")

def Close(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you close?")
		if dobj in cancels:
			return False

	I = P.search(dobj)
	if I == None:	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(I)
	if not hasattr(I,"open"):
		print("You can't close the " + I.name)
		return False
	if not I.open:
		print(f"The {I.name} is already closed")
		return False
	if hasMethod(I,"Close"):
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

	P.addCondition("crouched",-3)
	return True

def Cut(dobj,iobj,prep):
	print("cuting")

def Define(dobj,iobj,prep):
	if iobj != None or prep != None:
		print("Can only define one word at once")
		return False
	if dobj == None:
		dobj = getNoun("What term would you like defined?")
		if dobj in cancels:
			return False

	if dobj in definitions:
		print("\n"+definitions[dobj])
		return True
	elif dobj == P.name.lower():
		print(f"\n{P.name}\nThat is you!")
		return True
	print(f"'{dobj}' is unknown")
	return False

def Describe(dobj,iobj,prep):
	if iobj != None or prep != None:
		print("Can only describe one thing at once")
		return False
	if dobj == None:	#if no dobj, ask
		dobj = getNoun("What do you want to be described?")
		if dobj in cancels:
			return False

	D = P.search(dobj)
	if dobj == G.currentroom.name or dobj in {"room","here"}:
		D = G.currentroom
	if D == None:	D = G.currentroom.search(dobj)
	if D == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(D)
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
		if dobj in cancels:
			return False

	I = P.inGear(dobj)
	if I == None or not isinstance(I,Armor):
		print(f"You aren't wearing a '{dobj}'")
		return False

	G.setPronouns(I)
	P.unequip(I)
	print(f"You doff your {I.name}")
	return True

def Don(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to don?")
		if dobj in cancels:
			return False

	I = P.inInv(dobj)
	if I == None:
		print(f"There is no available '{dobj}' in your inventory")
		return False

	if not isinstance(I,Armor):
		print(f"You cannot wear your {I.name}")
		return False
	if I in P.gear.values():
		print(f"You are already wearing your {I.name}")
		return False

	G.setPronouns(I)
	if not P.equipArmor(I):
		return False
	print(f"You don your {I.name}")
	return True

def Drink(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to drink?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Drink"):
		print("You can't drink the " + I.name)
		return False
	I.Drink(P,G)
	return True

def Drop(dobj,iobj,prep):
	if prep != None:
		return Put(dobj,iobj,prep)
	if dobj == None:
		dobj = getNoun("What will you drop?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False

	G.setPronouns(I)
	if isinstance(I,Compass) and P.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not yesno(q):
			return False
	print("You drop your " + I.name)
	S.removeItem(I)
	G.currentroom.addItem(I)
	return True

def Dump(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you dump?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False
	G.setPronouns(I)
	if hasMethod(I,"Pour"):
		return Pour(dobj,iobj,prep)
	else:
		return Drop(dobj,iobj,prep)

def Eat(dobj,iobj,prep):
	if prep not in {"with",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What do you want to eat?")
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Eat"):
		print("You can't eat the " + I.name)
		return False
	I.Eat(P,G)
	return True

def Enter(dobj,iobj,prep):
	print("entering")

def Equip(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What would you like to equip?")
		if dobj in cancels:
			return False

	I = P.inInv(dobj)
	if I == None:
		print(f"There is no available '{dobj}' in your inventory")
		return False

	G.setPronouns(I)
	if P.inGear(dobj) and P.invNames(lower=True).count(dobj) == 1:
		print(f"Your {dobj} is already equipped")
		return False
	# if item is armor, equip it as armor, otherwise, equip it in hand
	if isinstance(I,Armor):		P.equipArmor(I)
	else:						P.equipInHand(I)
	print(f"You equip your {I.name}")
	return True

def Escape(dobj,iobj,prep):
	print("escapeing")

def Exit(dobj,iobj,prep):
	print("exiting")

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
	print("I'm not sure I, the game developer, can allow that")

def Give(dobj,iobj,prep):
	print("giveing")

# called when the user wants to go "up" or "down"
def GoVertical(dir,passage=None,dobj=None):
	print(dir,passage,dobj)
	if P.hasCondition("fly"):
		newroom = G.currentroom.exits[dir]
		print(f"You fly {dir}!")
		return G.changeRoom(W[newroom],P,W)

	if passage == None and dobj != None:
		print(f"There is no '{dobj}' to go {dir} here")
		return False
	if passage == None:
		passagename = getNoun(f"What will you go {dir}?")
		passage = G.currentroom.search(passagename)
	if passage == None:
		print(f"There is no '{passagename}' to go {dir} here")
		return False
	if hasMethod(passage,"Traverse"):
		return passage.Traverse(P,W,G,dir)

# not called directly from user input
# called when the intended direction, destination, and/or passage is known
# redirects to one of three functions to perform the room change operation
def ExecuteGo(dobj,dir,dest,passage):
	print(dobj, dir, dest, passage)
	# if the input contains a dir, validate the dir...
	# and assign either the destination room name or passage name
	if dir != None:
		if dir in G.currentroom.exits:
			dest = G.currentroom.exits[dir]
		elif dir in G.currentroom.allExits():
			passage = G.currentroom.getPassageFromDir(dir)
		else:
			print(f"There is no exit leading {dir} here")
			return False

	# further assign passage and dest depending on if they are valid terms
	if passage == None and dobj != None:
		passage = G.currentroom.search(dobj)
	if passage == None and dobj in G.currentroom.exits.values():
	 	dest = dobj
	elif dobj in G.currentroom.allExits().values():
		dir = G.currentroom.getDirFromDest(dobj)
		passage = G.currentroom.getPassageFromDir(dir)

	# call one of three functions to actually change rooms
	# depends if they go normally, traverse a passage, or go vertically
	if dir == "up" or dir == "down":	return GoVertical(dir,passage,dobj)
	if hasMethod(passage,"Traverse"):	return passage.Traverse(P,W,G,dir)
	if dest != None:					return G.changeRoom(W[dest],P,W)
	print(f"There is no exit leading to a {dobj} here")
	return False

# parses user input to determine the intended direction, destination, and/or... # passage. Then calls ExecuteGo to actually carry out the action
def Go(dobj,iobj,prep):
	preps = {"down","through","to","toward","up","in","into","on","onto",None}
	if prep not in preps:
		print("Command not understood")
		return False
	dir,dest,passage = None,None,None

	if dobj == None and iobj == None and prep == None:
		dobj,iobj,prep = parseWithoutVerb("Where will you go?",preps)
	if dobj in cancels:	return False
	if dobj == None: dobj = iobj

	# if any terms are abbreviations for a direction, expand them
	dobj,iobj,prep = map(expandDir,[dobj,iobj,prep])
	if prep not in preps:
		print("Command not understood")
		return False

	# if any terms are a direction, set dir
	if dobj in directions.values():		dir,dobj = dobj,None
	elif iobj in directions.values():	dir = iobj
	elif prep in directions.values():	dir = prep
	if dobj == None:	dobj = iobj
	if dobj == "back":	dobj = G.prevroom.name

	return ExecuteGo(dobj,dir,dest,passage)

# add in the ability to try to 'grab' creatures?
def Grab(dobj,iobj,prep):
	if prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you grab?")
		if dobj in cancels:
			return False

	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' to grab here")
		return False

	G.setPronouns(I)
	if isinstance(I,Item):
		return Take(dobj,iobj,prep)
	elif isinstance(I,Creature):
		return Carry(dobj,iobj,prep)
	else:
		print(f"You cannot grab the {I.name}")
		return False

def Hide(dobj,iobj,prep):
	if prep not in {"behind","below","beneath","inside","under",None}:
		print("Command not understood")
		return False

	if dobj == None:	dobj = iobj
	if dobj == None:
		dobj = getNoun("What do you want to hide behind?")
		if dobj in cancels:
			return False

	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(I)
	if not isinstance(I,Fixture) or I.weight < 50:
		print("You can't hide behind " + I.name)
		return False

	P.addCondition("hiding",-3)
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
		if dobj in cancels:
			return False
	return Attack(dobj,"foot","with")

def Kill(dobj,iobj,prep):
	if prep not in {"with","using",None}:
		print("Command not understood")
		return False
	if dobj in {"myself","me"}:
		if yesno("Are you sure you want to kill yourself?"):
			P.death()
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
		if dobj in cancels:
			return False
	I = G.currentroom.search(dobj)
	if I == None: I = P.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False
	G.setPronouns(I)
	if not hasMethod(I,"Lock"):
		print(f"The {I.name} doesn't lock")
		return False

	if iobj == None:
		iobj = getNoun("What will you lock with?")
		if iobj in cancels:
			return False
	K = P.search(iobj)
	if K == None:
		print(f"There is no '{iobj}' in your inventory")
		return False
	if not isinstance(K,Key):
		print(f"You can't lock with the {K.name}")
		return False

	return I.Lock(K)

def Look(dobj,iobj,prep):
	if prep not in {"at","in","inside","into","on","through",None}:
		print("Command not understood")
		return False
	if dobj == None:	dobj = iobj
	if dobj == None:
		dobj = getNoun("What will you look at?")
		if dobj in cancels:
			return False

	if dobj in {"room", "here"}:
		G.currentroom.describe()
		return True
	if dobj in {"me","myself",P.name}:
		print("You are " + P.desc)
		return True
	L = G.currentroom.search(dobj)
	if L == None: L = P.search(dobj)
	if L == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(L)
	L.describe()
	if hasMethod(L,"Look"):
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
		if dobj in cancels:
			return False

	I = P.search(dobj)
	if I == None: I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Open"):
		print("You can't open the " + I.name)
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
		if dobj in cancels:
			return False

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False
	G.setPronouns(I)
	if not hasMethod(I,"Pour"):
		print(f"You can't pour the {I.name}")
		return False

	R = None
	if iobj != None:
		if iobj == "here":	R = G.currentroom
		R = P.search(iobj)
		if R == None:
			R = G.currentroom.search(iobj)
		if R == None:
			print(f"There is no '{iobj}' here")
			return False

	if prep == None:	prep = "on"
	if R != None:		print(f"You pour your {I.name} {prep} the {R.name}")
	else:				print(f"You pour out your {I.name}")
	I.Pour(P,G)
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
		if dobj in cancels:
			return False
	return Attack(dobj,"fist","with")

def Push(dobj,iobj,prep):
	print("pushing")

def Put(dobj,iobj,prep):
	if prep not in {"in","into","inside","on","onto","upon",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you put?")
		if dobj in cancels:
			return False
	if iobj == None:
		iobj = getNoun(f"What will you put your {dobj} in?")

	I,S = P.search(dobj,getSource=True)
	if I == None:
		print(f"There is no '{dobj}' in your inventory")
		return False
	if isinstance(I,Compass) and P.countCompasses() == 1:
		q = "Are you sure you want to lose your compass? You might get lost!"
		if not yesno(q):
			return False
	G.setPronouns(I)

	R = P.search(iobj)
	if iobj == "here":	R = G.currentroom
	if R == None:
		R = G.currentroom.search(iobj)
	if R == None:
		print(f"There is no '{iobj}' here")
		return False
	if not isinstance(R,Table) and not isinstance(R,Box):
		print(f"You can't put the {I.name} {prep} the {R.name}")
		return False

	outprep = "on" if isinstance(R,Table) else "in"
	if iobj == "here":	print(f"You put your {I.name} here")
	else:				print(f"You put your {I.name} {outprep} the {R.name}")
	S.removeItem(I)
	R.addItem(I)
	return True

def Release(dobj,iobj,prep):
	print("releaseing")

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
		if dobj in cancels:
			return False
	C = G.currentroom.search(dobj)
	if C == None:
		print(f"There is no '{dobj}' here")
		return False
	G.setPronouns(C)
	if not isinstance(C,Creature):
		print(f"You can't restrain the {C.name}")
		return False

	I = None
	if iobj != None:
		I = P.search(iobj)
		if I == None:
			print(f"There is no '{iobj}' in your inventory")
			return False
		if not hasMethod(I,"RestrainWith"):
			print(f"You can't restrain with the {I.name}")
			return False

	if not C.Restrain(P,I):
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

def Steal(dobj,iobj,prep):
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

def Take(dobj,iobj,prep):
	if prep not in {"from","in","inside","up",None}:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you take?")
		if dobj in cancels:
			return False
	if dobj in {"all","everything","it all"}:
		C = [item.name.lower() for item in G.currentroom.contents if not isinstance(item,Fixture)]
		taken = False
		for name in C:
			taken = Take(name,iobj,prep) or taken
		return taken

	I,path = objSearch(dobj,G.currentroom,d=2,getPath=True,reqSource=iobj)
	if I == None:	I,path = objSearch(dobj,P,d=2,getPath=True,reqSource=iobj)
	if I == None:
		if prep in {None,"up"}:	print(f"There is no '{dobj}' here")
		else:				print(f"There is no '{dobj}' in a '{iobj}' here")
		return False
	if not isinstance(I,Item):
		if isinstance(I, Creature):
			return Carry(dobj,iobj,prep)
		print("You can't take the " + dobj)
		return False
	G.setPronouns(I)

	S = path[0]		#S is the 'source' object, the object containing I
	if isinstance(S,Creature) and prep == "from":	return Steal(dobj,iobj,prep)
	count = S.contentNames().count(I.name)
	if S is P:
		print("You can't take from your own Inventory")
		return False

	if S is G.currentroom:		appendstring = ""
	elif P in path:				appendstring = " from your " + S.name
	else:						appendstring = " from the " + S.name
	det = "the" if count == 1 else "a"
	msg = f"You take {det} {I.name}{appendstring}"
	return P.obtainItem(I,S,W,G,msg)

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
		if dobj in cancels:
			return False

	I = P.inGear(dobj)
	if I == None:
		print(f"You do not have a '{dobj}' equipped")
		return False

	G.setPronouns(I)
	print(f"You unequip your {I.name}")
	P.unequip(I)
	return True

def Unlock(dobj,iobj,prep):
	if prep != "with" and prep != None:
		print("Command not understood")
		return False
	if dobj == None:
		dobj = getNoun("What will you unlock?")
		if dobj in cancels:
			return False
	I = G.currentroom.search(dobj)
	if I == None: I = P.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' here")
		return False
	G.setPronouns(I)
	if not hasMethod(I,"Lock"):
		print(f"The {I.name} doesn't lock")
		return False

	if iobj == None:
		iobj = getNoun("What will you unlock with?")
		if iobj in cancels:
			return False
	K = P.search(iobj)
	if K == None:
		print(f"There is no '{iobj}' in your inventory")
		return False
	if not isinstance(K,Key):
		print(f"You can't unlock with the {K.name}")
		return False

	return I.Unlock(K)

def Untie(dobj,iobj,prep):
	print("untieing")

def Use(dobj,iobj,prep):
	if dobj == None:
		dobj = getNoun("What will you use?")
		if dobj in cancels:
			return False

	I = P.search(dobj)
	if I == None:	I = G.currentroom.search(dobj)
	if I == None:
		print(f"There is no '{dobj}' to use here")
		return False

	G.setPronouns(I)
	if not hasMethod(I,"Use"):
		print(f"You can't use the {I.name}")
		return False
	I.Use(P,W,G)
	return True

def Wait(dobj,iobj,prep):
	print("waiting")

def Wave(dobj,iobj,prep):
	print("waveing")



##################################
## ACTION FUNCTION DICTIONARIES ##
##################################

cheatcodes = {
	"\\get":Get,
	"\\zap":Zap,
	"\\lrn":Learn,
	"\\mod":Mode,
	"\\pot":Pypot,
	"\\set":Set,
	"\\tst":Test,
	"\\tpt":Teleport,
	"\\wrp":Warp
}

shortactions = {
"abilities":P.printAbilities,
"back":Return,
"clear":clearScreen,
"cry":Cry,
"dance":Dance,
"examples":Examples,
"gear":P.printGear,
"help":Help,
"hp":P.printHP,
"info": Info,
"information": Info,
"inventory":P.printInv,
"inv":P.printInv,
"laugh":Laugh,
"level":P.printLV,
"lv":P.printLV,
"money":P.printMoney,
"mp":P.printMP,
"quit":Quit,
"return":Return,
"here":G.describeRoom,
"rp":P.printRP,
"save":Save,
"scream":Shout,
"shout":Shout,
"sing":Sing,
"stats":P.printStats,
"status":P.printStatus,
"time":Time,
"traits":P.printTraits,
"weapons":P.printWeapons,
"xp":P.printXP,
"yell":Shout,
"yawn":Yawn
}

actions = {
"attack":Attack,
"bite":Bite,
"break":Break,
"build":Craft,
"carry":Carry,
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
"enter":Go,
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
"grab":Grab,
"grapple":Grab,
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
"put down":Put,
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
