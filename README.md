# ibc
Identity Block Chain
___making sense of the db___
writing to the DB:
- in ibc:
	- self.agents = something # initializing a new agent
	- commit()
	  - keeps the state execution in the correct order 
		- happens between writing to the ledger and the writing of the state
- in blockchain: (the one that deals with the ledger)
	- write to the ledger 
