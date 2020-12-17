
import sys
import json
from flask import Flask, request


# Create the application instance
app = Flask(__name__)


# Create a URL route in our application for contracts
@app.route('/contract/', methods = ['GET','POST','PUT','DELETE'])
def contract():
    contract = request.get_json()
    exec(contract["code"])
    o17 = locals()[contract["name"]]()
    print(o17.addEdge(3))
    return json.dumps({"reply":'hello world'})


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    app.run(debug=True, port = sys.argv[1])
