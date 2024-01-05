from nodes import *
import socket
from flask import Flask,request
import requests
import socket

app=Flask("__name__")
ip =socket.gethostbyname(socket.gethostname())

time.sleep(5)

def startTimeout():
    counter=50
    while(counter>0):
        data={"ip":ip,"counter":counter}
        print("sent",data,"to","bd_kraft-observer:5000")
        requests.post("http://bd_kraft-observer-1:5000/timer",json=data,headers={"Content-Type": "application/json"})
        counter-=0.05
timer=threading.Thread(target=startTimeout)
timer.start()


@app.route("/")
def index():
    return "<h1>Hello from Controller</h1>"

@app.route("vote_Req")
def voteReq():
    data=request.get_json()
    