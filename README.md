# BD_KRAFT

Run the command of this type

`docker-compose up -d --scale controller=4 --scale broker=3`

At localhost:5000 there is an extra container called the observer which can be used to visualize the leader election and the logs(NEW).

***NOTE - Its not yet complete. The the register message from the broker is sent to the 1st controller and not the leader. Also switching from the logs observer to the raft observer will no longer display the leader node because the leader does not continuosly send its timeout to the observer.***

