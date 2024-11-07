import socket
import ssl
import threading
import base64
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

load_dotenv()

public_key_path = os.getenv('PUBLIC_KEY_PATH')
cert_path = os.getenv('CERT_PATH')

with open(public_key_path, "rb") as key_file:
    server_public_key = serialization.load_pem_public_key(key_file.read())

host = input("Enter the server IP address: ")
port = 55545

# Created an SSL context
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

# Wrapped the socket with SSL
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ssl_client = context.wrap_socket(client, server_hostname=host)
ssl_client.connect((host, port))

nickname = input("\n\tChoose your nickname: ")
print("\n")

def receive():
    while True:
        try:
            message = ssl_client.recv(1024).decode('ascii')
            if message == 'username':
                ssl_client.send(nickname.encode('ascii'))
            else:
                print(message)
        except:
            print("An error occurred!")
            ssl_client.close()
            break

def write():
    while True:
        message = f'{nickname}: {input("")}'
        encrypted_message = server_public_key.encrypt(
            message.encode('ascii'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        ssl_client.send(base64.b64encode(encrypted_message))

receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()