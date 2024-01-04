from nodes import *
import socket
from flask import Flask,request
import requests


app=Flask("__name__")
my_ip=socket.gethostbyname(socket.gethostname())
fellow_ips=[my_ip[:-1]+str(i) for i in range(3,6)]


Node(my_ip,fellow_ips,"log.txt")

@app.route("/")
def index():
    return "<h1>Hello from Controller</h1>"

@app.route("vote_Req")
def voteReq():
    data=request.get_json()
    