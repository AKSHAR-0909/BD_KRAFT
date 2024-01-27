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

Storage={
    "RegisterBrokerRecords":{"records":[],"timestamp":time.time()},
    "TopicRecord":{"records":[],"timestamp":time.time()},
    "PartitionRecord":{"records":[],"timestamp":time.time()},
    "ProducerIdsRecord":{"records":[],"timestamp":time.time()},
    "BrokerRegistrationChangeBrokerRecord":{"records":[],"timestamp":time.time()}
}

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
        self.current_leader = None
        self.leader_commit_index = 0
        self.local_log = [] # set to null after commiting all the entries
        self.heartbeat_thread = None
        self.voting_lock = threading.Lock()
        self.last_msg_lock = threading.Lock()
        self.election_lock = threading.Lock()
        self.response_lock = threading.Lock()
        self.next_index_lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.term_loc = threading.Lock()
        self.log_file = log_file
        self.next_index = {}  #adding next index , initializing it 0 as of now
        self._initialize_next_index()
        # self.setup_logger()

        self.match_index = [0 for _ in range(len(self.node_list))] # same reason
        self.init_timeout()

    def _initialize_next_index(self):
        for ips in self.node_list:
            self.next_index[ips] = 0
    #resetting the timeout everytime
    def reset_timeout(self):
        with self.last_msg_lock:
            self.last_msg_time = time.time()    
        return
       
    #  Initilises the timeout and creates a timeout thread initially
    def init_timeout(self):
        self.reset_timeout()
        if not (self.timeout_thread and self.timeout_thread.is_alive()):
            self.timeout_thread = threading.Thread(target=self.check_timeout,args=())
            self.timeout_thread.start()    
        
    def setup_logger(self):
        logging.basicConfig(filename=self.log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


    # ------------------------------------------------------------------------------------------------------
    # LEADER FUNCTIONS
    
    #Thinking to keep a common route for both append entry and heartbeat
    #Reason : since the response is the same for both and conditions again have to be checked
    def appendEntriesSend(self,term,i, data):
        if self.state==LEADER:
            self.append_votes = 0
            try:
                res = requests.post(f"http://{i}:5000/messages",json=data,headers={"Content-Type": "application/json"},timeout=REQUEST_TIMEOUT)
                res = res.json()

                print(f"Append Entry Send Passed success to {i} , {res}")

                if res and res['success']:
                    print("incrementing vote from  votes = ",self.votes)
                    print(f"{res} from success i.e append succesfully")
                    if data!=[]:
                        self.incrementAppend(data)
                        self.handleResponse(i,res,data)

                elif res and not res['success'] and res['term']==term:
                    #case where follower log is lesser than leader log
                    print(f"follower log lesser than leader log {res}")
                    if data!=[]:
                        data['prevLogIndex'] = res['prevLogIndex']
                        self.appendEntriesSend(self,term,i,data)

                elif res and not res['success'] and res['term']>term:
                    print(f"leader transiting to follower {res}")
                    self.append_votes = 0
                    self.term = res['term']
                    self._transition_to_follower()
                    self.init_timeout()
                    
            except Exception as e:
                print(f"Append Entry Message failed sending to {i} failed")
        #since looping is called from another function , i think it wouldnt matter much                

            
    def handleResponse(self, follower_id, response,data):
        # handle appendEntry response given by follower i 
        with self.respone_lock:
            for y in range(self.next_index[follower_id]-data['previousLogIndex'],len(data['entries'])):
                send_data = data
                send_data['entries'] = data['entries'][y]
                self.appendToLog(self,send_data)
                    
        return

    def sendCommitMsg(self, data):
        pass


    def x(self,term, new_entries):
        for y in new_entries['entries']:
            send_data = data
            send_data['entries'] = data['entries'][y]
            self.appendToLog(send_data)
        for f_ip in self.node_list:
            data = {
                    "term": term,
                    "leaderId" : self.current_leader,
                    "prevLogIndex" : self.next_index[f_ip],
                    # "prevLogTerm" : self.log_file[self.next_index[i]][-1],  # FIX THIS LATER
                    "entries" : new_entries,
                    "msg":f"sending message to follower {f_ip}"
                }
            if self.my_ip != f_ip:
                threading.Thread(target=self.appendEntriesSend,args=(term, f_ip,data)).start()

        while(self.append_votes < ceil((len(self.node_list))/2)):
            continue
        self.sendCommitMsg(self.local_log)
        #changed this because the the commit wouldnt happen and it will be checked until 
        # the append votes are greater
        #if only checks once , but a while loop would keep checkcing

    def incrementAppend(self, data):
        # with self.voting_lock:
        # will put lock here later
        with self.voting_lock:
            self.append_votes += 1
            print("responses for append Entries = ",self.append_votes)
        # if self.state == LEADER:
            
    def handleBrokerRegistration(self,data):
        print(self.my_ip,self.current_leader)
        if(self.my_ip!=self.current_leader):
            print("***********************************************************")
            print(self.current_leader)
            requests.post(f"http://{self.current_leader}:5000/handleBroker/registerBrokerRecord",
                              json=data,headers={"Content-Type":"application/json"})
            return {"success":True}
        else:
            internalUUID=str(uuid.uuid4())
            brokerID=data['brokerId']
            newBrokerRecord={
                "type":"metadata",
                "name":"RegisterBrokerRecord",
                "fields":{
                    "internalUUID":internalUUID,
                    "brokerId":brokerID,
                    "brokerHost":data['brokerHost'],
                    "brokerPort":data['brokerPort'],
                    "securityProtocol":data["securityProtocol"],
                    "brokerStatus":data['brokerStatus'],
                    "epoch":0
                },
                "timestamp":time.time()
            }

            Storage["RegisterBrokerRecords"]["records"].append(newBrokerRecord)
            Storage["RegisterBrokerRecords"]["timestamp"]=time.time()
            print( Storage["RegisterBrokerRecords"]["records"])
            newBrokerRecord["currentLeader"]=self.current_leader
            newBrokerRecord["currentTerm"]=self.term
            requests.post("http://bd_kraft-observer-1:5000/logs/registerBrokerRecord",
                        json=newBrokerRecord,headers={"Content-Type":"application/json"})

            return {"success":True,"internalUUID":internalUUID}
            
    def appendToLog(self,data):
        pass
        # with self.log_lock:
        #     self.local_log.append(record)

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
    
    def startHearbeat(self,term):
        print("starting heatbeat!!!!")
        if self.term == term:
            for f_ips in self.node_list:
                if f_ips == self.my_ip:
                    continue
                threading.Thread(target=self.sendHeartbeat,args=(self.term,f_ips)).start()
        return

    # -----------------------------------------------------------------------------------------------------
    # FOLLOWER FUNCTIONS

    # It constantly checks whether the node has timed out or not
    # Implemented as thread so as to run it parallely
    def check_timeout(self):
        print(f"Node {self.my_ip} timeout started!!!")
        heartbeat_timeout = random.randint(MIN_TIMEOUT,MAX_TIMEOUT)/10
        while self.state!=LEADER and self.state!=CANDIDATE:
            if time.time()-self.last_msg_time>=heartbeat_timeout:
                self.start_election()
            else:
                data={"ip":self.my_ip,"counter":abs(heartbeat_timeout-(time.time()-self.last_msg_time)),"term":self.term}
                requests.post("http://bd_kraft-observer-1:5000/updateTimer",json=data,headers={"Content-Type": "application/json"})


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
        
        if self.prevLogIndex < data['prevLogIndex']:
            # follower is missing some entries
            print("in self.prevLogIndex < data['prevLogIndex']")
            return {
                "prevLogIndex" : self.prevLogIndex,
                "term" : self.term,
                "success" : False
            }
        self.init_timeout()
        if self.term < data['term']:
            
            with self.term_loc:
                self.term = data['term']
                if self.state != FOLLOWER:
                    self._transition_to_follower()
                    self.current_leader = data['leaderId']
            

        if self.prevLogIndex > data['prevLogIndex']:
            print("in self.prevLogIndex > data['prevLogIndex']")
            # follower has more entries than leader
            self.deleteFromLog(data['prevLogIndex'])
            
            return {
                "prevLogIndex" : self.prevLogIndex,
                "term" : self.term,
                "success" : True
            }
        # if appendEntries
        if data['entries'] != []:
            self.handleResponse(data)
        print("sending true")
        return {
            "prevLogIndex" : self.prevLogIndex,
            "term" : self.term,
            "success" : True
        }
    
    def vote_response_rpc(self,data):
        if self.term > data['term'] or self.state==LEADER: # if the follower term > candidate
                return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        elif  data['term']==self.term:
            return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        elif self.next_index[self.my_ip]-1 > data['lastLogIndex']:
            print(f"next index of ip : {self.my_ip} = {self.next_index[self.my_ip]}")
            return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        else:
            self._transition_to_follower()
            self.voted_for['term'] = data['term']
            with self.term_loc:
                self.term = data['term']
            self.voted_for['candidateId'] = data['candidateId']
            return {
                "term":self.term,
                "voteGranted":True
            }

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

    def _transition_to_follower(self):
        print("becoming follower!!")
        self.state = FOLLOWER
        print(f"{self.my_ip} - Transition to Follower")
        data={"followerIP":self.my_ip}
        requests.post("http://bd_kraft-observer-1:5000/transitionToFollower",json=data,headers={"Content-Type": "application/json"})
        return
    # CANDIDATE FUNCTION
    def _transition_to_leader(self):
        print(f"{self.my_ip} Transition to LEADER")
        data={"leaderIP":self.my_ip}
        requests.post("http://bd_kraft-observer-1:5000/transitionToLeader",json=data,headers={"Content-Type": "application/json"})
        # time.sleep(2)
        self.state = LEADER
        self.current_leader = self.my_ip
        data={"ip":self.my_ip,"counter":0,"term":self.term}
        requests.post("http://bd_kraft-observer-1:5000/updateTimer",json=data,headers={"Content-Type": "application/json"})
        self.startHearbeat(self.term)

        with self.next_index_lock:
            for ips in self.node_list:
                self.next_index[ips] = 0
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

    def increment_vote(self):
        with self.voting_lock:
            self.votes += 1
            print("votes = ",self.votes)
            if self.state == CANDIDATE:
                if(self.votes>=ceil((len(self.node_list))/2)):
                    print()
                    self._transition_to_leader()

                    # threading.Thread(self.start_heartbeat()).start()
        return

    # This function starts the election as soon as a node has timed out
    # from the init timeout function
    def start_election(self):
        with self.election_lock:
            print(f"in election : {self.my_ip} is candidate now!!!")
            self._transition_to_candidate() # to maintian modularity
            self.votes = 0
            self.increment_vote()
            self.voted_for['term'] = self.term
            self.voted_for['candidateID'] = self.my_ip
            self.vote_request_rpc(self.term) #safe to pass

    #call increment vote from this function
    def vote_request_rpc(self,term):
        # TODO: vote timeout
        # self.state = FOLLOWER
        # self.init_timeout()
        # if self.state == CANDIDATE:  safe to compare term rather than state
        if self.term == term and self.state == CANDIDATE:
            data = {
                "term":self.term,
                "candidateId":self.my_ip,
                "lastLogIndex" : self.next_index[self.my_ip]-1
                # "lastLogTerm" : self.log_file[self.next_index[self.my_ip]-1]
                # FIX LATER
            }
            
            for f_ip in self.node_list:
                if self.my_ip != f_ip:
                    threading.Thread(target=self.sending_vote_req,args=(f_ip,data)).start()
        return
    

    # ----------------------------------------------------------------
    # LOG FUNCTIONS
    def parse_log_line(self, line):
        # Define a regular expression to match log entries
        log_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (.*)')

        # Use the regular expression to match log entries
        match = log_pattern.match(line)
        if match:
            timestamp_str, log_level, message_str = match.groups()

            # Convert timestamp string to a datetime object
            # timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

            try:
                # Parse the message as JSON
                message = json.loads(message_str)
            except json.JSONDecodeError:
                # Handle the case where the message is not valid JSON
                message = {'raw_message': message_str}

            return {'timestamp': timestamp_str, 'message': message}
        else:
            print("None")
            return None
    
    def get_last_line(self, file_path):
        with open(file_path, 'rb') as file:
            file.seek(-2, 2)  # Move the cursor to the second-to-last byte of the file
            while file.read(1) != b'\n':
                file.seek(-2, 1)  # Move the cursor one byte back
            last_line = file.readline().decode('utf-8')
        return last_line

    # should delete all logs until prevLogIndex
    # change self.prevLogIndex
    def deleteFromLog(self, prevLogIndex):
        pass

# Node(1,[1,2,3])



        
    
    