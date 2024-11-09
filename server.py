import socket
import ssl
import threading
import base64
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

load_dotenv()

def load_private_key(path):
    with open(path, "rb") as key_file:
        return serialization.load_pem_private_key(key_file.read(), password=None)

def create_ssl_context(cert_path, private_key_path):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=cert_path, keyfile=private_key_path)
    return context

def start_server(host, port, context):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    return server

def broadcast(message, clients):
    for client in clients:
        client.send(message)

def handle_client(client, server_private_key, clients, nicknames):
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
            broadcast(message.encode('ascii'), clients)
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast(f'{nickname} left the chat!'.encode('ascii'), clients)
            nicknames.remove(nickname)
            break

def accept_clients(server, context, server_private_key, clients, nicknames):
    while True:
        client, address = server.accept()
        ssl_client = context.wrap_socket(client, server_side=True)
        print(f"Connected with {str(address)}")

        ssl_client.send('USERNAME'.encode('ascii'))
        nickname = ssl_client.recv(1024).decode('ascii')
        nicknames.append(nickname)
        clients.append(ssl_client)

        print(f"Nickname of the client is {nickname}")
        broadcast(f"{nickname} joined the chat!".encode('ascii'), clients)
        ssl_client.send('Connected to the server!'.encode('ascii'))

        thread = threading.Thread(target=handle_client, args=(ssl_client, server_private_key, clients, nicknames))
        thread.start()

def main():
    private_key_path = os.getenv('PRIVATE_KEY_PATH')
    cert_path = os.getenv('CERT_PATH')

    server_private_key = load_private_key(private_key_path)
    context = create_ssl_context(cert_path, private_key_path)

    host = '0.0.0.0'
    port = 55545

    server = start_server(host, port, context)

    clients = []
    nicknames = []

    print("Server is listening...")
    accept_clients(server, context, server_private_key, clients, nicknames)

if __name__ == "__main__":
    main()