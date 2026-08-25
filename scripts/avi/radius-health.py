#!/usr/bin/python3

import socket
import struct
import hmac
import hashlib
import os
import sys
import random

def send_radius_status_server(server_ip, server_port, shared_secret, timeout):
    # Prepare packet components
    code = 12  # Status-Server code
    packet_id = random.randint(0, 255)
    request_authenticator = os.urandom(16)
    
    # Message-Authenticator attribute (Type 80, Length 18) with a placeholder for calculation
    message_authenticator_attr_header = struct.pack('!BB', 80, 18)
    message_authenticator_attr_payload = b'\x00' * 16
    message_authenticator_attr = message_authenticator_attr_header + message_authenticator_attr_payload
    
    # Construct the base packet for HMAC-MD5 calculation
    header = struct.pack('!BBH', code, packet_id, 0)
    packet_without_length = header + request_authenticator + message_authenticator_attr
    
    # Update length in the header
    packet_length = len(packet_without_length)
    header = struct.pack('!BBH', code, packet_id, packet_length)
    
    packet_for_hmac = header + request_authenticator + message_authenticator_attr
    
    # Calculate the Message-Authenticator
    secret_bytes = shared_secret.encode('utf-8')
    hmac_md5 = hmac.new(secret_bytes, packet_for_hmac, hashlib.md5)
    final_message_authenticator = hmac_md5.digest()
    
    # Construct the final packet with the correct Message-Authenticator
    final_message_authenticator_attr = message_authenticator_attr_header + final_message_authenticator
    final_packet = header + request_authenticator + final_message_authenticator_attr
    
    # Send the packet
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(final_packet, (server_ip, server_port))
            
            # Receive the reply
            reply_packet, addr = sock.recvfrom(4096)
            
            # Process the reply
            process_reply(reply_packet, request_authenticator, shared_secret)

    except socket.timeout:
        sys.exit(1)
    except Exception as e:
        sys.exit(1)

def process_reply(reply_packet, request_authenticator, shared_secret):

    if len(reply_packet) < 20:
        return
        
    # Unpack the reply header
    reply_code, reply_id, reply_length = struct.unpack('!BBH', reply_packet[:4])
    reply_authenticator = reply_packet[4:20]
    reply_attributes = reply_packet[20:]
    
    # Check for expected reply codes (Access-Accept: 2 or Accounting-Response: 5)
    if reply_code == 2:
        reply_code_name = "Access-Accept"
        print("Success")
        sys.exit(0)

    elif reply_code == 5:
        reply_code_name = "Accounting-Response"
        print("Success")
        sys.exit(0)        

    else:
        sys.exit(1)

if __name__ == '__main__':
    # Configuration
    RADIUS_SERVER_IP = os.environ.get('IP')
    RADIUS_SERVER_PORT = int(os.environ.get('PORT'))
    RADIUS_SECRET = os.environ.get('SECRET')
    RADIUS_TIMEOUT = 3
    
    # Execute
    send_radius_status_server(RADIUS_SERVER_IP, RADIUS_SERVER_PORT, RADIUS_SECRET, RADIUS_TIMEOUT)
