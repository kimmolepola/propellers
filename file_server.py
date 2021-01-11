import socket
import os
import glob
import time

dir_path = os.path.dirname(os.path.realpath(__file__))

with open (dir_path+"/files/file_server_port_for_server.txt") as f:
    server_port = int(f.read())

print("loading files")
total_size = 0
try:
    file_list = [None for i in glob.glob(dir_path + '/files/server_upload_file/*.JPG')]
    for fullfilename in glob.glob(dir_path + '/files/server_upload_file/*.JPG'):
    
        base = os.path.basename(fullfilename)
        filename = os.path.splitext(base)[0]
        
        with open(dir_path + "/files/server_upload_file/1.jpg", "rb") as file:
            readfile = file.read()
            b = bytearray(readfile)
            file_list[int(filename) - 1] = b

            size = len(b)
            total_size += size
            
            print("Filename: " + filename + ", size: " + str(size) + " bytes")
        
except Exception:
    print("filenames have to be consecutive numbers starting from one")
    time.sleep(5)
    quit()

print("total size: " + str(total_size) + " bytes")

bytearray_list_list = []
slice_size = 1400
counter = 1
for f in file_list:
    print("slicing file number " + str(counter))
    counter += 1
    bytearray_list = []
    index = 0
    while 1:
        if (index + slice_size > len(b)):
            bytearray_list.append(b[index:])
            #print("slicing, size " + str(len(bytearray_list[-1])))
            break
        #print("slicing, size " + str(slice_size))
        bytearray_list.append(b[index:index + slice_size])
        index = index + slice_size
    bytearray_list_list.append(bytearray_list)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((socket.gethostname(), server_port))
sock.listen(5)

empty_byte = int(0).to_bytes(1, 'big')

while 1:
    print("ready to transfer files")
    counter = 1
    for bytearray_list in bytearray_list_list:
        print("waiting for client")
        clientsocket, addr = sock.accept()
        print("connection established, transferring file number " + str(counter))
        counter += 1
        for bytearr in bytearray_list:
            clientsocket.send(bytearr)
        clientsocket.close()
        print("finished, connection closed")
    clientsocket, addr = sock.accept()
    clientsocket.send(empty_byte)
    clientsocket.close()
    print("transferring of " + str(counter-1) + " file(s) completed")
