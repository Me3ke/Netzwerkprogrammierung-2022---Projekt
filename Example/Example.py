"""
This is an example of how a server network
is behaving. This is done by starting three
server (from Server.py) in different processes
and shutting them down or restarting them seperatly
on different times. To get more information see
-> Projekt/Readme.txt
"""
import multiprocessing
import time
import threading
import sys

sys.path.insert(1, '../src')
import Server

"""
Note:
To improve the overview in the terminal
it is recommended to redirect the server
output into a 'server.log' file. If you
want to run this example go into src/Server.py
and remove the '#' in line 44. To get a glimpse
of what the server is doing you can open this file
and enable all loggin calls in Server.py.
--------
WARNING:
The behavior differs from try to try because
of different sheduling in the processes, but
the rules of the network are never broken.
To make this example safe against racing conditions
would go beyond the scope of this project.
"""

def logger(server, start_time, server_name):
    while (time.time() - start_time) <= 180:
        time.sleep(21)
        print("after " + str(time.time()-start_time) + " seconds on " + server_name + " ; Master = " + str(server.get_master()) + " ; Online = " + str(server.is_online()))
        


def server_one(start):
    server_name = "server 1"
    s = Server.Server("127.0.0.9")
    thread = threading.Thread(target=s.start, args = ())
    thread.start()
    log = threading.Thread(target=logger, args = (s, start, server_name))
    log.start()

    time.sleep(35)
    print("after " + str(time.time()-start) + " seconds on " + server_name + " ; removing myself(master) from network")
    s.shutdown()
    time.sleep(30)
    print("after " + str(time.time()-start) + " seconds on " + server_name + " ; reboot server ")
    thread = threading.Thread(target=s.restart, args = ())
    thread.start()
    
    time.sleep(80)
    print("after " + str(time.time()-start) + " seconds on " + server_name + " ; removing two server from network (first)")
    s.shutdown()
    thread.join()


def server_two(start):
    server_name = "server 2"
    s = Server.Server("127.0.0.8")
    thread = threading.Thread(target=s.start, args = ())
    thread.start()
    log = threading.Thread(target=logger, args = (s, start, server_name))
    log.start()


    time.sleep(150)
    print("after " + str(time.time()-start) + " seconds on " + server_name + " ; removing two server from network (second)")
    s.shutdown()
    thread.join()

def server_three(start):
    server_name = "server 3"
    s = Server.Server("127.0.0.7")
    thread = threading.Thread(target=s.start, args = ())
    thread.start()
    log = threading.Thread(target=logger, args = (s, start, server_name))
    log.start()

    time.sleep(80)
    print("after " + str(time.time()-start) + " seconds on " + server_name + " ; removing myself(non master) from network")
    s.shutdown()
    time.sleep(30)
    print("after " + str(time.time()-start) + " seconds on " + server_name + " ; reboot server ")
    thread = threading.Thread(target=s.restart, args = ())
    thread.start()

    time.sleep(35)
    print("after " + str(time.time()-start) + " seconds on " + server_name + " ; i will not be shut down manually")
    thread.join()


def main():
    start = time.time()

    print("starting example server network....")
    p1 = multiprocessing.Process(target=server_one, args=(start,))
    p1.start()
    time.sleep(3)
    p2 = multiprocessing.Process(target=server_two, args=(start,))
    p2.start()
    time.sleep(3)
    p3 = multiprocessing.Process(target=server_three, args=(start,))
    p3.start()

    p1.join()
    p2.join()
    p3.join()

    finish = time.time()
    print("Finished in " + str(round(finish-start, 2)) + " seconds")

if __name__ == "__main__":
    main()
