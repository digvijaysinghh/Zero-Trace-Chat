import socket
import ssl
import threading
import base64
import os
import struct
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import padding
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

# Create an SSL context
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile=cert_path, keyfile=private_key_path)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

clients = []
nicknames = []

def broadcast(message: bytes):
    """Send a raw byte message to all connected clients."""
    for client in clients:
        client.send(message)

def handle(client: ssl.SSLSocket):
    """Handle incoming data from a single client."""
    while True:
        try:
            # Read incoming data
            data = client.recv(4096)
            if not data:
                break
            # Kill-switch command from a client
            if data.strip() == b"KILL":
                # Notify all clients of shutdown
                broadcast(b"KILLED\n")
                # Exit immediately
                os._exit(0)

            # File transfer?
            if data.startswith(b"FILE:"):
                # Header format: FILE:<filename>:<filesize>
                parts = data.decode('utf-8').split(':', 2)
                filename = parts[1]
                filesize = int(parts[2])

                # Broadcast header to all clients
                for c in clients:
                    c.sendall(data)

                # Relay the file bytes
                remaining = filesize
                while remaining > 0:
                    chunk = client.recv(min(4096, remaining))
                    if not chunk:
                        break
                    for c in clients:
                        c.sendall(chunk)
                    remaining -= len(chunk)

                continue

            # Otherwise, this is an encrypted chat message
            encrypted_message = data
            # Decrypt with the server's private key
            message = server_private_key.decrypt(
                base64.b64decode(encrypted_message),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            ).decode('ascii')
            # Broadcast plaintext message to all clients
            broadcast(message.encode('ascii'))

        except Exception:
            # Client disconnected or error – clean up
            idx = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames.pop(idx)
            broadcast(f'{Fore.BLUE}{nickname}{Style.RESET_ALL} left the chat!'.encode('ascii'))
            break

def receive():
    """Main server loop: accept new connections and start handler threads."""
    print(Fore.BLUE + "\n     Server is listening...\n" + Style.RESET_ALL, end="")
    print(Fore.GREEN + "\nUsers in the Chat Room\n" + Style.RESET_ALL)

    while True:
        client_sock, addr = server.accept()
        ssl_client = context.wrap_socket(client_sock, server_side=True)
        print("-" * 50)
        print(f"Connected with {addr}")

        # Perform nickname handshake
        ssl_client.send(b'NICK')
        nickname = ssl_client.recv(1024).decode('ascii')
        nicknames.append(nickname)
        clients.append(ssl_client)

        print(f"Nickname of the client is {Fore.BLUE}{nickname}{Style.RESET_ALL}")
        broadcast(f"{Fore.GREEN}{nickname}{Style.RESET_ALL} joined the chat :)".encode('ascii'))
        ssl_client.send(b'Connected to the server! \n')
        print("-" * 50 + "\n")

        # Launch a thread to handle this client
        thread = threading.Thread(target=handle, args=(ssl_client,))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    receive()