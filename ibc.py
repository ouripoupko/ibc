
import sys
import json
from flask import Flask, request
from state import State
from blockchain import BlockChain
from network import Network


# Create the application instance
app = Flask(__name__)
state = State()
chain = BlockChain()
network = None
me = 0


# Create a URL route in our application for contracts
@app.route('/contract/', methods = ['GET','POST','PUT','DELETE'])
def contract():
  params = request.get_json()
  if request.method == 'PUT':
    chain.log('CREATE', params)
    return state.add(params['name'], params['code'], network)
  elif request.method == 'POST':
    if params['to'] == network.me:
      if not params['from']:
        chain.log('TRIGGER', params)
      else:
        chain.log('INPUT', params)
      return state.call(params['msg'])


# Create a URL route in our application for partners
@app.route('/partner/', methods = ['GET','POST','PUT','DELETE'])
def partner():
  params = request.get_json()
  if request.method == 'PUT':
    network.addPartner(params['addr'], params['id'])
  return {'partners': str(network.partners)}


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
  me = str(int(sys.argv[1])-5000)
  network = Network(me)
  app.run(debug=True, port = sys.argv[1])
