import socket
import time
import nmap
from scapy.all import Ether, ARP, srp
import json

#x1 = 0
#y1 = 55
#x2 = 97
#y2 = 256
#color = "red"

#final = [{"x1" : x1, "y1" : y1, "x2" : x2, "y2" : y2, "color" : color},
#         {"x1" : 0, "y1" : 25, "x2" : 36, "y2" : 99, "color" : "blue"},
#         {"x1" : 0, "y1" : 25, "x2" : 36, "y2" : 99, "color" : "blue"}]

class TcpClient:
    def __init__(self):
        self.server_addr = ('192.168.31.44',9955)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def get_mac_address(self, ip):
        # 创建一个ARP请求数据包
        arp = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(op=1, pdst=ip)

        # 发送ARP请求并接收响应数据包
        result, _ = srp(arp, timeout=2, verbose=False)

        # 从响应数据包中获取目标主机的MAC地址
        if result:
            return result[0][1][Ether].src
        else:
            return None

    def scan(self):
        try:
            nm = nmap.PortScanner()
            nm.scan(hosts='192.168.31.0/24', arguments='-sn')
            for host in nm.all_hosts():
                if nm[host].state() == 'up':
                    mac = self.get_mac_address(host)
                    print(f"Host {host} is up!")
                    print(f"MAC address: {mac}")
        except nmap.PortScannerError as e:
            print("Scan error: " + str(e))
        except Exception as e:
            print("Unexpected error: " + str(e))

    def attempt_connection(self, server_addr,retry_interval = 0.1):
        """尝试连接服务器，直到成功或手动中断"""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                print(f"Attempting to connect to {server_addr[0]} on port {server_addr[1]}...")
                self.client_socket.connect(server_addr)
                print(f"Connected to {server_addr[0]} on port {server_addr[1]}")
                return self.client_socket  # 连接成功，跳出循环
            except ConnectionRefusedError:
                print("Connection refused. Server might be offline or busy. Retrying...")
            except Exception as e:
                print(f"An error occurred: {e}. Retrying...")
            time.sleep(retry_interval)  # 等待一段时间后重试

    def tcp_client(self, data):
        try:
            json_final = json.dumps(data)
            self.client_socket.sendall(json_final.encode())
            response = self.client_socket.recv(1024)
            if not response:
                print("Server closed connection")
                return 0
            print("Received message: ", response.decode())
        except ConnectionAbortedError:
            print("Connection aborted by server")
            return -1
        except Exception as e:
            print(f"Error: {e}")
            return -1
            
            
#if __name__ == "__main__":
#    json_final = json.dumps(final)
    #scan()
#    tcp_client(json_final)
