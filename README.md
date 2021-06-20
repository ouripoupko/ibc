# ibc
Identity Block Chain <br><br>
___making sense of the db___ <br><br>
Each agent contains 2 collections: ledger & state. <br>
The ledger has all the commands which were sent and agreed upon via BFT between the agents. <br>
The state is basically the application data of each of the contracts. <br><br>
- in ibc:
	- self.agents = something # get the agents collection
	- self.agents[self.identity] = something # initializing a new agent
	- commit()
		- The only function which writes to the db (except for intializing an agent above!)
		- keeps the state execution in the correct order 
		- writes to the ledger
		- waits to make sure it is the only one using the db right now
		- changes the state in accordance with the ledger state it just commited
		- note that the states can only change one at a time so contracts can run simultaneously..
- in blockchain: (the one that deals with the ledger)
	- write to the ledger collection (under a specific agent document)
	- read all records of a specific contract from the ledger 
- class state:
	- contains objects of type contract
	- add() - deoploy new contract
	- welcome() - connect between contracts between agents
- class contract:
	- run(): 
		- create an object which contains the code of the contract 
		- give it access to the db
		- write its relevant memory to state
	- connect() - write which agents are using the contract
