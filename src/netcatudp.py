import argparse
import socket
parser = argparse.ArgumentParser()
parser.add_argument("ip", help='ip a conectar')
parser.add_argument("puerto", help='puerto a conectar')
args = parser.parse_args()

print(f"conectando socket a -> {args.ip}:{args.puerto}")

address= args.ip, int(args.puerto)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    s = input("Tu entrada: ")
    sock.sendto(s.encode(), address)