from nodes import *
import socket
from flask import Flask,request,jsonify
import requests
import socket
from nodes import *

app=Flask("__name__")

my_ip =socket.gethostbyname(socket.gethostname())
node_list=[my_ip[:-1]+str(i) for i in range(3,6)]

myNode=Node(my_ip,node_list,"log.txt")


@app.route("/")
def index():
    return "<h1>Hello from Controller</h1>"

@app.route("/vote_Req",methods=['POST'])
def voteReq():
    data=request.get_json()
    res = myNode.vote_response_rpc(data)
    return res

@app.route("/heartbeat",methods=['POST'])
def heartbeat_handler():
    data = request.get_json()
    res = myNode.recv_heartbeat(data)
    return res
    