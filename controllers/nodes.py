import threading
import time
import random

MIN_TIMEOUT = 150
MAX_TIMEOUT = 300
FOLLOWER  = 0
CANDIDATE = 1
LEADER = 2

class Node:
    
    def __init__(self,my_ip,fellow_ip) -> None:
        
        self.my_ip = my_ip # the node's its own ip
        self.fellow_ip = fellow_ip
        self.term = 0       #Indicated the number of times a leader has been elected
        self.state = FOLLOWER
        self.timer = 0
        self.timeout_thread = None
        self.election_time = None
        self.votes = 0
        self.init_timeout()

    #resetting the timeout everytime
    def reset_timeout(self):
         return time.time()+random.randint(150,300)/1000
       
    
    def init_timeout(self):
        self.election_time = self.reset_timeout()

        if self.timeout_thread and self.timeout_thread.isAlive():
            return

        self.timeout_thread = threading.Thread(target=self.check_timeout,args=())
        self.timeout_thread.start()

    def check_timeout(self):

        while self.status!=LEADER:
            if time.time()-self.election_time>0:
                self.start_Election()
            else:
                time.sleep(self.election_time-time.time())/100
        
    def start_Election(self):
        self.term += 1
        self.votes = 0
        self.state = CANDIDATE
        self.init_timeout()
        self.ask_votes()



Node(100,[200,300,500])

        
    
    