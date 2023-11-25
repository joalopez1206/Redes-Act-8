import sys
import socket
import time
from utils import   parse_packet, check_routes_bgp, create_packet, get_address,\
                    Packet, fragment_IP_packet, reassemble_IP_packet, is_complete, get_table,\
                    create_BGP_message, table_to_text, get_vecinos_initial, asn_in_any_route, get_list_of_asn_routes, get_asn, unknown_asn, Entry, get_route
import pprint
pprint = pprint.PrettyPrinter()
if len(sys.argv) != 4:
    print("Usage: python3 router.py <ip> <port> <table>")
    exit(0)
## MESSAGE START BGP 127.0.0.1;8882;030;00000348;00000000;00000009;0;START_BGP
ip = sys.argv[1]
port = int(sys.argv[2])
router_number = port%10
iden = int(f"{router_number}000")
ADDRESS = (ip,port)
TABLE_FILE = sys.argv[3]

default = False
if "default" in TABLE_FILE: 
    default = True
    print(f"Router is default! @ port {port}")


router_sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
router_sock.bind(ADDRESS)

cache_msgs = {}
table = get_table(TABLE_FILE)
vecinos_lista = get_vecinos_initial(table)

def run_BGP():
    global iden, table
    
    print("Enviando STARTS a vecinos")
    for puerto in vecinos_lista:
        address = (ip, puerto)
        iden+=1
        p = Packet(ip, puerto, 50, iden, 0, 9, 0, b"START_BGP")
        router_sock.sendto(create_packet(p),address)
    
    print("Enviando mensajes bgp a los vecinos")
    for puerto in vecinos_lista:
        address = (ip, puerto)
        iden+=1
        mensaje = create_BGP_message(port, table).encode()
        p = Packet(ip, puerto, 50, iden, 0, len(mensaje), 0, mensaje)
        router_sock.sendto(create_packet(p),address)
    
    router_sock.settimeout(10.0)
    
    while True:
        changed=False
        try:
            msg, _ = router_sock.recvfrom(4024)
            print(f"Mensaje llego a {port}")
            if b'START_BGP' in msg:
                print("Es un start xd")
                continue

            p = parse_packet(msg)
            mensaje = p.msg.decode()
            asn = get_asn(mensaje)
            tabla_rutas_asn = get_list_of_asn_routes(mensaje)
            print("La tabla de rutas que llego es")
            print(tabla_rutas_asn)
            for ruta in tabla_rutas_asn:
                print(f"usando la ruta {ruta}")
                if port in ruta:
                    print("Ya esta nuestro asn (el port), descartado")
                    continue
                
                destiny_asn = ruta[0]

                if unknown_asn(destiny_asn, table):
                    print("La ruta tiene un asn de destino desconocido!")
                    nuevo_camino = ruta + [port]
                    e = Entry(ip, nuevo_camino, ip, asn, 1000)
                    table.append(e)
                    changed = True
                
                # if not unknown_asn(destiny_asn, table)
                else :
                    print("Ya conocemos esta ruta, comparamos y vemos si lo cambiamos o no")
                    nuevo_camino = ruta + [port]
                    i,entry_camino = get_route(destiny_asn, table)
                    if len(entry_camino.caminos) > len(nuevo_camino):
                        table[i].caminos=nuevo_camino
                        table[i].puerto_llegada=asn
                        changed=True
                
                if changed:
                    for puerto in vecinos_lista:
                        address = (ip, puerto)
                        iden+=1
                        mensaje = create_BGP_message(port, table)
                        p = Packet(ip, puerto, 50, iden, 0, 9, 0, mensaje.encode())
                        router_sock.sendto(create_packet(p),address)
                    changed = False
            
        except socket.timeout:
            return table_to_text(table)

if __name__ == "__main__":
    print(f"Starting router! {ip}@{port}")
    #print("Starting Table")
    #print(table)
    #print(table_to_text(table))
    while True:
        router_sock.settimeout(None)
        msg, addr = router_sock.recvfrom(1024)
        print(msg)
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
            #print(cache_msgs, bytes_or_none)
            if bytes_or_none != None:
                parsed = parse_packet(bytes_or_none)
                if is_complete(parsed):
                    if parsed.msg.decode() == "START_BGP":
                        nueva_tabla = run_BGP()
                        TABLE_FILE = f"ejemplo/ejemplo2/rutas_R{router_number}_mod.txt"
                        print("\nNueva tabla de ruta!")
                        print("-"*25)
                        print(nueva_tabla)
                        print("-"*25)
                        with open(TABLE_FILE, "w") as f:
                            f.write(nueva_tabla)
                    else:
                        print(parsed.msg.decode())
            continue
            
        *next_hop_address, next_hop_mtu = check_routes_bgp(TABLE_FILE, recv_address)
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
