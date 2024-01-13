import threading
import time
import random, requests
from math import ceil

# TIMEOUT_TIME = 200 ,the reason for removing this is that 
# in case all the hearbeats are sent parallely and leader dies ,
# then every node would time out at the same time and all would become candidates in check timeout
MIN_TIMEOUT = 50
MAX_TIMEOUT = 80
FOLLOWER  = 0
CANDIDATE = 1
LEADER = 2
REQUEST_TIMEOUT = 50
HEARBEAT_INTERVAL = 20
HEARTBEAT_TIMOUT = 50

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
        self.current_leader = None
        self.heartbeat_thread = None
        self.voting_lock = threading.Lock()
        self.last_msg_lock = threading.Lock()
        self.election_lock = threading.Lock()
        self.next_index_lock = threading.Lock()
        self.leader_log_lock = threading.Lock()
        self.term_loc = threading.Lock()
        self.log_file = log_file
        self.next_index = {}  #adding next index , initializing it 0 as of now
        self._initialize_next_index()

        self.match_index = [0 for _ in range(len(self.node_list))] # same reason
        self.init_timeout()

    def _initialize_next_index(self):
        for ips in self.node_list:
            self.next_index[ips] = len(self.log_file)
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

    # ------------------------------------------------------------------------------------------------------
    # LEADER FUNCTIONS
    def appendEntriesSend(self,term,i, new_entries):
        if self.state==LEADER:
            data = {
                "term": term,
                "leaderId" : self.current_leader,
                "prevLogIndex" : self.next_index[i],
                # "prevLogTerm" : self.log_file[self.next_index[i]][-1],  # FIX THIS LATER
                "entries" : new_entries,
                "msg":"sending heartbeat"
            }
            try:
                res = requests.post(f"http://{i}:5000/heartbeat",json=data,headers={"Content-Type": "application/json"})
            except Exception as e:
                    print(f"Error {e}")
        return
    
    def appendToLog(self,record):
        if self.state!=LEADER:
            return {
                "current_leader":self.current_leader,
                "success":False
            }
        pass

    def send_heartbeat(self, term, i):
        heart_beat_time = time.time()
        while time.time()-heart_beat_time<=HEARTBEAT_TIMOUT and self.term == term and self.state == LEADER:
            self.appendEntriesSend(term, i,[])
            time.sleep(HEARBEAT_INTERVAL/10)
            heart_beat_time = time.time()
        return
    
    def startHearbeat(self,term):
        print("starting heatbeat!!!!")
        if self.term == term:
            for f_ips in self.node_list:
                if f_ips == self.my_ip:
                    continue
                threading.Thread(target=self.send_heartbeat,args=(self.term,f_ips)).start()
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


    def recv_heartbeat(self,data):
        
        if self.term < data['term']:
            with self.term_loc:
                self.term = data['term']
                self._transition_to_follower()
        self.current_leader = data['leaderId']
        self.init_timeout()
        return {
            "term":self.term,
            "success": True
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
            return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        else:
            self.voted_for['term'] = data['term']
            with self.term_loc:
                self.term = data['term']
            self.voted_for['candidateId'] = data['candidateId']
            return {
                "term":self.term,
                "voteGranted":True
            }
        return None

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
                self.next_index[ips] = len(self.log_file)
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
                "lastLogIndex" : self.next_index[self.my_ip]-1,
                "lastLogTerm" : self.log_file[self.next_index[self.my_ip]-1]
                # FIX LATER
            }
            
            for f_ip in self.node_list:
                if self.my_ip != f_ip:
                    threading.Thread(target=self.sending_vote_req,args=(f_ip,data)).start()
        return


# Node(1,[1,2,3])



        
    
    