# BD_KRAFT

Run the command

`docker-compose up -d --scale controller=4 --scale broker=3`

At localhost:5000 there is an extra container called the observer which can be used to visualize the leader election and the logs with broker registration.



