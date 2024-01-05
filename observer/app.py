from flask import Flask , render_template, request
from flask_socketio import SocketIO

app=Flask("__name__")
socketio=SocketIO(app)

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/update",methods=['POST'])
def timer():
    data=request.get_json()
    socketio.emit("index",data)
    return render_template("index.html")