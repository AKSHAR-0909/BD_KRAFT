from flask import Flask 
import socket 
import requests
import time
app=Flask("__name__")


time.sleep(10)
brokerHost=socket.gethostbyname(socket.gethostname())
registerBrokerRecord={
    "brokerHost":brokerHost,
    "brokerId":int(brokerHost[-1]),
    "brokerPort":5000 ,
    "securityProtocol":"PLAINTEXT",
    "brokerStatus":"INIT",
    "rackId":"rack-1"
}

print("sending",registerBrokerRecord)
res=requests.post("http://bd_kraft-controller-1:5000/handleBroker/registerBrokerRecord",json=registerBrokerRecord,headers={"Content-Type":"application/json"})

    
@app.route("/")
def index():
    return "<h1>Hello from Broker</h1>"