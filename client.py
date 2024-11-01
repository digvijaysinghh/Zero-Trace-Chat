import socket
import ssl
import threading

host = '(server_IP)'
port = 55556

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ssl_client = context.wrap_socket(client, server_hostname=host)
ssl_client.connect((host, port))

nickname = input("Choose your nickname: ")

def receive():
    while True:
        try:
            message = ssl_client.recv(1024).decode('ascii')
            if message == 'NICK':
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