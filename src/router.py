import sys
import socket
from utils import parse_packet, check_routes, create_packet, get_address, Packet, fragment_IP_packet, reassemble_IP_packet, is_complete, get_table, create_BGP_message
import pprint
pprint = pprint.PrettyPrinter()
if len(sys.argv) != 4:
    print("Usage: python3 router.py <ip> <port> <table>")
    exit(0)

ip = sys.argv[1]
port = int(sys.argv[2])

ADDRESS = (ip,port)
TABLE_FILE = sys.argv[3]

default = False
if "default" in TABLE_FILE: 
    default = True
    print(f"Router is default! @ port {port}")


router_sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
router_sock.bind(ADDRESS)

cache_msgs = {}


if __name__ == "__main__":
    print(f"Starting router! {ip}@{port}")
    print("Starting Table")
    table = get_table(TABLE_FILE)
    pprint.pprint(get_table(TABLE_FILE))
    print(create_BGP_message(port, table))
    exit(0)
    while True:
        msg, addr = router_sock.recvfrom(1024)
        # para quitar el \n
        msg = msg.strip(b"\n")
        recv_packet = parse_packet(msg)
        recv_address = get_address(recv_packet)
        if recv_packet.ttl<=0:
            print(f"Se recibio un packete con ttl 0 {recv_packet}")
            continue

        if recv_address == ADDRESS:
            if cache_msgs.get(recv_packet.iden) == None:
                cache_msgs[recv_packet.iden] = []
            
            cache_msgs[recv_packet.iden] += [msg]
            bytes_or_none = reassemble_IP_packet(cache_msgs[recv_packet.iden])
            #pprint.pprint(cache_msgs)
            if bytes_or_none != None:
                parsed = parse_packet(bytes_or_none)
                if is_complete(parsed):
                    print(parsed.msg)
            continue
            
        *next_hop_address, next_hop_mtu = check_routes(TABLE_FILE, recv_address, is_default_router=default)
        next_hop_address = tuple(next_hop_address)

        if next_hop_address is None:
            print(f"No hay rutas hacia {recv_packet.ip} para paquete {recv_packet.port}")
            continue

        for fragment in fragment_IP_packet(msg, next_hop_mtu):
            parsed_msg = parse_packet(fragment)
            parsed_msg.ttl -= 1
            print()
            print("-"*30)    
            print(f"redirigiendo paquete {msg} con destino final {recv_address} desde {ADDRESS} hacia {next_hop_address}")
            print("-"*30) 
            print()
            msg = create_packet(parsed_msg)
            router_sock.sendto(msg ,next_hop_address)
