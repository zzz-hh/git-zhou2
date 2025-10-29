import os
import time
from . import config
from . import port_listen

def pre_start_node():
    '''开启一个命令行窗口，运行启动节点
    :time.sleep() : 节点首次启动需要时间较长，之后可以修改。
    '''
    if port_listen.judge_port_listen(4001) != 0 :
        path = config.simple_bootstrap_node_path
        os.chdir(path)
        os.system("sudo nohup go run main.go >> bootstrap.log 2>&1 &")
        time.sleep(60)
    else :
        print("Start_node has been started")


def pre_node():
    '''开启三个命令行窗口，运行节点'''
    path = config.fediux_path
    os.chdir(path)
    if port_listen.judge_port_listen(50050) == 0 and  port_listen.judge_port_listen(50051) == 0 and port_listen.judge_port_listen(50052) == 0 :
        print("All nodes have been started")
    else :
        if port_listen.judge_port_listen(50050) != 0 :
            os.system("sudo nohup  ./bazel-bin/node --node_id=node0 --service_port=50050 --config=./config/node0.yaml >> node0.log 2>&1 &")
        if port_listen.judge_port_listen(50051) != 0 :
            os.system("sudo nohup  ./bazel-bin/node --node_id=node1 --service_port=50051 --config=./config/node1.yaml >> node1.log 2>&1 &")
        if port_listen.judge_port_listen(50052) != 0 :
            os.system("sudo nohup  ./bazel-bin/node --node_id=node2 --service_port=50052 --config=./config/node2.yaml >> node2.log 2>&1 &")
        time.sleep(30)

