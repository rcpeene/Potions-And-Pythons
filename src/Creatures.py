# Creatures.py
# This file contains the creature classes used in the game
# This file is dependent on Core.py and is a dependency of Menu.py and Interpreter.py

import Effects
import Core
import Data




################################
## CREATURE CLASS DEFINITIONS ##
################################



factory = {
	"green python": lambda: Core.Animal("green python","A small brown and green spotted snake.",3,Data.inittraits,"python",aliases={"snake","python","green snake"}),
    "red python": lambda: Core.Animal("red python","A small brown and red striped snake.",3,Data.inittraits,"python",aliases={"snake","python","red snake"}),
	"goblin": lambda: Core.Humanoid("goblin","A small green humanoid with long ears, a pointy nose, and a grimacing visage.",10,[2]*10),
	"horse": lambda: Core.Animal("horse","A strong brown mustang.",300,[8,10,3,12,12,3,1,2,2,5],aliases={"mustang"})
}

# verify the integrity of the spawnpools with the factory
for domain, spawnpool in Data.spawnpools.items():
	for name, prob in spawnpool:
		assert name in factory, f"name {name} not in Creatures factory"