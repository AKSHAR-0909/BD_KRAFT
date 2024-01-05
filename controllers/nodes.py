import threading
import time
import random, requests
from math import ceil

# TIMEOUT_TIME = 200 ,the reason for removing this is that 
# in case all the hearbeats are sent parallely and leader dies ,
# then every node would time out at the same time and all would become candidates in check timeout
MIN_TIMEOUT = 150
MAX_TIMEOUT = 300
FOLLOWER  = 0
CANDIDATE = 1
LEADER = 2
REQUEST_TIMEOUT = 50

class Node:
    
    def __init__(self,my_ip,node_list,log_file) -> None:
        
        self.my_ip = my_ip # the node's its own ip
        self.node_list = node_list
        self.term = 0       #Indicated the number of times a leader has been elected
        self.state = FOLLOWER
        self.timeout_thread = None
        self.election_time = None
        self.voted_for = {"term":None , "candidateId":None}
        self.votes = 0
        self.current_leader = None
        self.heartbeat_thread = None
        self.voting_lock = threading.Lock()
        self.election_lock = threading.Lock()
        self.leader_log_lock = threading.Lock()
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
        # self.election_time =  time.time()+random.randint(MIN_TIMEOUT,MAX_TIMEOUT)/1000
        # assuming last message was sent some random time ago
        self.last_msg_time = time.time() - random.randint(MIN_TIMEOUT,MAX_TIMEOUT)/1000    
        return
       
    #  Initilises the timeout and creates a timeout thread initially
    def init_timeout(self):
        self.reset_timeout()
        # if self.state==FOLLOWER: removing this because the leader would also have a thread and it should reset when 
        # it receives a 
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return 
        
        # if not (self.timeout_thread and self.timeout_thread.is_alive()):
        self.timeout_thread = threading.Thread(target=self.check_timeout,args=())
        self.timeout_thread.start()

            
        # self.heartbeat_thread = threading.Thread(target=self.receive_heartbeat, args=())
        # self.heartbeat_thread.start()


    # making this uniform to receive both heartbeats and vote requests



    # It constantly checks whether the node has timed out or not
    # Implemented as thread so as to run it parallely
    def check_timeout(self):
        print(f"Node {self.my_ip} timeout started!!!")
        while self.state!=LEADER:
            if time.time()-self.last_msg_time>=0:
                self.start_election()
            else:
                time.sleep((time.time()-self.last_msg_time)/1000)


            
    # This function starts the election as soon as a node has timed out
    # from the init timeout function
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
        # self.state = FOLLOWER
        # self.init_timeout()
        # if self.state == CANDIDATE:  safe to compare term rather than state
        if self.term == term and self.state == CANDIDATE:
            data = {
                "term":self.term,
                "candidateId":self.my_ip,
                "lastLogIndex" : self.next_index[self.my_ip]-1,
                "lastLogTerm" : self.log_file[self.next_index[self.my_ip]-1]
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
                res = requests.post(f"http://bd_kraft-controller-{i}:5000/vote_Req",json=data,headers={"Content-Type": "application/json"},timeout = REQUEST_TIMEOUT)
                if res['VoteGranted']:
                    self.increment_vote()
                    break
            except Exception as e:
                print(f"Vote request to {i} by candidate {self.my_ip} failed!!!")
                turn += 1

        return

    def increment_vote(self):
        with self.voting_lock:
            self.votes += 1
            if self.state == CANDIDATE:
                if(self.votes>=ceil((len(self.node_list))/2)):
                    self._transition_to_leader()

                    # threading.Thread(self.start_heartbeat()).start()
        return
     
    def vote_response_rpc(self,data):
        if self.term > data['term']: # if the follower term > candidate
                return {
                    "term" : self.term,
                    "voteGranted" : False
                }
        elif  self.voted_for['term']==self.term:
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
            self.voted_for['candidateId'] = data['candidateId']
            return {
                "term":self.term,
                "voteGranted":True
            }
        
    def startHearbeat(self):
            
        pass
    

    def _transition_to_candidate(self):
        print(f"{self.my_ip} - Transition to CANDIDATE")
        self.state = CANDIDATE
        self.term += 1

    def _transition_to_leader(self):
        print(f"{self.my_ip} Transition to LEADER")
        self.state = LEADER
        self.current_leader = self.my_ip

        with self.next_index_lock:
            for ips in self.node_list:
                self.next_index[ips] = len(self.log_file)
        

        


# Node(1,[1,2,3])



        
    
    