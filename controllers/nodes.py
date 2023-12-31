import threading
import time
import random, requests

HEARTBEAT_TIME = 140
MIN_TIMEOUT = 150
MAX_TIMEOUT = 300
FOLLOWER  = 0
CANDIDATE = 1
LEADER = 2

class Node:
    
    def __init__(self,my_ip,fellow_ips) -> None:
        
        self.my_ip = my_ip # the node's its own ip
        self.fellow_ips = fellow_ips #con
        self.term = 0       #Indicated the number of times a leader has been elected
        self.state = FOLLOWER
        self.timeout_thread = None
        self.election_time = None
        self.votes = 0
        self.current_leader = None
        self.heartbeat_time = None
        self.init_timeout()

    #resetting the timeout everytime
    def reset_timeout(self):
        self.election_time =  time.time()+random.randint(MIN_TIMEOUT,MAX_TIMEOUT)/1000
        # assuming last heartbeat was sent some random time ago
        self.heartbeat_time = time.time() - random.randint(MIN_TIMEOUT,MAX_TIMEOUT)/1000    
        return
       
    #  Initilises the timeout and creates a timeout thread initially
    def init_timeout(self):
        self.reset_timeout()
        if not (self.timeout_thread and self.timeout_thread.is_alive()):
            self.timeout_thread = threading.Thread(target=self.check_timeout,args=())
            self.timeout_thread.start()

        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return 
        
        if self.state==FOLLOWER:
            self.heartbeat_thread = threading.Thread(target=self.receive_heartbeat, args=())
            self.heartbeat_thread.start()


    def receive_heartbeat(self):
        while self.state == FOLLOWER:
            # checking heartbeat time by follower
            if time.time()-self.heartbeat_time>HEARTBEAT_TIME:
                self.start_election()

            else:
                time.sleep(self.election_time-time.time())
            # RECEIVE HEARTBEAT SOMEHOW AND ASSIGN THAT TO DATA HERE
            data = {"leader_ip": self.fellow_ips[1], "timestamp":time.time()}   # test data
            self.heartbeat_time = data['timestamp']
            time.sleep(HEARTBEAT_TIME)



    # It constantly checks whether the node has timed out or not
    # Implemented as thread so as to run it parallely
    def check_timeout(self):
        while self.state==FOLLOWER:
            if time.time()-self.election_time>0:
                self.start_election()
        

            else:
                time.sleep(self.election_time-time.time())

            
    # This function starts the election as soon as a node has timed out
    # from the init timeout function
    def start_election(self):
        self.term += 1
        self.votes = 1
        self.state = CANDIDATE
        print("in election")
        # print(self.timeout_thread.is_alive())
        self.init_timeout()
        self.ask_votes()

    #call increment vote from this function
    def ask_votes(self):
        pass

    def increment_vote(self):
        self.votes += 1
        if self.state == CANDIDATE:
            if(self.votes>=(len(self.fellow_ips)+1)//2):
                self.state = LEADER
                self.current_leader = self.my_ip
                print(f"Leader Elected: {self.my_ip}")
                self.start_heartbeat()
        return
     
    # send heartbeat to followers
    def start_heartbeat(self):
        while self.state == LEADER:
            # sending heartbeat from leader in the form of leader_ip, timestamp
            data={"leader_ip":self.my_ip, "timestamp":time.time()}
            for f_ip in self.fellow_ips:
                print("sent",data,"to","bd_kraft-follower:")
                requests.post(f"FOLLOWER_IP/{f_ip}",json=data,headers={"Content-Type": "application/json"})
            print(f"Heartbeat sent by Leader {self.my_ip}")
            time.sleep(HEARTBEAT_TIME)
        
    
         

Node(100,[200,300,500])

        
    
    