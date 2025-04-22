import socket
import ssl
import threading
import base64
import os
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes

# Load environment variables
load_dotenv()

# Get cert path and server's public key path
public_key_path = os.getenv('PUBLIC_KEY_PATH')
cert_path = os.getenv('CERT_PATH')

# Load public key
with open(public_key_path, "rb") as key_file:
    server_public_key = serialization.load_pem_public_key(key_file.read())

# SSL setup
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ssl_client = context.wrap_socket(client)

# GUI Part
class ChatClient:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Secure GUI Chat Room")

        self.chat_label = tk.Label(self.window, text="Chat Room:")
        self.chat_label.pack(padx=10, pady=5)

        self.text_area = scrolledtext.ScrolledText(self.window)
        self.text_area.pack(padx=10, pady=5)
        self.text_area.config(state='disabled')

        self.msg_label = tk.Label(self.window, text="Your Message:")
        self.msg_label.pack(padx=10, pady=5)

        self.input_area = tk.Entry(self.window, width=50)
        self.input_area.pack(padx=10, pady=5)
        self.input_area.bind("<Return>", self.write)

        self.send_button = tk.Button(self.window, text="Send", command=self.write)
        self.send_button.pack(padx=10, pady=5)

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.nickname = simpledialog.askstring("Nickname", "Choose your nickname:")
        if not self.nickname:
            messagebox.showerror("Error", "Nickname is required!")
            self.window.quit()

        self.connect_to_server()

        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()

        self.window.mainloop()

    def connect_to_server(self):
        host = simpledialog.askstring("Server IP", "Enter the server IP address:")
        try:
            ssl_client.connect((host, 55545))
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            self.window.quit()

    def receive(self):
        while True:
            try:
                message = ssl_client.recv(1024).decode('ascii')
                if message == 'NICK':
                    ssl_client.send(self.nickname.encode('ascii'))
                else:
                    self.text_area.config(state='normal')
                    self.text_area.insert('end', message + "\n")
                    self.text_area.yview('end')
                    self.text_area.config(state='disabled')
            except:
                ssl_client.close()
                break

    def write(self, event=None):
        message = f"{self.nickname}: {self.input_area.get()}"
        if message:
            encrypted_message = server_public_key.encrypt(
                message.encode('ascii'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            ssl_client.send(base64.b64encode(encrypted_message))
            self.input_area.delete(0, 'end')

    def on_close(self):
        ssl_client.close()
        self.window.quit()

if __name__ == "__main__":
    ChatClient()
