
import os
import sys

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)
sys.path.append("../src")

import PoPy


class TeeLogger:
	def __init__(self,filename,inputFile=None):
		self.terminal = sys.stdout
		self.originalStdin = sys.stdin
		self.errorTerminal = sys.stderr
		os.makedirs(os.path.dirname(filename),exist_ok=True)
		self.log = open(filename,"w")
		self.stdin = open(inputFile,"r") if inputFile else self.originalStdin


	def write(self, message):
		self.terminal.write(message)
		self.log.write(message)


	def write_error(self,message):
		self.errorTerminal.write(message)  # Print errors to stderr in terminal
		self.log.write(message)  # Log errors in the same file
		self.flush()


	def readline(self):
		input_text = self.stdin.readline()
		self.log.write(input_text)
		self.log.flush()
		return input_text


	def flush(self):
		self.terminal.flush()
		self.log.flush()


	def setInputFile(self, inputFilename):
		if self.stdin != self.originalStdin:
			self.stdin.close()
		self.stdin = open(inputFilename,"r")



# test the main menu
def testMenu():
	sys.stdin.setInputFile("test/testMenu.txt")
	if os.path.exists("saves/testsave"):
		for filename in os.listdir("saves/testsave"):
			os.remove("saves/testsave/" + filename)
		os.rmdir("saves/testsave")
	PoPy.main(testing=True)
	PoPy.main(testing=True)
	PoPy.main(testing=True)


# tests each of the cheatcodes
def testCheatcodes():
	sys.stdin.setInputFile("test/testCheatcodes.txt")
	PoPy.main(testing=True)


# tests look, listen, and actions which don't alter the world state
def testInfo():
	sys.stdin.setInputFile("test/testInfo.txt")
	PoPy.main(testing=True)


# tests go, govertical, go through passages multi/single directionally, open/closing doors,
def testNavigation():
	sys.stdin.setInputFile("test/testNavigation.txt")
	PoPy.main(testing=True)


# tests open, close, take/grab, put, and drop actions
def testInventory():
	sys.stdin.setInputFile("test/testInventory.txt")
	PoPy.main(testing=True)


# tests use, eat, equip, lock, pour and related actions
def testBasicItems():
	sys.stdin.setInputFile("test/testInventory.txt")
	PoPy.main(testing=True)


# tests attacking and breaking, cut
def testCombat():
	sys.stdin.setInputFile("test/testCombat.txt")
	PoPy.main(testing=True)


# tests crawl, hide, stealth, mount, laying, flying, jump, climb, swim
def testMobility():
	pass


# tests push, pull, catch, throw, tie, fish, press, ignite
def testMiscItems():
	pass


# tests pray, wave, point, touch, rub, play, pet, rest
def testGesturing():
	pass


# craft, cook,
def testCraft():
	pass


# tests basic spell usage
def testSpells():
	pass



if __name__ == "__main__":
	os.chdir("..")
	logger = TeeLogger("test/output.log")
	sys.stdout = logger
	sys.stdin = logger
	sys.stderr = logger
	testMenu()
	testInfo()
	testCheatcodes()
	testNavigation()
	testInventory()
	testBasicItems()
	testCombat()
	testSpells()
	print("\nAll tests passed without error\n")
