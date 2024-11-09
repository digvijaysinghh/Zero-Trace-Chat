import socket
import ssl
import threading
import base64
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

load_dotenv()

def load_server_public_key(path):
    with open(path, "rb") as key_file:
        return serialization.load_pem_public_key(key_file.read())

def create_ssl_context(cert_path):
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

def connect_to_server(host, port, context):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ssl_client = context.wrap_socket(client, server_hostname=host)
    ssl_client.connect((host, port))
    return ssl_client

def receive_messages(ssl_client):
    while True:
        try:
            message = ssl_client.recv(1024).decode('ascii')
            if message == 'USERNAME':
                ssl_client.send(nickname.encode('ascii'))
            else:
                print(message)
        except Exception as e:
            print(f"An error occurred: {e}")
            ssl_client.close()
            break

def send_messages(ssl_client, server_public_key):
    while True:
        message = input("")
        full_message = f"{nickname}: {message}"
        encrypted_message = base64.b64encode(
            server_public_key.encrypt(
                full_message.encode('utf-8'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
        )
        ssl_client.send(encrypted_message)

def main():
    public_key_path = os.getenv('PUBLIC_KEY_PATH')
    cert_path = os.getenv('CERT_PATH')

    server_public_key = load_server_public_key(public_key_path)
    context = create_ssl_context(cert_path)

    host = input("Enter the server IP address: ")
    port = 55545

    global nickname
    nickname = input("\n\tChoose your nickname: ")
    print("\n")

    ssl_client = connect_to_server(host, port, context)

    receive_thread = threading.Thread(target=receive_messages, args=(ssl_client,))
    receive_thread.start()

    send_thread = threading.Thread(target=send_messages, args=(ssl_client, server_public_key))
    send_thread.start()

if __name__ == "__main__":
    main()