# ibc
Identity Block Chain <br><br>
___making sense of the db___
writing to the DB:
- in ibc:
	- self.agents = something # get the agents collection
	- self.agents[self.identity] = something # initializing a new agent
	- commit()
	  - keeps the state execution in the correct order 
	  - happens between writing to the ledger and the writing of the state
- in blockchain: (the one that deals with the ledger)
	- write to the ledger collection (under a specific agent document)
	- read all records of a specific contract from the ledger 
