from nodes import *
import socket
from flask import Flask,request,jsonify
import requests
import socket
from nodes2 import *
import uuid
import json

app=Flask("__name__")

Storage={
    "RegisterBrokerRecords":{"records":[],"timestamp":time.time()},
    "TopicRecord":{"records":[],"timestamp":time.time()},
    "PartitionRecord":{"records":[],"timestamp":time.time()},
    "ProducerIdsRecord":{"records":[],"timestamp":time.time()},
    "BrokerRegistrationChangeBrokerRecord":{"records":[],"timestamp":time.time()}
}

my_ip =socket.gethostbyname(socket.gethostname())
node_list=[my_ip[:-1]+str(i) for i in range(3,6)]

myNode=Node(my_ip,node_list,"log.txt")


@app.route("/")
def index():
    return "<h1>Hello from Controller</h1>"

@app.route("/vote_Req",methods=['POST'])
def voteReq():
    data=request.get_json()
    print("received msg from candidate",data)
    res = myNode.vote_response_rpc(data)
    return res

@app.route("/messages",methods=['POST'])
def heartbeat_handler():
    data = request.get_json()
    res = jsonify(myNode.AppendEntriesReceive(data))
    return res

@app.route("/handleBroker/registerBrokerRecord",methods=['POST'])
def registerBrokerRecord():
    data=request.get_json()
    response_data=myNode.receiveMessages(data, "/handleBroker/registerBrokerRecord")
    print(response_data)
    return jsonify(response_data)
    
    

@app.route("/handleBroker/getActiveBrokers",methods=['GET'])
def getActiveBrokers():
    return Storage["RegisterBrokerRecords"]["records"]

@app.route("/handleBroker/getSpecificBroker/<brokerID>",methods=['GET'])
def getSpecificBroker(brokerID):
    return Storage["RegisterBrokerRecords"]["records"][brokerID]

@app.route("/handleTopic/createTopic",methods=['POST'])
def createTopic():
    data=request.get_json()
    topicName=data['topic_name']
    topicUUID=uuid.uuid4()
    newTopicRecord={
        "type": "metadata",
        "name": "TopicRecord",
        "fields": {
            "topicUUID": topicUUID,
            "name": topicName
        },
        "timestamp": time.time() 
    }
    # Storage["TopicRecord"]["records"][topicName]=newTopicRecord
    res = myNode.appendEntriesSend(topicName,"/handleTopic/createTopic")
    
    return res

@app.route("/handleTopic/getTopic/<name>",methods=['GET'])
def getTopic(name):
    res = myNode.getBrokers(name)
    return res

@app.route("/handlePatition/createPatition",methods=['POST'])
def createPatition():
    data=request.get_json()
    newPartitionRecord={
        "type": "metadata",
        "name": "PartitionRecord",
        "fields": {
            "partitionId": data['partitionId'],
            "topicUUID": data['topicUUID'],
            "replicas": data['replicas'], # type: []int; list of broker IDs with replicas; given by client, through config
            "ISR": data['ISR'], # type: []int; list of insync broker ids; given by client, through config
            "removingReplicas": data['removingReplicas'], # type: []int; list of replicas in process of removal; set as [] by default; updated by the server but not in scope of the project;
		    "addingReplicas": data['addingReplicas'], # type: []int; list of replicas in the process of addition; set as [] by default; updated by the server but not in scope of the project;
            "leader": data['leader'], # type: string uuid of broker who is leader for partition; given by client
            "paritionEpoch":0
        },
        "timestamp": time.time()
    }
    # Storage["PartitionRecord"]["records"][data['partitionId']]=newPartitionRecord
    res =  myNode.appendToLog(newPartitionRecord,"/handlePatition/createPatition")
    
    return 0


@app.route("/handleProducer/registerProducer")
def registerProducer():
    data=request.get_json()
    newProducerRecord={
        "type": "metadata",
        "name": "ProducerIdsRecord",
        "fields": {
            "brokerId": data['broker_Id'], # type : string/int; uuid of requesting broker; given by client
            "brokerEpoch": data['brokerEpoch'], # type : int; the epoch at which broker requested; set to broker epochl
            "producerId": data['producerId'] # type : int; producer id requested; given by client 
        },
        "timestamp": time.time()
    }
    # Storage['ProducerIdsRecord']["records"][data['producerId']]=newProducerRecord
    # Storage['ProducerIdsRecord']['timestamp']=time.time()
    res = myNode.appendToLog(newProducerRecord,"/handleProducer/registerProducer")


@app.route("/handleBroker/changeBrokerRecord")
def changeBrokerRecord():
    data=request.get_json()
    newProducerRecord={
        "type": "metadata",
        "name": "RegistrationChangeBrokerRecord",
        "fields": {
            "brokerId":data['Id'],
            "brokerHost":data['Host'],
            "brokerPort":data['port'],
            "securityProtocol":data["securityProtocol"],
            "brokerStatus":data['brokerStatus']
        },
        "timestamp": time.time()
    }
    res = myNode.appendToLog(newProducerRecord,"/handleBroker/changeBrokerRecord")

    return res
    # Storage['ProducerIdsRecord']["records"][data['producerId']]=newProducerRecord
    # Storage['ProducerIdsRecord']['timestamp']=time.time()
    