
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


if __name__ == "__main__":
	testMenu()
