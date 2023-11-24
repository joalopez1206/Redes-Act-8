from __future__ import annotations
from dataclasses import dataclass
from itertools import islice
DEFAULT_PORT = 7000
HEADER_SIZE = 8+1+8+8+3+4+9+7
@dataclass
class Packet:
    ip: str
    port: int
    ttl: int
    iden: int
    offset:int
    size: int
    flag: int
    msg: bytes

@dataclass
class Entry:
    ip_net: str
    caminos: list[int]
    ip_llegada: str
    puerto_llegada: int
    mtu: int

#Lo que guarda el cache es
# key: la
cache = dict()

def is_complete(packet: Packet):
    return packet.offset == 0 and packet.flag==0

def batched(iterable, n):
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError('n must be at least one')
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch

def pad_zeros(x: int, n: int):
    return str(x).zfill(n)

def get_address(packet: Packet) -> tuple[str,int]:
    return (packet.ip, packet.port)

def parse_packet(msg: bytes):
    ip, port, ttl, iden, offset, size, flag, msg= msg.split(b";")
    ip = ip.decode()
    ttl = int(ttl)
    port = int(port)
    iden = int(iden)
    offset = int(offset)
    size = int(size)
    flag = int(flag)
    return Packet(ip, port, ttl, iden, offset, size, flag, msg)


def create_packet(packet: Packet):
    l = [packet.ip.encode(), str(packet.port).encode(),
        pad_zeros(packet.ttl, 3).encode(), pad_zeros(packet.iden, 8).encode(),
        pad_zeros(packet.offset, 8).encode(), pad_zeros(packet.size, 8).encode(),
        str(packet.flag).encode(), packet.msg
        ]
    return b";".join(l)


def check_routes(routes_file_name: str, dest_addr: tuple[str,int], is_default_router=False) -> tuple[str,int,int] | None :
    global cache
    dest_ip, dest_port = dest_addr
    #si la direccion de cache no esta en el destino
    if cache.get(dest_addr) == None:
        #la inicializamos; donde la llave es la direccion de destino
        cache[dest_addr] = 0
    with open(routes_file_name, "r") as f:
        lines = f.readlines()
        
        #funcion para filtar las lineas
        def filter_lines(line):
            network_ip, puerto_inicial, puerto_final, ip_para_llegar, puerto_para_llegar, mtu = line.split(" ")
            
            puerto_inicial = int(puerto_inicial)
            puerto_final = int(puerto_final)
            return dest_port in range(puerto_inicial, puerto_final+1) and \
                puerto_final != DEFAULT_PORT
        
        #obtenemos los posibles puertos destinos
        lines_filtered = list(filter(filter_lines, lines))

        # Si es posible llegar a ellos
        if len(lines_filtered) != 0:
            #print(cache)

            #vemos que para llegar, tomo la llave, obtengo la linea donde estoy actualmente y obtengo la ip 
            # y el puerto para llegar
            _,_,_, ip_para_llegar, puerto_para_llegar, mtu = lines_filtered[cache[dest_addr]%len(lines_filtered)].split(" ")

            # le sumo 1 al cache
            cache[dest_addr] +=1

            #retorno la direccion
            return ip_para_llegar, int(puerto_para_llegar), int(mtu)
        
        
        
        # si no, soy el default y no encontre nada y por lo tanto tiro none
        return None
 
def fragment_IP_packet(IP_packet: bytes, MTU: int) -> list[bytes]:
    l = len(IP_packet)

    if l <= MTU:
        return [IP_packet]
    else:
        size = MTU-HEADER_SIZE
        parsed_packet = parse_packet(IP_packet)
        new_msg_left = parsed_packet.msg[0:size]
        new_msg_right = parsed_packet.msg[size:]
        new_size_right = len(new_msg_right)
        p_left = Packet(parsed_packet.ip, parsed_packet.port, parsed_packet.ttl, parsed_packet.iden,
                        parsed_packet.offset, size, 1, new_msg_left)
        rest = Packet(parsed_packet.ip, parsed_packet.port, parsed_packet.ttl, parsed_packet.iden,
                        parsed_packet.offset+size, new_size_right, parsed_packet.flag, new_msg_right)
        return [create_packet(p_left)] + fragment_IP_packet(create_packet(rest), MTU)

def reassemble_IP_packet(fragment_list: list[bytes]) -> bytes:
    if len(fragment_list) == 1:
        fragment = parse_packet(fragment_list[0])
        if fragment.flag == 1:
            return fragment_list[0]
        else: return None
    fragment_parsed_list = [parse_packet(fragment) for fragment in fragment_list]
    fragment_parsed_list = sorted(fragment_parsed_list, key=lambda x: x.offset)
    for i in range(len(fragment_parsed_list)-1):
        if fragment_parsed_list[i].offset+fragment_parsed_list[i].size != fragment_parsed_list[i+1].offset:
            return None
    fragment_msgs = [fragment.msg for fragment in fragment_parsed_list]
    msg = b''.join(fragment_msgs)
    size = len(msg)
    fragment = fragment_parsed_list[0]
    last_fragment = fragment_parsed_list[-1]
    return Packet(fragment.ip, fragment.port, 
                                fragment.ttl, fragment.iden, fragment.offset,
                                size, last_fragment.flag, msg)


def create_BGP_message(asn: int, lista: list[Entry]):
    prelude = f"BGP_ROUTES\n{asn}\n"
    middle = "\n".join([" ".join([str(x) for x in entry.caminos]) for entry in lista])
    epilogue = "\nEND_BGP_ROUTES"
    return prelude + middle + epilogue

def get_table(table_file: str):
    table = []
    with open(table_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            ip, *camino, ip_llegada, puerto_llegada, mtu =line.split(" ")
            camino = [int(c) for c in camino]
            puerto_llegada = int(puerto_llegada)
            mtu = int(mtu)
            camino.reverse()
            table.append(Entry(ip,camino,ip_llegada, puerto_llegada, mtu))
        return table
            