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
    rejectVote=jsonify({
        "term" : myNode.term,
        "voteGranted" : False
    })
    
    data=request.get_json()
    if myNode.term > data['term']: # if the follower term > candidate
        return rejectVote
    elif  myNode.voted_for['term']==myNode.term:
        return rejectVote
    elif myNode.next_index[myNode.my_ip]-1 > data['lastLogIndex']:
        return rejectVote
    else:
        myNode.voted_for['term'] = data['term']
        myNode.voted_for['candidateId'] = data['candidateId']
        return jsonify({
            "term":myNode.term,
            "voteGranted":True
        })

    