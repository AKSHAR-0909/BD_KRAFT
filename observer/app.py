from flask import Flask , render_template, request
from flask_socketio import SocketIO

app=Flask("__name__")
socketio=SocketIO(app)

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/updateTimer",methods=['POST'])
def updateTimer():
    data=request.get_json()
    socketio.emit("index",data)
    return render_template("index.html")

@app.route("/transitionToCandidate",methods=['POST'])
def handleCandidate():
    data=request.get_json()
    socketio.emit("transitionToCandidate",data)
    return "Hello"

@app.route("/transitionToLeader",methods=['POST'])
def handleLeader():
    data=request.get_json()
    socketio.emit("transitionToLeader",data)
    return "Hello"

@app.route("/transitionToFollower",methods=['POST'])
def handleFollower():
    data=request.get_json()
    socketio.emit("transitionToFollower",data)
    return "Hello"