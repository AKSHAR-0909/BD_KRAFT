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
VOTING_TIMEOUT = 20
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
        self.local_log = [] # set to null after commiting all the entries
        self.heartbeat_thread = None
        self.commit_index = 0
        self.voting_lock = threading.Lock()
        # self.last_msg_lock = threading.Lock()
        self.election_lock = threading.Lock()
        # self.response_lock = threading.Lock()
        self.next_index_lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.term_loc = threading.Lock()
        self.append_lock = threading.Lock()
        self.log_file = log_file
        self.next_index = {}  #adding next index , initializing it 0 as of now
        self._initialize_next_index(0)
        self.setup_logger()

        self.match_index = [0 for _ in range(len(self.node_list))] # same reason
        self.init_timeout()

    # ----------------------------------------------------------------------------------------- 
    # AS FOLLOWER
    
    #  Initilises the timeout and creates a timeout thread initially
    def init_timeout(self):
        self.reset_timeout()
        if not (self.timeout_thread and self.timeout_thread.is_alive()):
            self.timeout_thread = threading.Thread(target=self.check_timeout,args=())
            self.timeout_thread.start()  
    def reset_timeout(self):
        with self.last_msg_lock:
            self.last_msg_time = time.time()    
        return
            
    def check_timeout(self):
        print(f"Node {self.my_ip} timeout started!!!")
        heartbeat_timeout = random.randint(MIN_TIMEOUT,MAX_TIMEOUT)/10
        while self.state!=LEADER and self.state!=CANDIDATE:
            if time.time()-self.last_msg_time>=heartbeat_timeout:
                self.start_election()
            else:
                data={"ip":self.my_ip,"counter":abs(heartbeat_timeout-(time.time()-self.last_msg_time)),"term":self.term}
                requests.post("http://bd_kraft-observer-1:5000/updateTimer",json=data,headers={"Content-Type": "application/json"})

    
    def setup_logger(self):
        logging.basicConfig(filename=self.log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


    def vote_response_rpc(self,data):
        last_term = 0 if self.prevLogIndex==0 else self.local_log[self.prevLogIndex]['term']
        if self.term > data['term'] or self.state==LEADER: # if the follower term > candidate
                return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        if data['term']==self.term:
            if self.voted_for["term"]==self.term and self.voted_for["candidateId"]==data["candidateId"]:
                return {
                    "term" : self.term,
                    "voteGranted" : True
                }
            return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        
        if not ((data['lastLogTerm'] > last_term) or (data['lastLogTerm']==last_term and self.prevLogIndex+1 > data['lastLogIndex'])):
            print("request not granted because lastLogTerm smaller")
            return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        
        # condition already satified
        # elif self.prevLogIndex > data['lastLogIndex']:
        #     print(f"next index of ip : {self.my_ip} = {self.next_index[self.my_ip]}")
        #     return {
        #             "term" : self.term,
        #             "voteGranted" : False
        #         }
        
        if self.state != FOLLOWER:
            self._transition_to_follower()
        with self.term_loc:
            self.term = data['term']
        self.voted_for["candidateId"] = data["candidateId"]
        self.voted_for["term"]=data["term"]
        return {
            "term" : self.term,
            "voteGranted" : True
        }

    # follower receiving append entries 
    def AppendEntriesReceive(self,data):
        hOrA = 0 if data[0]["entries"]==None else 1
        first_log = data[0]
        last_log = data[-1]
        # if last_log["term"] >= self.term:
        #     if self.state != FOLLOWER:
        #         self._transition_to_follower()
        #         self.current_leader = last_log["leaderId"]
        #     with self.term_loc:
        #         self.term = last_log["term"]

        # if self.prevLogIndex >= first_log['prevLogIndex'] and (self.prevLogIndex==0 or self):
        #             print("in self.prevLogIndex > data['prevLogIndex']")
        #             # follower has more entries than leader
        #             self.deleteFromLog(data['prevLogIndex'])
        #             if self.prevLogTerm==first_log["prevLogTerm"]:
        #                 for y in range(0,len(data)):
        #                     self.appendToLog(data[y])
        #             else:
        #                 return {
        #                 "prevLogIndex" : self.prevLogIndex,
        #                 "term" : self.term,
        #                 "success" : False}
        
        # if self.prevLogIndex == first_log["prevLogIndex"] and self.prevLogTerm==first_log["prevLogTerm"]:
        #     for y in range(0,len(data)):
        #             self.appendToLog(data[y])
        # '''

        print(f"{first_log} , {self.term}")

        self.init_timeout()
        if self.term > last_log['term']:
            print("in self.term>data['term']")
            return {
                "lastLogIndex" : self.prevLogIndex,
                "term" : self.term,
                "success" : False
            }
        
        if self.state != FOLLOWER:
            self._transition_to_follower()
            # self.term = data[-1]['term']

        if self.prevLogIndex < first_log['lastLogIndex']:
            # follower is missing some entries
            print("in self.prevLogIndex < data['lastLogIndex']")
            return {
                "lastLogIndex" : self.prevLogIndex,
                "term" : self.term,
                "success" : False
            }
        
        #added these 2 cases
        if first_log['lastLogIndex']!=0 and self.local_log[self.prevLogIndex]["term"]!= last_log['lastLogTerm']:
            return {
                "lastLogIndex" : self.prevLogIndex,
                "term" : self.term ,
                "success" : False
            }
        
        if last_log['term'] > self.term:
            with self.term_loc:
                self.term = last_log['term']

        
        if self.prevLogIndex >= first_log['lastLogIndex']:
            print("in self.prevLogIndex > data['lastLogIndex']")
            # follower has more entries than leader
            index = -1
            if hOrA and self.prevLogIndex+1 > first_log['lastLogIndex']:
                index = min(self.prevLogIndex+1,first_log['lastLogIndex']+len(data))-1

                if self.local_log[index]["term"]!= data[index-first_log['lastLogIndex']]['term']:
                    self.deleteFromLog(first_log['lastLogIndex'])


            # commented because its redundant
                    
            # if first_log['prevLogIndex'] + len(data) > self.prevLogIndex+1:
            #     prevind = self.prevLogIndex
            #     for y in range(prevind-first_log['prevLogIndex'],len(data)):
            #         self.appendToLog(data[y])
                    # self.prevLogIndex = data[y]["prevLogIndex"]
            
            # return {
            #     "prevLogIndex" : self.prevLogIndex,
            #     "term" : self.term,
            #     "success" : True
            # }
                    
        # if appendEntries
        if hOrA: 
            if first_log['lastLogIndex'] + len(data) > self.prevLogIndex+1:
                    prevind = self.prevLogIndex
                    for y in range(prevind-first_log['lastLogIndex'],len(data)):
                        self.appendToLog(data[y])
            
        # committing until leader commit
        leader_commit = first_log["leaderCommit"]
        if leader_commit > self.commit_index and leader_commit<=self.prevLogIndex:
            self.commitEntries(leader_commit)

        print("sending true")
        return {
            "lastLogIndex" : self.prevLogIndex,
            "term" : self.term,
            "success" : True
        } 
    
    
    def appendToLog(self,data):
        with self.log_lock:
                self.local_log.append(data)
                self.prevLogIndex += 1

    # delete all logs after from_index
    def deleteFromLog(self, from_index):
        with self.log_lock:
            self.local_log = self.local_log[:from_index]
        self.prevLogIndex = from_index

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
        # if self.state == CANDIDATE:  safe to compare term rather than state
        if self.term == term and self.state == CANDIDATE:
            data = {
                "term":self.term,
                "candidateId":self.my_ip,
                "lastLogIndex" : self.prevLogIndex,
                # "lastLogTerm" : 0 if self.local_log[self.prevLogIndex[self.my_ip]-1]
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
                    self.current_leader = self.my_ip
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
        # self._initialize_next_index(self.prevLogIndex)
        return


    # ------------------------------------------------------------------------------
    # LEADER
    def _initialize_next_index(self,index):
        with self.next_index_lock:
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
            self.appendEntriesSend(term, i)
            time.sleep(HEARBEAT_INTERVAL/10)
            heart_beat_time = time.time()
        return
    
    # leader's function to receive INDIVIDUAL messages from client and append it to its log
    def receiveMessages(self, new_entry, path):
        if self.state!=LEADER:
            try:
                res = requests.post(f"http://{self.current_leader}/5000/{path}",json=new_entry,headers={"Content-Type": "application/json"},timeout=REQUEST_TIMEOUT)
            except Exception as e:
                print("error occured!!!")
            return res
        
        leader_data = {
                    "term": self.term,
                    "leaderId" : self.current_leader,
                    "lastLogIndex" : self.prevLogIndex,
                    # "prevLogTerm" : self.local_log[self.prevLogIndex]["term"], 
                    "entries" : new_entry,
                    "leaderCommit": self.commit_index
                }
        self.appendToLog(leader_data)
        self.append_votes = 1
    
        # for f_ip in self.node_list:
        #     if self.my_ip != f_ip:
        #         threading.Thread(target=self.appendEntriesSend,args=(self.term, f_ip,1)).start()
        # st_commit_time = time.time()
        # flag = True
        # while(self.append_votes < ceil((len(self.node_list))/2)):
        #     if time.time()-st_commit_time>COMMIT_TIMEOUT:
        #         flag = False
        #         break
        #     continue
        # if flag:
        #     self.commitEntries()

        
            # if new_entry['']=="Registerbroker":
            #     self.handleBrokerRegistration()
        #changed this because the the commit wouldnt happen and it will be checked until 
        # the append votes are greater
        #if only checks once , but a while loop would keep checkcing

    # index is the index until which to be committed
    def commitEntries(self, index):
        for i in range(self.commit_index, index):
            json_data = json.dumps(self.local_log[i])
            logging.info(json_data)
        self.commit_index = index
        

    # to send data from either appendEntries or heartbeats. 
    # here to ith follower
    # hOrA is 0 if heartbeat and 1 if ae
    def appendEntriesSend(self,term,i):
        if self.state!=LEADER:
            return
        # heartbeat if no entries to send, else appendEntries
        hOrA = 0 if self.next_index[i] == self.prevLogIndex + 1 else 1
        to_send = []
        if hOrA:
            # all entries in a list
            for j in self.local_log[self.next_index[i]:]:
                to_send.append(j)
        else: 
            data = {
                "term": term,
                "leaderId" : self.current_leader,
                "lastLogIndex" : self.next_index[i],
                # "prevLogTerm" : self.local_log[self.next_index[i]-1]["term"],  
                "entries" : None,
                # "msg":f"sending message to follower {i}"
                "leaderCommit":self.commit_index
            }
            to_send.append(data)
        try:
            res = requests.post(f"http://{i}:5000/messages",json=to_send,headers={"Content-Type": "application/json"},timeout=REQUEST_TIMEOUT)
            res = res.json()
            print("res=",res)
            print(f"Append Entry Send Passed success to {i} , {res}")
            # if not hOrA:
            #     return

            if res and res['success']:
                # if ith follower successfully put AppendEntries into its log
                print("incrementing vote from  votes = ",self.votes)
                print(f"{res} from success i.e append succesfully")
                if hOrA:
                    self.incrementAppend(data)
                    self.checkAppendVotes(res["lastLogIndex"])
                    # self.handleResponse(i,res,data)
                    with self.next_index_lock:
                        self.next_index[i] = self.prevLogIndex + len(to_send)     # or number of entries?
                    
            elif res and not res['success'] and res['term']==term:
                # case where follower log is lesser than leader log prevIndex
                print(f"follower log lesser than leader log {res}")
                if hOrA:
                    with self.next_index_lock:
                        if self.next_index[i] > 0:
                            self.next_index[i] = res["lastLogIndex"]
                            self.appendEntriesSend(self,term,i)

            elif res and not res['success'] and res['term']>term:
                print(f"leader transiting to follower {res}")
                self.append_votes = 0
                with self.term_loc:
                    self.term = res['term']
                self._transition_to_follower()
                
        except Exception as e:
            print(e)
            print(f"Append Entry Message failed sending to {i} failed")
    #since looping is called from another function , i think it wouldnt matter much  
                
        
    # def sendCommitMsg(self)
                

    def incrementAppend(self):
        # reusing this lock! :)
        with self.voting_lock:
            self.append_votes += 1
            print("responses for appendEntries = ",self.append_votes)

    def checkAppendVotes(self, index):
        if(self.append_votes > ceil((len(self.node_list))/2)):
            self.commitEntries(index)

                
    def _transition_to_follower(self):
        print("becoming follower!!")
        self.state = FOLLOWER
        print(f"{self.my_ip} - Transition to Follower")
        data={"followerIP":self.my_ip}
        requests.post("http://bd_kraft-observer-1:5000/transitionToFollower",json=data,headers={"Content-Type": "application/json"})
        self.init_timeout()
        return