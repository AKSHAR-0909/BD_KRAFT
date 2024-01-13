from flask import Flask 
import socket 
import requests
import time
import random
import uuid
app=Flask("__name__")


time.sleep(10)
brokerHost=socket.gethostbyname(socket.gethostname())
registerBrokerRecord={
    "brokerHost":brokerHost,
    "brokerId":int(brokerHost[-1]),
    "brokerPort":5000 ,
    "securityProtocol":"PLAINTEXT",
    "brokerStatus":"ALIVE",
    "rackId":"rack-1"
}
topic_store = {}

print("sending",registerBrokerRecord)
controller_ip = "bd_kraft-controller-1:5000"
success = False
while not success:
    res=requests.post(f"http://{controller_ip}/handleBroker/registerBrokerRecord",json=registerBrokerRecord,headers={"Content-Type":"application/json"})
    if res and not res['success']:
        controller_ip = res['current_leader']
    else:
        success = True

    
@app.route("/TopicRecords")
def TopicRecord():
    topic_name =  f"kafka-topic{random.randint(1,100)}"
    topicRecord = {
        "topic_name":topic_name
    }
    ip_controller = "bd_kraft-controller-1:5000"
    while True:
        res = requests.post(f"http://{ip_controller}/handleTopic/createTopic",json=topicRecord,headers={"Content-Type":"application/json"})
        if res and not res['success']:
            ip_controller = res['current_leader']
        else:
            topic_store[res] = topic_name
            break
    return res
@app.route("/PartitionRecords")
def CreatePartitionRecord():
    paritionId = str(uuid.uuid4())
    partitionRecord = {
        "partitionId": paritionId,
		"topicUUID": random.choice(topic_store.keys()), 
		"replicas": [],
		"ISR": [], 
		"removingReplicas": [], 
		"addingReplicas": [], 
		"leader": paritionId, 
    }
    ip_controller = "bd_kraft-controller-1:5000"
    while True:
        res = requests.post(f"http://{ip_controller}/handleTopic/handlePatition/createPatition",json=partitionRecord,headers={"Content-Type":"application/json"})
        if res and not res['success']:
            ip_controller = res['current_leader']
        else:
            break
    return res

@app.route("/BrokerRegistrationChangeBrokerRecord")
def BrokerRegistrationChangeBrokerRecord():
    changeRegisterBrokerRecord = {
		"brokerId": int(brokerHost[-1]), #// type: string; given by client
		"brokerHost": brokerHost, #// type: string; given by client
		"brokerPort": "TCP", #// ype: string; given by client
		"securityProtocol": "INIT",#// type: string; given by client
		"brokerStatus": "ALIVE/Dead", #// type: string; given by client
    }
    ip_controller = "bd_kraft-controller-1:5000"
    while True:
        res = requests.post(f"http://{ip_controller}/handleTopic/handlePatition/createPatition",json=changeRegisterBrokerRecord,headers={"Content-Type":"application/json"})
        if res and not res['success']:
            ip_controller = res['current_leader']
        else:
            break
    return res


