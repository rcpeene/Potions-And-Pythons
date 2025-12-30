# Core.py
# This file contains all core functions and classes used throughout the game
# This file is a dependency of Creatures.py, Items.py, Menu.py, and Interpreter.py
# and is dependent on Data.py

# It consists of three main parts;
# 1. Core functions			(used throughout gameplay)
# 2. Dialogue Classes		(DialogueNode and DialogueTree)
# 3. Core class definitions	(GameObject, Game, Room, Item, Creature, Player, etc.)


import sys, os, re, subprocess
import tempfile
import subprocess
import atexit
try:
	import msvcrt
	sys.stdout.reconfigure(encoding='utf-8')
except:
	import termios, select, tty, shlex

from time import sleep
from random import choice,choices,randint,sample,shuffle
from math import floor, sqrt
from bisect import insort

import Data




####################
## CORE FUNCTIONS ##
####################


# Used to determine if a term has a match with any of an object's names
def nameMatch(term,obj):
	if term is None or obj is None:
		return False
	term = term.lower()
	# print(term, obj.name, obj.nounPhrase(), obj.nounPhrase('the'))
	if isinstance(obj, Room):
		return term == obj.name.lower() or term in ["room"]
	return term == obj.name.lower() or \
		term == obj.nounPhrase().lower() or \
		term == obj.nounPhrase('the').lower() or \
		term in obj.aliases


# retrieves a class object with className from the modules list
# returns None if no such object exists
def strToClass(className,moduleNames):
	classObject = None
	for moduleName in moduleNames:
		try:
			classObject = getattr(sys.modules[moduleName],className)
		except:
			continue
	return classObject


# returns bool indicating whether an obj has a method with the given string name
# used as a shortcut for more readable code than the traditional method
def hasMethod(obj,methodName):
	possibleMethod = getattr(obj,methodName,None)
	if not possibleMethod:
		possibleMethod = getattr(obj.__class__,methodName,None)
	if possibleMethod != None and callable(possibleMethod):
		return True
	return False


# get key for a room in the world
def getRoomKey(room,world):
	for key,value in world.items():
		if value == room:
			return key


# clear screen on windows or unix systems
def clearScreen(delay=0.1):
	if os.name == "nt":
		os.system("cls")
		# ensure screen isn't being cleared during subsequent output
		sleep(delay)
	else:
		os.system("clear")


# clears pending keyboard input. strategy varies by operating system.
def flushInput():
	try:
		while msvcrt.kbhit():
			msvcrt.getch()
	except NameError:
		try:
			termios.tcflush(sys.stdin,termios.TCIOFLUSH)
		except termios.error:
			pass


# checks for any keyboard input in buffer
def kbInput():
	try:
		dr,dw,de = select.select([sys.stdin], [], [], 0.00001)
		return dr != []
	except:
		return msvcrt.kbhit()


# color text using ANSI formatting
def tinge(color,*args):
	if len(args) > 0 and color is not None:
		args = list(args)
		c = Data.colorCodes[color]
		args[0] = f"\033[{c}m" + args[0]
		args[-1] = args[-1] + f"\033[0m"
	return tuple(args)


# calculate lengths of displaying string by ignoring formatting chars
def displayLength(text):
	# Regular expression to match ANSI escape sequences
	# ansi_escape = re.compile(r"\033\[[0-9;]*m")
	l = len(ANSI_ESCAPE.sub("", text.replace("\n","")))
	return l


def formatColorCodes(text):
	for color,code in Data.colorCodes.items():
		text = text.replace(f"<{color}>",f"\033[{code}m")
	text = text.replace("<x>","\033[37m")
	return text


# print text to user, with options for color, delay, sep, end, and outfile
# also manipulates the output based on player status effects
def Print(*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,outfile=None):
	if (game.silent or player.hasStatus("asleep")) and allowSilent:
		return 0

	# set outfile, color, delay, sep
	if outfile is None:
		outfile = sys.stdout
	if player.hasStatus("apathy") and color != "k":
		color = "w"
	elif player.hasStatus("insanity") and color != "k" and outfile is sys.stdout:
		color = choices(list(Data.colorCodes.keys()),[1]*7 + [28])[0]
	if delay is None:
		if player.hasAnyStatus("dead","slowness"): delay = 0.03
		else: delay = 0.001
	if sep is None:
		sep=" " if len(args) > 1 else ""

	# preprocessing to handle conditions that affect text content
	args = [str(arg) for arg in args]
	if not player.canNavigate():
		args = [ambiguateDirections(arg) for arg in args]
	if player.hasStatus("stupidity") and color not in ('k','y'):
		args = [ambiguateNumbers(arg,grammatical=True) for arg in args]
		# don't misspell in stats sidepanel
		if outfile is sys.stdout:
			args = [misspell(arg) for arg in args]

	# save printLength for return, add color formatting
	printLength = sum(displayLength(s) for s in args) + \
		displayLength(sep)*(len(args)-1) + displayLength(end)
	if color is not None:
		args = tinge(color,*args)

	# output text
	if game.mode == 1 or delay is None or outfile is not sys.stdout:
		print(*args,end=end,sep=sep,file=outfile)
		return printLength
	sleep(delay)
	outfile.flush()
	for arg in args:
		for char in str(arg):
			# user keyboard input speeds up text output
			if kbInput() and not player.hasStatus("slowness"):
				delay = 0
			outfile.write(char)
			outfile.flush()
			sleep(delay)
		outfile.write(sep)
		outfile.flush()
	sleep(delay)
	outfile.write(end)
	outfile.flush()
	sleep(delay)
	return printLength


# waits for any keyboard input on windows and unix
def waitInput(text=None,end="\n",delay=None,color=None):
	sys.stdout.flush
	if text is not None:
		Print(text,end=end,delay=delay,color=color,allowSilent=False)
	# just pass if in test mode
	if game.mode == 1:
		return True
	flushInput()
	if os.name == 'nt':  # For Windows
		msvcrt.getch()
	else:  # For Unix-based systems
		fd = sys.stdin.fileno()
		old_settings = termios.tcgetattr(fd)
		try:
			tty.setraw(fd)
			sys.stdin.read(1)  # Wait for a single keypress
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# moves the print cursor nlines up or down, option to clear intervening lines
def movePrintCursor(nlines,clear=False,clearLast=True,outfile=None):
	if outfile is None:
		outfile = sys.stdout
	step = 1 if nlines > 0 else -1  # direction
	for i in range(abs(nlines)):
		# Move one line in the desired direction
		if step > 0:
			outfile.write("\033[1A")  # up one line
		else:
			outfile.write("\033[1B")  # down one line
		outfile.flush()

		# Clear that line if requested
		if clear and (clearLast or i != abs(nlines)-1):
			outfile.write("\r\033[2K")
			outfile.flush()

	# Make sure cursor is at start of final destination line
	outfile.write("\r")
	outfile.flush()


# print prompt, print cue, and read in user input
def Input(prompt="",cue="\n> ",low=True,delay=None,color=None):
	sys.stdout.flush()
	# should never be silent when asking for input
	Print(prompt,end="",delay=delay,color=color,allowSilent=False)
	Print(cue,end="",delay=0,color=color,allowSilent=False)
	ret = input()
	if low:
		ret = ret.lower()
	return ret


# gets input with a prompt and a cue, locks the line and repeats until accepted
def InputLock(prompt="",cue="\n> ",acceptKey=None,low=True,delay=None,color=None):
	if acceptKey is None:
		acceptKey = lambda inp: inp.strip()
	cueLines = cue.count("\n")+1 # account for the newline from input

	Print(prompt,end="",delay=delay,color=color,allowSilent=False)

	# leave an aesthetic buffer so the cue is never at the very bottom of the screen
	print("\n"*cueLines,end="")
	movePrintCursor(cueLines,clear=True,clearLast=False)

	while True:
		sys.stdout.flush()
		inp = Input(prompt="",cue=cue,low=low,delay=delay,color=color)
		if acceptKey(inp):
			return inp
		flushInput()
		movePrintCursor(cueLines,clear=True,clearLast=False)


# loops until input is cancelled by user or accepted, provides informative messages
def InputLoop(prompt,cue="> ",acceptKey=None,escapeKey=None,refuseMsg="",
			  helpMsg="Type 'cancel' to undo.",color=None,delay=None):
	if acceptKey is None:
		acceptKey = lambda inp: inp
	if escapeKey is None:
		escapeKey = lambda inp: inp in Data.cancels
	if refuseMsg != "":
		refuseMsg += "\n"
	if helpMsg != "":
		helpMsg += "\n"

	invalid_count = 0
	inp = InputLock(prompt,"\n"+cue,color=color,delay=delay)
	while True:
		if escapeKey(inp):
			return None
		acceptInp = acceptKey(inp) 
		if acceptInp is not None:
			return acceptInp
		Print(refuseMsg,end="",color="k",delay=delay)
		invalid_count += 1
		if invalid_count == 2:
			# Print(helpMsg,color="k",delay=delay)
			refuseMsg = refuseMsg + helpMsg
		inp = InputLock("",cue,color=color,delay=delay)


# prints a question, loops until user answers yes or no, returns True/False
def yesno(question,delay=None,color=None):
	def acceptKey(inp):
		if inp in Data.yesses:
			return True
		elif inp in Data.noes:
			return False
		else:
			return None
	refuseMsg = "Enter yes or no."
	return InputLoop(question,acceptKey=acceptKey,escapeKey=None,helpMsg="",
	refuseMsg=refuseMsg,color=color,delay=delay)


# print delay and flushes any intervening input
def delay(seconds):
	flushInput()
	sleep(seconds)
	flushInput()


# prints a timed ellipsis, used for dramatic transitions
def ellipsis(n=3,color=None):
	for _ in range(n):
		delay(1)
		Print(".",color=color,delay=0,allowSilent=False)
	delay(1)


# prints a list of strings, l, into n columns of width w characters
# if an element is longer than one column, it takes up as many columns as needed
# b is the number of buffer spaces between columns
def columnPrint(l,n,w=None,b=1,delay=0,color=None,inplace=False,outfile=None):
	# automatically set column width based on longest item
	termLengths = [displayLength(term)+b for term in l]
	if w is None:
		w = max(termLengths)+b
	assert w > 1

	nRowsPrinted = 1
	# k is the number of characters that have been printed in the current row
	k = 0
	# for each string element in l
	for term, length in zip(l,termLengths):
		# all terms are trailed by b buffer spaces
		buf = (" "*b)
		# if the string is longer than remaining row width
		# print on a new row
		if length > (n*w) - k:
			if inplace:
				movePrintCursor(-1,outfile=outfile)
				newline=""
			else:
				newline="\n"
				nRowsPrinted += 1
			k = Print(newline+term+buf,end="",delay=delay,color=color,outfile=outfile)
		# if the string is short enough, print it, increment k
		else:
			k += Print(term+buf,end="",delay=delay,color=color,outfile=outfile)
		# to preserve column alignment, print spaces until k is divisble by w
		spaces = (-k % w)
		k += Print(spaces * ' ',end="",delay=delay,color=color,outfile=outfile)
	if not inplace:
		Print(outfile=outfile)
	return nRowsPrinted


# capitalizes the first letter of all the words in a string
# if c is given, then only capitalize the first c words
def capWords(string,c=-1):
	listString = string.split(' ')
	cappedString = ''
	for idx,word in enumerate(listString):
		if len(word) > 0:
			if c != -1 and idx < c:
				cappedString += word[0].upper() + word[1:] + ' '
			else:
				cappedString += word + ' '
	# removes trailing space character
	return cappedString[0:-1]


# gets first index encountered of any substrings within text
# returns end of text if none found
def findFirst(text,substrs):
	idxs = [text.find(substr) for substr in substrs]
	idxs = [i for i in idxs if i != -1]
	if not idxs:
		return len(text)
	return min(idxs)


# uses first word of verbString (assumes its a verb) and conjugates it based on noun
def conjugate(noun,verbString):
	irregulars = (('has','have'),('is','are'),("isn't","aren't"),('was','were'))
	sibilants = ("s","sh","ch","x","z","o")

	# get the first word (assumed to be a verb) that begins verbString
	if verbString.startswith(" "):
		verbString = verbString[1:]
	firstWordEnd = findFirst(verbString,tuple(" .,!?"))
	verb = verbString[:firstWordEnd]
	remainder = verbString[firstWordEnd:]
	assert len(verb) > 1

	# conjugate to infinitive form
	if noun.lower() in ("you","they"):
		# irregular verbs (is -> are)
		for thirdPerson,infinitive in irregulars:
			if verb == thirdPerson:
				return infinitive + remainder
		# flies -> fly
		if verb.endswith("ies") and len(verb) > 3:
			return verb[:-3] + "y" + remainder
		# mixes, mashes, goes -> mix, mash, go
		elif verb.endswith("es") and verb[:-2].endswith(sibilants):
			return verb[:-2] + remainder
		# runs -> run, but kiss -> kiss
		elif verb.endswith("s") and not verb.endswith("ss"):
			return verb[:-1] + remainder
		# run, fly, mix -> run, fly, mix
		else:
			return verb + remainder

	# conjugate to third-person singular form
	else:
		# irregular verbs (is -> are)
		for thirdPerson,infinitive in irregulars:
			if verb == infinitive:
				return thirdPerson + remainder
		# flies, runs, mixes -> flies, runs, mixes
		if verb.endswith("s"):
			return verb + remainder
		# fly -> flies
		if verb.endswith("y") and verb[-2] not in "aeiou":
			return verb[:-1] + "ies" + remainder
		# mix, mash, go -> mixes, mashes, goes
		elif verb.endswith(sibilants):
			return verb + "es" + remainder
		# run -> runs
		else:
			return verb + "s" + remainder


# returns the ordinal string for a number n
def ordinal(n):
	lastDigit = n % 10
	if lastDigit == 1: return str(n)+"st"
	elif lastDigit == 2: return str(n)+"nd"
	elif lastDigit == 3: return str(n)+"rd"
	else: return str(n)+"th"


# cleans a string by remove trailing symbols and lowercasing
def clean(string):
	return string.lower().rstrip(Data.symbols) if string else None


# helper for ambiguateDirections() when removing strings but want to keep grammar structure
# takes a list of strings and a given index
# lends the capitalization/punctuation of given string to following/preceding strings,
# then removes the string at given index
def subsume(lst,idx):
	# lend punctuation to previous string
	if idx > 0 and lst[idx][-1] in Data.symbols:
		if lst[idx-1][-1] in Data.symbols:
			lst[idx-1] = lst[idx-1][:-1]
		lst[idx-1] += lst[idx][-1]
	# lend capitalization to following string
	if idx < len(lst)-1 and lst[idx][0].isupper():
		lst[idx+1] = lst[idx+1].capitalize()
	lst.pop(idx)


# replaces directional terms in text with ambiguous alternatives
def ambiguateDirections(text):
	directions = Data.cardinals # north, northeast, southeast etc.
	wards = tuple(dir+"ward" for dir in directions) + \
		tuple(dir+"wards" for dir in directions)
	erns = tuple(dir+"ern" for dir in directions)
	unknownDirs = ("some direction","one way","in a certain direction","up ahead",
	"a ways away","far off","over yonder","elsewhere")
	additionalUnknownDirs = ("another direction","some other way","the other way",
	"behind","also ahead")
	adjectivalUnknownDirs = ("the nearby","the far","the left","the right")
	# prepositions that precede directions, e.g. "from the north"
	dirPreps = {"of","from","to","toward","into","on","in","at","by","across","along"}
	# words that follow directional nouns, e.g. "Eastward, stands a window"
	followsNounDir = {"there","theres","is","are","lie","stand","rise","begin","stretch",
	"extend","run","rest","reach","flow"}

	# Assume a token t1 is a noun if it ends with punctuation or t2 is a relevant verb
	def dirIsNoun(t1,t2):
		return t1[-1] in Data.symbols or clean(t2).endswith("s") or \
			clean(t2) in followsNounDir|dirPreps

	lastChoice = None
	replacedYet = False
	# get random string to replace old tokens, but keep the capitalization/punctuation
	# for textual flavor, add more unknownDirs after first replacement
	def getReplacement(oldTokens,newOptions):
		nonlocal replacedYet, lastChoice, unknownDirs, additionalUnknownDirs
		newToken = choice(newOptions)
		# ensure replacement is different from last
		while newToken == lastChoice:
			newToken = choice(newOptions)
		lastChoice = newToken
		# preserve capitalization and punctuation
		if oldTokens[0][0] == oldTokens[0][0].upper():
			newToken = newToken.capitalize()
		if oldTokens[-1][-1] in Data.symbols:
			newToken += oldTokens[-1][-1]
		# after we've replaced one direction, we can use additional phrases
		if not replacedYet and newOptions is unknownDirs:
			unknownDirs += additionalUnknownDirs
			replacedYet = True
		return newToken

	# Loop over stream three tokens tracked at a time, replacing or removing as needed
	# First we simplify the token stream; cases 0-5
	# Then replace directions with phrases depending if its noun or adjective; cases 6-7
	# Since we only iterate when no replacements are made, 
	# the triplet of tokens is fully simplified before they are replaced
	i = 0
	tokens = text.split(" ")
	while i < len(tokens):
		if i < 0: i = 0
		t0 = tokens[i]
		t1 = tokens[i+1] if i+1 < len(tokens) else None
		t2 = tokens[i+2] if i+2 < len(tokens) else None
		# print(i,t0,t1,t2)
		# 0. Remove adjectives; "the far northern" -> "the northern"
		if clean(t0) == "the" and clean(t2) in directions+wards+erns:
			subsume(tokens,i+1)
			i -= 1
		# 1. Simplify terms; "northward(s)" -> "north"
		elif clean(t2) in wards:
			tokens[i+2] = t2.replace("wards","").replace("ward","")
		# 2. Remove adjectival 'erns'; "a northern window" -> "a window"
		elif clean(t2) in erns:
			subsume(tokens,i+2)
		# 3. Reduce lists; "north and east" -> "north east"
		elif clean(t1) in directions and clean(t2) == "and":
			subsume(tokens,i+2)
		# 4. Reduce lists; "North, east, west" -> "West"
		elif clean(t1) in directions and clean(t2) in directions:
			if tokens[i+1][-1] in Data.symbols:
				tokens[i+1] = tokens[i+1][:-1]
			subsume(tokens,i+1)
		# 5. Remove determiner; "to the north" -> "to north"
		elif clean(t1) == "the" and clean(t2) in directions:
			subsume(tokens,i+1)
		# 6. NOUN "to north, a window..." -> "in a certain direction, a window..."
		# "to north lies a window" -> "in a certain direction lies a window"
		elif clean(t1) in directions and dirIsNoun(t1,t2):
			tokens[i+1] = getReplacement((tokens[i+1]),unknownDirs)
			if clean(t0) in dirPreps:
				subsume(tokens,i)
		# 7. ADJECTIVE "the north side" -> "a nearby side"
		elif clean(t1) in directions:
			tokens[i+1] = getReplacement((tokens[i+1],),adjectivalUnknownDirs)
		# TODO: may need a case for removing the direction when it is followed by a dirPrep
		# 'a brook flows from the east into a pond' -> 'a brook flows into a pond'
		else:
			i += 1
		# print(tokens)

	return " ".join([t for t in tokens if t is not None])


# replaces numbers in text with ambiguous alternative words
def ambiguateNumbers(text,grammatical=False):
	text = str(text)
	# capture the number and the preceding non-whitespace character (if any)
	# don't match ordinals (1st, 2nd, 3rd, 4th, etc)
	pattern = r'(?:(?P<prev>[^\d\s]))?\s*(?P<num>\d+)(?!st|nd|rd|th)'

	replacementMap = {
		"none": ("no","zero","not any"),
		"two": ("two","a couple","a pair of"),
		"few": ("a few","not many","a small amount of"),
		"some": ("some","several","an amount of"),
		"many": ("many","a lot of","a bunch of","a big amount of"),
		"a ton": ("a ton of","a whole lot of","a really big amount of")
	}
	# when printing stats, don't use random selections
	if not grammatical:
		replacementMap = {k:(k,) for k in replacementMap}

	def repl(match):
		prev = match.group("prev")
		num = int(match.group("num"))

		# if number was in an ANSI escape sequence, ignore it
		if prev in ("[","\\",";"):
			return match.group(0)
		elif num == 0:
			replacement = choice(replacementMap["none"])
		elif num == 1:
			replacement = "one"
		elif num == 2:
			replacement = choice(replacementMap["two"])
		elif num > 2 and num < 6:
			replacement = choice(replacementMap["few"])
		elif num >= 6 and num < 15:
			replacement = choice(replacementMap["some"])
		elif num <= 60:
			replacement = choice(replacementMap["many"])
		else:
			replacement = choice(replacementMap["a ton"])

		# capitalize only if preceding non-whitespace char is . ! ?
		if (prev is None or prev in ".!?") and grammatical:
			replacement = replacement.capitalize()
		# §10 -> "some money"
		if prev == "§" and grammatical:
			replacement += " money"
			return replacement

		# concatenate previous char, any whitespace, and replacement
		textBeforeNum = match.group(0)[:-len(match.group("num"))]
		replacement = textBeforeNum + replacement
		return replacement

	return re.sub(pattern, repl, text)


# introduces common misspellings into text
def misspell(text):
	replacementMap = {
		"to":"too", "too":"to", "there":"their", "where":"wear", "sword":"sord",
		"library":"libary", "higher":"hire", "break":"brake", "window":"windo",
		"above":"abuv", "python":"pithon"
	}
	def getReplacement(oldToken):
		newToken = replacementMap[clean(oldToken)]
		if oldToken[0].isupper():
			newToken = newToken.capitalize()
		if any(oldToken.endswith(s) for s in Data.symbols):
			newToken += oldToken[-1]
		return newToken

	# chance to replace predetermined words with common misspellings
	tokens = text.split(" ")
	i = 0
	while i < len(tokens):
		if clean(tokens[i]) in replacementMap and randint(0,3) == 0:
			tokens[i] = getReplacement(tokens[i])
		i += 1
	text = " ".join(tokens)

	# used to exclude None when concatenated chars
	def cat(*parts):
		return "".join(p for p in parts if p)

	# for every character, chance to make a common misspelling
	i = 0
	while i < len(text):
		if i < 0: i = 0
		t0 = text[i]
		t1 = text[i+1] if i+1 < len(text) else None
		t2 = text[i+2] if i+2 < len(text) else None

		# 25% chance of misspelling
		if randint(0,3) != 0:
			i += 1
			continue
		# print(text+"\n",i,t0,t1,t2,"\n")
		match (t0,t1,t2):
			# double letter -> single letter
			case (x,y,z) if x ==y and x in "sltfrmnbdcz": repl = cat(x,z)
			# oor -> or
			case ("o","o","r"): repl = "or"
			# ore -> or
			case ("o","r","e"): repl = "or"
			# ie -> ei
			case ("i","e",z): repl = cat("ei",z)
			# ea -> ee
			case ("e","a",z) if z not in ("d"," ",None): repl = cat("ee",z)
			# ais -> aze
			case ("a","i","s"): repl = "aze"
			# air,ain,aid -> are,ane,ade
			case ("a","i",z) if z in ("d","l","m","n","p","r"): repl = cat("a",z,"e")
			# ign -> ine
			case ("i","g","n"): repl = "ine"
			# th[End] -> the[End]
			case ("t","h",z) if z in (" ",None): repl = cat("the",z)
			# gh[Vowel] -> w[Vowel]
			case ("g","h",z) if z in Data.vowels: repl = cat("w",z)
			# ght -> te
			case ("g","h","t"): repl = "te"
			# dge -> j
			case ("d","g","e"): repl = "j"
			# dgy -> jy
			case ("d","g",z) if z in ("i","y"): repl = cat("j",z)
			# age -> aje
			case ("a","g","e"): repl = "aje"
			# ue[End] -> ew[End]
			case ("u","e",z) if z in (" ",None): repl = cat("ew",z)
			# u[Vowel] -> w[Vowel] (except not gua or nue)
			case (x,"u",z) if x not in ("n","g") and z in Data.vowels: repl = cat(x,"w",z)
			# ou -> ow
			case ("o","u",z) if z not in ("g"," ",None): repl = cat("ow",z)
			# oi -> oy
			case ("o","i",z): repl = cat("oy",z)
			# ph -> f
			case ("p","h",z): repl = cat("f",z)
			# tio -> shu
			case ("t","i","o"): repl = "shu"
			# tch -> ch
			case ("t","c","h"): repl = "ch"
			# ce -> se
			case (a,"c","e"): repl = a+"se"
			# ck -> k
			case (a,"c","k"): repl = a+"k"
			# c -> k
			case ("c",y,z) if y not in ("e","h","k") and randint(0,1): repl = cat("k",y,z)
			# wr -> r
			case ("w","r",z): repl = cat("r",z)
			# wh -> w
			case ("w","h",z): repl = cat("w",z)
			# default case
			case (x,y,z): repl = cat(x,y,z)

		text = text[:i] + repl + text[i+3:]
		i += 1
	return text


# returns an abbreviated direction into an expanded one
# for example, converts 'nw' -> 'northwest' or 'u' -> 'up'
def expandDir(term):
	if term in Data.directions:
		return Data.directions[term]
	else:
		return term


# returns list of (obj,n) where n is the count of object in objects
# uses equivKey to determine object equivalence for counting
def bagObjects(objects,equivKey=None):
	if equivKey is None:
		equivKey = lambda obj: obj.nounPhrase()
	bag = []
	for obj in objects:
		for entry in bag:
			if equivKey(entry[0]) == equivKey(obj):
				entry[1] += 1
				break
		else:
			bag.append([obj,1])
	return bag


# takes a prepend string and list of objects
# converts list of objects to a bag of (obj,count) pairs
# returns a string that grammatically lists all strings in names
def listObjects(prepend,objects,append=""):
	objBag = bagObjects(objects)
	liststring = ""
	l = len(objBag)
	for i, (obj, count) in enumerate(objBag):
		if i == l-1:
			liststring += obj.nounPhrase(det="a",n=count)
		elif i == l-2:
			liststring += obj.nounPhrase(det="a",n=count) + " and "
		else:
			liststring += obj.nounPhrase(det="a",n=count) + ", "
	liststring = prepend + liststring
	liststring += append

	if player.hasStatus("stupidity"):
		liststring = ambiguateNumbers(liststring,grammatical=True)
	return liststring


# used on room area conditions to extract the info of the condition it causses
def extractConditionInfo(roomCondition):
	condInfo = roomCondition.split(" ")
	assert len(condInfo) >= 3 and condInfo[0] in ("AREA","CREATURE","ITEM")

	key = condInfo[0]
	if key == "CREATURE":
		key = lambda x: isinstance(x,Creature)
	elif key == "ITEM":
		key = lambda x: not isinstance(x,Creature) and isinstance(x,Item)
	else:
		key = lambda x: True

	name = ' '.join(condInfo[1:-1])
	dur = int(condInfo[-1])
	return key,name,dur


# returns a number, n, with a lower bound of 0
def min0(n): return 0 if n < 0 else n


# returns a number, n, with a lower bound of 1
def min1(n): return 1 if n < 1 else n


# returns a number n, bounded by lo and hi
def bound(n,lo,hi): return lo if n < lo else (hi if n > hi else n)


# rolls n dice of range d, adds a modifier m, returns int >= 1
def diceRoll(n,d,m=0):
	if d < 1:
		n = 0
	x = sum(randint(1,d) for _ in range(n))
	return min1(x+m)


def roll(d,m=0):
	return diceRoll(1,d,m)


# rolls a number between d//2 and d, adds m
def halfRoll(d,m=0):
	return roll(d//2,m+d//2)


# has a p percent chance of returning True
def percentChance(p):
	return randint(1,100) <= p



# the Room, Creatures, and some Items can contain Items within themselves
# thus all objects within a room can be thought of as a tree
# where each node is an item or creature, and the root is the Room
# the player object can also be thought of this way where the player is the root
# this function recursively queries the tree of objects for those that pass the given key
# the object tree might look as follows:
#           _____Room_____
#         /     /    \     \
#     cat  trunk   sword  wizard
#    /     /   \         /   |   \
# bell lockbox candle potion wand scroll
#        |
#     saffron
# d is the 'degree' of the query; how thorough it is
# if d is 0: looks in objects which are not "closed" and not in creature inventories
# i.e. "visible" to the player (only cat, trunk, sword, wizard)
# if d is 1: look in objects that are not locked and not in creature inventories
# i.e. objects which are "available" to the player (also lockbox, candle)
# if d is 2: looks in all objects which are not locked
# i.e. objects which are "accessible" to the player (also bell, potion, wand, scroll)
# if d is 3: looks in all objects from the root  (also saffron)

# this function is a wrapper for objQueryRecur()
def objQuery(root,key=None,d=0):
	if key is None: key = lambda obj:True
	matches = set()
	if key(root):
		matches.add(root)
	matches = objQueryRecur(root,matches,key,d)
	return matches

# recurs through all objects within node, adds them to matches if supplied key is True
# d is the degree of the query, see objQuery() comments above for details
def objQueryRecur(node,matches,key,d):
	for obj in node:
		# check if obj is a match
		if key(obj): matches.add(obj)
		# depending on the degree, dont query into closed, Creature or locked objects
		if d == 0 and hasattr(obj,"closed") and obj.closed: continue
		elif (d <= 1) and isinstance(obj,Creature): continue
		elif d <= 2 and hasattr(obj,"locked") and obj.locked: continue
		# recur the query on each object's subtree
		matches = objQueryRecur(obj,matches,key,d)
	return matches


# recurs through objects within the parent and assigns it as their parent
def assignRefsRecur(parent):
	for obj in parent:
		if obj in celestials:
			continue
		# everything in the world or player inv should be Item or Creature
		assert isinstance(obj, (Item, Creature)), \
		f"Object {obj} is type {type(obj)} not Item or Creature"
		obj.assignRefs(parent)
		assignRefsRecur(obj)


# removes any room links pointing to rooms which don't exist in the world,
# to prevent errors if the world file was written incorrectly
# also assigns references for all world objects (parent, occupants, cover, carrying etc.)
# also assigns dialogue trees for speakers and validates them
def buildWorld():
	# assign all room links to existing rooms
	# ensure all room names are stored as lowercase
	for roomName in list(world.keys()):
		room = world[roomName]
		del world[roomName]
		assert room.name.lower() == roomName, f"Room name {room.name.lower()} does not " \
		f"match its key in world dict {roomName}"
		assert room.name.lower() not in world, f"Room name {room.name.lower()} " \
		"already exists in world"
		world[room.name.lower()] = room

	# register all objects that already have an ID
	for room in world.values():
		for obj in room.objTree():
			if obj.id is not None:
				game.registerItem(obj)

	# assign IDs to global celestial objects
	for celestial in celestials:
		if celestial.id is None:
			celestial.id = game.getNextID()
			game.registerItem(celestial)

	# assign IDs to all Items and Creatures that don't have one
	for room in world.values():
		for obj in room.objTree():
			if obj.id is None:
				obj.id = game.getNextID()
				game.registerItem(obj)

	# assign references for all rooms and objects, and assign dialogue trees
	for room in world.values():
		assert isinstance(room, Room)
		room.assignRefs()
		assignRefsRecur(room)

		# assign the dialogue trees for all Creatures and validate them
		for creature in objQuery(room, d=3, key=lambda x: isinstance(x,Speaker)):
			creature.buildDialogue()



#############
## LOGGING ##
#############


# A secondary text window used to display static text which can be updated
class SidePanel:
	# store OS type ('nt' for Windows, 'posix' for Linux/Mac)
	OSname = os.name

	def __init__(self,width=50,height=25):
		self.title = ""
		self.width = width
		self.height = height
		self.pipePath = None
		self.pipe = None
		self.process = None


	### Process Handling ###

	def isOpen(self):
		return self.process is not None and self.process.poll() is None


	def open(self, title=""):
		if self.isOpen():
			Print(f"{self.title} side panel is already open.",color="k")
			return False
		self.title = title
		if SidePanel.OSname == "nt":
			self.openWindows()
		elif sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
			self.openUnix()
		else:
			raise OSError("Unsupported OS")


	def openWindows(self):
		pipe_dir = tempfile.gettempdir()
		self.pipePath = os.path.join(pipe_dir, f"sidepanel_{os.getpid()}.txt")
		open(self.pipePath, "w", encoding="utf-8").close()
		self.pipe = open(self.pipePath, "w", buffering=1, encoding="utf-8")
		# escape any spaces in the path
		safe_path = f'"{self.pipePath}"'

		# write batch file with @echo off and Quick Edit disabled
		batch_cmd = (
			f'@echo off\n'
			f'chcp 65001 >nul\n'
			f'title {self.title}\n'
			f'mode con: cols={self.width} lines={self.height}\n'
			f':loop\n'
			f'cls\n'
			f'type {safe_path}\n'
			f'timeout /t 1 >nul\n'
			f'goto loop\n'
		)
		bat_file = os.path.join(pipe_dir, f"sidepanel_{os.getpid()}.bat")
		with open(bat_file, "w", encoding="utf-8") as f:
			f.write(batch_cmd)
		# launch cmd directly, not via "start"
		self.process = subprocess.Popen(
			["cmd", "/K", bat_file],
			creationflags=subprocess.CREATE_NEW_CONSOLE,
		)


	def openUnix(self):
		self.pipePath = os.path.join(tempfile.gettempdir(), 
		f"sidepanel_{os.getpid()}.txt")
		self.pipe = open(self.pipePath, "w", buffering=1, encoding="utf-8")

		cmd = (
			f"xterm -T {shlex.quote(self.title)} "
			f"-geometry {self.width}x{self.height} "
			f"-e bash -c 'clear; tail -f {shlex.quote(self.pipePath)}'"
		)
		self.process = subprocess.Popen(cmd, shell=True)
		sleep(0.5)


	def close(self):
		if not self.isOpen():
			return False
		if self.pipe:
			self.pipe.close()
			self.pipe = None
		if self.process:
			if SidePanel.OSname == "nt":
				subprocess.call(
					f'taskkill /FI "WINDOWTITLE eq {self.title}" /F >nul 2>&1',
					shell=True
				)
			else:
				self.process.terminate()
			self.process = None
		if self.pipePath and os.path.exists(self.pipePath):
			try:
				os.remove(self.pipePath)
			except Exception:
				pass


	### I/O Handling ###

	def write(self, text=""):
		if self.pipe:
			self.pipe.write(str(text))


	def flush(self):
		return
		# if self.pipe:
		# 	self.pipe.flush()


	def clear(self):
		if SidePanel.OSname == "nt":
			if self.pipe:
				self.pipe.seek(0)
				self.pipe.truncate()
		else:
			if self.pipe:
				self.pipe.seek(0)
				self.pipe.truncate()


sidepanel = SidePanel()

def cleanup():
    if sidepanel.isOpen():
        sidepanel.close()
atexit.register(cleanup)

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;?]*[ -/]*[A-Za-z]')


# Descriptor that will write both to the terminal and to a log file
class TeeLogger:
	def __init__(self,logFile,inputFile=None):
		self.terminal = sys.stdout
		self.originalStdin = sys.stdin
		self.errorTerminal = sys.stderr
		os.makedirs(os.path.dirname(logFile),exist_ok=True)
		self.log = open(logFile,"w",encoding="utf-8", errors="replace")
		self.stdin = open(inputFile,"r") if inputFile else self.originalStdin
		self.logbuffer = ""


	def setInputFile(self, inputFilename):
		if self.stdin != self.originalStdin:
			self.stdin.close()
		self.stdin = open(inputFilename,"r")


	# if the buffer gets too long for whatever reason, we try to clean it and drain
	def forceDrainBuffer(self):
		cleanBuffer = ANSI_ESCAPE.sub('', self.logbuffer)
		self.log.write(cleanBuffer)
		self.log.flush()
		self.logbuffer = ""


	# in this game, text is typically printed one-character-at-a-time
	# we don't want ansi escape sequences appearing in the log, 
	# so we accumulate characters in a buffer and flush it at every newline
	def drainBufferToNewline(self):
		newline = self.logbuffer.find('\n')
		if newline == -1:
			return
		line = self.logbuffer[:newline]
		cleanLine = ANSI_ESCAPE.sub('', line)
		self.log.write(cleanLine + '\n')
		self.log.flush()
		self.logbuffer = self.logbuffer[newline + 1:]


	# write text to terminal, accumulate text in log buffer, flush at newlines
	def write(self, message):
		self.logbuffer += message
		while '\n' in self.logbuffer:
			self.drainBufferToNewline()
		if len(self.logbuffer) > 3000:
			self.forceDrainBuffer()
		self.terminal.write(message)
		self.terminal.flush()


	def write_error(self,message):
		self.forceDrainBuffer()
		self.errorTerminal.write(message)


	def readline(self):
		self.forceDrainBuffer()
		input_text = self.stdin.readline()
		if len(input_text.strip()) > 0:
			self.log.write(input_text)
			self.log.flush()
		return input_text


	def flush(self):
		self.terminal.flush()
		self.log.flush()



######################
## DIALOGUE CLASSES ##
######################



# it is recommended to read the notes for DialogueTree below first
# in addition to having children, nodes in the tree may have a few important parameters;
# nodes may contain either a remark or a list of 'trites' from which to generate dialogue
# - a remark is a simple line of output dialogue. A trite is the name of a 'triteset'
# - tritesets are sets of predetermined remarks that can be sampled by many speakers
# the node may also contain either a list of 'cases' or 'replies' to correspond to children
# - cases is a list of boolean expressions which can access the game's global objects
# - instead of a boolean expression, a case may be an integer representing a probability
# - replies is a list of replies that the user may choose from during dialogue
# the child that is traversed is determined by the first true case or the chosen reply

# guard criteria:
# nodes may have a 'visitLimit', to ensure dialogue is not repeated in one 'parley'
# nodes may have a 'rapportReq' that requires a certain 'rapport' with the speaker
# in addition to these, nodes can have a special 'guardCase' expression preventing traversal

# side effects:
# reaching certain nodes can modify certain external values, such as:
# - modfying the listener's love, fear, or reputation stats
# - adding to the speaker's memories set or the game's events set
# nodes may be marked as checkPoints; they will be saved by the tree as a return point

# traversal:
# The Dialogue Tree object will traverse each main branch node of the tree in order,
# calling branch.visit() until one traversal yields some output
# each node visit is as follows;
# 	output this nodes output (remark or trite) if it has any
#	then try to 'hop' to each child node (using cases or replies if they're present)
#	child nodes will fail the hop if it fails any guard criteria,
#	if child passes the hop, then stop hopping and select this as next node
#	then evoke any side effects this node has
#	then return the selected child for traversal by the tree 
#	if no children were selected, None will be returned to the tree
class DialogueNode():
	def __init__(self,parent,label,idx,lastTriteRemark=None,visitLimit=None,
	rapportReq=None,guardCase="True",isCheckpoint=False,loveMod=0,fearMod=0,repMod=0,
	memories=None,events=None,remark=None,trites=None,cases=None,replies=None,
	children=[],reactTrue=False):
		self.parent = parent
		self.label = label
		# id is actually the path from root to node, stored as a tuple of indices
		self.id = self.parent.id + (idx,)
		self.lastTriteRemark = lastTriteRemark
		self.visitLimit = visitLimit
		self.guardCase = guardCase
		self.rapportReq = rapportReq
		self.isCheckpoint = isCheckpoint
		self.children = [DialogueNode(self,label,i,**childJson) for i,childJson in enumerate(children)]

		### the following are effects that visiting the node will have

		# these modify speaker stats
		self.loveMod=loveMod
		self.fearMod=fearMod
		self.repMod=repMod
		# this adds memory to speaker memories
		self.memories = set() if memories is None else memories
		if type(memories) is list:
			self.memories = set(memories)
		elif type(memories) is str:
			self.memories = {memories}
		for memory in self.memories:
			assert type(memory) is str
		# events set is used to add to game events
		self.events = set() if events is None else events
		if type(events) is list:
			self.events = set(events)
		elif type(events) is str:
			self.events = {events}
		for event in self.events:
			assert type(event) is str

		### the following are possible dialogue outputs from visiting the node

		# this is a basic output dialogue remark
		self.remark = remark
		# these are names of sets of strings in Dialogue.json, containing 'canned' dialogue
		self.trites = [] if trites is None else trites
		if type(self.trites) is not list:
			self.trites = [trites]
		for trite in self.trites:
			assert type(trite) is str
		# should only be used for terminal nodes in 'reactions' branch of tree
		# meant so dialogue tree can be used to determine if speaker's reaction is 'True'
		# e.g. if a speaker refuses or accepts a player's 'Give' action
		self.reactTrue = reactTrue
		if self.reactTrue: assert len(self.children) == 0

		### the following are mechanisms to determine which child to branch to traverse

		# these are strings of python code which should evaluate to a bool or int
		self.cases = [] if cases is None else cases
		# these are the optional Player replies to the dialogue
		self.replies = [] if replies is None else replies
		# ensure the number of child nodes matches the cases or replies
		if self.cases:
			if type(self.cases) is not list:
				self.cases = [self.cases]
			# one extra child for when all cases are false
			assert len(self.children) == len(self.cases) + 1
		elif self.replies:
			if type(self.replies) is not list:
				self.replies = [self.replies]
			assert len(self.children) == len(self.replies)

		# ensure node doesn't have both a remark and a trite set
		assert self.remark is None or self.trites == []
		# ensure node doesn't have both conditional cases and reply cases
		assert self.cases == [] or self.replies == []

		if hasattr(self.parent, 'replies'):
			assert self.visitLimit is None and self.rapportReq is None, \
			f"Child of reply node {self.parent.id} must not have visitLimit or " \
			f"rapportReq in dialogue tree {self.label}"

		# used as context to eval() guardCase and cases
		self.globals = {"player":player,"game":game,"world":world}


	### Dunder Methods ###

	def __str__(self):
		return f"{self.label} dlogNode {self.id}"


	### File I/O ###

	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		del jsonDict["id"]
		del jsonDict["globals"]
		return jsonDict


	@classmethod
	def convertFromJSON(cls,d):
		return cls(**d)


	# ensures the following:
	# that the tree is structurally valid by determining the ID
	# that all cases (which are stored in JSON as strings) are ints or evaluate to a bool
	# that all trites (which are stored in JSON as strings) are valid sets in Data.py
	# note that speaker, player, game, and world are provided to ensure eval() is valid
	def ensureIntegrity(self,speaker,**kwargs):
		err = "Invalid guard case node condition in "
		f"{speaker.name}'s node {self.id}: {self.guardCase}"
		context = kwargs | {"speaker":speaker}
		guardCaseRes = eval(self.guardCase,self.globals,context)
		assert type(guardCaseRes) is bool, err
		for case in self.cases:
			err = f"Invalid case node condition in {speaker.name}'s node {self.id}:{case}"
			caseRes = eval(str(case),self.globals,context)
			assert type(caseRes) in (bool,int), err
		for trite in self.trites:
			triteset = game.dlogForest["pools"][trite]
			assert len(triteset) > 2
		for child in self.children:
			child.ensureIntegrity(speaker,**kwargs)


	### Operation ###

	# try to visit the child with the first true case
	# cases can be numbers, representing a probability of visiting that child
	# if all are false, try to visit the last child (like an 'else')
	def conditionalHop(self,speaker,**kwargs):
		for i, case in enumerate(self.cases):
			nextNode = self.children[i]

			context = kwargs | {"speaker":speaker}
			# cases can be boolean cases or integer probabiliies
			# note that it is an independent probability for each node
			if type(case) is int and percentChance(case):
				if nextNode.hop(speaker,**kwargs):
					return nextNode
			elif type(case) is str and eval(case,self.globals,context) is True:
				if nextNode.hop(speaker,**kwargs):
					return nextNode

		else:
			nextNode = self.children[-1]
			if nextNode.hop(speaker,**kwargs):
				return nextNode
		
		return None


	# try to visit the child corresponding to the user-chosen dialogue reply
	# users can end the dialogue by inputting a cancel command
	# note that this does NOT call nextNode.hop(); a reply hop mandates a traversal
	def replyHop(self):
		for i, reply in enumerate(self.replies):
			Print()
			Print(f'{i+1}. {reply}',end="",color='k')

		def acceptKey(inp):
			try:
				return self.children[int(inp)-1]
			except:
				return None

		refuseMsg = "That is not one of the options. Input a number or type 'cancel'."
		return InputLoop("",acceptKey=acceptKey,refuseMsg=refuseMsg)


	# test if this node can be visited using visitLimit, rapportReq, and guardCase
	def hop(self,speaker,**kwargs):
		if self.visitLimit is not None:
			if speaker.dlogTree.getVisitCount(self.id) >= self.visitLimit:
				return False
		if self.rapportReq is not None:
			if speaker.rapport != self.rapportReq:
				return False
		context = kwargs | {"speaker":speaker}
		if not eval(self.guardCase,self.globals,context):
			return False
		return True


	# attempt to branch down the tree, visiting this node
	# printing a dialogue remark if the node has one, and visiting a child node
	def visit(self,speaker,**kwargs):
		if self.isCheckpoint:
			speaker.dlogTree.checkpoint = self.id

		# output this node's remark
		if self.remark:
			waitInput(f'"{self.remark}"',color="y")
		elif self.trites:
			tritepool = set()
			for trite in self.trites:
				tritepool |= set(game.dlogForest["pools"][trite])

			samples = sample(tritepool,2)
			triteRemark = samples[0]
			if triteRemark == self.lastTriteRemark:
				triteRemark = samples[1]

			waitInput(f'"{triteRemark}"',color="y")
			self.lastTriteRemark = triteRemark

		# return next node if this node has children
		# note that it is possible for nextNode to end up as None (from conditionalHop)
		nextNode = None
		if self.cases:
			nextNode = self.conditionalHop(speaker,**kwargs)
		elif self.replies:
			nextNode = self.replyHop()
		else: # TODO: run this if nextNode is still none?
			for child in self.children:
				if child.hop(speaker,**kwargs):
					nextNode = child
					break

		# count this node as successfully visited
		speaker.dlogTree.countVisit(self.id)

		# if applicable, affect speaker or player stats
		speaker.updateLove(self.loveMod)
		speaker.updateFear(self.fearMod)
		player.updateReputation(self.repMod)
		for memory in self.memories:
			speaker.memories.add(memory)
		for event in self.events:
			game.events.add(event)

		# unmark checkpoint if this node was succesfully visited
		if nextNode and speaker.dlogTree.checkpoint == self.id:
			speaker.dlogTree.checkpoint = None
		return nextNode


	### Getters ###

	# checks that at least one path in the tree will provide dialogue
	def hasDefiniteDialogue(self):
		if self.remark or self.trites:
			return True
		if self.cases:
			if self.children[-1].hasDefiniteDialogue():
				return True
			return False
		for child in self.children:
			if child.hasDefiniteDialogue():
				return True
		return False



# a reaction node is a special type of dialogue node that heads the 'reactions' branch
# it is not traversed during normal parley, but when the speaker reacts to something
# it behaves just like a dictionary, mapping keys like 'attacked' to dialogue nodes
# any objects relevant the reaction can be supplied in the **kwargs of node.traverse()
class ReactionNode(DialogueNode):
	def __init__(self,parent,label,idx,treeJson):
		super().__init__(parent,label,idx)
		assert len(self.children) == 0, "Reaction node has non-reaction children"
		self.reactions = {key: DialogueNode(self,label,i,**childJson) for i,(key,childJson) in enumerate(treeJson.items())}
		self.children = (child for child in self.reactions.values())


	def __getitem__(self,key):
		return self.reactions[key]


	def __contains__(self,key):
		return key in self.reactions



# in order for characters to produce unique and variable dialogue with minimal repetition-
# and apparent intelligence, a character's dialogue is stored as a directed tree

# Structure:
# there are five branches from the root; surprise, quest, colloquy, chatter, and reaction
# the tree will try to traverse each branch in order until one produces dialogue output
# 1. surprise is for dialogue which a character would prioritize before anything else
# 2. quest is for dialogue that is generally important for the game or story
# 3. colloquy is for dialogue that is meant to give the character depth or individuality
# 4. chatter is for when the rest are exhausted and is sampled from specified tritesets 
# 5. reaction is not used during a normal parley, it is used to react to other actions

# Features:
# - Checkpoint
#	trees may store a node 'checkpoint' in case the user leaves and reenters the dialogue
# - Rapport
#	the speaker's rapport value is incremented when the user engages in colloquy
#	rapport is meant to give the dialogue a sense of progression throughout the game
# - Parleys
#	to give the speakers the appearance of short term memory, 
#	the tree maintains its state until a new 'parley'
#	a new parley occurs after a certain length of time since the previous dialogue
#	a new parley erases the checkpoint and the visitCounts of all nodes
class DialogueTree():
	def __init__(self,label,treeJson=None,visitCounts=None,checkpoint=None):
		if treeJson is None:
			treeJson = {"chatter":{}}
		self.label = label
		self.id = ()
		# note that chatter is required to be populated; there must be some dialogue
		self.surprise = DialogueNode(self,label,0,**treeJson.get("surprise",{}))
		self.quest = DialogueNode(self,label,1,**treeJson.get("quest",{}))
		self.colloquy = DialogueNode(self,label,2,**treeJson.get("colloquy",{}))
		self.chatter = DialogueNode(self,label,3,**treeJson["chatter"])
		self.reactions = ReactionNode(self,label,4,treeJson.get("reactions",{}))
		self.children = (self.surprise,self.quest,self.colloquy,self.chatter,self.reactions)
		self.visitCounts = {} if visitCounts is None else visitCounts
		self.visitCounts = self.deserializeTupDict(self.visitCounts)
		self.checkpoint = None


	### Dunder Methods ###

	def __str__(self):
		return f"{self.label} dlog tree"


	### File I/O ###

	def deserializeTupDict(self,tupDict):
		return {tuple(tupStr.split(',')): val for tupStr, val in tupDict.items()}


	# within world.json, the tree is just stored with its name and state
	# the actual tree structure should be stored in Dialogue.json and not altered
	def convertToJSON(self):
		return {
			"label": self.label,
			"visitCounts": {str(id): count for id, count in self.visitCounts.items()},
			"checkpoint": self.checkpoint
		}


	def copy(self):
		treeCopy = DialogueTree(self.label)
		treeCopy.surprise = self.surprise
		treeCopy.quest = self.quest
		treeCopy.colloquy = self.colloquy
		treeCopy.chatter = self.chatter
		treeCopy.reactions = self.reactions
		treeCopy.children = self.children
		return treeCopy


	# ensures the following;
	# that the tree is structurally valid (parents are assigned to children)
	# that the checkpoint, if there is one, is a valid node
	# that at least one path of the tree will yield dialogue in all cases
	def ensureIntegrity(self,speaker):
		# this is used for running eval (specifically reaction nodes)
		dummyContext = {"I": Item("","",0,0,""), "C": Creature("","",0,[0]*10,0)}
		for child in self.children:
			child.ensureIntegrity(speaker,**dummyContext)

		if self.checkpoint:
			assert self.findNode(self.checkpoint), \
			f"Checkpoint {self.checkpoint} not found in {speaker.name}'s dialogue tree"

		for id in self.visitCounts.values():
			assert self.findNode(id), \
			f"Visited node {id} not found in {speaker.name}'s dialogue tree"			

		assert self.chatter.hasDefiniteDialogue(), \
		f"In {speaker.room()} {speaker.name} dialogue Tree has no definite dialogue"


	### Operation ###
	
	# should only be called by node.visit() to mark that node as visited
	def countVisit(self,nodeId):
		if nodeId in self.visitCounts:
			self.visitCounts[nodeId] += 1
		else:
			self.visitCounts[nodeId] = 1


	# should only be called by node.hop() to check how many times node has been visited
	def getVisitCount(self,nodeId):
		if nodeId in self.visitCounts:
			return self.visitCounts[nodeId]
		return 0


	# visit the branch, return True if visiting any child resulted in speaker dialogue
	def visitBranch(self,node,speaker):
		had_dialogue = False
		while node:
			if node.remark or node.trites:
				had_dialogue = True
			node = node.visit(speaker)
		return had_dialogue


	# visit the corresponding reaction branch, return True if reached a 'reactTrue' node 
	def react(self,reaction,speaker,**kwargs):
		if reaction not in self.reactions:
			return False
		node = self.reactions[reaction]
		if node.hop(speaker,**kwargs):
			while node:
				nextNode = node.visit(speaker,**kwargs)
				if node.reactTrue:
					return True
				node = nextNode
		return False


	# attempt to visit each branch of the tree until one yields dialogue
	# after the surprise branch, start at the dialogue checkpoint if there is one
	# returns True if any branch successfully yielded dialogue.
	# Visiting 'chatter' should always succeed
	def visit(self,speaker):
		if self.surprise.hop(speaker):
			if self.visitBranch(self.surprise,speaker):
				return True

		if self.checkpoint:
			checkpointNode = self.findNode(self.checkpoint)
			if checkpointNode.hop(speaker):
				if self.visitBranch(checkpointNode,speaker):
					return True

		for branch in (self.quest,self.colloquy,self.chatter):
			if branch.hop(speaker):
				if self.visitBranch(branch,speaker):
					if branch is self.colloquy:
						speaker.rapport += 1
					return True

		return Print("...",color="y",delay=0.3)


	# uses a nodeId (the path to the node using child indices) to retrieve node
	def findNode(self,nodeId):
		node = self
		for idx in nodeId:
			node = node.children[idx]
		return node


	# resets all nodes for new parley
	def newParley(self):
		self.checkpoint = None
		self.visitCounts = {}




############################
## SUPERCLASS DEFINITIONS ##
############################


# base class for all "physical objects" in the world
# the three main types are Room, Item, and Creature (which is a subclass of Item)
# the methods herein are mostly for representing objects or for handling basic interactions
class GameObject():
	def __init__(self):
		self.name = "[GAME OBJECT]"
		self.weight = 0
		self.pronoun = "it"
		self.plural = "[GAME OBJECTS]"
		self.determiner = None
		self.status = set()


	### Dunder Methods ###

	def __str__(self):
		return self.name


	def __neg__(self):
		return self.nounPhrase('the')


	def __pos__(self):
		return self.nounPhrase('the',cap=1)


	def __invert__(self):
		return self.nounPhrase('a')


	def __add__(self,other):
		return +self + " " + conjugate(+self,other)


	def __sub__(self,other):
		return -self + " " + conjugate(-self,other)


	def __mul__(self,other):
		return self.pronoun.capitalize() + " " + conjugate(self.pronoun,other)


	def __truediv__(self,other):
		return self.pronoun.lower() + " " + conjugate(self.pronoun,other)


	def __hash__(self):
		return hash(id(self))


	def __iter__(self):
		yield from self.contents().copy()


	def __contains__(self,obj):
		return obj in self.contents()


	def __lt__(self,other):
		if hasMethod(other,"Weight"):
			other = other.Weight()
		return self.Weight() < other


	def __gt__(self,other):
		if hasMethod(other,"Weight"):
			other = other.Weight()
		return self.Weight() > other


	def __lfshift__(self,other):
		if hasMethod(other,"Size"):
			other = other.Size()
		return self.Size() < other


	def __rshift__(self,other):
		if hasMethod(other,"Size"):
			other = other.Size()
		return self.Size() > other


	def __matmul__(self,other): # TODO: reflexive?
		return None
	

	def __mod__(self,other): # TODO: plural?
		return None


	def __and__(self,other): # TODO: not sure what to use & for
		return None


	def __or__(self,other): # TODO: not sure what to use | for
		return None


	def __xor__(self,other): # TODO: not sure what to use ^ for
		return None


	### Operation ###

	# decrements the duration for each status condition applied to the object by t
	# removes status conditions whose duration is lowered past 0
	def passTime(self,t):
		for condition in self.status:
			# subtract remaining duration on condition
			# dont go below 0, negative durations have special meaning
			if condition[1] > 0:
				condition[1] = min0(condition[1] - t)

		# remove conditions with 0 duration left
		self.removeStatus(reqDuration=0)


	### Getters ###

	# integral to objQuery() (see comments)
	# should be empty for objects that aren't Containers, Creatures, or Rooms
	def contents(self):
		return []


	# True if object has a status condition with any of the given names
	def hasAnyStatus(self,*names):
		if len(names) == 1:
			only = names[0]
			if isinstance(only, str):
				names = (only,)
			elif isinstance(only, (list, tuple, set)):
				names = tuple(only)

		if len(names) == 0:
			return len(self.status) > 0
		for name in names:
			if self.hasStatus(name):
				return True
		return False


	# returns True if the object has a status condition with given name.
	# if reqDuration is given, only returns True if duration matches reqDur
	def hasStatus(self,name,reqDuration=None):
		for condname,duration in self.status:
			if condname == name:
				if reqDuration == None or reqDuration == duration:
					return True
		return False


	def nameQuery(self,term,d=2):
		term = term.lower()
		# querying  into player inventory must be explicitly demanded
		key = lambda obj: nameMatch(term,obj) and player not in obj.ancestors()
		return self.query(key=key,d=d,includeSelf=True)


	# wrapper for objQuery() (see comments)
	# get all objects in object tree
	def objTree(self,includeSelf=False):
		matches = objQuery(self,d=3)
		if not includeSelf:
			matches.remove(self)
		return matches


	# wrapper for objQuery() (see comments)
	# sets the degree of the query to 2 by default
	def query(self,key=None,d=2,includeSelf=False):
		# querying into player inventory must be explicitly demanded
		if key is None: key = lambda obj: player not in obj.ancestors()
		matches = objQuery(self,key=key,d=d)
		if not includeSelf and self in matches:
			matches.remove(self)
		return matches


	# compared with Container capacity and for checking cover/hiding
	def Size(self):
		return self.weight


	# used to compare objects mass
	def Weight(self):
		return self.weight


	### User Output ###

	# gets an object's name in various grammatical contexts
	# such as 'an elephant', 'the elephants', 'The elephant', '3 elephants', etc.
	# det should be given as 'a' or 'the'
	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
		# if det.lower() == "the":
		strname = self.name
		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		# if self.determiner is not None and det == "":
		if self.determiner is not None:
			det = self.determiner
		if det == "" and n == 1:
			det = "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname



# EmptyGear is a singleton class representing the absence of gear
# it is used as a placeholder for creatures with nothing equipped
class EmptyGear(GameObject):
	_instance = None
	name = "[EMPTY]"
	aliases = set()
	weight = 0
	durability = 0
	composition = None
	prot = 0
	might = 1
	sleight = 0
	sharpness = 0
	type = "e"
	slots = None


	### Dunder Methods ###

	# singleton instance, so all EmptyGear instances are the same
	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance


	def __repr__(self):
		return f"<empty>"


	def __setattr__(self, key, value):
		# EmptyGear may not be modified, but we don't want to throw an error
		pass


	### Getters ###

	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
		return "[EMPTY GEAR]"


	def asWeapon(self):
		return self
	
	
	### User Output ###

	def displayName(self):
		return "[---]"



# The Game class stores a series of global data about the game that is not
# contained in the global world dict, W, including things like the time,
# a pointer to the current room and previous room, and a pointer to the
# Creature who is currently taking a turn.
# It also offers a series of methods for identifying the currently rendered
# rooms and finding information about them.
class Game():
	def __init__(self,mode,currentroom,prevroom,time,events,dlogForest,creatureFactory,
	itemFactory):
		### Settings

		# 0 for normal mode, 1 for testing mode, 2 for god mode
		self.mode = mode

		### Timing

		# 23 moments in an hour
		self.hourlength = 23
		self.daylength = len(Data.hours) * self.hourlength
		# 14 days in a month
		self.monthlength = 14 * self.daylength

		### General game state

		# the Room play is in now, room player was in last
		self.currentroom = currentroom
		self.prevroom = prevroom
		# the number of action loops that have elapsed since the game's start
		self.time = time
		# the time of the last save made
		self.lastSave = time
		# the creature who is currently acting
		self.whoseTurn = None
		# set of important events that have transpired in the game's progression
		# serves as the game's "memory" for story purposes
		self.events = events
		# set of all Celestial objects currently present (depends on time)
		self.celestials = set()
		self.checkDaytime(silent=True)
		self.checkAstrology(silent=True)

		### Objects Infrastructure

		# dictionaries used to generate dlog Trees, creatures, and items respectively
		self.dlogForest = dlogForest
		self.creatureFactory = creatureFactory
		self.itemFactory = itemFactory
		# references to all Items in the world, each item.id should be its key here
		self.itemRegistry = {None: None}
		self.nextObjId = 0
		# counter for portal link ids (distinct from Item ids)
		# used for saving portals in the world with unique links
		self.portalLinkIds = 0

		### User I/O

		# used for determining whether or not to print most things 
		# usually, silent is True when the player is unconscious
		self.silent = False
		# pronoun references for objects that the player may
		# implicitly refer to with the given pronoun in their user input
		# for instance, if the user inputs "attack him", or "take it"
		self.it = None
		self.they = None
		self.he = None
		self.she = None
		# stores the last command before processing. Used for cheatcode input
		self.lastRawCommand = None
		# used to trigger a quit from the player
		self.quit = False


	### Item Registry ###

	# clear Item registry between runs of the game
	def clearRegistry(self):
		self.itemRegistry = {None: None}
		self.nextObjId = 0


	# get next id to give an Item
	def getNextID(self):
		while self.nextObjId in self.itemRegistry:
			self.nextObjId += 1
		return self.nextObjId


	# Give Item an ID if it doesn't have one and add it to registry
	def registerItem(self,obj):
		assert isinstance(obj,Item), f"Cannot register non-Item {obj}"
		if self.itemRegistry.get(obj.id) is obj:
			return
		elif obj.id in self.itemRegistry:
			raise Exception(f"Object ID {obj.id} from {obj.name} "
			f"already exists in registry as {self.itemRegistry[obj.id].name}")
		self.itemRegistry[obj.id] = obj


	# replace one Item with another in the registry
	# should only be called after lender has been removed from the world
	def replaceID(self,lender,borrower):
		assert isinstance(lender,Item) and isinstance(borrower,Item)
		assert lender not in self.itemRegistry.values(), \
		f"lender {lender} still in registry values when trying to give ID to {borrower}"
		# in case borrower already registered with ID, delete it
		if borrower.id is not None and borrower.id in self.itemRegistry:
			registryObj = self.itemRegistry[borrower.id]
			assert registryObj is borrower, f"ID conflict with {registryObj}" \
			f" when trying to replace {lender} with {borrower}"
			del self.itemRegistry[borrower.id]
		self.itemRegistry[lender.id] = borrower
		borrower.id = lender.id


	# spawn a new item (may instantiate it from a string) and register it
	def spawn(self,obj):
		if isinstance(obj,str):
			if obj in self.creatureFactory:
				obj = self.creatureFactory[obj]()
			elif obj in self.itemFactory:
				obj = self.itemFactory[obj]()
			else:
				raise Exception(f"Cannot spawn unknown factory object {obj}")
		else:
			assert isinstance(obj,Item)

		assert obj.id is None or obj.id not in self.itemRegistry
		obj.id = self.getNextID()
		self.registerItem(obj)
		return obj


	### Operation ###

	# has player exit the previous room and enter the new room
	def changeRoom(self,newroom):
		if newroom is self.currentroom:
			return
		# if newroom != self.currentroom:
		self.clearPronouns()
		clearScreen()
		self.prevroom = self.currentroom
		self.currentroom = newroom

		# these need to happen before describeRoom; they may affect player.canNavigate()
		player.parent = newroom
		self.checkDaytime(silent=True)
		self.checkAstrology(silent=True)

		self.describeRoom()
		# then can print any celestial messages after describing the Room
		if self.prevroom.ceiling and not self.currentroom.ceiling:
			self.checkDaytime()
			self.checkAstrology()
		return True


	# when context changes, forget all implicit pronouns
	def clearPronouns(self):
		self.it = None
		self.they = None
		self.her = None
		self.him = None


	# passes time for each room, and each creature in each room
	# important for decrementing the duration counter on all status conditions
	def passTime(self,t=1):
		# print("T =",self.time)
		prev_hour = self.hour()
		self.time += t
		self.silent = player.hasAnyStatus("asleep","dead")

		# objs can change location during passTime;
		# flatten all object trees so we don't call passtime twice on any object
		roomObjTrees = (room.objTree(includeSelf=True) for room in self.renderedRooms())
		for obj in {o for objTree in roomObjTrees for o in objTree}:
			obj.passTime(t)

		# probably not necessary, celestials don't have status conditions
		# for celestial in celestials:
		# 	celestial.passTime(t)

		# check again, it may have changed during room.passTime
		self.silent = player.hasAnyStatus("asleep","dead")
		if prev_hour != self.hour():
			self.checkDaytime()
		self.checkAstrology()


	# sets implicit pronouns based on the type of object
	def setPronouns(self,obj):
		if not isinstance(obj,Person):
			self.it = obj
		if isinstance(obj,Creature):
			self.they = obj
		pronoun = getattr(obj,"pronoun",None)
		if pronoun == "he":
			self.he = obj
		elif pronoun == "she":
			self.she = obj


	### Getters ###

	# recursively adds all adjacent rooms to the set of found rooms
	# used by renderedRooms()
	# n is the path length at which the query stops
	# Sroom is the "source" room, or the current node in the query
	def roomFinder(self,n,Sroom,pathlen,foundrooms):
		if pathlen >= n:
			return
		adjacentRooms = (dest for dest in Sroom.allDests() if isinstance(dest,Room))

		for room in adjacentRooms:
			foundrooms.add(room)
			self.roomFinder(n,room,pathlen+1,foundrooms)


	# returns set of all rooms connected to currentroom with path length < REND_DIST
	def renderedRooms(self):
		# constant render distance of rooms in world
		REND_DIST = 3
		# the set of found rooms initially includes only the current room
		R = {self.currentroom}
		# add all rooms within a distance of REND_DIST to R
		self.roomFinder(REND_DIST,self.currentroom,0,R)
		return R


	# gets set of all rendered rooms except the current room
	def nearbyRooms(self):
		R = self.renderedRooms()
		R.remove(self.currentroom)
		return R


	# returns a list of objects in rendered rooms which fit a certain condition
	def queryRooms(self,key=lambda x:True,d=3):
		matchingObjects = []
		for room in self.renderedRooms():
			matchingObjects += room.query(key=key,d=d)
		return matchingObjects


	# True if there's an object in rendered rooms whose name matches objname
	# not case sensitive
	def inWorld(self,term):
		key = lambda obj: nameMatch(term,obj)
		objects = self.queryRooms(key)
		return len(objects) > 0


	# hours have names in this game, get name of the hour from the time
	def hour(self):
		return Data.hours[(self.time % self.daylength) // self.hourlength]


	### Celestials ###

	# change the phase of the moon based on time, print message if not silent
	def checkMoon(self,silent=False):
		if getattr(getattr(player,"parent",None),"ceiling",None) is not None:
			silent=True
		self.events.discard("new moon")
		self.events.discard("full moon")
		msg = ""
		mooncycle = (self.time % self.monthlength) // self.daylength
		if mooncycle == 0:
			msg = "It is a new moon."
			self.events.add("new moon")
		elif mooncycle == 7:
			msg = "It is a full moon."
			self.events.add("full moon")
		if msg and not silent:
			Print(msg,color="b")


	# change the state of astrological objects, print message if not silent
	def checkAstrology(self,silent=False):
		if getattr(getattr(player,"parent",None),"ceiling",None) is not None:
			silent=True

		darkhours = ("hearth","cat","mouse","owl","serpent","wolf")
		aurora_cycle = self.time % 2000
		if aurora_cycle >= 0 and aurora_cycle < 100 and self.hour() in darkhours:
			if "aurora" not in self.events and not silent:
				Print("There is an aurora in the sky!",color="b")			
				self.setPronouns(aurora)
			self.events.add("aurora")
			self.celestials.add(aurora)
		elif "aurora" in self.events and not silent:
			self.events.remove("aurora")
			self.celestials.remove(aurora)
			Print("The aurora is over.")

		meteor_cycle = self.time % 3500
		if meteor_cycle >= 0 and meteor_cycle < 300 and self.hour() in darkhours:
			if "meteor shower" not in self.events and not silent:
				Print("There is a meteor shower in the sky!",color="b")
				self.setPronouns(meteorshower)
			self.events.add("meteor shower")
			self.celestials.add(meteorshower)
		elif "meteor shower" in self.events and not silent:
			self.events.remove("meteor shower")
			self.celestials.remove(meteorshower)
			Print("The meteor shower is over.")

		lighthours = ("rooster","juniper","bell","sword","willow","lily")
		eclipse_cycle = self.time % (self.monthlength*3+100)
		if eclipse_cycle > 0 and eclipse_cycle < 30 and self.hour() in lighthours:
			if "eclipse" not in self.events and not silent:
				Print("There is a solar eclipse in the sky!",color="b")
				self.setPronouns(eclipse)
			self.events.add("eclipse")
			self.celestials.add(eclipse)
		elif "eclipse" in self.events and not silent:
			self.events.remove("eclipse")
			self.celestials.remove(eclipse)
			Print("The solar eclipse is over.")


	# change time of day, print message if not silent, check moon phase
	def checkDaytime(self,silent=False):
		if getattr(getattr(player,"parent",None),"ceiling",None) is not None:
			silent=True
		self.celestials.add(sky)
		for daytime in ("morning","day","evening","night"):
			self.events.discard(daytime)
		for celestial in (sun,moon,stars):
			self.celestials.discard(celestial)

		if self.hour() in ("stag","rooster","juniper"):
			self.celestials.add(sun)
			self.events.add("morning")
		if self.hour() in ("bell","sword","willow","lily"):
			self.celestials.add(sun)
		if self.hour() in ("hearth","cat"):
			self.celestials.add(sun)
			self.celestials.add(stars)
		if self.hour() in ("mouse","owl","serpent","wolf"):
			self.celestials.add(moon)
			self.celestials.add(stars)

		if not silent:
			for daytime in ("morning","day","evening","night"):
				if daytime in self.events and not silent:
					Print(f"It is {daytime}.")
					break
		self.checkMoon(silent=(silent or "night" not in self.events))


	### User Output ###		

	# begin game and set the scene
	def startUp(self):
		clearScreen()
		# if not sidepanel.isOpen():
		# 	player.openDisplay()
		self.describeRoom()
		if self.currentroom.ceiling is None:
			game.checkDaytime()
			game.checkAstrology()


	# describe the current room
	def describeRoom(self):
		Print("\n"+self.currentroom.domain+"\n"+self.currentroom.name)
		self.currentroom.describe()
		if not isinstance(player.parent,Room):
			Print(f"You are in {-player.parent}.")
		# if player.carrying:
		# 	Print(f"You are carrying {~player.carrying}.")


	# look up at the sky or ceiling and describe what is seen
	def LookUp(self,target):
		if target.startswith("the "):
			target = target[4:]
		if self.currentroom.ceiling is not None:
			if target not in (None,"ceiling","roof"):
				Print("You can't see the sky from here.")
				return False
			return self.currentroom.ceiling.describe()

		if target in ("sky",None):
			target = "sun" if self.hour() in Data.dayhours else "moon"		

		if "eclipse" in self.events:
			Print(Data.eclipseDesc,color="b")
			player.takeDamage(5,"r")
		elif "eclipse" not in self.events and target in ("eclipse","solar eclipse"):
			Print("There's no eclipse happening right now.")
		elif target == "sun":
			if self.hour() in ("stag","rooster","juniper"):
				Print(Data.morningSunDesc)
			elif self.hour() in ("bell","sword","willow","lily"):
				Print(Data.highSunDesc)
			elif self.hour() in ("hearth","cat"):
				Print(Data.eveningSunDesc)
			else:
				Print("The sun isn't out right now.")
		elif target in ("moon","stars"):
			if self.hour() in Data.nighthours:
				if "full moon" in self.events:
					Print(Data.fullMoonDesc,color="b")
				elif "new moon" in self.events:
					Print(Data.newMoonDesc,color="b")
				else:
					Print(Data.moonDesc)
			elif target == "moon":
				Print("The moon isn't out right now.")
			elif target == "stars" and self.hour() in ("hearth","cat"):
				Print(Data.eveningStarsDesc,color="b")
			elif target == "stars":
				Print("The stars aren't out right now.")

		if "aurora" in self.events:
			Print(Data.auroraDesc,color="b")
		elif target in ("aurora","auroras"):
			Print("There's no aurora happening right now.")

		if "meteor shower" in self.events:
			Print(Data.meteorDesc,color="b")
		elif target in ("shower","meteors","meteor shower"):
			Print("There's no meteor shower happening right now.")
		return True



# the Room class is the fundamental unit of the game's world.
# The world dict, consists of key:value pairs of the form {"room name":Room}

# Importantly, each room contains a links dict, where keys are directions
# such as such as 'north', 'up', or 'beyond', and values are the neighboring rooms
# In this way, every Room object can be thought of like a node in a large
# directed graph, facilitated by the world dict, where the links dict specifies
# the edges from a given node to its neighboring nodes.
class Room(GameObject):
	def __init__(self,name,domain,desc,links,fixtures,items,creatures,capacity=1000,
	passprep=None,composition=None,ceiling=None,walls=None,floor=None,status=None):
		# name serves as the Room's unique id
		self.name = name
		# domains are regions within the world, used for determining creatures to spawn
		# typically many rooms near eachother belong to the same domain
		self.domain = domain
		self.desc = desc
		self.links = links

		# room's contents is split between these three, mostly for convenience
		self.fixtures = fixtures
		self.items = items
		self.creatures = creatures
		for f in self.fixtures:
			assert f.fixed and not isinstance(f,Creature), \
			f"Non-fixed fixture {f} in Room {self.name}"
		for i in self.items:
			assert not i.fixed and not isinstance(i,Creature), \
			f"Fixture or creature {i} in Room {self.name} items list"
		for c in self.creatures:
			assert isinstance(c,Creature), \
			f"Non-creature {c} in Room {self.name} creatures list"

		# determines how much mass the Room can hold, objects too large cannot enter
		self.capacity = capacity

		self.status = status if status else []
		for cond,dur in self.status:
			assert isinstance(cond,str) and isinstance(dur,int)

		self.passprep = "at" if passprep is None else passprep
		self.parent = None
		self.pronoun = "it"
		self.determiner = None

		self.composition = composition
		# these are the default room surfaces, 
		# given from the world json as strings of the surface's composition
		self.ceiling = None
		self.walls = None
		self.floor = None
		if ceiling:
			self.ceiling = Surface("ceiling",f"A ceiling of {ceiling}.",capacity//3,
			ceiling,aliases=["roof"])
		if walls:
			self.walls = Surface("wall",f"Walls of {walls}.",capacity//3,walls,
			aliases=["walls"])
		if floor in Data.liquids:
			self.floor = Surface("surface",f"A surface of {floor}.",capacity//3,floor,
			aliases=[floor],determiner="the")
		elif floor:
			self.floor = Surface("ground",f"A floor of {floor}.",capacity//3,floor,
			aliases=["floor"],determiner="the")
		self.surfaces = (self.ceiling,self.walls,self.floor)


	### Dunder Methods ###

	def __repr__(self):
		return f"Room({self.name})"


	### File I/O ###

	# after all objects instantiated from json, assign room links to actual Room objects
	# uses the string names in the links to get Room objects from world dict
	def assignRefs(self):
		for dir, dest in self.links.items():
			assert dest in world, f"Room {self.name} has a link to unknown dest '{dest}'"
			assert type(world[dest]) is Room, f"Room {self.name} has a link to" \
			f" non-Room '{dest}'"
			self.links[dir] = world[dest]

		assert self.vacancy() >= 0, (f"Room {self.name} has negative space available"
		f"size is {self.size}, but occupied space is {self.itemsSize()}")


	# restore links dict to using strings as values for saving to json
	# restore surfaces to using strings representing their composition
	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		jsonDict["links"] = {}
		for dir, dest in self.links.items():
			assert isinstance(dest, Room), f"Trying to save room {self.name} "
			f"with exit to non-Room '{dest}'"
			jsonDict["links"][dir] = dest.name.lower()

		del jsonDict["pronoun"]
		if self.ceiling:
			jsonDict["ceiling"] = self.ceiling.composition
		if self.walls:
			jsonDict["walls"] = self.walls.composition
		if self.floor:
			jsonDict["floor"] = self.floor.composition

		del jsonDict["surfaces"], jsonDict["determiner"]
		return jsonDict


	### Operation ###

	# spawn object if not fully instantiated, try to add it to contents depending on type
	def add(self,O):
		# spawn object if given as string or has no ID
		if isinstance(O,str) or O.id is None:
			O = game.spawn(O)

		# check if object can be added to room, displace it if not
		# displacing it out of a room will probably destroy it
		if not self.canAdd(O):
			O.displace(None)
			return False

		# set platform surface for object if it has none
		if O.anchor() is None and not O.hasStatus("flying"):
			O.platform = self.floor

		# add object to appropriate content list
		if isinstance(O,Creature):
			insort(self.creatures,O)
			O.parent = self
			return O
		elif O.fixed:
			insort(self.fixtures,O)
			O.parent = self
			return O
		elif isinstance(O,Item):
			# ensure only one bunch of Gold exists here
			if isinstance(O,Serpens):
				for item in self.items:
					if isinstance(item,Serpens):
						item.merge(O)
						return item
			insort(self.items,O)
			O.parent = self
			O.timeDespawn()
			return O
		return False


	# apply an area condition to all objs in the Room
	def addAreaCondition(self,areacond):
		key,cond,dur = extractConditionInfo(areacond)
		for obj in self.query(key=key):
			obj.addStatus(cond,dur)


	# add a status condition to the Room with a name and duration
	def addStatus(self,name,dur,stackable=True):
		if self.hasStatus(name) and not stackable:
			return False
		if self.hasStatus(name,dur):
			return False
		insort(self.status,[name,dur])
		if name.startswith(("AREA","ITEM","CREATURE")):
			self.addAreaCondition(name)
		return True


	# add one-way link to a neighboring Room
	# to ensure a bidirectional link between Rooms, call this once on each room.
	def addLink(self,dir,loc):
		self.links[dir] = loc


	# apply any room effects to the obj entering
	def enter(self,obj):
		obj = self.add(obj)
		# add status conditions from this room
		for cond,dur in self.status:
			# if room's condition is an area condition, apply to obj when applicable
			if cond.startswith(("AREA","ITEM","CREATURE")):
				key,name,dur = extractConditionInfo(cond)
				if key(obj):
					obj.addStatus(name,dur)

		obj.checkSubmersion()
		return True


	# remove any room effects from the obj exiting
	def exit(self,obj):
		# remove status conditions from this room
		condsToRemove = [pair for pair in obj.status if pair[1] == -2]
		for cond,dur in condsToRemove:
			obj.removeStatus(cond,-1)
		self.remove(obj)
		return True


	# pass time for the Room, chance to spawn creatures, sort creatures by MVMT speed
	def passTime(self,t):
		super().passTime(t)

		# chance to spawn up to 1 creature in the Room
		# type of creature depends on the domain
		for name, prob in Data.spawnpools.get(self.domain,()):
			if len(self.creatures) > 0 or self is game.currentroom:
				continue
			# TODO: refactor this to have an event chance for creatures in spawnpools?
			# right now it is biased to earlier in the list
			if percentChance(prob):
				self.enter(name)

		# sort all Creatures occupying the Room by their MVMT() value, descending
		self.creatures.sort(key=lambda x: x.MVMT(), reverse=True)


	# Try to remove object from contents, ignore if not present
	def remove(self,O):
		if isinstance(O,Creature):
			if O in self.creatures:
				self.creatures.remove(O)
				O.parent = None
				return True
		elif O.fixed:
			if O in self.fixtures:
				# TODO: should this even be possible? fixtures are fixed...
				self.fixtures.remove(O)
				O.parent = None
				return True
		elif isinstance(O,Item):
			if O in self.items:
				self.items.remove(O)
				O.parent = None
				return True
		return False


	# try to remove an area condition from all affected objs in the Room
	def removeAreaCondition(self,areacond):
		key,cond,dur = extractConditionInfo(areacond)
		# -3 indicates the condition is caused by being in the Room, otherwise ignore
		if dur != -3:
			return
		for obj in self.query(key=key):
			obj.removeStatus(cond,dur)


	# given an object, try to replace it with another object in the Room
	# returns True if successful, False if newObj was not added
	def replaceObj(self,oldObj,newObj):
		assert oldObj in self
		self.remove(oldObj)

		if not self.canAdd(newObj):
			return False
		self.enter(newObj)
		return True


	# removes all conditions with the given name and duration
	# when nothing given, remove all status conditions
	def removeStatus(self,reqName=None,reqDuration=None):
		# copy to prevent removing-while-iterating errors
		for name,duration in self.status.copy():
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])
					if name.startswith(("AREA","ITEM","CREATURE")):
						self.removeAreaCondition(name)


	### Getters ###

	# get all neighboring rooms
	def allDests(self):
		return {dest for dest in self.allLinks().values()}


	# get the set of all directions leading out of the Room
	def allDirs(self):
		return {tuple[0] for tuple in self.allLinks()}


	# get all creatures in this room's object tree, sorted by MVMT descending
	def allCreatures(self):
		creatures = objQuery(self,key=lambda obj: isinstance(obj,Creature),d=3)
		return sorted(list(creatures), key=lambda x: x.MVMT(), reverse=True)


	# returns dict of links, where keys are (direction,Portal) and values are rooms
	# portal is None if the link is direct from the Room
	# d is the degree of the portal search, see objQuery() for details
	def allLinks(self,d=3):
		links = {}
		for dir in self.links:
			links[(dir,None)] = self.links[dir]
		# for each portal, add its links to links
		for portal in self.query(key=lambda x: isinstance(x,Portal),d=d):
			for dir in portal.getLinksForParent():
				links[(dir,portal)] = portal.links[dir]
		return links


	# rooms are the roots of the obj tree, they have no ancestor
	def ancestors(self):
		return []


	# typically called before trying to add an object to the Room
	# if this fails, object will not be added
	def canAdd(self,I):
		if self.ceiling and I in celestials:
			return False
		if I.totalSize() > self.vacancy():
			return False
		if I in self:
			return False
		return True


	# room contents is the fixtures, items, creatures, surfaces, and celestials
	def contents(self):
		cts = self.fixtures + self.items + self.creatures
		cts += [s for s in self.surfaces if s not in (None,self)]
		if not self.ceiling: cts += game.celestials
		return cts


	# given a direction (like 'north' or 'down)
	# return the Portal with that direction in this room
	def getPortalsFromDir(self,dir):
		portals = []
		for thisDir, portal in self.allLinks(d=0):
			if dir == thisDir:
				portals.append(portal)
		return portals


	# if the given room object, dest, is in one of the Rooms links,
	# then find the direction it is in from the Room.
	# not that this will return None if dest is not linked to from this room
	def getDirPortalPair(self,dest):
		for (dir,portal), room in self.allLinks().items():
			if nameMatch(dest,room):
				return dir, portal
		return None, None


	# total size of all items in the Room (note this ignores celestials and surfaces)
	def itemsSize(self):
		spatialObjects = self.items + self.creatures + self.fixtures
		return sum(obj.Size() for obj in spatialObjects)


	# get items that are 'mentioned' and not anchored to some other platform
	def listableItems(self):
		condition = lambda x: x.mention and x.platform in (None,self.floor)
		objects = list(filter(condition,self.items+self.fixtures))
		return objects


	# for rooms, size is their capacity
	def Size(self):
		return self.capacity


	# get vacant space in the Room
	def vacancy(self):
		return self.capacity - self.itemsSize()


	### User Output ###

	# prints room name, description, all its items and creatures
	def describe(self):
		Print("\n" + self.desc)
		self.describeItems()
		self.describeCreatures()		


	# prints all the items of the Room in sentence form
	def describeItems(self):
		items = self.listableItems()
		if len(items) != 0:
			Print(listObjects("There is ",items,"."))
			game.setPronouns(items[-1])


	# prints all the creatures in the Room in sentence form
	def describeCreatures(self):
		# don't directly describe creatures which are anchored to player
		# or creatures riding another creature
		select = lambda creature: creature not in \
		(player, player.carrying, player.riding) and \
		creature.anchor() in (creature.parent.floor,None)

		listCreatures = [creature for creature in self.creatures if select(creature)]
		if len(listCreatures) != 0:
			Print(listObjects("There is ",listCreatures,"."))

		# now describe if one creature carrying another
		carriers = [creature for creature in self.creatures if select(creature) and \
		creature.carrying is not None]
		carrierPhrases = [f"{-creature} is carrying {~creature.carrying}" \
		for creature in carriers]

		if len(carrierPhrases) > 1:
			carrierDescriptions = (", ".join(carrierPhrases[:-1]) + \
			" and " + carrierPhrases[-1])
		elif len(carrierPhrases) == 1:
			carrierDescriptions = carrierPhrases[0]
		else:
			carrierDescriptions = ""
		if carrierDescriptions:
			Print(capWords(carrierDescriptions,1) + ".")

		# set pronouns for the last creature described
		for creature in listCreatures:
			game.setPronouns(creature)



# Items are the heart of the game. Everything in a room should be an Item
# All items come with a name, description, weight, durability, and composition
class Item(GameObject):
	def __init__(self,name,desc,weight,durability,composition,aliases=None,rarity=1,
	status=None,plural=None,descname=None,determiner=None,pronoun="it",fixed=False,
	mention=True,longevity=None,despawnTimer=None,scent=None,flavor=None,texture=None,
	platform=None,occupants=None,covering=None,id=None):

		### Basic Properties
	
		self.name = name
		self.desc = desc
		self.weight = weight
		self.durability = durability
		# used to determine obj density and for crafting
		self.composition = composition

		### Additional Properties

		# rarities are:
		# -1. hazardous (red) 0. worthless (grey) 1. common (white) 2. uncommon (orange)
		# 3. rare (green) 4. sterling (blue) 5. legendary (magenta) 6. unique (yellow)
		self.rarity = rarity
		assert rarity >= -1 and rarity <= 6
		self.descname = descname if descname else name
		# whether or not it can be removed from its parent
		self.fixed = fixed
		# whether or not it is mentioned when describing its parent
		self.mention = mention
		# how long it lasts in despawnable conditions
		self.longevity = longevity
		self.despawnTimer = despawnTimer
		self.scent = scent
		self.flavor = flavor
		self.texture = texture

		### Grammatical Properties

		self.plural = plural
		if self.plural is None:
			self.plural = self.name + 's'
		self.determiner = determiner
		self.pronoun = pronoun
		# used for identifying object from player input
		self.aliases = list(set(aliases)) if aliases else []

		### World Properties -- may be reassigned during assignRefs() 

		# used to uniquely identify this object instance
		self.id = id
		# the parent object containing this object (usually a Room or Container)
		self.parent = None

		### Status Effects

		self.status = status if status else []
		for cond,dur in self.status:
			assert isinstance(cond,str) and isinstance(dur,int)
		# sort status effects by duration; change idx '1' to '0' to sort by name
		self.status.sort(key=lambda x: x[1])

		### Tethers

		# these describe physical position relative to other objects
		self.platform = platform
		self.occupants = occupants if occupants else []
		self.covering = covering if covering else []


	### Dunder Methods ###

	def __repr__(self):
		return f"{self.__class__.__name__}({self.name}, {self.weight}, {self.durability})"


	### File I/O ###

	# when instantiating this object, many other objects may not yet be instantiated,
	# so during __init__ these are provided as object IDs (integers) or None.
	# after all objects are instantiated, we call this to substitute IDs with real objects
	def assignRefs(self,parent):
		self.parent = parent
		isID = lambda x: isinstance(x,int) or x is None

		# this allows us to define objects occupants as an occupant in the World.json,
		# rather than and defining it in parent's contents then using an ID in .occupants
		occupants = []
		for o in self.occupants:
			if isID(o):
				o = game.itemRegistry[o]
				assert self is o.platform or self.id is o.platform
				continue
			if self.parent.add(o):
				# add() might have displaced o and assigned another parent
				o.assignRefs(o.parent)
				assignRefsRecur(o)
				o.platform = self
				occupants.append(o)
		self.occupants = occupants

		self.covering = [game.itemRegistry[o] if isID(o) else o for o in self.covering]
		self.occupants = [game.itemRegistry[o] if isID(o) else o for o in self.occupants]
		if isID(self.platform):
			self.platform = game.itemRegistry[self.platform]

		# assign the item's anchor unless it is flying
		if self.anchor() is None and not self.hasStatus("flying"):
			# creatures don't have floors, and surfaces may not have a platform
			if not isinstance(self.parent,Creature) and not self in self.parent.surfaces:
				self.platform = self.parent.floor


	# convert these references back into integer IDs
	def convertToJSON(self):
		jsonDict = self.__dict__.copy()
		jsonDict["occupants"] = [o.id for o in self.occupants] if self.occupants else None
		jsonDict["covering"] = [c.id for c in self.covering] if self.covering else None
		jsonDict["platform"] = self.platform.id if self.platform else None
		return jsonDict


	### Operation ###

	def addStatus(self,name,dur,stackable=True):
		if self.hasStatus(name) and not stackable:
			return False
		if self.hasStatus(name,dur):
			return False
		insort(self.status,[name,dur])
		return True


	# try to break the item, destroying it if successful
	def breaks(self):
		# if self.id not in game.itemRegistry:
		# 	return False
		assert self.id in game.itemRegistry, f"{self} ID{self.id} not in Item registry"
		if self.durability == -1:
			# if not silent:
			# 	Print(f"{+self} cannot be broken.")
			return False
		self.Print(f"{+self} breaks.")
		self.destroy()
		return True


	# change location to a new Room/Container
	def changeLocation(self,newparent):
		if not newparent.canAdd(self):
			self.Print(f"Something prevents entering {-newparent}.")
			return False

		# Item cant be covered by another object when changing rooms
		self.clearCovering()
		prevparent = self.parent
		if prevparent:
			prevparent.exit(self)
		if self is player.parent:
			Print(f"{+self} rumbles...")

		# Item no longer covers other objects when changing rooms
		for covered in self.covering:
			covered.removeCover()
		# everything on top of this item moves with it
		for occupant in self.occupants.copy():
			occupant.changeLocation(newparent)

		newparent.enter(self)
		self.platform = newparent.floor
		return True


	# Items bearing too much weight will break
	def checkOccupantsWeight(self,silent=True):
		if self.occupantsWeight() > self.durability*2 and self.durability != -1:
			self.waitInput(f"{+self} collapses under the weight!",color="o")
			self.breaks()
		elif self.occupantsWeight() > self.durability and self.durability != -1:
			if not silent:
				# TODO: this should vary based on composition
				self.Print(f"{+self} creaks under the weight...")


	# check if Item is submersible in liquid based on size and floor composition
	# not that this does not *remove* submersion, only adds it if needed
	def checkSubmersion(self):
		submerseComp = self.submersedIn()
		if submerseComp in Data.liquids:
			self.addStatus("wet",-5)
		else:
			self.replaceStatus(("wet",-5),("wet",21))

		if submerseComp in Data.liquids or \
		hasMethod(self.parent,"canSubmerse") and self.parent.canSubmerse(self):
			liquidDensity = Data.densities.get(submerseComp,1)
			if getattr(self.parent,"composition",None) in Data.liquids:
				self.addStatus("submerged",-4)
				return True
			if not self.canSwim(liquidDensity) and not self.hasStatus("submerged"):
				self.Print("You are too heavy to stay afloat!",color="o")
				self.addStatus("submerged",-4)
				return True

		elif submerseComp not in Data.liquids:
			self.removeStatus("submerged")
			self.removeStatus("swimming")
		return False


	# if there's not enough space to occupy an Item, objects fall off, biggest first
	def checkVacancy(self,obj=None):
		if obj is not None:
			occupants = [obj]
		else:
			occupants = sorted(self.occupants, key=lambda x: x.Size(), reverse=True)

		anyFell = False
		for occupant in occupants:
			# An occupant can occupy something 5x smaller than itself
			# But if theres more than one occupant total size must be less than item size
			notVacant = self.Size() < occupant.Size()//5 and len(self.occupants) <= 1
			notVacant = self.Size() < self.Size() - self.occupantsSize(occupant)
			if notVacant:
				self.Print(f"{+self} is too small for {-occupant}.",color="o")
				self.disoccupy(occupant)
				occupant.fall(self.Size()//5)
				anyFell = True
		return not anyFell


	# removes this Item and all references to it from the game
	def destroy(self,silent=True):
		if not silent:
			self.Print(f"{+self} disappears.")

		self.clearCovering()
		occupants = self.occupants.copy()
		self.clearOccupants()
		for occupant in occupants:
			occupant.fall(self.Size()//5)
		self.removePlatform()

		# may have already been removed from parent
		if self.parent and self in self.parent:
			self.parent.remove(self)

		# TODO: first drop all items from contents? or just some important ones?
		assert game.itemRegistry[self.id] is self, \
		f"{self} ID{self.id} holds wrong Item in registry {game.itemRegistry[self.id]}"
		del game.itemRegistry[self.id]


	# if an Item is too small for its parent, repeatedly move it to parent's parent
	# until theres space for it. if it cannot fit in the final parent (Room), destroy it
	# this prevents strange physical scenarios and should not normally be called
	def displace(self,newparent):
		# print("DISPLACING",self,"TO",newparent)
		if self.parent:
			self.parent.remove(self)
		nextparent = getattr(newparent,"parent",None)
		if hasMethod(newparent,"canObtain"):
			if newparent.canObtain(self,silent=True):
				return newparent.ObtainItem(self)
			else:
				return self.displace(nextparent)
		elif hasMethod(newparent,"canAdd"):
			if newparent.canAdd(self):
				return self.changeLocation(newparent)
			else:
				return self.displace(nextparent)
		else:
			self.destroy()
			return False


	# prevent despawning
	def nullDespawn(self):
		self.despawnTimer = None


	# possibly despawn Item, if it is unanchored make it fall, ensure occupants fit
	def passTime(self,t):
		super().passTime(t)

		if self.despawnTimer is not None:
			self.despawnTimer -= t
			if self.canDespawn():
				return self.destroy()

		self.checkVacancy()
		self.checkOccupantsWeight(silent=True)

		if not isinstance(self.parent,Creature):
			if not self.fixed and not self.hasAnyStatus("flying"):
				if self.anchor() is None:
					self.fall()			
				if self.anchor().composition in Data.liquids and \
				self.hasStatus("submerged"):
					self.fall()

		self.checkSubmersion()


	# removes all condition of the same name
	# if reqDuration is given, only removes conditions with that duration
	def removeStatus(self,reqName=None,reqDuration=None):
		for name,duration in self.status.copy():
			if name == reqName or reqName is None:
				if duration == reqDuration or reqDuration is None:
					self.status.remove([name,duration])


	# replace one status with another
	# if they have the same name, make sure to add new before removing old
	def replaceStatus(self,tup1,tup2):
		c1, d1 = tup1
		c2, d2 = tup2
		if not self.hasStatus(c1,d1):
			return False
		if c1 == c2:
			self.addStatus(c2,d2)
			self.removeStatus(c1,d1)
		else:
			self.removeStatus(c1,d1)
			self.addStatus(c2,d2)



	# when one Item is replaced by another, ensure references to it get substituted
	# removes old Item's refs from parent,covered,occupants,platform
	# attempts to add corresponding refs with newObj, and destroys the old object
	def replace(self,newObj):
		if isinstance(newObj,str) or newObj.id is None:
			newObj = game.spawn(newObj)

		# if it fails to place the new object in parent, displace it
		if not self.parent.replaceObj(self,newObj):
			self.destroy()
			game.replaceID(self,newObj)
			return newObj.displace(self.parent)
		for covered in self.covering.copy():
			covered.removeCover(silent=True)
			covered.addCover(newObj)

		for occupant in self.occupants.copy():
			self.disoccupy(occupant)
			if isinstance(newObj,Creature) or newObj.parent is None:
				occupant.fall(self.Size()//5)
			else:
				newObj.occupy(occupant,silent=True)
			# if newObj was destroyed when adding occupants, end here
			if newObj.parent is None:
				return self.destroy()

		if self.platform not in (None,self.parent) and newObj.parent:
			p = self.platform
			self.removePlatform()
			if not getattr(p,"closed",True) and hasMethod(p,"canAdd") and p.canAdd(newObj):
				newObj.changeLocation(p)
			else:
				p.occupy(newObj)
		# if newObj was destroyed when replacing platform, end here
		if newObj.parent is None:
			return self.destroy()

		self.destroy()
		game.replaceID(self,newObj)
		return newObj


	# degrade Item durability if damage is high enough, break if durability goes to 0
	def takeDamage(self,dmg,type,silent=True):
		# TODO: add damage type vulnerabilities based on composition
		# i.e. wood is extra weak to fire and slashing
		if self.composition in Data.liquids:
			self.Print("Splish splash...")
			return True
		if dmg > 0 or not silent:
			typeDisplay = "" if type == "e" else Data.dmgtypes[type] + " "
			self.printNearby(f"{+self} took {dmg} {typeDisplay}damage.")
		if self.durability != -1:
			dmg = min0(dmg-self.durability)
			self.durability -= dmg
			if self.durability <= 0:
				return self.breaks()


	# set the despawn timer in despawnable conditions
	def timeDespawn(self):
		self.despawnTimer = self.longevity


	# remove occupants and cover and change location
	def teleport(self,newParent):
		if newParent is self.parent:
			return False
		self.clearCovering()
		self.clearOccupants()
		if newParent.canAdd(self):
			self.Print(f"{+self} disappears!",color="w")
			self.changeLocation(newParent)


	### Interaction ###

	# Try to cover an Item, ensure theres enough space to cover it
	def addCovering(self,covered):
		assert isinstance(covered,Creature)
		if covered in self.covering:
			Print(f"{+self} is already covering {-covered}.")
			return False
		if self.availableCover(covered) < 0:
			nCovered = len(self.covering)
			msg = f"{+self} has no space to cover {-covered}. "
			if nCovered == 0:
				addendum = self*"is too small."
			elif nCovered == 1:
				addendum = self*f"is already covering {~self.covering[0]}."
			elif nCovered == 2:
				addendum = self*f"is already covering {~self.covering[0]} " \
				f"and {~self.covering[1]}."
			else:
				addendum = self*f"is covering {nCovered} others."
			Print(msg+addendum)
			return False

		self.covering.append(covered)
		covered.cover = self
		# try to cover any carried creatures too
		if covered.carrying:
			covered.carrying.addCovering(covered)
		return True


	# try to hit with projectile, have chance to miss
	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		hitProb = bound(missile.aim+self.Size()+10,1,99)
		if percentChance(hitProb):
			return missile.collide(self)
		return False


	# Called when Item can no longer serve as cover for others in room
	def clearCovering(self):
		for covered in self.covering:
			self.removeCovering(covered)
		self.covering.clear()
		return True


	# Called generally when occupying Items drop off of self
	def clearOccupants(self):
		for occupant in self.occupants:
			occupant.platform = None
			if not isinstance(self.parent,Creature):
				if getattr(occupant,"riding",False):
					occupant.removeRiding()
				occupant.platform = self.parent.floor
		self.occupants.clear()


	# Called by specific occupant when changing its anchor
	def disoccupy(self,occupant):
		if occupant in self.occupants:
			self.occupants.remove(occupant)
			occupant.platform = None
			return True
		return False


	# Item falls through rooms accumulating fall height until hitting floor, 
	# then take damage and set platform to room's floor
	def fall(self,height=0,room=None):
		if isinstance(self.parent,Creature):
			return False
		verb = "sink" if self.hasStatus("submerged") else "fall"

		# contents could be removed if item breaks, so save this first
		contents = self.contents().copy()
		if room is None:
			room = self.room()
		self.printNearby(f"{+self} {verb}s down.")
		for occupant in self.occupants.copy():
			occupant.fall(height,room)
		self.clearOccupants()

		while (room.floor is None or room.floor.composition in Data.liquids) and \
		"down" in room.links:
			height += room.capacity // 5 # approximate vertical height of room
			room = room.links["down"]
		if room != self.room():
			self.changeLocation(room)
			self.printNearby(f"{~self} {verb}s from above!".capitalize())

		if self.anchor() is not self.parent.floor:
			# self.parent.floor.occupy(self)
			self.platform = self.parent.floor

		# TODO: add some collision checking for composition of the floor?
		if room.floor is not None and not self.hasStatus("submerged"):
			force = min(height,20*self.weight)
			self.takeDamage(force,"b")
			for item in contents:
				item.takeDamage(force//3,"b")
		return True


	# Try to add occupant to self.occupants
	def occupy(self,occupant,silent=False):
		assert not isinstance(self.parent,Creature) and occupant in self.parent
		if occupant in self.occupants:
			Print(occupant+f"is already on {-self}.")
			return False
		### TODO: instead of just checking ancestors, should check tether loops
		if occupant in self.ancestors():
			Print(f"{+self} is already carrying {-occupant}.")
			return False
		if isinstance(occupant,Creature) and occupant.riding is not None:
			occupant.removeRiding()
		occupant.removePlatform()

		if not self.checkVacancy(occupant):
			return False
		self.occupants.append(occupant)
		occupant.platform = self
		self.checkOccupantsWeight(silent=silent)
		return occupant in self.occupants


	# remove tethers when being obtained by a Creature
	# obtainer given because may be used in child class overrides
	def obtain(self,obtainer):
		if self.platform:
			self.platform.disoccupy(self)
		self.clearOccupants()
		if self.covering:
			self.covering.removeCover()
		self.platform = None


	# covered object from self.covering if exists
	def removeCovering(self,covered):
		if covered in self.covering:
			self.covering.remove(covered)
			covered.cover = None
			if covered.carrying:
				covered.carrying.removeCovering(covered)
			return True
		return False


	# remove platform tether if exists
	def removePlatform(self):
		if self.platform is not None:
			self.platform.disoccupy(self)
			self.platform = None
			return True
		return False


	# describe smell based on composition
	def smell(self,smeller):
		if smeller.hasStatus("apathy"):
			msg = f"You have the curse of apathy; {self+'smells like nothing...'}"
		elif self.composition in Data.scents:
			msg = Data.scents[self.composition]
		elif self.composition in Data.tastes:
			msg = Data.tastes[self.composition]
			msg = msg.replace("taste","smell").replace("tasting","smelling")
		else:
			msg = f"Smells like nothing in particular."
		smeller.Print(msg)
		return True


	# describe taste based on composition
	def taste(self,taster):
		if taster.hasStatus("apathy"):
			msg = "You have the curse of apathy; it tastes like nothing..."
		elif self.composition in Data.tastes:
			msg = Data.tastes[self.composition]
		elif self.composition in Data.scents:
			msg = Data.scents[self.composition]
			msg = msg.replace("scent","taste").replace("smelling","tasting")
		else:
			msg = f"Tastes like nothing in particular."
		taster.Print(msg)
		return True


	# try to use item (does nothing atm)
	def use(self,user):
		if user not in self.ancestors():
			Print(f"{+self} is not in your Inventory.")
			return False
		Print(f"You use {-self}")
		return True


	### Getters ###

	# get recursive chain of Item's parents, up to Room (which should have no parent)
	def ancestors(self):
		ancs = []
		ancestor = self
		while not isinstance(ancestor,Room) and ancestor is not None:
			ancestor = ancestor.parent
			ancs.append(ancestor)
		return ancs


	# for Items, anchor is always a platform (or None)
	# this differs for creatures
	def anchor(self):
		return self.platform


	# returns this object wrapped as a projectile (gives it a speed and other properties)
	def asProjectile(self):
		return Projectile(self.name,self.desc,self.weight,self.durability,
		self.composition,min1(self.weight//4),0,"b",item=self)


	# Used to create a generic Weapon() if this item is used to attack something
	def asWeapon(self):
		#TODO: if item is too large/heavy, make it two-handed
		return Weapon(self.name,self.desc,self.weight,self.durability,self.composition,
		min1(self.weight//4),0,0,0,"b")


	# determine cover available for obj from this Item
	def availableCover(self,obj):
		return self.Size() - obj.Size() - \
		sum(c.Size() for c in self.covering if c is not obj)


	# Items can despawn when the despawnTimer hits 0 and theyre in a room and not fixed
	def canDespawn(self):
		return self.despawnTimer is not None and \
			self.despawnTimer <= 0 and \
			isinstance(self.parent,Room) and \
			self.parent is not game.currentroom and \
			not self.fixed


	# checks if Creature can swim based on gear, weight ATHL, and MVMT
	def canSwim(self,liquidDensity=None):
		if liquidDensity is None:
			submerseComp = self.submersedIn()
			liquidDensity = Data.densities.get(submerseComp,1)

		density = Data.densities.get(self.composition,1)
		return density < liquidDensity


	# count objects with same name in parent
	# useful for knowing when to use 'a' or 'the' to describe an object
	def count(self,parent=None,key=None):
		if parent is None:
			parent = self.parent
		if key is None:
			key = lambda x: x.name == self.name
		return sum(1 for obj in parent if key(obj))


	# used so we don't bog down the player asking for which item they want
	# when two items are negligibly different
	def objMatch(self,other):
		if type(self) == type(other) and \
			self.name == other.name and \
			self.weight == other.weight and \
			self.durability == other.durability and \
			self.composition == other.composition and \
			self.rarity == other.rarity and \
			self.descname == other.descname and \
			self.status == other.status and \
			self.aliases == other.aliases and \
			self.parent == other.parent:
			return True
		return False


	# get total size of all occupants, excluding 'exclude' if given
	def occupantsSize(self,exclude=None):
		return sum(o.Size() for o in self.occupants if o is not exclude)


	# get total weight of all occupants, excluding 'exclude' if given
	def occupantsWeight(self,exclude=None):
		return sum(o.Weight() for o in self.occupants if o is not exclude)


	# get the Room that ultimately contains this Item at the root of its object tree
	def room(self):
		return self.ancestors()[-1]


	# get object size from weight, accounting for density based on composition
	def Size(self):
		# under normal conditions, size is equal to weight
		# account for density based on composition
		density = Data.densities.get(self.composition,1)
		return min1(self.weight // density)


	# gets the composition of the liquid the Item may be submersed in, if any
	def submersedIn(self):
		parentComp = getattr(self.parent,"composition",None)
		platformComp = getattr(self.platform,"composition",None)
		if parentComp in Data.liquids:
			return parentComp
		elif platformComp in Data.liquids:
			return platformComp
		else:
			return None


	# gets the first ancestor that isn't open, or the final ancestor (room)
	# used to determine the 'root' of a Creature's available surroundings
	def surroundings(self):
		# print(self,self.ancestors())
		for anc in self.ancestors():
			if getattr(anc,"closed",False):
				return anc
		return self.room()


	# get total size of Item and everything upon it
	def totalSize(self):
		return self.Size() + self.occupantsSize()


	# get the total weight of Item and everything upon it
	def Weight(self):
		return self.weight + self.occupantsWeight()


	### User Output ###

	# print Item description, including occupants if any
	def describe(self):
		Print(f"It's {~self}.")
		Print(f"{self.desc}")
		if len(bagObjects(self.occupants)) > 2:
			Print(listObjects("On it is ",self.occupants,"."))


	# the name of the item colored by rarity for display in inventory
	def displayName(self,count=1):
		color = Data.rarityColors.get(self.rarity,"w")
		if player.hasStatus("apathy"): color = "w"
		displayName = self.name
		if count > 1: displayName = self.plural + f" ({count})"
		return tinge(color,displayName)[0]


	# intelligently get name of this item in various grammatical forms
	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
		if det.lower() == "the":
			strname = self.name
		else:
			if len(bagObjects(self.occupants)) > 2:
				strname = f"{self.name} with things on it"
			elif self.occupants:
				strname = listObjects(f"{self.name} with ",self.occupants," on it")
			else:
				strname = self.descname

		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		# if self.determiner is not None and det == "":
		if self.determiner is not None:
			det = self.determiner
		if det == "" and n == 1:
			det = "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


	# print message to self
	def Print(self,*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,
	outfile=None):
		# in godmode we can see all prints
		if game.mode == 2:
			args.insert(0,f"[{self.id} {self.name}]:")
			color="k"
			return Print(*args,end=end,sep=sep,delay=delay,color=color,
			allowSilent=allowSilent,outfile=outfile)
		else:
			return False


	# for Items this is similar to self.Print, but distinct for Creatures
	def printNearby(self,*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,
	outfile=None):
		# in godmode we can see all prints
		if game.mode == 2:
			args.insert(0,f"[{self.id} {self.name}]:")
			color="k"
		if (player in self.surroundings() or game.mode == 2) and self is not player:
			return Print(*args,end=end,sep=sep,delay=delay,color=color,
			allowSilent=allowSilent,outfile=outfile)
		return


	# get reflexive pronoun for this Item
	def reflexive(self):
		if self.pronoun in Data.reflexives:
			return Data.reflexives[self.pronoun]
		else:
			return "itself"


	# just like self.Print except waits for user input afterwards
	def waitInput(self,text=None,end="\n",delay=None,color=None):
		# in godmode we can see all prints
		if game.mode == 2:
			text = f"[{self.id} {self.name}]:" + text if text else ""
			color="k"
			return waitInput(text=text,end=end,delay=delay,color=color)
		return False



# The Creature class is the main class for anything in the game that can act
# Creatures have 10 base stats, called traits
# They also have abilities; stats which are derived from traits through formulas
# For their contents, Creatures have an Inventory and a gear dict of equipped items
# In addition to platform anchor, Creatures can be carried or riding another Creature
class Creature(Item):
	def __init__(self,name,desc,weight,traits,hp=None,mp=0,money=0,inv=None,gear=None,
	love=0,fear=0,carrying=None,carrier=None,riding=None,platform=None,
	cover=None,composition="flesh",memories=None,appraisal=None,lastAte=0,lastSlept=0,
	lastBreathed=0,regenTimer=0,alert=False,lastSawPlayer=None,**kwargs):
		# Creatures have infinite durability, may not be fixed, and despawn after 1000
		super().__init__(name,desc,weight,-1,composition,fixed=False,longevity=1000,
		**kwargs)

		### Main Statistics

		# physical traits are strength, speed, skill, stamina, and constitution
		# mental traits are charisma, intelligence, wisdom, faith, and luck
		# traits should normally be between 1 and 20
		if type(traits) is int:
			traits = [traits]*10
		assert len(traits) == 10, "Creature traits must be a list of 10 integers"
		self.str = traits[0]
		self.spd = traits[1]
		self.skl = traits[2]
		self.stm = traits[3]
		self.con = traits[4]
		self.cha = traits[5]
		self.int = traits[6]
		self.wis = traits[7]
		self.fth = traits[8]
		self.lck = traits[9]
		self.hp = hp if hp else self.MXHP() 
		self.mp = mp if mp else self.MXMP()
		self.money = money

		### Contents

		self.inv = inv if inv else []
		# values of gear must either be EmptyGear() or an Item in the inventory
		self.gear = gear if gear else Data.initgear
		self.gear = {k:(v if v else EmptyGear()) for k,v in self.gear.items()}
		# when equipping gear in gear dict, these may be assigned
		self.weapon = EmptyGear()
		self.weapon2 = EmptyGear()
		self.shield = EmptyGear()
		self.shield2 = EmptyGear()

		### Behavior

		self.memories = memories if memories else set()
		self.appraisal = appraisal if appraisal else set()
		# love and fear are the creature's attraction and aversion to the player
		self.love = love
		self.fear = fear

		### Tethers

		# these represent relationships to other Items in the Creature's parent
		# during __init__(), these are given as object IDs or None
		# but are replaced with real object references in assignRefs()
		self.riding = riding
		self.carrying = carrying
		self.carrier = carrier
		self.platform = platform
		self.cover = cover

		### Timers

		# health regens very slowly
		self.regenTimer = regenTimer
		# eventually creatures get hungry and sleepy
		self.lastAte = lastAte
		self.lastSlept = lastSlept
		self.lastBreathed = lastBreathed
		# these attributes remain unused in the Player subclass
		self.alert = alert
		self.lastSawPlayer = lastSawPlayer


	### Dunder Methods ###

	def __repr__(self):
		traits = [self.str, self.spd, self.skl, self.stm, self.con,
		self.cha, self.int, self.wis, self.fth, self.lck]
		return f"{self.__class__.__name__}({self.name}, {traits}, " \
		f"{self.hp}, {self.mp}, {self.money})"


	def __getitem__(self, key):
		return self.gear[key]


	def __setitem__(self, key, value):
		assert key in self.gear, f"Creature {self.name} has no gear slot '{key}'"
		self.gear[key] = value


	### File I/O ###

	# take Item IDs from attributes and replace them with object references
	def assignRefs(self,parent):
		self.parent = parent
		self.carrying = game.itemRegistry[self.carrying]
		self.carrier = game.itemRegistry[self.carrier]
		self.riding = game.itemRegistry[self.riding]
		self.cover = game.itemRegistry[self.cover]
		self.covering = [game.itemRegistry[o] for o in self.covering]
		self.occupants = [game.itemRegistry[o] for o in self.occupants]
		self.platform = game.itemRegistry[self.platform]

		# ensure platform is assigned if unanchored
		if self.anchor() is None and not self.hasStatus("flying"):
			# creatures don't have floors, and surfaces may not have a platform
			if not isinstance(self.parent,Creature) and not self in self.parent.surfaces:
				self.platform = self.parent.floor

		# replace gear IDs with actual objects, replace None with EmptyGear()
		uncompGear = {}
		for slot, id in self.gear.items():
			if id == "carrying":
				assert self.carrying is not None, f"Creature {self.name} has gear " \
				f"slot '{slot}' set to 'carrying' but is not carrying anything."
				uncompGear[slot] = self.carrying
			# if id is already the real object, add it to inventory if needed
			elif type(id) not in (int, EmptyGear, type(None)):
				assert self.add(id)
				uncompGear[slot] = id
			elif id is None or id is EmptyGear():
				uncompGear[slot] = EmptyGear()
			else:
				uncompGear[slot] = game.itemRegistry[id]
		self.gear = uncompGear

		for slot,item in self.gear.items():
			assert item is EmptyGear() or item in self.inv or item is self.carrying, \
			f"Creature {self.name} has item in gear slot '{slot}' not in inventory"
			assert isinstance(item,Creature) or item.slots is None or slot in item.slots, \
			f"Creature {self.name} has item {item.name} in invalid slot '{slot}'"

		assert self.invWeight() + self.carryWeight() <= 2*self.BRDN(), f"Creature " \
		f"{self.name} is carrying too much weight. BRDN is {self.BRDN()}, " \
		f"but total weight is {self.invWeight() + self.carryWeight()}"


	# returns a dict which contains all the necessary information to store
	# this object instance as a JSON object when saving the game
	# replace object references with their Item IDs
	def convertToJSON(self):
		jsonGear = {}
		for slot, item in self.gear.items():
			if isinstance(item,Creature):
				jsonGear[slot] = "carrying"
			elif item is EmptyGear():
				jsonGear[slot] = None
			else:
				jsonGear[slot] = item.id

		jsonDict = super().convertToJSON()
		jsonDict["carrying"] = self.carrying.id if self.carrying else None
		jsonDict["carrier"] = self.carrier.id if self.carrier else None
		jsonDict["riding"] = self.riding.id if self.riding else None
		jsonDict["cover"] = self.cover.id if self.cover else None
		jsonDict["covering"] = [c.id for c in self.covering] if self.covering else None
		del jsonDict["occupants"]

		dictkeys = list(jsonDict.keys())
		delAttrs = ("gear","weapon","weapon2","shield","shield2")
		# these attributes do not get stored between saves
		for key in dictkeys:
			if key.lower() in Data.traits or key in delAttrs:
				del jsonDict[key]
		jsonDict["gear"] = jsonGear
		# convert traits to a form more easily writable in a JSON object
		jsonDict["traits"] = [self.str,self.skl,self.spd,self.stm,self.con,
		self.cha,self.int,self.wis,self.fth,self.lck]

		# delete attributes that should be given as defaults
		del jsonDict["fixed"], jsonDict["longevity"], jsonDict["durability"]
		return jsonDict


	### Operation ###

	# try to add an Item to Inventory, it will fail if the inventory is too heavy
	def add(self,I):
		# spawn new object if given as a string
		newlySpawned = False
		if isinstance(I,str) or I.id is None:
			I = game.spawn(I)
			newlySpawned = True

		# check if can obtain item
		if not self.canObtain(I,silent=True):
			if newlySpawned:
				I.displace()
			return False

		# Serpens can't get added to inventory
		if isinstance(I,Serpens):
			return True

		alphabetical = lambda x: (x.name.lower(), x.name)
		insort(self.inv,I,key=alphabetical)
		I.parent = self
		I.nullDespawn()
		if self is player:
			self.display()
		return True


	# add a status condition, print message unless silent
	def addStatus(self,name,dur,stackable=True,silent=False):
		if self.hasStatus(name) and not stackable:
			return False
		if self.hasStatus(name,dur):
			return False
		if self is not player and name in Data.privateStatus:
			silent = True
		if not self.hasStatus(name) and not silent:
			allowSilent = self is not player
			color = "w"
			if name in Data.buffs | Data.blessings: color = "g"
			if name in Data.debuffs | Data.curses: color = "r"
			displayName = name
			if name in Data.curses: displayName = "the curse of " + name
			if name in Data.blessings: displayName = "the blessing of " + name
			elif name in Data.curses | Data.blessings:
				self.Print(self+f"have {displayName}.",color=color,allowSilent=allowSilent)
			elif name == "asleep":
				self.Print(self+f"falls {name}.",allowSilent=allowSilent)
			else:
				self.Print(self+f"are {name}.",color=color,allowSilent=allowSilent)

		# lift off ground if added flying
		if name == "flying" and self.platform is self.parent.floor:
			self.platform = None
		insort(self.status,[name,dur])

		if name in Data.blessings | Data.curses:
			self.checkStatus()
		if self is player:
			self.display()
		return True


	# not used for Creatures but defined for consistency with Player subclass
	def awaken(self,wellRested=True):
		pass


	# change location to a new Room/Container, return True on success
	def changeLocation(self,newparent):
		assert not isinstance(newparent,Creature)
		# shouldn't be changing rooms alone if riding or being carried
		if self.carrier and self.carrier.parent is not newparent:
			return False
		if self.riding and self.riding.parent is not newparent:
			return self.riding.changeLocation(newparent)
		self.removeCover()
		self.clearCovering()

		prevparent = self.parent
		if prevparent:
			prevparent.exit(self)
		if self is player and isinstance(newparent,Room):
			game.changeRoom(newparent)
		# when not riding or being carried, platform becomes new room's floor
		if self.riding is None and self.carrier is None:
			self.platform = newparent.floor
		if self.hasStatus("flying"):
			self.platform = None

		newparent.enter(self)

		# propagate location change to creatures riding or being carried
		if self.carrying and self.carrying.parent is not self.parent:
			self.carrying.changeLocation(newparent)
		for occupant in self.occupants:
			if occupant.parent is not self.parent:
				occupant.changeLocation(newparent)
		assert self.carrying is None or self.carrying.parent is self.parent
		return True


	# change posture to given posture, removing other postures
	def changePosture(self,posture,silent=False):
		if posture is None:
			posture = "standing"
		if not posture.endswith("ing"):
			posture = ("sitt" if posture == "sit" else posture) +"ing"

		validPostures = ("standing","crouching","sitting","laying")
		assert posture in validPostures
		if self.posture() == posture:
			return False

		for p in validPostures:
			if p != posture:
				self.removeStatus(p,silent=silent)
		# standing is the absence of the other conditions
		if posture != "standing":
			self.addStatus(posture,-4,silent=silent)
		if posture in ("standing","crouching"):
			self.removeStatus("cozy",-4,silent=silent)

		self.checkHidden()
		return self.posture() == posture


	def checkBreathing(self):
		# hunger takes longer with more endurance
		sinceLastBreathed = game.time - self.lastBreathed
		if sinceLastBreathed > self.ENDR() // 2 and self.hasStatus("breathless"):
			# add drowning before removing breathless because removeStatus will recur here
			self.addStatus("drowning",-2)
			self.removeStatus("breathless",silent=True)
		elif sinceLastBreathed > self.ENDR() // 3 and \
		not self.hasAnyStatus("breathless","drowning"):
			self.Print("You can't hold your breath much longer...")
			self.addStatus("breathless",-2,silent=True)
		elif sinceLastBreathed <= self.ENDR() // 3:
			self.removeStatus("breathless",silent=True)
			self.removeStatus("drowning")


	# add/remove hidden status based on cover
	def checkHidden(self):
		transparent = ("glass","ice","water")
		if getattr(self.parent,"closed",False):
			self.addStatus("hidden",-4)
		elif self.coverBonus() >= 5 and self.cover.composition not in transparent:
			self.addStatus("hidden",-4)
		elif self.coverBonus() < 5:
			self.removeStatus("hidden",-4)


	# add/remove hindered status based on inventory weight and BRDN
	def checkHindered(self):
		if self.invWeight() + self.carryWeight() > self.BRDN():
			if not self.hasStatus("hindered",-4):
				self.Print("Your Inventory grows heavy.")
			if not self.hasStatus("hindered",-4):
				self.addStatus("hindered",-4)

		if self.invWeight() + self.carryWeight() <= self.BRDN():
			if self.hasStatus("hindered",-4):
				self.Print("Your Inventory feels lighter.")
				self.removeStatus("hindered",-4)


	# unused for Creatures, but used in Player subclass
	def checkHungry(self):
		return False


	# TODO: if creature changes size, we need to check platform vacancy and parent capacity
	def checkSize(self):
		pass


	# check all status conditions that may need updating
	def checkStatus(self):
		# self.checkBreathing()
		self.checkHungry()
		self.checkTired()
		self.checkHindered()
		self.checkHidden()
		self.checkSubmersion()


	# unused for Creatures, but used in Player subclass
	def checkTired(self):
		return False


	# called when a creature's hp hits 0
	def death(self):
		self.timeDespawn()
		self.addStatus("dead",-2)
		self.changePosture("laying",silent=True)
		Print(f"{+self} died.",color="o")

		if self.hasStatus("anointed"):
			return self.reanimate()

		self.removeRiding(silent=True)
		self.removeCarry(silent=True)

		self.descname = f"dead {self.descname}"
		self.aliases.extend(["dead "+a for a in self.aliases])

		n = diceRoll(3,player.LOOT(),-2)
		self.parent.add(Serpens(n))
		Print(f"Dropped §{n}.",color="g")

		if game.whoseTurn is player:
			r = self.rating()
			# xp granted generally scales with rating
			xp = halfRoll(r)
			player.gainxp(xp)


	# remove all tethers and references with this Creature, then destroy it
	def destroy(self,silent=True):
		if not silent:
			self.Print(f"{+self} disappears.")
		if self.cover:
			self.removeCover()
		self.clearCovering()
		self.clearOccupants()
		if self.carrier:
			self.carrier.removeCarry()
		if self.carrying:
			self.carrying.fall()
		self.removeCarry(silent=silent)
		self.removePlatform()
		self.removeRiding(silent=silent)

		# may have already been removed from parent
		if self.parent and self in self.parent:
			self.parent.remove(self)
		# TODO: drop all items from inventory? or just some important ones?
		super().destroy(silent=True)


	# TODO: is this function necessary?
	# drop Inventory Items if over capacity
	def ejectInventory(self):
		# drop any items over capacity
		if self.invWeight() + self.carryWeight() > 2*self.BRDN():
			self.Print("Your Inventory overflows!",color="o")
		while self.invWeight() + self.carryWeight() > 2*self.BRDN():
			item = max(self.inv, key=lambda x: x.Weight())
			self.remove(item)
			self.Print(f"You drop {-item}.")


	# heals hp a given amount
	def heal(self,heal,overflow=False):
		if self.hp + heal > self.MXHP() and not overflow:
			heal = self.MXHP() - self.hp
		if heal <= 0 or not self.isAlive():
			return 0
		self.hp += heal
		if self is player:
			self.display()
		self.Print(f"You healed {heal} HP.",color="g")
		return heal


	# pass time, take damage from status conditions, regen health/mana
	def passTime(self,t):
		super().passTime(t)

		if not self.hasStatus("submerged"):
			self.lastBreathed = game.time
		self.checkBreathing()
		self.checkStatus()

		# take damage from damaging status conditions
		for condition in {c for (c,d) in self.status}:
			if condition in Data.conditionDmg:
				factor, dmgType = Data.conditionDmg[condition]
				dmg = halfRoll(factor) - halfRoll(self.LCK())
				self.takeDamage(dmg,dmgType)

		# natural healing is faster with a higher endurance
		if self.hasAnyStatus("hungry","starving") and not self.hasStatus("mending"):
			self.regenTimer = 0
		elif not self.hasStatus("dead"):
			self.regenTimer += t
			if self.regenTimer >= 50 - self.ENDR() or self.hasStatus("mending"):
				self.regenTimer = 0
				h = 5 if self.hasAnyStatus("cozy","mending") else 1
				self.heal(h)
				# TODO: do mana resurgence at separate rate than healing
				self.resurge(1)


	# reanimate from dead status with 1 hp
	def reanimate(self):
		if not self.hasStatus("dead"):
			return False
		self.hp = 1
		self.nullDespawn()
		if self is player:
			delay(1)
			self.waitInput("You reawaken!",color="g")
			self.removeStatus("dead")
		else:
			Print(f"{+self} has been reanimated!")
			self.removeStatus("dead")
		return True


	# remove an Item from Inventory
	# if it was equipped, unequip it. if it has a Drop() method, call that
	# check if still hindered
	def remove(self,I,silent=False):
		for slot,obj in self.gear.items():
			if I is obj:
				self.unequip(slot,silent=silent)
		if I is self.carrying:
			self.removeCarry(silent=silent)
		if I in self.inv:
			self.inv.remove(I)
		if hasMethod(I,"Drop"):
			I.Drop(self)
		if not silent:
			self.checkStatus()


	# remove any status condition with reqName and reqDuration
	# if reqName or reqDuration are None, remove all
	def removeStatus(self,reqName=None,reqDuration=None,silent=False):
		wasSleeping = self.hasStatus("asleep")
		wellRested = False
		anyRemoved = False

		# copy to prevent removing-while-iterating errors
		for name,duration in self.status.copy():
			if reqName in (name,None) and reqDuration in (duration,None):
				self.status.remove([name,duration])
				anyRemoved = True
				# TODO: this is hacky, it should check the total duration of time slept
				# needs a counter sleepTime in the class
				if name == "asleep" and duration < 30:
					wellRested = True
				if name != "asleep" and not self.hasStatus(name):
					if silent:
						continue
					verb = conjugate(+self,"has")
					if name in Data.curses:
						Print(f"{+self} no longer {verb} the curse of {name}.")
					elif name in Data.blessings:
						Print(f"{+self} no longer {verb} the blessing of {name}.")
					else:
						verb = conjugate(+self,"is")
						Print(f"{+self} {verb} no longer {name}.")

		# this recurs into removeStatus, so guard to prevent infinite loop
		if anyRemoved:
			self.checkStatus()
		if wasSleeping and not self.hasStatus("asleep"):
			self.awaken(wellRested=wellRested)
		if self is player:
			self.display()
		return anyRemoved


	# replace this object with newObj in parent and all tethers
	# newObj may be an object ID string, in which case it is spawned first
	def replace(self,newObj):
		parent = self.parent
		if isinstance(newObj,str) or newObj.id is None:
			newObj = game.spawn(newObj)
		# if we fail to place this object in parent, displace the newObj
		if not self.parent.replaceObj(self,newObj):
			self.destroy()
			return newObj.displace(self.parent)

		for covered in self.covering.copy():
			covered.removeCover(silent=True)
			covered.addCover(newObj)
		for occupant in self.occupants.copy():
			occupant.replaceObj(self,newObj)
		# if newObj was destroyed by new rider, then we can end here
		if not newObj.parent:
			return self.destroy()

		# TODO: when replacing creature with creature, copy carrying and riding?
		if self.carrying:
			c = self.carrying
			# parent is used to removeCarry, so reassign it temporarily
			self.parent = parent
			self.removeCarry(silent=True)
			self.parent = None
			c.fall(self.Size()//5)

		if self.carrier:
			self.carrier.replaceObj(self,newObj)
		elif self.riding:
			r = self.riding
			self.removeRiding()
			newObj.fall(r.Size()//5)
		elif self.platform:
			p = self.platform
			self.removePlatform()
			if isinstance(p,Portal) and p.canPass(newObj) and p.canAdd(newObj):
				p.transfer(newObj)
			else:
				p.occupy(newObj)

		self.destroy()
		# newObj may have already been destroyed
		if newObj.parent:
			game.replaceID(self,newObj)
			return newObj


	# replace Creature with a Creature or Item in this Creature's tethers
	# replace riding with platform, carrying with inventory item
	def replaceCreature(self,oldObj,newObj):
		assert isinstance(oldObj,Creature)
		if self.riding is oldObj:
			self.removeRiding(silent=True)
			if isinstance(newObj,Creature):
				newObj.ride(self)
			else:
				newObj.occupy(self)

		if self.carrying is oldObj:
			carrySlot = "left" if self["left"] is oldObj else "right"
			carrySlot = carrySlot if self[carrySlot] is oldObj else None
			self.removeCarry(silent=True)
			if isinstance(newObj,Creature):
				newObj.carry(newObj,silent=True)
			elif self.canObtain(newObj,silent=True):
				self[carrySlot] = newObj
				self.ObtainItem(newObj,silent=True)
				self.equipInHand(newObj,slot=carrySlot)
			else:
				return False
		self.checkStatus()


	# replace Item with a Creature or Item in tis Creature's tethers
	# if newObj is creature, replaced equipped gear with carried
	def replaceItem(self,oldObj,newObj):
		assert oldObj in self and not isinstance(oldObj,Creature)
		if isinstance(newObj,Creature):
			# if Item is in gear, note which slot
			carriedSlot = "left" if self["left"] is oldObj else "right"
			carriedSlot = carriedSlot if self[carriedSlot] is oldObj else None

			self.remove(oldObj,silent=True)
			if not self.parent.canAdd(newObj):
				return False
			self.parent.add(newObj)

			# if it was equipped in gear, carry the creature instead
			if carriedSlot and not self.carrying:
				self.carry(newObj,slot=carriedSlot)
		else:
			self.remove(oldObj,silent=True)
			if not self.canObtain(newObj):
				return False
			self.ObtainItem(newObj,silent=True)

		for slot,obj in self.gear.items():
			if oldObj is obj:
				self[slot] = newObj

		self.checkStatus()
		return True


	# replace an object in this Creature's tethers
	def replaceObj(self,old,new):
		if isinstance(old,Creature):
			return self.replaceCreature(old,new)
		elif isinstance(old,Item):
			return self.replaceItem(old,new)
		else:
			return None


	# regain mp a given amount
	def resurge(self,mana,overflow=False):
		if self.mp + mana > self.MXMP() and not overflow:
			mana = min0(self.MXMP() - self.mp)
		if mana <= 0:
			return 0
		self.mp += mana
		if self is player:
			self.display()
		self.Print(f"You regained {mana} MP.",color="b")
		return mana


	# takes incoming damage, accounts for damage vulnerability or resistance
	def takeDamage(self,dmg,type):
		if self.hasStatus("dead"):
			return False
		prevhp = self.hp
		if(f"{type} vulnerability" in self.status): dmg *= 2
		if(f"{type} resistance" in self.status): dmg //= 2
		if(f"{type} immunity" in self.status): dmg = 0
		# bludgeoning damage can't kill you in one hit
		if type in ("b","d") and self.hp > 1:
			self.hp = min1(self.hp-dmg)
		# hp lowered to a minimum of 0
		else:
			self.hp = min0(self.hp-dmg)
		total_dmg = prevhp - self.hp

		p = "!" if self.hasStatus("asleep") or total_dmg > self.MXHP()//4 else "."
		color = "w"
		if self is player and total_dmg > 0:
			delay(0.5)
			color = "r"
		typeDisplay = "" if type == "e" else Data.dmgtypes[type] + " "
		msg = f"{+self} took {total_dmg} {typeDisplay}damage{p}"
		self.Print(msg,color=color)
		self.printNearby(msg,color=color)
		if self is player:
			self.display()
			delay(0.5)
		if self.hp == 0:
			return self.death()
		if total_dmg > 0 and self.hasStatus("asleep"):
			self.removeStatus("asleep")


	# ensure fear is within bounds
	def updateFear(self,fearMod):
		self.fear = bound(fearMod,-100,100)


	# ensure love is within bounds
	def updateLove(self,loveMod):
		self.love = bound(loveMod,-100,100)


	# update money by given amount, print new total
	def updateMoney(self,money):
		self.money += money
		color = "g" if money > 0 else "w"
		if money == 0:
			self.Print(f"You have §{self.money}.")
		else:
			self.Print(f"You have §{self.money}!",color=color)
		if self is player:
			self.display()


	### Interaction ###

	# add a Creature to be carried by this Creature, replace gear in given slot
	def addCarry(self,creature,slot="left",silent=False):
		assert isinstance(creature,Creature)
		assert self.carrying is None
		assert creature.anchor() is None
		otherSlot = "right" if slot == "left" else "left"
		self.unequip(slot)
		if getattr(self[otherSlot],"twohanded",False):
			self.unequip(otherSlot)

		self.carrying = creature
		creature.carrier = self

		creature.parent.remove(creature)
		self.parent.add(creature)

		self[slot] = creature
		self.checkStatus()


	# add cover to this Creature, attempt to hide
	def addCover(self,cover):
		if self.cover is cover:
			return
		cover.addCovering(self)
		if self.carrying:
			self.carrying.addCover(cover)
		self.checkHidden()


	# add riding tether
	def addRiding(self,creature):
		assert isinstance(creature,Creature)
		assert self.anchor() is None
		self.riding = creature


	# only used by equip and unequip to reassign several attributes
	# specifically, weapon, weapon2, shield, shield2
	def assignWeaponAndShield(self):
		#if unassigned, attributes are empty, self.weapon is always assigned
		self.weapon2 = EmptyGear()
		self.shield = EmptyGear()
		self.shield2 = EmptyGear()

		# assign weapon and weapon2 based on types of gear in left and right
		if isinstance(self["right"],Weapon) and isinstance(self["left"],Weapon):
			self.weapon2 = self["left"]
		elif isinstance(self["left"],Weapon) and not isinstance(self["right"],Weapon):
			self.weapon = self["left"]
		elif isinstance(self["left"],Item) and self["right"] == EmptyGear():
			self.weapon = self["left"]
		else:
			self.weapon = self["right"]

		# ensure that weapons are of type Weapon
		if not isinstance(self.weapon,Weapon):
			if hasMethod(self.weapon,"asWeapon"):
				self.weapon = self.weapon.asWeapon()
		if not isinstance(self.weapon2,Weapon):
			if hasMethod(self.weapon,"asWeapon"):
				self.weapon2 = self.weapon.asWeapon()

		# assign shield and shield2 based on types of gear in left and right
		if isinstance(self["right"],Shield) and isinstance(self["left"],Shield):
			self.shield = self["right"]
			self.shield2 = self["left"]
		elif isinstance(self["right"],Shield):
			self.shield = self["right"]
		elif isinstance(self["left"],Shield):
			self.shield = self["left"]


	# be bombarded by a projectile with a chance to hit
	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		dodge = self.EVSN()
		if missile.speed < self.MVMT():
			# TODO: determine how they'll decide if they catch here
			if percentChance(50) and hasMethod(self,"Catch"):
				dodge = -10
				if self.Catch(missile):
					return True
		if percentChance(bound(missile.aim+missile.speed-dodge,1,99)):
			return missile.collide(self)
		return False


	# try to carry this Creature in carrier's gear
	def carry(self,carrier,silent=False):
		assert isinstance(carrier,Creature)
		if self.checkTetherLoop(carrier,self,"carry"):
			return False
		if self > carrier.BRDN()//2:
			carrier.Print(f"{+self} is too heavy to carry.")
			return False
		if self.carrier:
			self.Print(f"{+self} is already being carried by {self.carrier}.")
			if roll(carrier.ATHL()) > roll(self.carrier.ATHL()):
				carrier.Print(f"You wrest {-self} away from {-self.carrier}!")
			else:
				carrier.Print(f"{+self.carrier} holds onto {-self}.")
				return False

		if not self.restrain(carrier):
			return False

		if self.carrier:
			self.carrier.removeCarry()	
		self.removeRiding()
		self.removePlatform()

		self.Dismount(posture="stand")
		carrier.addCarry(self)

		if carrier.cover is not self.cover:
			self.addCover(carrier.cover)
		return True


	# if the Item is armor, equip it, otherwise return False
	def equipArmor(self,I,slot=None):
		assert I in self
		if slot == None:
			slot = I.slots[0]
		if slot not in I.slots:
			return False
		if slot not in self.gear.keys():
			return False
		self[slot] = I
		I.equip()
		return True


	# unequips the lefthanded item, moves righthanded item to left,
	# equips the new item in right hand
	# if the new item is twohanded, set lefthand to EmptyGear()
	# calls the new item's equip() method if it has one
	def equipInHand(self,I,slot="right"):
		assert I in self or I is self.carrying
		if I is self["right"] or I is self["left"]:
			return
		if getattr(self["right"],"twohanded",False):
			self.unequip("right")

		if getattr(I,"twohanded",False):
			self.unequip("right")
			self.unequip("left")
		elif slot == "right" and not self.carrying:
			self.unequip("left")
			self["left"] = self["right"]
		elif slot == "left" and self["right"] is EmptyGear:
			self["right"] = self["left"]
		else:
			self.unequip(slot)

		self[slot] = I
		self.assignWeaponAndShield()
		if hasMethod(I,"equip"): I.equip(self)
		self.checkStatus()


	# Creature falls through rooms accumulating fall height until hitting floor, 
	# then take damage and set platform to room's floor
	def fall(self,height=0,room=None):
		if self.riding or self.carrier:
			return self.anchor().fall(height,room)

		verb = "fall"
		if self.hasStatus("submerged"):
			if self.canSwim():
				return False
			verb = "sink"

		if player in self.occupants or player is self.carrying or player is self:
			waitInput(self+f"{verb}s!",color="o")
		else:
			self.printNearby(self+f"{verb}s.",color="o")

		if self.hasStatus("flying"):
			self.printNearby("But"+(self*"is flying."))
			return False

		if room is None:
			room = self.room()
		while (room.floor is None or room.floor.composition in Data.liquids) and \
		"down" in room.links:
			height += room.capacity // 5 # approximate height of room
			room = room.links["down"]
		if room != self.room():
			if self.carrying:
				self.carrying.fall(height,room)
			if self is player:
				ellipsis()
			self.changeLocation(room)
			self.printNearby(f"{~self} {verb}s from above!".capitalize())

		# if self.anchor() is not self.parent.floor:
		# 	# self.parent.floor.occupy(self)
		# 	self.platform = self.parent.floor

		force = min(height,20*self.weight)
		if not self.hasAnyStatus("fleetfooted","submerged") and room.floor is not None:
			if force > 0:
				self.takeDamage(force,"b")
				for rider in self.occupants:
					rider.takeDamage(force//3,"b")
			self.changePosture("laying")
		return True


	# occupying a Creature is equivalent to riding it
	def occupy(self,creature,silent=False):
		return self.ride(creature,silent=silent)



	def offer(self,I):
		self.Print(f"{+self} ignores your offer.")



	# remove carrying tether if exists
	def removeCarry(self,silent=False):
		if self.carrying is None:
			return
		slot = "left" if self["left"] is self.carrying else "right"
		assert self[slot] is self.carrying

		self[slot] = EmptyGear()
		if not silent:
			self.Print(f"You drop {-self.carrying}.")
			self.carrying.Print(f"{+self} is no longer carrying you.")
		self.carrying.carrier = None
		self.carrying.platform = self.parent.floor
		self.carrying.removeStatus("restrained",-4,silent=True)
		self.carrying = None
		self.checkStatus()


	# remove cover if exists
	def removeCover(self,silent=False):
		if self.cover:
			self.Print(f"You are no longer behind {-self.cover}.") if not silent else None
			self.cover.removeCovering(self)
		self.cover = None
		if self.carrying:
			self.carrying.removeCover(silent=silent)
		self.checkHidden()


	# remove riding tether if exists
	def removeRiding(self,silent=False):
		if self.riding is not None:
			# store this because dismounting affects riding.print
			wasRiding = self.riding
			self.riding.disoccupy(self)
			self.riding = None
			if not silent:
				self.Print(f"You are no longer riding {-wasRiding}.")
				wasRiding.Print(f"{+self} is no longer riding {-wasRiding}.")


	# attempt to restrain this Creature
	def restrain(self,restrainer,item=None):
		if not self.isAlive():
			return True
		if not self.isFriendly() and self.canMove():
			if item != None:
				#TODO: add restraining with items? like rope??
				pass
			if self.ATHL() > restrainer.ATHL():
				restrainer.Print(f"{+self} resists restraint!",color="r")
				return False
			if self.EVSN() > restrainer.ATHL():
				restrainer.Print(f"{+self} evades restraint!",color="r")
				return False
		self.addStatus("restrained",-4,silent=True)
		restrainer.Print(f"You restrain {-self}!",color="g")
		return True


	# attempt to ride this Creature
	def ride(self,rider,silent=False):
		if self.checkTetherLoop(rider,self,"ride"):
			print("TETHER LOOPS")
			return False
		if rider > self.BRDN()//2:
			rider.Print(f"You are too heavy to ride {-self}.")
			rider.fall(self.Size()//5)
			return False
		if rider.Size()//2 > self.Size():
			rider.Print(f"{+self} is too small to ride.")
			return False

		rider.removeRiding()
		rider.removePlatform()

		if rider.Size() + self.occupantsSize() > self.Size():
			pushOff = max(self.occupants, key=lambda x: x.Size())
			self.Print(f"{+pushOff} is already riding {self}.")
			if roll(rider.ATHL()) > roll(pushOff.ATHL()):
				rider.Print(f"You push {-pushOff} off of {-self}.")
				pushOff.Print(f"{+rider} pushes you off of {-self}.",color="r")
				pushOff.removeRiding()
				pushOff.fall(self.Size()//5)
			else:
				pushOff.Print(f"{+pushOff} hold onto {-self}.")
				rider.Print(f"You don't manage to occupy {-self}",color="r")
				rider.fall(self.Size()//5)
				return False
		if rider.Size() + self.occupantsSize() > self.Size():
			rider.Print(f"{+self} doesn't have enough space to ride.")
			rider.fall(self.Size()//5)
			return False

		contest = not self.isFriendly() and self.canMove()
		if contest:
			rider.Print(f"{+self} struggles.",color="o")
			contestPenalty = -10 if self.posture() == "laying" else 0
			contestBonus = 10 if rider.posture() == "crouching" else 0
			athl_contest = self.ATHL() - rider.ATHL() + contestBonus + contestPenalty
			if athl_contest > 0:
				rider.Print(f"{+self} shakes you off!",color="r")
				fallHeight = athl_contest - rider.ATHL()
				if fallHeight < 0:
					fallHeight = 0
				rider.fall(fallHeight)
				return False

		# TODO: some additional checking to prevent too many riders here?
		rider.addRiding(self)
		self.occupants.append(rider)
		rider.riding = self

		# rider.Print(f"You ride {-self}.",color="g" if contest else "w")
		rider.printNearby(rider+f"rides {-self}.")
		return True


	# sever tethers and change location to new Container or Room
	def teleport(self,newParent):
		if newParent is self.parent:
			self.Print("You are already there.",color="w")
			return
		if self.carrier:
			self.carrier.removeCarry(silent=True)
		self.removePlatform()
		self.removeCarry()
		self.removeRiding()
		self.removeCover()
		self.clearCovering()
		self.clearOccupants() # should do nothing, but just in case
		self.waitInput("You teleport!",color="b")
		if newParent.canAdd(self):
			self.changeLocation(newParent)
		else:
			self.Print("Teleportation failed...",color="r")
		self.changePosture("stand")


	# finds the slot in which item resides, sets it to EmptyGear()
	# calls the item's unequip() method if it has one
	def unequip(self,slot,silent=False):
		assert slot in self.gear, f"'{slot}' is not a valid gear slot."
		I = self[slot]
		if I is EmptyGear():
			return False
		if I is self.carrying:
			self.removeCarry(silent=silent)
		else:
			self[slot] = EmptyGear()
			self.assignWeaponAndShield()
			if not silent:
				self.Print(f"You unequip your {I}.")
			if hasMethod(I,"unequip"): I.unequip()


	### Behavior ###

	# take an action in the game according to regimen
	def Act(self):
		pass


	# dismount from current platform or riding creature
	def Dismount(self,posture=None,silent=False):
		if self.anchor() is None or self.platform is self.parent.floor:
			self.Print("You're not on anything.") if not silent else None
			return False
			
		occupyPrep = getattr(self.anchor(),"occupyprep","on")
		disoccupyPrep = "out of" if occupyPrep == "in" else "off"
		if self.riding:
			if not silent:
				self.Print(f"You get {disoccupyPrep} {-self.riding}.")
			self.removeRiding(silent=True)
		if self.platform and self.platform != self.parent.floor:
			if not silent:
				self.Print(f"You get {disoccupyPrep} {-self.platform}.")
			self.platform.disoccupy(self)

		if not self.hasStatus("flying"):
			# self.parent.floor.occupy(self)
			self.platform = self.parent.floor
		if self.anchor() in (None,self.parent.floor):
			self.changePosture(posture,silent=True)
		return True


	# eat something
	def Eat(self,food):
		if not hasMethod(food,"consume"):
			self.Print(f"You can't eat {-food}.")
			return False
		food.parent.remove(food)
		food.consume()


	def Emerge(self):
		if not self.hasStatus("submerged"):
			self.Print("You are not submerged.")
			return False
		if not self.canSwim():
			self.Print("You can't surface because you can't swim!")
			return False
		self.removeStatus("submerged")
		self.lastBreathed = game.time
		self.checkBreathing()


	# hide behind an Item if it provides cover
	def Hide(self,I,posture):
		if self.carrier:
			return False

		if self.parent is not I.parent:
			self.Print(f"You can't, you are {self.parent.passprep} {-self.parent}.")
			return False
		if I is self.cover:
			self.Print(f"You are already hidden behind {-I}.")
			return False
		tip = " Try crouching." if posture != "crouch" else ""
		if I.availableCover(self) <= 0:
			self.Print(f"{+I} is too small to hide behind.{tip}")
			return False
		if I.fixed: # can't hide behind room fixtures
			self.Print(f"You can't hide behind {-I}.")
			return False

		if hasMethod(I,"HideBehind"):
			I.HideBehind(self)

		self.Print(f"You {posture} behind {-I}.")
		self.changePosture(posture,silent=True)
		I.addCovering(self)
		self.checkHidden()
		return True


	# lick something
	def Lick(self,licker):
		# TODO: make creatures evade this or try to
		Print("Yuck!")


	# mount an Item or Creature, add it as platform or riding tether
	# or traverse if it is an open Container
	def Mount(self,anchor,posture="sit"):
		if anchor is self.anchor():
			if not self.changePosture(posture,silent=True):
				self.Print(f"You are already {self.posture()} on {-anchor}.")
				return False
		elif anchor is self.parent.floor and not self.hasStatus("flying"):
			return self.Dismount(posture=posture)
		elif self.anchor() not in (None,self.parent.floor):
			self.Print(f"You can't, you are {self.position()}.")
			return False
		if not hasMethod(anchor,"ride") and not hasMethod(anchor,"occupy"):
			self.Print(f"{+anchor} cannot be mounted.")
			return False

		if hasMethod(anchor,"traverse") and not getattr(anchor,"closed",False):
			if not getattr(anchor,"closed",True):
				self.Print(f"{+anchor} is open.")
			return anchor.traverse(self,verb=posture)
		if anchor is self.platform or anchor is self.riding:
			pass
		elif self.checkTetherLoop(self,anchor,"get on"):
			return False
		else:
			if anchor == anchor.parent.floor:
				self.platform = anchor
			elif not anchor.occupy(self):
				return False

		if self.platform is anchor:
			self.Print(f"You {posture} on {-anchor}.")
		if self.platform is anchor or self.riding is anchor:
			self.removeCover()
			self.changePosture(posture,silent=True)
		return True


	# takes an item from a source location
	# checks if it can be obtained, removes from old parent, adds to inventory
	def ObtainItem(self,I,silent=False):
		assert isinstance(I,GameObject)
		oldParent = I.parent
		if isinstance(oldParent,Room): suffix = ""
		elif self in I.ancestors(): suffix = " from your " + oldParent.name
		elif oldParent: suffix = f" from {-oldParent}"
		else: suffix = ""
		strname = I.nounPhrase('a' if self.count()>1 else 'the')

		if self.canObtain(I):
			if oldParent:
				oldParent.remove(I)
			assert self.add(I)
			if not silent:
				self.Print(f"You take {strname}{suffix}.")
				if self is player:
					game.setPronouns(I)
			I.obtain(self)
			# check if hindered after obtaining item
			self.checkStatus()
			return True
		return False


	def Submerge(self):
		if getattr(self.platform,"composition",None) not in Data.liquids:
			self.Print("You can't submerge here.")
			return False
		if not self.canSwim():
			return False
		self.addStatus("submerged",-4)


	# throw a projectile at a target
	def Throw(self,missile,target,maxspeed=None):
		if missile is target:
			return False
		if missile is self.carrying:
			self.removeCarry(silent=True)
		else:
			if not self.parent.canAdd(missile):
				return False
			# first must be equipped in hand to throw
			self.equipInHand(missile)
			self.remove(missile,silent=True)
			self.parent.add(missile)

		missile = missile.asProjectile()

		# force is half STR, reduced by 1 for every 4*STR in missile weight
		# basically, its just reduced for the amount of weight the missile has
		force = min1(self.STR()//2) - bound((missile.Weight()//4)//self.STR(),0,10)
		if force <= 0:
			self.Print(f"{+missile} is too heavy to throw!")
			missile.asItem().fall()
			return False

		# bound by SPD; can only throw as fast as you can move
		speed = bound(diceRoll(1,force),1,self.SPD()+2)
		if maxspeed and speed > maxspeed:
			speed = maxspeed

		aim = self.ACCU()
		return missile.launch(speed,aim,self,target)


	### Statistics ###

	# the following are the player's traits, which can be modified by status effects
	def STR(self):
		modifiers = (("brawniness",10), ("weakness",-10))
		return self.conditionalMod(self.str, modifiers, lo=1)

	def SPD(self):
		modifiers = (("swiftness",10), ("slowness",-10))
		return self.conditionalMod(self.spd, modifiers, lo=1)

	def SKL(self):
		modifiers = (("prowess",10), ("clumsiness",-10))
		return self.conditionalMod(self.skl, modifiers, lo=1)

	def STM(self):
		modifiers = (("liveliness",10), ("weariness",-10), ("tired",-3), ("fatigued",-5))
		return self.conditionalMod(self.stm, modifiers, lo=1)

	def CON(self):
		modifiers = (("toughness",10), ("illness",-10))
		return self.conditionalMod(self.con, modifiers, lo=1)

	def CHA(self):
		modifiers = (("felicity",10), ("timidity",-10))
		return self.conditionalMod(self.cha, modifiers, lo=1)

	def INT(self):
		modifiers = [("sagacity",10), ("stupidity",-10)]
		return self.conditionalMod(self.int, modifiers, lo=1)

	def WIS(self):
		modifiers = [("lucidity",10), ("insanity",-10), ("fatigued",-3)]
		return self.conditionalMod(self.wis, modifiers, lo=1)

	def FTH(self):
		modifiers = [("fidelity",10), ("apathy",-10), ("fatigued", 3)]
		return self.conditionalMod(self.fth, modifiers, lo=1)

	def LCK(self):
		modifiers = [("prosperity",10), ("calamity",-10)]
		return self.conditionalMod(self.lck, modifiers, lo=1)

	def LOVE(self):
		modifiers = [("enchanted",50)]
		return self.conditionalMod(self.love, modifiers, lo=-100, hi=100)

	def FEAR(self):
		modifiers = [("haunted",50)]
		return self.conditionalMod(self.fear, modifiers, lo=-100, hi=100)

	# these are creature stats that are determined dynamically with formulas
	# these formulas are difficult to read, check design document for details
	def ACCU(self): return 60 + 2*self.SKL() + self.LCK() + self.weapon.sleight

	def ATCK(self): return diceRoll(self.STR(), self.weapon.might, self.atkmod())

	def ATHL(self): return self.STR() + self.SKL() + self.STM()

	def ATSP(self): return min0(self.SPD() - min0(self.handheldWeight()//4-self.STR()+10))

	def BRDN(self): return 12*self.CON() + 6*self.STR() + 3*self.FTH() + self.weight

	def CAST(self): return min0(self.WIS() + self.FTH() + self.INT() - self.gearToll())

	def CRIT(self): return self.SKL() + self.LCK() + self.weapon.sharpness

	def CSSP(self): return min0(self.WIS() - self.invToll() - self.gearToll())

	def DCPT(self): return 2*self.CHA() + self.INT()

	def DFNS(self): return 2*self.CON() + self.protection()

	def ENDR(self): return 2*self.STM() + self.CON()

	def EVSN(self): return 10 if self.hasAnyStatus("sitting","laying") \
	else 2*self.ATSP() + self.LCK() + self.SPD()

	def INVS(self): return 2*self.INT() + self.WIS()

	def KNWL(self): return 2*self.INT() + self.LCK()

	def LOOT(self): return 2*self.LCK() + self.FTH()

	def MVMT(self): return min0(self.SPD() + self.STM() + 10 - \
	self.invToll() - self.gearToll()) // (2 if self.hasStatus("hindered") else 1)

	def MXHP(self): return self.level()*self.CON() + (self.level()//10+1) * self.STM() + 1

	def MXMP(self): return self.level()*self.WIS() + (self.level()//10+1) * self.STM() + 1

	def PRSD(self): return 2*self.CHA() + self.WIS()

	def RSTN(self): return 2*self.FTH() + self.STM()

	def RITL(self): return 2*self.FTH() + self.LCK()

	def SLTH(self): return min0(2*self.SKL() + self.INT() - self.invToll()) + \
	self.coverBonus()

	def SPLS(self): return 3*self.INT()

	def TNKR(self): return 2*self.INT() + self.SKL()


	# TODO: add logic here for conditions which improve atkmod
	def atkmod(self):
		return 0


	# for Creatures, level is determined by rating
	def level(self):
		return ((self.rating() - 10) // 10) + 1


	# rating is sum of all base stats
	def rating(self):
		return self.str + self.spd + self.skl + self.stm + self.con + \
		self.cha + self.int + self.wis + self.fth + self.lck


	### Getters ###

	# Creature is anchored to either riding, carrier, or platform
	# only one of these may be non-None at a time.
	def anchor(self):
		assert sum(a is not None for a in (self.riding, self.carrier, self.platform)) <= 1
		for a in (self.riding, self.carrier, self.platform):
			if a is not None:
				return a
		return None


	# return the creature wrapped in a projectile object for temporary use
	def asProjectile(self):
		return Projectile(self.name,self.desc,self.weight,self.DFNS(),self.composition,
		self.weight//4,0,"b",item=self,pronoun=self.pronoun)


	# check if item can fit in inventory, print relevant refusal msg if not
	def canObtain(self,I,silent=False):
		refusal = None
		if isinstance(I,Serpens):
			pass
		elif isinstance(I,Creature) or I.fixed:
			refusal = f"You can't put {-I} in your Inventory."
		elif I in self:
			refusal = f"You already have {-I} in your Inventory."
		elif I in self.ancestors():
			refusal = f"You can't take {-I}. You're within {I.pronoun}."
		elif I is self.anchor():
			refusal = f"You can't take {-I}. You're on {I.pronoun}."
		elif I.occupants:
			refusal = f"You can't take {-I}. It's occupied."
		elif self.invWeight() + I.Weight() > 2*self.BRDN():
			refusal = f"You can't hold {-I}. Your Inventory is too full."
		# not necessary because you can't take creatures
		# if self.checkTetherLoop(self,I,"take"):
		# 	refusal = f"You can't take {-I}. It would create a tether loop."
		if refusal:
			if not silent:
				self.Print(refusal)
				if self is player:
					game.setPronouns(I)
			return False
		return True


	# checks if Creature can swim based on gear, weight ATHL, and MVMT
	def canSwim(self,liquidDensity=None):
		if liquidDensity is None:
			submerseComp = self.submersedIn()
			liquidDensity = Data.densities.get(submerseComp,1)

		if not self.canMove():
			return False
		buoyancy = 5*liquidDensity
		return self.Weight()+self.gearWeight() <= self.ATHL()+self.MVMT()+buoyancy


	# since creatures can carry creatures while also being carried themselves,
	# and same can happen for riding and riders, loops could form where
	# a carrier is trying to carry the creature that is carrying them
	# this must be prevented
	def checkTetherLoop(self,actor,target,dverb):
		assert dverb in ("carry","ride","take","get on")
		looplink = None		

		iverb = "carrying"
		carrier = actor
		while carrier:
			if getattr(carrier,"carrier",None) == target:
				looplink = carrier
			# carrier may be an item, which can't have its own carrier
			carrier = getattr(carrier,"carrier",None)

		iverb = "being carried by"
		carrying = actor
		while carrying:
			if carrying.carrying == target:
				looplink = carrying
			carrying = carrying.carrying

		iverb = "being ridden by"
		riding = actor
		while riding:
			if riding.riding == target:
				looplink = riding
			riding = riding.riding

		# if a creature is found creating a loop with the actor and attempted target,
		# identify the culprit
		if looplink:
			self.Print(f"You can't {dverb} {-target},", target/f"is {iverb} {looplink}")
			return True
		return False


	# Creature may despawn if it is dead, it is midnight, not in current room,
	def canDespawn(self):		
		return self.despawnTimer is not None and \
			self.despawnTimer <= 0 and \
			percentChance(-self.despawnTimer//10) and \
			game.hour() == "serpent" and \
			isinstance(self.parent,Room) and \
			self.parent is not game.currentroom and \
			not self.fixed


	# returns True if Creature can move (not restrained, paralyzed, etc)
	def canMove(self):
		conds = ("restrained","paralyzed","frozen","unconscious","dead")
		return self.isAlive() and not self.hasAnyStatus(conds)


	# returns weight of carried creature, or 0 if none
	def carryWeight(self):
		return 0 if self.carrying is None else self.carrying.Weight()


	# modify a stat conditionally based on status effects
	def conditionalMod(self,stat,bonuses=[],lo=None,hi=None):
		for condname, bonus in bonuses:
			if self.hasStatus(condname):
				stat = stat + bonus
		if lo:
			stat = max(lo,stat)
		if hi:
			stat = min(hi,stat)
		return stat


	# for Creatures, contents is the inventory. This is used in objQuery()
	def contents(self):
		return self.inv


	# cover bonus equals how much bigger the available cover is than the creature
	def coverBonus(self):
		return min0(self.cover.availableCover(self)) if self.cover else 0


	# gear toll is 1/4 how much the gearWeight exceeds CON
	def gearToll(self):
		return min0(self.gearWeight()//4 - self.CON())


	# sum of the weight of all items in player gear
	def gearWeight(self):
		return sum(I.Weight() for I in self.gear.values())


	# returns the sum of the weight of all items being held
	def handheldWeight(self):
		left = self.gear.get("left", EmptyGear()).Weight()
		right = self.gear.get("right", EmptyGear()).Weight()
		return left + right


	# returns number of allies creature can see
	def hasAlliesPresent(self):
		pass


	# returns number of enemies creature can see
	def hasEnemiesPresent(self):
		pass


	# looks through gear for an item whose name matches 'term'
	# if a match is found, return the item, otherwise return None
	def inGear(self,term):
		for slot,object in self.gear.items():
			if nameMatch(term,object) or term.lower() == slot.lower():
				return slot, object
		return None, None


	# return all Items in Inventory whose name matches term, otherwise return None
	def inInv(self,term):
		if term.startswith("my "):
			term = term[3:]
		return [obj for obj in self.inv if nameMatch(term,obj)]


	# Inventory toll is how much the Inventory weight exceeds BRDN
	def invToll(self):
		return min0(self.invWeight() - self.BRDN())


	# returns sum of the weight of all Items in the Inventory
	def invWeight(self):
		return sum(item.Weight() for item in self)


	# Creature is alive if despawnTimer is None
	def isAlive(self):
		return self.despawnTimer is None


	# returns True if Creature has less than 1/3 health
	def isBloodied(self):
		pass

	
	# returns True if Creature is not wearing any pants
	def isNaked(self):
		if self['legs'] == EmptyGear():
			return True


	# returns True if Creature is friendly to player
	def isFriendly(self):
		return self.hasStatus("tamed")


	# use posture and tethers to determine position description
	def position(self,ignoreStanding=False):
		pos = ""
		# if self.carrier:
		# 	pos += f"being carried by {~self.carrier}"
		if self.riding:
			pos += f"riding {~self.riding}"
		elif self.platform:
			pos += self.posture()
			if self.platform != getattr(self.parent,"floor",None):
				occupyprep = getattr(self.platform,"occupyprep","on")
				pos += f" {occupyprep} {-self.platform}"
		else:
			pos = "floating"
		if self.cover:
			pos += f" behind {-self.cover}"
		if ignoreStanding and pos == "standing":
			pos = ""
		return pos


	# get posture from status and anchor
	def posture(self):
		for pos in ("laying","sitting","crouching"):
			if self.hasStatus(pos):
				return pos
		else:
			if self.anchor() is None:
				return "floating"
			return "standing"


	# returns sum of all protection values of all items in gear
	def protection(self):
		return sum(getattr(item,"prot",0) for item in self.gear.values())


	# size is normally equal to weight, but halved if not standing
	def Size(self,posture=None):
		posture = self.posture() if posture is None else posture
		# under normal conditions, size is equal to weight
		# I realize this doesn't count for density... whatever
		size = self.weight
		if posture not in ("stand","standing"):
			size //= 2
		return size


	# total size includes size of those riding and those being carried by Creature
	def totalSize(self):
		ridersSize = sum(r.totalSize() for r in self.occupants)
		carrySize = 0 if self.carrying is None else self.carrying.totalSize()
		return self.Size() + ridersSize + carrySize

	# returns list of all weapons in inventory
	def weapons(self):
		return [I for I in self if isinstance(I,Weapon)]


	# total weight includes those riding and those being carried by Creature
	def Weight(self):
		ridersWeight = sum(r.Weight() for r in self.occupants)
		carryWeight = 0 if self.carrying is None else self.carrying.Weight()
		return self.weight + ridersWeight + carryWeight


	### User Output ###

	# returns name to display in stats panel
	def displayName(self):
		return self.nounPhrase()


	def tethersDescription(self,name=None,allowRiding=True,allowCarrying=True):
		if not name:
			name = self.name
		tethersMsgs = []
		if self.carrying and allowCarrying:
			tethersMsgs.append(f"carrying {-self.carrying}")
		if self.occupants and allowRiding:
			if len(self.occupants) < 3:
				tethersMsgs.append(listObjects("being ridden by ",self.occupants))
			else:
				tethersMsgs.append(f"being ridden by {len(self.occupants)} creatures")
		return f" {' and '.join(tethersMsgs)}" if tethersMsgs else ""


	# describe the creature, including tethers
	def describe(self):
		Print(f"It's {~self}.")
		Print(f"{self.desc}")
		# tethersMsgs = []
		# if self.carrying:
		# 	tethersMsgs.append(f"carrying {-self.carrying}")
		# if self.occupants:
		# 	tethersMsgs.append(listObjects("being ridden by ",self.occupants))
		# if tethersMsgs:
		# 	Print(f"It is {' and '.join(tethersMsgs)}.")


	# intelligently get name of this Item in various grammatical forms
	def nounPhrase(self,det="",n=-1,plural=False,cap=-1):
		strname = self.descname
		# if self.riding and det != "the":
		# 	strname = f"{strname} on {self.riding.nounPhrase()}"
		# self.parent.floor causes error when displacing
		# elif self.platform not in (None,self.parent.floor) and det != "the":
		# 	strname = f"{strname} {self.posture()} on {-self.platform}"
		# position = self.position(ignoreStanding=True)
		if det == "a" and self.determiner != "your":
			strname = strname + self.tethersDescription(allowCarrying=False)
			# if position == "floating":
			# 	if self.anchor() is None:
			# 		strname = "floating " + strname
			# elif position != "":
			# 	strname = f"{strname} {position}"

		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		if self.determiner is not None:
			det = self.determiner
		if det == "" and n == 1:
			det = "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


	# this is used as a shortcut to show output only to the user
	# It should do nothing for any other creature
	def Print(self,*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,
		   outfile=None):
		# in godmode we can see all prints
		if game.mode == 2:
			text = f"[{self.id} {self.name}]:" + text if text else ""
			color="k"
		elif self is not player.riding:
			return
		return Print(*args,end=end,sep=sep,delay=delay,color=color,
		allowSilent=allowSilent,outfile=outfile)


	# get reflexive pronoun
	def reflexive(self):
		if self.pronoun in Data.reflexives:
			return Data.reflexives[self.pronoun]
		else:
			return "itself"



# The Player mostly behaves like a normal Humanoid Creature,
# but it has an xp to track leveling up, and RP to track reputation
class Player(Creature):
	def __init__(self,name,desc,weight,traits,xp,rp,spells=None,**kwargs):
		self.xp = xp
		self.rp = rp
		self.spells = spells if spells else []
		self.pronoun = "he"
		super().__init__(name,desc,weight,traits,**kwargs)


	### Dunder Methods ###

	def __neg__(self):
		return "you"


	def __pos__(self):
		return "You"


	def __invert__(self):
		return "you"


	### File I/O ###

	def convertToJSON(self):
		jsonDict = super().convertToJSON()
		# these lines seem redundant
		# (the menu functions handle parent and __class__ attributes)
		# but they are needed because player is read from its own file
		if "parent" in jsonDict:
			del jsonDict["parent"]
		jsonDict["__class__"] = self.__class__.__name__
		return jsonDict


	### Operation ###

	def awaken(self,wellRested=True):
		game.silent = False
		delay(1)
		waitInput("You wake up!",color="o")
		if wellRested:
			self.lastSlept = game.time
			self.checkTired()
		game.startUp()


	def traitMenu(self,QP,prompt="",warning="",nReturn=8):
		movePrintCursor(nReturn+1,clear=(QP+1)%10==0) # clear lingering extra digits
		nRowsPrinted = self.printTraits()
		# backtrack to clear any extra rows from printTraits
		movePrintCursor(1,clear=False)
		movePrintCursor(-2,clear=True)
		displayQP = ambiguateNumbers(QP) if self.hasStatus("stupidity") else QP
		Print(f"Quality Points:	{displayQP}",end="",delay=0)
		movePrintCursor(-1,clear=True)
		Print(prompt,end="",delay=0)
		movePrintCursor(-1,clear=True)
		Print(warning,end="",delay=0)
		movePrintCursor(-1,clear=True)
		if prompt.endswith("?"):
			return Input(cue="> ",delay=0), nRowsPrinted + 4
		waitInput()
		return "", nRowsPrinted + 4


	def gainQP(self,QP):
		Print("\n"*8)
		warning = ""
		rowsPrinted = 7
		while QP > 0:
			trait, rowsPrinted = self.traitMenu(QP,"What trait will you improve?",
			warning,rowsPrinted)
			if trait not in Data.traits:
				if trait == "":
					warning = ""
				else:
					warning = "That's not a trait you can improve."
				continue
			# increment corresponding player trait
			traitval = getattr(self,trait)
			if traitval >= 20:
				warning = f"Your {trait} cannot be raised any higher."
				continue
			warning = ""
			setattr(self,trait,traitval+1)
			QP -= 1
			self.display()
		self.traitMenu(0,"You have no more QP.","",rowsPrinted)
		movePrintCursor(8,clear=True)


	# player gets 1 QPs for each level gained, can dispense them into any trait
	def levelUp(self,oldlv,newlv):
		displayLevel = "something" if self.hasStatus("stupidity") else newlv
		waitInput(f"You leveled up to level {displayLevel}!",color="g")
		clearScreen()
		self.gainQP(newlv-oldlv)
		game.startUp()
		self.checkStatus()


	def updateReputation(self,repMod):
		self.rp = bound(repMod,-100,100)


	# adds xp, checks for player level up
	def gainxp(self,newxp):
		oldlv = self.level()
		if self.hasStatus("apathy"):
			newxp = 0
		Print(f"You gained {newxp} xp.",color="g")
		self.xp += newxp
		# Print(f"You have {self.xp}")
		newlv = self.level()
		if oldlv != newlv:
			self.levelUp(oldlv,newlv)


	def checkHungry(self):
		# being invigorated prevents hunger but not starving
		invigorated = self.hasStatus("invigorated")
		# hunger takes longer with more endurance
		sinceLastAte = game.time - self.lastAte
		if sinceLastAte > 100 + 10*self.ENDR():
			self.removeStatus("hungry",-2)
			self.addStatus("starving",-2)
		elif sinceLastAte > 50 + 5*self.ENDR() and not invigorated:
			self.addStatus("hungry",-2)
		elif sinceLastAte < 100:
			self.removeStatus("starving")
			self.removeStatus("hungry")
		elif invigorated:
			self.removeStatus("hungry")			


	def checkTired(self):
		# being invigorated prevents tired and fatigue
		invigorated = self.hasStatus("invigorated")
		# sleep deprivation takes longer with more endurance
		sinceLastSlept = game.time - self.lastSlept
		if sinceLastSlept > 300 + 40*self.ENDR() and not invigorated:
			self.removeStatus("tired",-2)
			self.addStatus("fatigued",-2)
		elif sinceLastSlept > 150 + 20*self.ENDR() and not invigorated:
			self.addStatus("tired",-2)
		elif sinceLastSlept < 100 or invigorated:
			self.removeStatus("fatigued")
			self.removeStatus("tired")


	# called when player hp hits 0
	def death(self):
		self.timeDespawn()
		Print("You have died!",color="r")
		self.changePosture("laying",silent=True)
		ellipsis(color="r")

		if self.hasStatus("anointed"):
			return self.reanimate()

		self.removeRiding(silent=True)
		self.removeCarry(silent=True)

		self.addStatus("dead",-2)
		waitInput()
		return True


	def dualAttack(self,target):
		Print("\nDual Attack!",color="o")
		hit = bound(self.ACCU() - target.EVSN(),1,99)
		if percentChance(hit):
			crit = percentChance(self.CRIT())
			attack = self.ATCK()
			if crit:
				waitInput("Critical hit!",color="o")
				self.weapon2.dull(1)
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if not target.isAlive():
				return
		else:
			Print("Aw it missed.")
		waitInput()


	def attackCreature(self,target):
		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			Print(f"{n} attacks!",color="o")
		for i in range(n):
			if n > 1:
				waitInput(f"\n{ordinal(i+1)} attack:")
			# TODO: what about if weapon is ranged?
			hit = bound(self.ACCU() - target.EVSN(),1,99)
			if percentChance(hit):
				crit = percentChance(self.CRIT())
				attack = self.ATCK()
				if crit:
					waitInput("Critical hit!",color="o")
					self.weapon.dull(1)
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
			else:
				Print("Aw it missed.")
			waitInput()
			if not target.isAlive():
				return
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	def attackItem(self,target):
		# TODO determine damage type here instead of always bludgeoning
		attack = self.ATCK()
		return target.takeDamage(attack,"b")


	def Catch(self,missile):
		assert isinstance(missile,Projectile)
		self.unequip("left")
		canCatch = 5*self.ATHL() > missile and self.canObtain(missile)
		catch = bound(self.ACCU() - missile.speed*missile.Size(),1,99)
		if canCatch and percentChance(catch):
			missileItem = missile.asItem()
			Print(f"You catch {-missileItem}!",color="o")
			self.ObtainItem(missileItem)
			self.equipInHand(missileItem)
			return True
		else:
			Print(f"You fail to catch {-missile}.")
			return False


	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		dodge = self.EVSN()
		if missile.speed < self.MVMT():
			if yesno(f"Will you try to catch {-missile}?"):
				dodge = -10
				if self.Catch(missile):
					return True
		if percentChance(bound(missile.aim+missile.speed-dodge,1,99)):
			return missile.collide(self)
		return False


	### Getters ###

	# Player can't navigate if they are blind/stupid or
	# if the sun is not visible and they have no compass
	def canNavigate(self,location=None):
		if location is None:
			location = self.parent
		if location is None or self.hasAnyStatus("blind","stupidity"):
			return False
		return self.countCompasses() > 0 or sun in location


	# count number of compasses in Inventory
	def countCompasses(self):
		return len([item for item in self.inv if isinstance(item,Compass)])


	# check status conditions and refresh stats display
	def checkStatus(self):
		super().checkStatus()
		self.display()


	# returns the sum of the weight of all items being held
	def handheldWeight(self):
		carryingWeight = 0 if self.carrying is None else self.carrying.Weight()
		return self["left"].Weight() + self["right"].Weight() + carryingWeight


	# weird formula right? returns a positive number rounded down to nearest int
	# also note that the level must be between 1 and 100
	def level(self):
		return bound(floor(sqrt(self.xp/2)),1,100)


	# query is overridden here, other nameQuery() methods don't search within Player
	def nameQuery(self,term,d=2):
		term = term.lower()
		key = lambda obj: nameMatch(term,obj)
		return self.query(key=key,d=d)


	# query is overridden here, other query() methods don't search within Player
	def query(self,key=None,d=2):
		matches = objQuery(self,key=key,d=d)
		return matches


	### User Output ###

	# takes args because interpreter passes them
	def display(self,*args):
		sidepanel.clear()
		if self.hasStatus("asleep"):
			return self.Print("...",color="k",outfile=sidepanel)
		self.printStats(outfile=sidepanel)
		Print(outfile=sidepanel)

		self.printTraits(outfile=sidepanel)
		self.printGear(outfile=sidepanel)

		if len(self.status) > 0:
			self.Print(outfile=sidepanel)
			self.printStatus(outfile=sidepanel)

		tethersDisplay  = ""
		if self.platform is not None and self.platform != self.parent.floor:
			occuprep = getattr(self.platform,"occupyprep","on")
			tethersDisplay += f"\n{occuprep.capitalize()} {self.platform.name}"
		if self.carrying is not None:
			tethersDisplay += f"\nCarrying {self.carrying}"
		if self.riding is not None:
			tethersDisplay += f"\nRiding {self.riding}"
		if tethersDisplay:
			self.Print(tethersDisplay, outfile=sidepanel)

		self.Print(outfile=sidepanel)
		self.printInv(outfile=sidepanel)


	# if each trait is below or above normal, color it accordingly and print
	def displayTrait(self,t):
		assert hasattr(self,t.lower()) and hasMethod(self,t.upper())
		displayTrait = t.upper() + ": "+ str(getattr(self,t))

		if self.hasStatus("stupidity"):
			displayTrait = ambiguateNumbers(displayTrait)
		if getattr(self,t.lower()) < getattr(self,t.upper())():
			displayTrait = tinge("g",displayTrait)[0]
		if getattr(self,t.lower()) > getattr(self,t.upper())():
			displayTrait = tinge("r",displayTrait)[0]

		return displayTrait


	def nounPhrase(self,det="",n=-1,plural=False,cap=-1):
		strname = "you"
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


	# takes args because interpreter passes them
	def openDisplay(self,*args):
		if not sidepanel.isOpen():
			sidepanel.open(self.name)
			self.display()
		else:
			self.display()
			self.Print(f"Your stats panel is already open.",color="k")


	# This method does nothing for non-player creatures
	def Print(self,*args,end="\n",sep=None,delay=None,color=None,allowSilent=True,
		outfile=None):
		return Print(*args,end=end,sep=sep,delay=delay,color=color,
		allowSilent=allowSilent,outfile=outfile)


	# prints a single ability or all abilities if ability is None
	def printAbility(self,ability=None):
		if ability == "ATCK":
			Print(f"ATCK: {self.weapon.might*self.STR()}")
		elif ability is not None:
			Print(f"{ability}: {getattr(self,ability)()}")
		else:
			for ability in Data.abilities:
				self.printAbility(ability.upper())


	# takes args because interpreter passes them
	def printCarrying(self,*args,silent=False,outfile=None):
		if self.carrying is not None:
			Print(f"You are carrying {~self.carrying}.", outfile=outfile)
			# Print(f"Weight: {self.carrying.Weight()}")
		elif silent is False and outfile is None:
			Print("You aren't carrying anything.")


	# print each player gear slot and the items equipped in them
	def printGear(self,*args,outfile=None):
		Print(outfile=outfile)
		for slot in self.gear:
			val = self[slot].displayName()
			Print(slot + ":\t" + val,outfile=outfile)

	# takes args because interpreter passes them
	def printHP(self,*args): Print(f"HP: {self.hp}/{self.MXHP()}",color="r")

	# prints player inventory
	def printInv(self,*args,outfile=None):
		cols = 8 if outfile is None else 4
		W = self.invWeight() + self.carryWeight()
		color = "o" if W / self.BRDN() > 0.80 else "w"
		color = "r" if W > self.BRDN() else color
		displayInvWeight = f"Inv Weight: {W}/{self.BRDN()}"
		if self.hasStatus("stupidity"):
			displayInvWeight = ambiguateNumbers(displayInvWeight)
		Print(displayInvWeight, color=color, outfile=outfile)
		if len(self.inv) == 0:
			if outfile is None:
				Print("Your Inventory is empty.")
		else:
			displayInv = self.inv
			if outfile is not None:
				displayInv = [n for n in displayInv if n not in self.gear.values()]
			baggedObjects = bagObjects(displayInv, equivKey=lambda x: x.displayName())
			invDisplayNames = [I.displayName(c) for I,c in baggedObjects]
			columnPrint(invDisplayNames,cols,12,outfile=outfile)

	# takes args because interpreter passes them
	def printLV(self,*args): Print(f"LV: {self.level()}",color="o")

	# takes args because interpreter passes them
	def printMoney(self,*args): Print(f"§ {self.money}",color="g")

	# takes args because interpreter passes them
	def printMP(self,*args): Print(f"MP: {self.mp}/{self.MXMP()}",color="b")

	# takes args because interpreter passes them
	def printPosition(self,*args): Print(f"You are {self.position()}.")

	# takes args because interpreter passes them
	def printRiding(self,silent=False,*args):
		if self.riding:
			Print(f"You are riding {~self.riding}.")
		elif silent is False:
			Print("You aren't riding anything.")

	# takes args because interpreter passes them
	def printRP(self,*args): Print(f"RP: {self.rp}/100",color="y")

	# takes args because interpreter passes them
	def printSpells(self,*args):
		Print(f"Spells: {len(self.spells)}/{self.SPLS()}")
		if len(self.spells) == 0:
			Print("\nYou don't know any spells.")
		else:
			columnPrint(self.spells,8,12)


	# prints player level, money, hp, mp, rp, and status effects
	def printStats(self, *args, outfile=None):
		colWidth = None
		name = self.name
		if len(name) > 45:
			name = name[:42] + "..."
		stats = [name,f"LV: {self.level()}",f"§ {self.money}",
		   f"RP: {self.rp}/100",f"HP: {self.hp}/{self.MXHP()}",
		   f"MP: {self.mp}/{self.MXMP()}"]
		colors = ["w","o","g","y","r","b"]
		if self.hasStatus("insanity") and outfile is None:
			shuffle(colors)
		if self.hasStatus("apathy"):
			colors = ["w"]*len(colors)
		if self.hasStatus("stupidity"):
			stats = [ambiguateNumbers(stat,grammatical=False) for stat in stats]
		if max(len(term) for term in stats) > 16:
			colWidth = 16
		stats = [tinge(colors[i],stats[i])[0] for i in range(len(stats))]

		columnPrint(stats,3,w=colWidth,outfile=outfile)


	# prints all status conditions and their durations in a formatted table
	# conditions with negative (special) durations are represented with "--"
	def printStatus(self, *args, outfile=None):
		if len(self.status) == 0:
			Print("None")
			return

		conditions = []
		durations = []
		# populate conditions with unique condition names affecting the player
		# populate durations with the highest duration for that condition
		# negative (special) durations take precedence over positive durations
		for cond, dur in sorted(self.status, key=lambda x: x[0]):
			if cond in conditions:
				idx = conditions.index(cond)
				olddur = durations[idx]
				newdur = dur if dur > olddur and olddur > 0 else olddur
				durations[idx] = newdur
				continue
			conditions.append(cond)
			durations.append(dur)

		# display permanent durations as "--", adjust length according to max digit length
		displayDurs = [str(dur) if dur > 0 else "--" for dur in durations]
		if self.hasStatus("stupidity"):
			displayDurs = [ambiguateNumbers(dur) for dur in displayDurs]
		nDigits = max(len(dur) for dur in displayDurs)
		displayDurs = ["-"*nDigits if dur=="--" else dur for dur in displayDurs]

		# pad to align and color conditions and their durations for display
		nChars = max([len(condname) for condname in conditions])
		statusDisplay = []
		for i,condition in enumerate(conditions):
			padding = " "*(nChars-len(condition)+2)
			displayCondition = condition + padding + displayDurs[i]
			if self.hasStatus("stupidity"):
				displayCondition = ambiguateNumbers(displayCondition)

			color = "w"
			if self.hasStatus("apathy") and condition != "apathy":
				color = "w"
			elif condition in Data.blessings | Data.buffs:
				color = "g"
			elif condition in Data.curses | Data.debuffs:
				color = "r"
			statusDisplay.append(tinge(color,displayCondition)[0])

		# nCols = min(3,((len(statusDisplay)-1)//5)+1)
		nCols = 2 if len(statusDisplay) > 5 else 1
		columnPrint(statusDisplay,nCols,outfile=outfile)


	# prints all 10 player traits
	# returns number of lines printed
	def printTraits(self,trait=None,outfile=None):
		if trait == None:
			traits = [self.displayTrait(t) for t in Data.traits]
			colWidth = max(displayLength(trait) for trait in traits)
			# cols = min(50 // colWidth, 5)
			return columnPrint(traits,5,outfile=outfile)

		Print(self.displayTrait(trait))
		return 1

	# takes args because interpreter passes them
	def printXP(self,*args): Print(f"XP: {self.xp}",color="o")

	# for every item in player inventory, if its a weapon, print it
	def printWeapons(self, *args):
		if len(self.weapons()) == 0:
			Print("You have no weapons.")
		else:
			columnPrint(self.weapons(),12,12)


	# This method does nothing for non-player creatures
	def waitInput(self,text=None,delay=None,color=None):
		return waitInput(text=text,delay=delay,color=color)




##########################
## SUBCLASS DEFINITIONS ##
##########################


class Humanoid(Creature):
	### Operation ###

	# attack another creature
	def attackCreature(self,target):
		Print(f"{+self} tries to attack {-target}.",color="o")

		n = min1( self.ATSP() // min1(target.ATSP()) )
		if n > 1:
			Print(f"{n} attacks!")
		for i in range(n):
			if n > 1:
				target.waitInput(f"\n {+self}'s {ordinal(i+1)} attack on {target}:")
			# TODO: what about if weapon is ranged?
			hit = bound(self.ACCU() - target.EVSN(),1,99)
			if percentChance(hit):
				crit = percentChance(self.CRIT())
				attack = self.ATCK()
				if crit:
					target.waitInput("Critical hit!",color="o")
					attack *= 2
				damage = min0( attack - target.DFNS() )
				target.takeDamage(damage,self.weapon.type)
			else:
				self.Print("It missed!")
			# target.waitInput()
			if not target.isAlive():
				return
			if self.weapon2 != EmptyGear():
				self.dualAttack(target)
			if not target.isAlive():
				return


	# attack with a second hand item
	def dualAttack(self,target):
		self.Print("\nDual Attack!",color="o")
		hit = bound(self.ACCU() - target.EVSN(),1,99)
		if percentChance(hit):
			crit = percentChance(self.CRIT())
			attack = self.ATCK()
			if crit:
				self.waitInput("Critical hit!",color="o")
				self.weapon2.dull(1)
				attack *= 2
			damage = min0( attack - target.DFNS() )
			target.takeDamage(damage,self.weapon2.type)
			if not target.isAlive():
				return
		else:
			Print("It missed!")
		self.waitInput()


	### Behavior ###

	# perform action on Creature's turn
	def Act(self):
		if not self.isAlive():
			return
		self.printNearby(f"\n{self.name}'s turn!")
		if self.canMove():
			self.Attack()


	# attack something
	def Attack(self):
		if not self.canMove():
			return
		select = lambda obj: isinstance(obj,Creature) and obj is not self
		targets = [obj for obj in self.parent if select(obj)]
		if self.parent is player.parent:
			targets += [player]
		if len(targets) > 0:
			target = choice(targets)
			return self.attackCreature(target)
		return False


	# try to catch a projectile
	def Catch(self,missile):
		assert isinstance(missile,Projectile)
		self.unequip("left")
		canCatch = 5*self.ATHL() > missile and self.canObtain(missile)
		catch = bound(self.ACCU() - missile.speed*missile.Size(),1,99)
		if canCatch and percentChance(catch):
			missileItem = missile.asItem()
			Print(f"{+self} catches {-missileItem}!",color="o")
			self.ObtainItem(missileItem)
			self.equipInHand(missileItem)
			return True
		else:
			Print(f"{+self} fails to catch {-missile}.")
			return False


	### Getters ###

	# returns True is monster has healing potion or food
	def hasHealing():
		pass


	# returns True if self is armed
	def isArmed():
		pass


	### User Output ###

	# describe the humanoid, including gear
	def describe(self):
		Print(f"It's {~self}.")
		Print(f"{self.desc}")
		gearKey = lambda item: not isinstance(item,(EmptyGear,Creature))
		gearitems = [item for item in self.gear.values() if gearKey(item)]
		if len(gearitems) != 0:
			self.Print(listObjects("It has ", gearitems,"."))
		# tethersMsgs = []
		# if self.carrying:
		# 	tethersMsgs.append(f"carrying {-self.carrying}")
		# if self.occupants:
		# 	tethersMsgs.append(listObjects("being ridden by ",self.occupants))
		# if tethersMsgs:
		# 	Print(f"It is {' and '.join(tethersMsgs)}.")



# Speakers are Creatures that can talk
# they have a dialogue tree (taken from Dialogue.json or constructed as a default tree)
# upon meeting the player they will take a firstImpression()
# and every encounter with them after that they will perform appraise()
class Speaker(Creature):
	def __init__(self,name,desc,weight,traits,dlogName=None,dlogTree=None,rapport=0,
	lastParley=None,**kwargs):
		super().__init__(name,desc,weight,traits,**kwargs)
		self.dlogName = self.name if dlogName is None else dlogName
		self.dlogTree = dlogTree
		self.rapport = rapport
		self.lastParley = lastParley


	### File I/O ###

	# build dialogue tree from dlogName in game.dlogForest
	def buildDialogue(self):
		# dlogTree actually just records the visitCounts & checkpoint when written to json
		dlogRefs = self.dlogTree
		self.dlogTree = game.dlogForest["trees"][self.dlogName].copy()
		if dlogRefs:
			self.dlogTree.visitCounts = dlogRefs["visitCounts"]
			self.dlogTree.checkpoint = dlogRefs["checkpoint"]
		self.dlogTree.ensureIntegrity(self)


	### Operation ###

	# get an impression of the player
	def firstImpression(self,partner):
		# TODO: add this
		print(self.name, "impression")
		# adjust love, fear from person baselines
		self.memories.add("met")
		self.updateLove(partner.rp)
		self.updateFear(partner.rp)


	# appraise the player upon talking
	def appraise(self,partner):
		if self.lastParley is None:
			self.lastParley = game.time
		elif game.time - self.lastParley > 100:
			self.dlogTree.newParley()
		self.lastParley = game.time
		if partner.isNaked():
			self.appraisal.add("naked")


	### Interaction ###

	# talk to this speaker
	def converse(self):
		if "met" not in self.memories:
			self.firstImpression(player)
		self.appraise()
		if not self.dlogTree.visit(self):
			Print(f"{self.name} says nothing...")


	# offer something to this speaker
	def offer(self,I):
		if not self.canObtain(I):
			Print(f"{+self} can't carry any more!")	
		elif self.dlogTree.react("offer",self,I=I):
			# if we fail to obtain item for whatever reason, drop it into room
			if not self.ObtainItem(I):
				game.currentroom.add(I)
		else:
			Print(f"{+self} ignores your offer.")			
		return True



# People are Speakers that are Humanoid
class Person(Speaker,Humanoid):
	def __init__(self,name,descname,weight,traits,pronoun,spells=None,desc=None,
	isChild=False,**kwargs):
		super().__init__(name,"",weight,traits,descname=descname,pronoun=pronoun,**kwargs)
		self.spells = spells if spells else []
		if desc:
			self.desc = desc
		else:
			prefix = "An " if self.descname[0] in Data.vowels else "A "
			self.desc = prefix + self.descname

		if self.pronoun == "he":
			if isChild:
				self.aliases.extend(["boy","male"])
			else:
				self.aliases.extend(["man","guy","dude","male"])
		elif self.pronoun == "she":
			if isChild:
				self.aliases.extend(["girl","female"])
			else:
				self.aliases.extend(["woman","lady","dudette","female"])
		else:
			self.pronoun = "they"
		if isChild:
			self.aliases.extend(["child","kid"])
		self.aliases.append("person")


	### Operation ###

	# act on Person's turn
	def Act(self):
		pass


	### User Output ###

	# describe the Person using appropriate pronouns, including gear
	def describe(self):
		pro = "They're" if self.pronoun == "they" else self.pronoun.capitalize() + "'s"
		nounPhrase = ~self
		Print(f"{pro} {nounPhrase}.")
		if nounPhrase.lower() != self.desc.lower():
			Print(f"{self.desc}")
		gearKey = lambda item: not isinstance(item,(EmptyGear,Creature))
		gearitems = [item for item in self.gear.values() if gearKey(item)]
		if len(gearitems) != 0:
			Print(listObjects(self*"has ", gearitems,"."))
		tethersMsgs = []
		if self.carrying:
			tethersMsgs.append(f"carrying {-self.carrying}")
		# if self.occupants:
		# 	tethersMsgs.append(listObjects("being ridden by ",self.occupants))
		if tethersMsgs:
			Print(self*f"is {' and '.join(tethersMsgs)}.")


	# intelligently get name of this Item in various grammatical forms
	# display a description of them (descname) if they haven't met Player yet
	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
		# if self.riding and det != "the":
		# 	suffix = f" riding {self.riding.nounPhrase()}"
		# elif self.anchor() not in (None,self.parent.floor) and det != "the":
		# 	suffix = f" {self.posture()} on {self.anchor().nounPhrase()}"
		# if det == "a":
		# 	suffix = self.position(ignoreStanding=True)
		# else:
		# 	suffix = ""
		tethersSuffixes = ""
		if (self.carrying or self.occupants) and det == "a":
			tethersSuffixes = self.tethersDescription(allowCarrying=False)
		if "met" in self.memories:
			return self.name + tethersSuffixes
		else:
			strname = self.descname + tethersSuffixes

		if len(strname) == 0:
			return ""
		if n > 1:
			plural = True
		if plural:
			strname = self.plural
		if n > 1:
			strname = str(n) + " " + strname
		if self.determiner is not None and det == "":
			det = self.determiner
		if det == "" and n == 1:
			det = "a"

		if det:
			if det == "a":
				if not plural:
					if strname[0] in Data.vowels:
						strname = "an " + strname
					else:
						strname = "a " + strname
			else:
				strname = det + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname



# Animals can only speak when player has 'wildspeaking' status
class Animal(Speaker):
	def __init__(self,name,desc,weight,traits,species=None,dlogName=None,**kwargs):
		super().__init__(name,desc,weight,traits,**kwargs)
		self.species = name if species is None else species
		# dlogName was assigned by Speaker init, but should be reassigned here
		self.dlogName = self.species if dlogName is None else dlogName


	# build dialogue tree from dictionary in game.dlogForest
	# or make a default tree based on species
	def buildDialogue(self):
		# dlogTree actually just records the visitCounts & checkpoint when written to json
		dlogRefs = self.dlogTree

		# dlogName must either be the name of a tree or a trite
		if self.dlogName in game.dlogForest["trees"]:
			self.dlogTree = game.dlogForest["trees"][self.dlogName].copy()
		else:
			defaultTree = {"chatter":{"trites":self.dlogName}}
			self.dlogTree = DialogueTree(self.dlogName,defaultTree)

		if dlogRefs:
			self.dlogTree.visitCounts = dlogRefs["visitCounts"]
			self.dlogTree.checkpoint = dlogRefs["checkpoint"]
		self.dlogTree.ensureIntegrity(self)


	# perform action on Animal's turn
	def Act(self):
		if not self.isAlive():
			return
		self.printNearby(f"\n{self.name}'s turn!")
		self.Attack()


	# eat offer if it is edible otherwise ignore
	def offer(self,I):
		if hasMethod(I,"consume"):
			I.consume(self)
			self.updateLove(1)
			self.updateFear(-1)
		else:
			Print(f"{+self} ignores your offer.")


	# talk to this Animal
	def converse(self,partner):
		if not player.hasStatus("wildspeaking"):
			sounds = game.dlogForest["sounds"][self.species]
			sound = sample(sounds,1)[0]
			waitInput(f'"{sound}"',color="y")
			return True
		if "met" not in self.memories:
			self.firstImpression(player)
		self.appraise(partner)
		if not self.dlogTree.visit(self):
			Print(f"{self.name} says nothing...")


	# touch this Animal
	def touch(self,toucher):
		if self.species in Data.textures:
			Print(Data.textures[self.species])
		else:
			return super().touch(toucher)


	def Attack(self):
		pass


	def Climb(self):
		pass


	def Go(self):
		pass


	def Steal(self):
		pass


	def Swim(self):
		pass



notes = '''
self.alive = True
self.seesPlayer = False
self.lastSawPlayer = -1

creatures can take 'actions'
they have a 'act' function, which dictates their actions

actions they can take on a turn include;
moving (swimming, climbing)
attacking
casting a spell
speaking
equipping/unequipping an item
using an item (eating food, using a key, etc.)
hiding somewhere
dropping/taking an item
stealing
throwing
heal itself
shield/defend

in their turn function, actions are dictated by several factors, including;
if they know the player is present,
if they recently saw the player,
if the player has weapons, or if the player is bloodied
if other creatures are present (and if they are allies or not)
if they have a weapon
if they have food or healing items
if their own stats are higher than a certain number
if they have a specific status condition
what the player's RP is

different types of creatures act with different limitations;
animal cannot speak, trade, or equip, take, and use items, or cast spells,
monsters cannot speak, or trade

_______________________________
TECHNICAL DESIGN

prior to taking a turn, each creature updates a series of attributes which just represent its perception of its surroundings. current values are;

all creatures:
Bool seesPlayer
Int lastSawPlayer
Bool alliesPresent()
Bool enemiesPresent()

monsters and people:
Int player.rp
Bool isArmed
Bool hasHealing
Bool playerBloodied()
Bool playerArmed()

other values utilized in taking a turn:
Set status

'''


# Item that is fixed and not mentioned by default
class Fixture(Item):
	def __init__(self,name,desc,weight,composition,durability=-1,mention=False,fixed=True,
	**kwargs):
		super().__init__(name,desc,weight,durability,composition,mention=mention,
		fixed=True,**kwargs)


	# def destroy(self):
	# 	Print(f"{+self} cannot be destroyed.")
	# 	return False


	# Fixtures shouldn't be breakable by normal means
	def breaks(self):
		Print(f"{+self} cannot be broken.")
		return False



# Surfaces are Fixtures that surround a Room or Container
class Surface(Fixture):
	def __init__(self,name,desc,weight,composition,**kwargs):
		super().__init__(name,desc,weight,composition,**kwargs)
		if any("water" in alias for alias in self.aliases):
			self.aliases.append("water")
		if any(name in Data.liquids for name in self.aliases+[self.name]):
			self.aliases.append("liquid")

	# Surfaces can't take damage
	def takeDamage(self,dmg,type):
		pass


	# Surfaces don't have a density, so size is just weight
	def Size(self):
		return self.weight



# Celestials are Fixtures that can be in Room contents depending on the time
class Celestial(Fixture):
	def __init__(self,name,desc,weight,composition,**kwargs):
		super().__init__(name,desc,weight,composition,**kwargs)
		self.determiner = "the"


	# Celestials have no ancestors, they don't belong in any one Room
	def ancestors(self):
		return []


moon = Celestial("moon","The glowing moon hangs in the sky, illuminating the world below.",
0,"cheese",aliases=["full moon","new moon"])
sun = Celestial("sun","The blazing sun shines down from above, its warmth felt by all.",
0,"fire",aliases=["sun"])
stars = Celestial("stars","The twinkling stars dot the night sky, each one a distant sun.",
0,"fire",aliases=["star"],pronoun="they")
eclipse = Celestial("eclipse","The sun and moon align perfectly, casting an eerie shadow" \
" over the land.",0,"fire",aliases=["solar eclipse","sun","moon"])
meteorshower = Celestial("meteor shower","A dazzling meteor shower streaks across the" \
" sky, lighting up the darkness with brief flashes of light.",0,"rock",
aliases=["meteors","shower"])
aurora = Celestial("aurora","The sky is painted with vibrant colors as the aurora dances" \
" overhead, a mesmerizing display of nature's beauty.",0,"energy",aliases=["auroras"])
sky = Celestial("sky","The vast expanse of the sky stretches out above, a canvas for " \
"the sun, moon, and stars.",0,"air",aliases=["heavens","firmament"],determiner="the")
celestials = (sky,sun,moon,stars,eclipse,meteorshower,aurora)


# Just as Rooms link to Rooms to allow creatures to move, Portals can link to Rooms too
# But a Portal can link to another Portals as well 
# They have traverse(), transfer(), a links dict and a passprep
class Portal(Item):
	def __init__(self,name,desc,weight,durability,composition,links,capacity=None,
	passprep="into",**kwargs):
		super().__init__(name,desc,weight,durability,composition,**kwargs)
		self.links = links
		self.capacity = capacity if capacity else self.Size()
		self.passprep = passprep


	### File I/O ###

	# In JSON, Portals' links eachother are represented by a unique link ID
	# search in the World for the Portal that has a link with the same link ID
	# and link that portal to self
	def linkPortals(self,linkId):
		# find paired portal in world
		pairedPortals = set()
		pairKey = lambda x: isinstance(x,Portal) and linkId in x.links.values()
		for room in world.values():
			pairedPortals |= objQuery(room,key=pairKey,d=3)
		pairedPortals.remove(self)
		assert len(pairedPortals) == 1, f"Portal {self.name} has an ambiguous" \
		f" connection for '{linkId}'. Found {len(pairedPortals)} matches."
		pairedPortal = list(pairedPortals)[0]

		# link paired portal to self
		for dir, dest in self.links.items():
			if dest == linkId:
				self.links[dir] = pairedPortal
		# link self to the paired portal
		for dir, dest in pairedPortal.links.items():
			if dest == linkId:
				pairedPortal.links[dir] = self


	# after reading objects in from JSON portals must be linked to their destinations
	# links to Rooms are stored as the Room's unique name
	# for convenience, links to Portals are stored as int IDs or "port:<name>" strings
	def assignRefs(self,parent):
		super().assignRefs(parent)

		for dir, dest in self.links.items():
			# set one-way link to Room
			if isinstance(dest,str) and dest in world:
				self.links[dir] = world[dest]
			# set two-way link to Portal with string pair ID
			elif isinstance(dest,str) and dest.startswith("port:"):
				self.linkPortals(dest)
			# set two-way link to Portal with int pair ID
			elif isinstance(dest,int):
				self.linkPortals(dest)
			# link is an object, so its already assigned
			elif isinstance(dest,Room) or isinstance(dest,Portal):
				continue
			else:
				raise Exception(f"Portal {self.name} has a connection to unknown" \
				f" destination '{dest}'")


	# replace link to paired Portal with given linkId for storing to json
	# sometimes called from self, sometimes from the paired Portal
	def assignLinkIDs(self,pairPortal,linkId):
		if not hasattr(self, "compressedLinks"):
			self.compressedLinks = self.links.copy()

		assert pairPortal in self.compressedLinks.values()
		for dir, dest in self.compressedLinks.items():
			if dest is pairPortal:
				self.compressedLinks[dir] = linkId


	# replace object references in Portal Links with json-serializable values
	def convertToJSON(self):
		# must copy links for saving to JSON so real links remain
		if not hasattr(self, "compressedLinks"):
			self.compressedLinks = self.links.copy()

		# convert Portal links to int IDs
		for portal in {v for v in self.compressedLinks.values() if isinstance(v,Portal)}:
			# get next available linkId
			linkId = game.portalLinkIds
			# replace this reference link with unique linkId in both Portals
			self.assignLinkIDs(portal,linkId)
			portal.assignLinkIDs(self,linkId)
			# mark this linkId as used
			game.portalLinkIds += 1

		# convert Room links to unique name strings
		for dir, dest in self.compressedLinks.items():
			if isinstance(dest,Room):
				self.compressedLinks[dir] = dest.name.lower()

		# all links should now be either strings or ints
		for dir,dest in self.compressedLinks.items():
			assert isinstance(dest,(str,int)), f"Portal {self.name} failed to convert" \
			f" link {dest} at direction {dir} into string or int"
		jsonDict = self.__dict__.copy()
		jsonDict["links"] = jsonDict["compressedLinks"]
		del jsonDict["compressedLinks"]
		return jsonDict


	### Operation ###

	# when going through a portal without a concerted direction, pick a default one
	# if there's 1 destination, pick that. if there's "down", pick that. otherwise random
	def getDefaultDir(self):
		if len(set(self.links.values())) == 1:
			return list(self.links.keys())[0]
		elif "down" in self.links:
			return "down"
		return choice(list(self.links.keys()))


	# given a direction, get the new location that the Portal leads to
	# if self links to another Portal, the new location is other Portal's parent
	def getNewLocation(self,dir=None):
		if dir is None:
			dir = self.getDefaultDir()
		newloc = self.links[dir]
		if isinstance(newloc,Portal):
			newloc = newloc.parent
			if isinstance(newloc,Creature):
				newloc = newloc.parent
		return newloc


	# for Creatures intentionally travelling through the portal
	# takes a verb because some subclasses may take verbs to traverse
	def traverse(self,traverser,dir=None,verb=None):
		if dir in Data.directions: dir = Data.directions[dir]
		if self in traverser.objTree():
			if traverser is player:
				Print(f"You can't enter {-self}. It's within your Inventory.")
			else:
				Print(f"{+traverser} can't enter {-self}. It's within {-traverser}'s" \
				" Inventory.")
			return False

		if dir == None or dir not in self.links:
			if len(set(self.links.values())) == 1:
				dir = list(self.links.keys())[0]
			else:
				msg = f"Which direction on the {self.name}?"
				dir = InputLoop(msg)
				if dir is None:
					return False
		if dir not in self.links:
			Print(f"The {self.name} does not go '{dir}'.")
			return False
		if not self.canPass(traverser):
			traverser.Print(f"{+traverser} can't fit through {-self}.")
			return False

		newloc = self.getNewLocation(dir)
		if not newloc.canAdd(traverser):
			if traverser is player:
				Print(f"You can't enter {-self}. There's not enough room.")
			return False

		if traverser is player:
			waitInput(f"You go {dir} the {self.name}.")
		traverser.changeLocation(newloc)
		return True


	# for Items/Creatures travelling through Portal unintentionally
	def transfer(self,item):
		if isinstance(item,Creature):
			dir = self.getDefaultDir()
			if dir == "down":
				return item.fall(1,room=self.getNewLocation("down"))
			return self.traverse(item,dir=dir)
		if self in item.objTree():
			Print(f"{+item} can't enter {-self}. It's within {-item}'s contents.")
			return False
		if not self.canPass(item):
			item.Print(f"{+item} can't fit through {-self}.")
			return False

		# fall through Portal if possible
		if "down" in self.links:
			return item.fall(room=self.links["down"])

		# item can't randomly go up
		dir = choice([dir for dir in self.links])
		if self.links[dir] == self.links.get("up",None):
			return item.fall()

		# Print(f"{+item} goes {self.passprep} {-self}.")	
		newloc = self.getNewLocation(dir)
		if not newloc.canAdd(item):
			return False

		item.changeLocation(newloc)


	# for Projectiles colliding with the Portal
	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		if percentChance(bound(missile.aim+self.Size()+10,1,99)):
			if getattr(self,"closed",False):
				Print(f"{+missile} goes {self.passprep} {-self}.")
				self.transfer(missile.asItem())
			else:
				missile.collide(self)
			return True
		return False


	### Getters ###

	# returns dict of links, where keys are directions and values are Rooms/Portals
	def allLinks(self,d=3):
		links = {}
		for dir in self.links:
			links[(dir,None)] = self.links[dir]
		return links


	# get the links dict to use in the parent's allLinks method
	def getLinksForParent(self):
		return self.links


	# given a direction (like 'north' or 'down)...
	# return the first portal object with that direction in its connections
	def getPortalsFromDir(self,dir):
		portals = []
		for thisDir, portal in self.allLinks(d=0):
			if dir == thisDir and portal is not None:
				portals.append(portal)
		return portals


	# if the given room object dest, is in one of the Rooms links, 
	# then find the (dir,Portal) link key for it.
	def getDirPortalPair(self,dest):
		for (dir,portal), room in self.allLinks().items():
			if nameMatch(dest,room):
				return dir, portal
		return None, None


	# get all directions that this portal can lead to
	def allDirs(self):
		return (tuple[0] for tuple in self.allLinks())


	def allDests(self):
		return {dest for dest in self.allLinks().values()}


	def canPass(self,obj):
		if self.capacity == -1:
			return True
		return obj.totalSize() <= self.capacity



# In addition to Rooms and Creatures, Containers can also contain Items and be a 'parent'
# Containers special Portals. they have traverse and transfer methods
# but they link to themselves, adding traversers into their items list
# see Container.links()
class Container(Portal):
	def __init__(self,name,desc,weight,durability,composition,items,capacity=None,
	passprep=None,exitprep="out",**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.capacity = capacity if capacity else self.Size()
		self.passprep = passprep if passprep else "in"
		self.exitprep = exitprep if exitprep else "out"
		self.items = items
		# for containers, the surfaces surrounding it are itself
		self.ceiling = self
		self.walls = self
		self.floor = self
		self.surfaces = (self.ceiling,self.walls,self.floor)


	### File I/O ###

	# delete unneeded attributes for storing to json
	def convertToJSON(self):
		jsonDict = Item.convertToJSON(self)
		del jsonDict["ceiling"]
		del jsonDict["walls"]
		del jsonDict["floor"]
		del jsonDict["surfaces"]
		return jsonDict


	# assign object references after reading from json, ensure capacity is not exceeded
	def assignRefs(self,parent):
		super().assignRefs(parent)

		assert self.itemsSize() <= self.capacity or self.capacity == -1, (f"Container" \
		f" {self.name} has negative vacancy available. Capacity is {self.capacity}," \
		f" but occupied space is {self.itemsSize()}.")


	### Operation ###

	# add Item to Container's items list
	def add(self,I):
		# spawn object if given as string or has no ID
		if isinstance(I,str) or I.id is None:
			I = game.spawn(I)

		# ensure only one bunch of Gold exists here
		if isinstance(I,Serpens):
			for item in self.items:
				if isinstance(item,Serpens):
					item.merge(I)
					return item

		insort(self.items,I)
		I.parent = self
		I.nullDespawn()
		return I


	# apply an area condition to all objs in the Container
	def addAreaCondition(self,areacond):
		return Room.addAreaCondition(self,areacond)


	# add a status condition to the Container with a name and duration
	def addStatus(self,name,dur,stackable=True):
		return Room.addStatus(self,name,dur,stackable=stackable)


	# try to break the Container, spill its contents into parent
	def breaks(self):
		# self.parent may get deleted during super().breaks()
		parent = self.parent
		if not super().breaks():
			return False
		if len(self.items) > 0:
			if self in player.surroundings():
				Print("Its contents spill out.")
		# drop things it contains into parent
		for item in self.items.copy():
			item.waitInput(f"You are no longer in {-self}.")
			item.changeLocation(parent)
			item.Print(f"{+item} comes out of {-self}.")
		return True


	# check that capacity is not exceeded, displacing largest items if so
	def checkCapacity(self):
		while self.capacity != -1 and self.itemsSize() > self.capacity:
			item = max(self.items, key=lambda x: x.Size())
			self.Print(f"{+item} falls out of {-self}.")
			item.displace(self.parent)


	# remove Item
	def remove(self,I):
		self.items.remove(I)


	# try to remove an area condition from all affected objs in the Container
	def removeAreaCondition(self,areacond):
		return Room.removeAreaCondition(self,areacond)


	# removes all conditions with the given name and duration
	# when nothing given, remove all status conditions
	def removeStatus(self,reqName=None,reqDuration=None):
		return Room.removeStatus(self,reqName=reqName,reqDuration=reqDuration)


	### Interaction ###

	# try to bombard the Container with a Projectile
	# if it hits, go in it if possible, otherwise collide with it
	def bombard(self,missile):
		assert isinstance(missile,Projectile)
		if roll(100) < bound(missile.aim+self.Size()+10,1,99):
			if getattr(self,"closed",False):
				self.printNearby(f"{+self} is closed.")
				missile.collide(self)
			elif missile.item.parent is self:
				missile.collide(self)				
			elif not self.canAdd(missile):
				self.printNearby(f"{+self} is too full.")
				missile.collide(self)
			else:
				self.printNearby(f"{+missile} goes into {-self}.")
				missile = missile.asItem()
				missile.changeLocation(self)
			return True
		return False


	# try to enter the Container, applying any relevant status effects
	def enter(self,traverser):
		if traverser in self:
			return False
		return Room.enter(self,traverser)


	# be looked at be a looking Creature and show description of contents
	def examine(self,looker):
		# exclude player if they are inside the box
		displayItems = [item for item in self.items if item is not looker]
		if len(displayItems) == 0:
			text = "It is empty"
			if looker in self.items:
				text += ", apart from you"
			looker.Print(f"{text}.")
		else:
			looker.Print(listObjects("Inside there is ", displayItems,"."))
			if looker is player:
				game.setPronouns(self.items[-1])
		return True


	# try to exit the Container, removing any relevant status effects
	def exit(self,traverser):
		if traverser not in self:
			return False
		traverser.removeStatus("hidden",-4)
		return Room.exit(self,traverser)


	# replace oldItem in items with newItem if possible
	def replaceObj(self,oldItem,newItem):
		assert oldItem in self.items
		if not self.canAdd(newItem):
			return False
		index = self.items.index(oldItem)
		self.items[index] = newItem
		newItem.parent = self
		oldItem.parent = None
		return True


	# for Creatures intentionally travelling into/out of the Container
	def traverse(self,traverser,dir=None,verb=None):
		# unabbreviate/simplify direction
		if dir in Data.directions: dir = Data.directions[dir]
		if self in traverser.objTree():
			traverser.Print(f"You can't enter {-self}. It's within your Inventory.")
			return False
		if traverser in self.occupants:
			traverser.Print(f"You can't, you are {traverser.position()}.")
			return False

		# exit the container
		if dir == self.exitprep:
			if self is traverser.parent:
				if hasMethod(self,"open") and getattr(self,"closed",False):
					if not self.open(traverser,silent=False):
						return False
				traverser.Print(f"You get out of {-self}.")
				if self.parent is not game.currentroom:
					traverser.waitInput()
				traverser.changeLocation(self.parent)
				return True
			else:
				traverser.Print(f"You're not in {-self}.",color="k")
				return False

		# try to enter the container
		if traverser.parent is self:
			traverser.Print(f"You're already in {-self}.")
			return False
		if dir not in (self.passprep,None):
			traverser.Print(f"{+self} does not go {dir}.",color="k")
			return False

		if getattr(self,"closed",False):
			if not self.open(traverser,silent=False):
				return False
		if not self.canAdd(traverser):
			traverser.Print(f"You can't enter {-self}. There's not enough room.")
			return False

		if dir is None: dir = "into"
		if verb is None: verb = "get"
		traverser.Print(f"You {verb} {dir} {-self}.")
		traverser.changeLocation(self)
		return True


	### Getters ###


	# returns dict of links, where keys are directions and values are Rooms/Portals
	def allLinks(self,d=3):
		links = super().allLinks(d=d)
		# get a list of Portals in this Container
		portals = self.query(key=lambda x: isinstance(x,Portal),d=d)
		# for each Portals, add its links to links
		for portal in portals:
			for dir in portal.getLinksForParent():
				if dir not in links:
					links[(dir,portal)] = portal.links[dir]
		return links


	# check if item fits within Container's capacity
	def canAdd(self,I):
		if self.capacity == -1:
			return True
		return I.Size() <= self.vacancy() and self not in I.objTree()


	# return self.items plus surfaces that are not None or self
	def contents(self):
		cts = self.items + [s for s in self.surfaces if s not in (None,self)]
		return cts


	# when getting a random direction to go, always go 'into' the Container
	def getDefaultDir(self):
		return self.passprep


	# get the links dict to use in the parent's allLinks method
	# we don't want to include the exit link, that is not accessible from the parent
	def getLinksForParent(self):
		return {self.passprep:self}


	# get total size of all items in Container
	def itemsSize(self):
		return sum(i.Size() for i in self.items)


	# get total weight of all items in Container
	def itemsWeight(self):
		return sum(i.weight for i in self.items)


	# for Containers, the links are dynamic, but are used as property for compatibility
	# entering always links to self and exiting always links to parent
	@property
	def links(self):
		return {self.passprep:self, self.exitprep:self.parent}


	# get available capacity in Container
	def vacancy(self):
		return self.capacity - self.itemsSize()


	# get total weight of Container plus its Items
	def Weight(self):
		return self.weight + self.itemsWeight()



# used as shorthand to make a Portal that is fixed and not mentioned by default
class Passage(Portal):
	def __init__(self,name,desc,weight,composition,links,passprep="into",mention=False,
	durability=-1,fixed=True,**kwargs):
		super().__init__(name,desc,weight,durability,composition,links,passprep=passprep,
		mention=mention,fixed=True,**kwargs)



# Serpens are piles of gold coins
# they must be merged together if they're in the same contents
class Serpens(Item):
	def __init__(self,value,**kwargs):
		desc = f"{str(value)} glistening coins made of an ancient metal."
		Item.__init__(self,"gold",desc,value,-1,"gold",**kwargs)
		self.aliases = ["coin","coins","money","serpens",str(value)+" gold"]
		self.plural = "gold"
		self.descname = str(value) + " gold"
		self.value = value


	### File I/O ###

	# returns a dict which contains all the necessary information to store...
	# this object instance as a JSON object when saving the game
	def convertToJSON(self):
		return {
			"value": self.value,
			"status": self.status
		}


	### Operation ###

	# don't obtain normally, just increase obtainer's money
	def obtain(self,obtainer):
		super().obtain(obtainer)
		obtainer.updateMoney(self.value)


	# absorb value of other into self, then update description
	def merge(self,other):
		if not isinstance(other,Serpens):
			raise TypeError("Cannot merge non-Serpens with Serpens")

		self.status += other.status
		self.value += other.value
		self.desc = f"{str(self.value)} glistening coins made of an ancient metal."


	### User Output ###

	# intelligently get phrase to represent this in different grammatical contexts
	def nounPhrase(self,det="",n=-1,plural=False,cap=0):
		strname = "Gold"
		if det:
			# "a" only applies if there's 1, otherwise use indefinite plural
			if det == "a" and self.value != 1:
				det = "some"
			strname = det + " " + strname
		else:
			strname = str(self.value) + " " + strname
		if cap > 0:
			strname = capWords(strname,c=cap)
		return strname


# Projectiles are Items that can be launched at targets
# it can be a standalone "true" Item when Projectile.item is None
# or it could be a temporary wrapper for another Item stored in Projectile.item
# __getattribute__ and __setattr__ pass through any attribute access to self.item first
# if it exists, otherwise to self
class Projectile(Item):
	def __init__(self,name,desc,weight,durability,composition,might,sharpness,type,speed=0,item=None,**kwargs):
		# must be first or setattr will fail
		object.__setattr__(self,"item",item)
		if self.item is None:
			Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		object.__setattr__(self,"might",might)
		object.__setattr__(self,"sharpness",sharpness)
		object.__setattr__(self,"type",type)
		object.__setattr__(self,"speed",speed)
		# self.parent may be borrowed from self.item
		# in this case, the Projectile instance won't show up in parent's contents
		object.__setattr__(self,"parent",getattr(self.item,"parent",None))


	### Dunder Methods ###

	def __str__(self):
		return str(self.item) if self.item else self.name


	def __neg__(self):
		return super().__neg__() if self.item else "the " + self.name


	def __pos__(self):
		return super().__pos__() if self.item else "The " + self.name


	def __invert__(self):
		return super().__invert__() if self.item else "a " + self.name


	# if accessing .item or .asProjectile(), get from self
	# otherwise always try to get attributes from self.item first,
	# and then only get attribute from self if not found on self.item
	def __getattribute__(self, attr):
		if attr in ("item","asProjectile"):
			return object.__getattribute__(self, attr)
		try:
			return getattr(object.__getattribute__(self, "item"), attr)
		except AttributeError:
			return object.__getattribute__(self, attr)


	# if setting .item, always set on self
	# otherwise, set it in self.item if it exists and has that attribute
	# else set it on self
	def __setattr__(self, attr, value):
		# always allow setting the wrapped item itself
		if attr == "item":
			object.__setattr__(self, attr, value)
			return

		item = object.__getattribute__(self, "item")
		if item is not None and hasattr(item, attr):
			setattr(item, attr, value)
		else:
			object.__setattr__(self, attr, value)


	### Operation ###

	# launch the Projectile at target from launcher with given speed and aim accuracy
	def launch(self,speed,aim,launcher,target):
		self.speed = speed
		self.aim = 90 if self.hasStatus("homing") and aim < 90 else aim

		# when launching into another Room, just change location
		if isinstance(target,Room):
			self = self.asItem()
			if self.parent is not target:
				self.changeLocation(target)
			return self.fall(speed//4)
		# if has occupants, then make them fall off
		if isinstance(self.item,Item):
			for occupant in self.occupants.copy():
				occupant.fall(speed//4)
			self.item.clearOccupants()

		# when launching from within in a Container at something outside the Container
		if self.item.parent not in (target,target.parent):
			# if parnet is closed, bombard the parent
			if getattr(self.parent,"closed",False):
				return self.parent.bombard(self)
			# otherwise change location to parent first
			self.item.changeLocation(target.parent)

		# try to bombard the target
		if not target.bombard(self):
			Print(f"{self.pronoun.title()} misses!")
			self.miss(launcher,target)

		# if not a true projectile, then fall to ground
		if self.item:
			if not self.hasStatus("flying") and target is not target.parent.floor:
				if target is None or target.anchor() is None:
					self.fall(speed//4)
		return True


	# when missed the target, have a chance to hit another object in the room
	def miss(self,launcher,target):
		self.aim = -10 if self.asItem().hasStatus("homing") else min1(self.aim-10)

		# can't hit itself, the launcher, or the intended target
		otherObjs = [obj for obj in self.parent if obj not in \
		(self,self.item,launcher,target)]
		# having the curse of calamity makes ricocheting objects hit oneself
		if launcher.hasStatus("calamity"):
			otherObjs.append(launcher)
		if any(obj.hasStatus("calamity") for obj in otherObjs):
			otherObjs = [o for o in otherObjs if o.hasStatus("calamity")]
		sizes = [obj.Size() for obj in otherObjs]

		# more likely to hit larger objects
		victim = choices(otherObjs,sizes)[0]
		if victim is None:
			return False
		if victim is target.parent:
			return victim.bombard(self)
		Print(f"{self.pronoun.title()} whizzes toward {-victim}!", color="o")
		if not victim.bombard(self):
			Print(f"{self.pronoun.title()} misses...")


	# when colliding with target, deal damage and take self damage
	def collide(self,target):
		if target is player:
			Print(f"{+self} hits you!",color="o")
		else:
			Print(f"{+self} hits {-target}.")

		# deal damage to target
		d = self.might * self.speed
		if percentChance(self.sharpness):
			d *= 2
			Print("Critical hit!",color="o")
			self.dull(1)
		damage = diceRoll(0,d,d)
		target.takeDamage(damage,self.type)

		# take self damage
		if self.item:
			selfdmg = 0
			# if hits a creature, take damage according to one of the creature's gear
			if isinstance(target,Creature):
				gearItems = [item for item in target.gear.values()]
				sizes = [min1(item.Size()) for item in gearItems]
				target = choices(gearItems,sizes)[0]
			if target.durability == -1:
				selfdmg = self.speed * 3
			elif target.durability > self.durability:
				selfdmg = self.speed * (target.durability // self.durability)
			if selfdmg > 0:
				self.item.takeDamage(selfdmg,"b")
		else:
			self.parent.remove(self)
		return True


	# get the wrapped Item if it exists, otherwise return self
	def asItem(self):
		return self.item if self.item else self


	# its already a projectile!
	def asProjectile(self):
		return self



# Weapons are Items that can be used to attack
# they have might, sleight, sharpness, range, type and twohanded attributes
class Weapon(Item):
	def __init__(self,name,desc,weight,durability,composition,might,sleight,sharpness,
	range,type,twohanded=False,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		# amount of damage weapon deals
		self.might = might
		# accuracy of weapon
		self.sleight = sleight
		# chance of critical hits, degrades over time
		self.sharpness = sharpness
		# effective distance weapon can reach
		self.range = range
		# whether weapon requires two hands to wield
		self.twohanded = twohanded
		# damage type
		self.type = type


	# decrease sharpness by dec unless keen
	def dull(self,dec):
		if not self.hasStatus("keen"):
			self.sharpness = min0(self.sharpness - dec)


	# display weapon and stats
	def show(self):
		Print(f"{self.name} {self.might} {self.sleight}")
		Print(f"{self.sharpness} {self.twohanded} {self.range}")


	# licking shark weapons hurts!
	def lick(self,licker):
		# TODO: don't check for composition, check for if its sharp?
		if self.composition in ("glass","bronze","iron","steel"):
			Print("It tastes like... blood.")
			licker.takeDamage(3,"s")
			return True

		if self.composition in Data.tastes:
			Print(Data.tastes[self.composition])
		if self.composition in Data.scents:
			Print(Data.scents[self.composition].replace("scent","taste"))


	# wrap as Projectile for temporary use while launching
	def asProjectile(self):
		return Projectile(self.name,self.desc,self.weight,self.durability,
		self.composition,self.might,self.sharpness,self.type,item=self)


	# if given keen status, maximize sharpness
	def addStatus(self,name,dur,stackable=True):
		if super().addStatus(name,dur,stackable=stackable):
			if self.hasStatus("keen"):
				self.sharpness = 20
			return True



class Shield(Item):
	def __init__(self,name,desc,weight,durability,composition,prot,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.prot = prot



class Armor(Item):
	def __init__(self,name,desc,weight,durability,composition,prot,slots=None,**kwargs):
		Item.__init__(self,name,desc,weight,durability,composition,**kwargs)
		self.prot = prot
		self.slots = slots if slots else []
		if type(slots) is not list:
			self.slots = [slots]


	def equip(self):
		pass


	def unequip(self):
		pass



class Compass(Item):
	def orient(self):
		Print("Orienting you northward!")




#############
## GLOBALS ##
#############


player = Player("","",0,[0]*10,0,0)
defaultRoom = Room("","","",{},[],[],[])
game = Game(-1,defaultRoom,defaultRoom,-1,set(),{},{},{})
world = {}