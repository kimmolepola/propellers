import socket
import os
import time

dir_path = os.path.dirname(os.path.realpath(__file__))

with open (dir_path+"/files/file_server_host_and port_for_client.txt") as f:
    lines = f.readlines()
    server_host = lines[0][:-1]
    server_port = int(lines[1])

if server_host == "localhost":
    server_host = socket.gethostname()

path = dir_path+"/files/client_download_file/"

counter = 1
print("ready to receive data")

finished = False

while 1:
    if finished:
        break

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_host, server_port))
    data_list = []
 
    while 1:
        data = sock.recv(1024)
        if (len(data) == 0):
            break
        data_list.append(data)
    file = b''.join(data_list)
    if len(file)==1 and int.from_bytes(file, 'big') == 0:
        sock.close()
        finished = True
        print(str(counter-1)+ " file(s) received, connection closed")
        break
    print("file number "+str(counter)+" received")
    nameForFile = str(counter)+'.jpg'
    with open(path+nameForFile, "wb") as f:
        f.write(file)
    counter += 1
    time.sleep(5)

print("files saved to "+path)

time.sleep(15)