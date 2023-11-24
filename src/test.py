from utils import parse_packet, create_packet, fragment_IP_packet, reassemble_IP_packet
s = "127.0.0.1;8885;010;00000347;00000000;00000012;1;holaholahola".encode()

print(parse_packet(s))
print(s == create_packet(parse_packet(s)))

#for fragment in fragment_IP_packet(s, 51):
#    parsed_msg = parse_packet(fragment)
#    parsed_msg.ttl -= 1
#    msg = create_packet(parsed_msg)
#    print(msg)

fragment_list = fragment_IP_packet(s, 51)
IP_packet_v2 = reassemble_IP_packet(fragment_list)
print(IP_packet_v2)
print("IP_packet_v1 = IP_packet_v2 ? {}".format(s == IP_packet_v2))