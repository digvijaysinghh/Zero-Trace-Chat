import socket
import ssl
import threading
import base64
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from colorama import Fore, Style, init

# Initialize colorama
init()

# Load environment variables from .env file
load_dotenv()

# Get paths from .env
private_key_path = os.getenv('PRIVATE_KEY_PATH')
cert_path = os.getenv('CERT_PATH')

with open(private_key_path, "rb") as key_file:
    server_private_key = serialization.load_pem_private_key(key_file.read(), password=None)

host = '0.0.0.0'
port = 55545

# Created an SSL context
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile=cert_path, keyfile=private_key_path)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

clients = []
nicknames = []

def broadcast(message):
    for client in clients:
        client.send(message)

def handle(client):
    while True:
        try:
            encrypted_message = client.recv(1024)
            message = server_private_key.decrypt(
                base64.b64decode(encrypted_message),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            ).decode('ascii')
            broadcast(message.encode('ascii'))
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast(f'{Fore.BLUE}{nickname}{Style.RESET_ALL} left the chat!'.encode('ascii'))
            nicknames.remove(nickname)
            break


def receive():
    while True:
        client, address = server.accept()
        ssl_client = context.wrap_socket(client, server_side=True)
        print("-" * 50)
        print(f"Connected with {str(address)}")

        ssl_client.send('NICK'.encode('ascii'))
        nickname = ssl_client.recv(1024).decode('ascii')
        nicknames.append(nickname)
        clients.append(ssl_client)

        print(f"Nickname of the client is {Fore.BLUE}{nickname}{Style.RESET_ALL}")
        broadcast(f"{Fore.GREEN}{nickname}{Style.RESET_ALL} joined the chat :)".encode('ascii'))
        ssl_client.send(f'Connected to the server! \n'.encode('ascii'))
        print("-" * 50 + "\n")

        thread = threading.Thread(target=handle, args=(ssl_client,))
        thread.start()

print(Fore.BLUE + "\n" + " " *5 +"Server is listening..." + "\n" + Style.RESET_ALL, end="")
print(Fore.GREEN + "\n"+"Users in the Chat Room" + "\n" + Style.RESET_ALL)

receive()