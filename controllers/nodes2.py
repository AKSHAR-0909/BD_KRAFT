import re
import json
import logging
import threading
import time
import random, requests
from math import ceil
import uuid

MIN_TIMEOUT = 50
MAX_TIMEOUT = 80
FOLLOWER  = 0
CANDIDATE = 1
LEADER = 2
REQUEST_TIMEOUT = 50
HEARBEAT_INTERVAL = 10
HEARTBEAT_TIMOUT = 20
COMMIT_TIMEOUT = 3

class Node:
    
    def __init__(self,my_ip,node_list,log_file) -> None:
        
        self.my_ip = my_ip # the node's its own ip
        self.node_list = node_list
        self.ip_list=[my_ip[:-1]+str(i) for i in range(3,6)]
        self.term = 0       #Indicated the number of times a leader has been elected
        self.state = FOLLOWER
        self.timeout_thread = None
        self.election_time = None
        self.voted_for = {"term":None , "candidateId":None}
        self.votes = 0
        self.append_votes = 0
        self.prevLogIndex = 0
        self.prevLogTerm = 0
        self.current_leader = None
        self.leader_commit_index = 0
        self.log_file = [] # set to null after commiting all the entries
        self.heartbeat_thread = None
        self.commit_index = 0
        self.voting_lock = threading.Lock()
        self.last_msg_lock = threading.Lock()
        self.election_lock = threading.Lock()
        self.response_lock = threading.Lock()
        self.next_index_lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.term_loc = threading.Lock()
        self.log_file = log_file
        self.next_index = {}  #adding next index , initializing it 0 as of now
        self._initialize_next_index(0)
        # self.setup_logger()

        self.match_index = [0 for _ in range(len(self.node_list))] # same reason
        self.init_timeout()

    # AS FOLLOWER
    def check_timeout(self):
        print(f"Node {self.my_ip} timeout started!!!")
        heartbeat_timeout = random.randint(MIN_TIMEOUT,MAX_TIMEOUT)/10
        while self.state!=LEADER and self.state!=CANDIDATE:
            if time.time()-self.last_msg_time>=heartbeat_timeout:
                self.start_election()
            else:
                data={"ip":self.my_ip,"counter":abs(heartbeat_timeout-(time.time()-self.last_msg_time)),"term":self.term}
                requests.post("http://bd_kraft-observer-1:5000/updateTimer",json=data,headers={"Content-Type": "application/json"})


    def vote_response_rpc(self,data):
        if self.term > data['term'] or self.state==LEADER: # if the follower term > candidate
                return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        elif data['term']==self.term:
            return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        
        # elif self.prevLogTerm > data['lastLogTerm']:
        #     print("request not granted because lastLogTerm smaller")
        #     return {
        #             "term" : self.term,
        #             "voteGranted" : False
        #         }
        elif self.prevLogIndex > data['lastLogIndex']:
            print(f"next index of ip : {self.my_ip} = {self.next_index[self.my_ip]}")
            return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        else:
            if self.state != FOLLOWER:
                self._transition_to_follower()
            with self.term_loc:
                self.term = data['term']
            return {
                "term" : self.term,
                "voteGranted" : True
            }

    # follower receiving append entries 
    def AppendEntriesReceive(self,data):
        if(self.current_leader==None):
            self.current_leader=data['leaderId']

        print(f"{data} , {self.term}")

        if self.term > data['term']:
            print("in self.term>data['term']")
            return {
                "prevLogIndex" : self.prevLogIndex,
                "term" : self.term,
                "success" : False
            }
        
        if self.state != FOLLOWER:
            self._transition_to_follower()
            self.term = data['term']

        if self.prevLogIndex < data['prevLogIndex']:
            # follower is missing some entries
            print("in self.prevLogIndex < data['prevLogIndex']")
            return {
                "prevLogIndex" : self.prevLogIndex,
                "term" : self.term,
                "success" : False
            }
        
        self.init_timeout()            

        if self.prevLogIndex > data['prevLogIndex']:
            print("in self.prevLogIndex > data['prevLogIndex']")
            # follower has more entries than leader
            self.deleteFromLog(data['prevLogIndex'])
            for y in range(0,len(data['entries'])):
                self.appendToLog(data['entries'][y])
            return {
                "prevLogIndex" : self.prevLogIndex,
                "term" : self.term,
                "success" : True
            }
        # if appendEntries
        if data['entries'] != []:
            for y in range(0,len(data['entries'])):
                self.appendToLog(data['entries'][y])
            print("sending true")
            return {
                "prevLogIndex" : self.prevLogIndex,
                "term" : self.term,
                "success" : True
            }
        return 
    
    def appendToLog(self,data):
        with self.log_lock:
            entry = {"index":self.prevLogIndex, "term":self.term, "record":data}
            self.log_file.append(entry)
            self.prevLogIndex += 1


    # -------------------------------------------------------------------------------------------------------------------------
    # AS CANDIDATE
    def start_election(self):
        with self.election_lock:
            print(f"in election : {self.my_ip} is candidate now!!!")
            self._transition_to_candidate() # to maintian modularity
            self.votes = 0
            self.increment_vote()
            self.vote_request_rpc(self.term) #safe to pass

    #call increment vote from this function
    def vote_request_rpc(self,term):
        # TODO: vote timeout
        # if self.state == CANDIDATE:  safe to compare term rather than state
        if self.term == term and self.state == CANDIDATE:
            data = {
                "term":self.term,
                "candidateId":self.my_ip,
                "lastLogIndex" : self.prevLogIndex
                # "lastLogTerm" : self.log_file[self.prevLogIndex[self.my_ip]-1]
            }
            for f_ip in self.node_list:
                if self.my_ip != f_ip:
                    threading.Thread(target=self.sending_vote_req,args=(f_ip,data)).start()
        return
    
    def sending_vote_req(self,i,data):
        turn = 0
        res = None
        while not res and turn<3:
            try:
                res = requests.post(f"http://{i}:5000/vote_Req",json=data,headers={"Content-Type": "application/json"},timeout=REQUEST_TIMEOUT)
                res=res.json()
                if res['voteGranted']:
                    # print("incrementing vote from  votes = ",self.votes)
                    self.increment_vote()
                    break
            except Exception as e:
                print(e)
                print(f"Vote requests to {i} by candidate {self.my_ip} failed!!!")
                turn += 1
        return
    
    
    def _transition_to_candidate(self):
        print(f"{self.my_ip} - Transition to CANDIDATE")
        data={"candidateIP":self.my_ip}
        requests.post("http://bd_kraft-observer-1:5000/transitionToCandidate",json=data,headers={"Content-Type": "application/json"})
        # time.sleep(2)
        self.state = CANDIDATE
        with self.term_loc:
            self.term += 1
        data={"ip":self.my_ip,"counter":0,"term":self.term}
        requests.post("http://bd_kraft-observer-1:5000/updateTimer",json=data,headers={"Content-Type": "application/json"})
        return

    def increment_vote(self):
        with self.voting_lock:
            self.votes += 1
            print("votes = ",self.votes)
            if self.state == CANDIDATE:
                if(self.votes>=ceil((len(self.node_list))/2)):
                    print()
                    self._transition_to_leader()
        return
    
    def _transition_to_leader(self):
        print(f"{self.my_ip} Transition to LEADER")
        data={"leaderIP":self.my_ip}
        requests.post("http://bd_kraft-observer-1:5000/transitionToLeader",json=data,headers={"Content-Type": "application/json"})
        # time.sleep(2)
        self.state = LEADER
        self.current_leader = self.my_ip
        data={"ip":self.my_ip,"counter":0,"term":self.term}
        self._initialize_next_index(self.prevLogIndex+1)
        requests.post("http://bd_kraft-observer-1:5000/updateTimer",json=data,headers={"Content-Type": "application/json"})
        self.startHearbeat(self.term)

        with self.next_index_lock:
            for ips in self.node_list:
                self.next_index[ips] = 0
        return


    # ------------------------------------------------------------------------------
    # LEADER
    def _initialize_next_index(self,index):
        for ips in self.node_list:
            self.next_index[ips] = index
        
    def startHearbeat(self,term):
        print("starting heatbeat!!!!")
        if self.term == term:
            for f_ips in self.node_list:
                if f_ips == self.my_ip:
                    continue
                threading.Thread(target=self.sendHeartbeat,args=(self.term,f_ips)).start()
        return

    def sendHeartbeat(self, term, i):
        heart_beat_time = time.time()
        while time.time()-heart_beat_time<=HEARTBEAT_TIMOUT and self.term == term and self.state == LEADER:
            data = {
                "term": term,
                "leaderId" : self.current_leader,
                "prevLogIndex" : self.next_index[i],
                # "prevLogTerm" : self.log_file[self.next_index[i]][-1],  # FIX THIS LATER
                "entries" : [],
                "msg":f"sending message to follower {i}"
            }
            self.appendEntriesSend(term, i,data)
            time.sleep(HEARBEAT_INTERVAL/10)
            heart_beat_time = time.time()
        return
    
    

    # to send data from either appendEntries or heartbeats. 
    # here to ith follower
    def appendEntriesSend(self,term,i, data):
        if self.state==LEADER:
            self.append_votes = 0
            try:
                # FRAGMENT DATA INTO PARTS?
                res = requests.post(f"http://{i}:5000/messages",json=data,headers={"Content-Type": "application/json"},timeout=REQUEST_TIMEOUT)
                res = res.json()

                print(f"Append Entry Send Passed success to {i} , {res}")

                if res and res['success']:
                    # if ith follower successfully put AppendEntries into its log
                    print("incrementing vote from  votes = ",self.votes)
                    print(f"{res} from success i.e append succesfully")
                    if data!=[]:
                        self.incrementAppend(data)
                        # self.handleResponse(i,res,data)
                        self.next_index[i] += len(data['entries'])     # or number of entries?
                        
                elif res and not res['success'] and res['term']==term:
                    # case where follower log is lesser than leader log prevIndex
                    print(f"follower log lesser than leader log {res}")
                    if data!=[]:
                        self.next_index[i] = res["prevLogIndex"]
                        # FIX THIS PART
                        data['prevLogIndex'] = res['prevLogIndex']
                        self.appendEntriesSend(self,term,i,data)

                elif res and not res['success'] and res['term']>term:
                    print(f"leader transiting to follower {res}")
                    self.append_votes = 0
                    self.term = res['term']
                    self._transition_to_follower()
                    
            except Exception as e:
                print(f"Append Entry Message failed sending to {i} failed")
        #since looping is called from another function , i think it wouldnt matter much  
                

    def incrementAppend(self):
        # reusing this lock! :)
        with self.voting_lock:
            self.append_votes += 1
            print("responses for appendEntries = ",self.append_votes)
                
    def _transition_to_follower(self):
        print("becoming follower!!")
        self.state = FOLLOWER
        print(f"{self.my_ip} - Transition to Follower")
        data={"followerIP":self.my_ip}
        requests.post("http://bd_kraft-observer-1:5000/transitionToFollower",json=data,headers={"Content-Type": "application/json"})
        self.init_timeout()
        return