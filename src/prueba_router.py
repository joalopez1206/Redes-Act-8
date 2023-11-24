import sys
import socket
from utils import create_packet, Packet
FILE = "test.txt"

if len(sys.argv) != 4:
    print("Usage: python3 prueba_router.py <header> <init_ip> <init_port>")
    exit(0)

_, header, init_ip, init_port = sys.argv

address = init_ip, int(init_port)

with open(FILE, "r") as f:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for line in f.readlines():
        # Extraemos la ip,port y ttl del header dado
        ip,port,ttl = header.split(";")
        #creamos el packete y lo hacemos mensaje
        pack = Packet(ip,int(port), int(ttl),line.encode())
        msg = create_packet(pack)
        # Enviamos el mensaje
        sock.sendto(msg, address)

