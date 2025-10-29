import socket

def judge_port_listen(port_num):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = s.connect_ex(('127.0.0.1', port_num))
    if result == 0:
        print("Port %d is open" % port_num)
    else :
       print("Port %d is not open" % port_num)
    s.close()
    return result