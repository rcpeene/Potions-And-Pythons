
import os
import sys

sys.path.append("../src")
import PoPy



# test the main menu
def testMenu():
	sys.stdin = open("test/testMenu.txt")
	if os.path.exists("saves/testsave"):
		for filename in os.listdir("saves/testsave"):
			os.remove("saves/testsave/" + filename)
		os.rmdir("saves/testsave")
	PoPy.main()
	PoPy.main()
	PoPy.main()


# tests each of the cheatcodes
def testCheatcodes():
	sys.stdin = open("test/testCheatcodes.txt")
	PoPy.main()


# tests look, listen, and actions which don't alter the world state
def testInfo():
	sys.stdin = open("test/testInfo.txt")
	PoPy.main()

# tests all forms of navigation
def testNavigation():
	sys.stdin = open("test/testNavigation.txt")
	PoPy.main()


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
	os.chdir("..")
	testMenu()
	testInfo()
	testCheatcodes()
	testNavigation()
	testInventory()
	print("\nAll test passed without error\n")
