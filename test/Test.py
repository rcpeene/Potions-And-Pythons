
import os
import sys

sys.path.append("../src")
import PoPy



def test1():
	sys.stdin = open("test1.txt")
	os.chdir("..")
	PoPy.main()
	os.chdir("test")


def testMenu():
	sys.stdin = open("testMenu.txt")
	if os.path.exists("../saves/menu test"):
		os.rmdir("../saves/menu test")
	os.chdir("..")
	PoPy.main()
	PoPy.main()
	PoPy.main()


if __name__ == "__main__":
	test1()
