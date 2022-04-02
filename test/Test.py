
import os
import sys

sys.path.append("../src")
import PoPy




def testMenu():
	sys.stdin = open("testMenu.txt")
	if os.path.exists("../saves/testsave"):
		os.rmdir("../saves/testsave")
	os.chdir("..")
	PoPy.main()
	PoPy.main()
	PoPy.main()

# tests each of the cheatcodes
def testCheatcodes():
	pass

# tests look, listen, and actions which don't alter the world state
def testInfo():
	pass

# tests all forms of navigation
def testNavigation():
	pass

# tests open, close, take/grab, put, and drop actions
def testInventory():
	pass

# tests use, eat, equip, lock, pour and related actions
def testBasicItems():
	pass

# tests attacking and breaking
def testCombat():
	pass

# tests basic spell usage
def testSpells():
	pass

if __name__ == "__main__":
	testMenu()
