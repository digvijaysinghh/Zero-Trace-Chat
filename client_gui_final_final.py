import socket
import ssl
import threading
send_lock = threading.Lock()
import base64
import os
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, filedialog
import time
from dotenv import load_dotenv
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
import re  # For ANSI cleanup
import os

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

def strip_ansi_codes(text):
    return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

# GUI Part
class ChatClient:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Secure GUI Chat Room")
        self.window.geometry("600x400")
        self.window.rowconfigure(1, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.chat_label = tk.Label(self.window, text="Chat Room:")
        self.chat_label.grid(row=0, column=0, padx=10, pady=5, sticky='w')

        self.text_area = scrolledtext.ScrolledText(self.window)
        self.text_area.grid(row=1, column=0, padx=10, pady=5, sticky='nsew')
        self.text_area.config(state='disabled')

        self.msg_label = tk.Label(self.window, text="Your Message:")
        self.msg_label.grid(row=2, column=0, padx=10, pady=5, sticky='w')

        self.input_area = tk.Entry(self.window)
        self.input_area.grid(row=3, column=0, padx=10, pady=5, sticky='ew')
        self.input_area.bind("<Return>", self.write)

        self.send_button = tk.Button(self.window, text="Send", command=self.write, width=12)
        self.send_button.grid(row=4, column=0, padx=10, pady=5, sticky='e')

        # Feature buttons (not gridded individually)
        self.fullscreen = False
        self.invisible_input = False
        # Bottom feature button panel (horizontal row at bottom)
        btn_frame = tk.Frame(self.window)
        btn_frame.grid(row=5, column=0, padx=10, pady=5, sticky='ew')
        btn_frame.columnconfigure(tuple(range(5)), weight=1)

        features = [
            ("Files", self.open_download_folder),
            ("Export Logs", self.export_logs),
            ("Invisible Input", self.toggle_invisible),
            ("Self Destruct", self.set_self_destruct),
            ("Kill Switch", self.kill_switch),
        ]
        for idx, (label, cmd) in enumerate(features):
            btn = tk.Button(btn_frame, text=label, command=cmd, width=10)
            btn.grid(row=0, column=idx, padx=3, sticky='ew')

        self.chat_logs = []

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.nickname = simpledialog.askstring("Nickname", "Choose your nickname:")
        if not self.nickname:
            messagebox.showerror("Error", "Nickname is required!")
            self.window.quit()

        self.connect_to_server()

        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()

        self.window.mainloop()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.window.attributes('-fullscreen', self.fullscreen)

    def connect_to_server(self):
        host = simpledialog.askstring("Server IP", "Enter the server IP address:")
        try:
            ssl_client.connect((host, 55545))
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            self.window.quit()

    
    
    def receive(self):
        downloads_dir = os.path.join(os.path.expanduser("~"), "ChatDownloads")
        os.makedirs(downloads_dir, exist_ok=True)

        while True:
            try:
                data = ssl_client.recv(1024)
                # Kill-switch reaction
                if data.startswith(b"KILLED"):
                    # Clear UI and exit immediately
                    try:
                        self.clear_messages()
                        messagebox.showinfo("Server Shutdown", "Server was terminated by kill switch.")
                    except:
                        pass
                    ssl_client.close()
                    self.window.destroy()
                    os._exit(0)
                message = data.decode('ascii')
                if message == 'NICK':
                    ssl_client.send(self.nickname.encode('ascii'))
                elif message.startswith("FILE:"):
                    filename = message.split(":", 1)[1]
                    wants_file = messagebox.askyesno("File Received", f"Do you want to download the file: {filename}?")
                    file_data_encoded = ssl_client.recv(10000000).decode('ascii')

                    if not wants_file:
                        continue  # Discard the data but don't break flow

                    file_data = base64.b64decode(file_data_encoded)
                    save_path = os.path.join(downloads_dir, filename)
                    with open(save_path, "wb") as f:
                        f.write(file_data)

                    notify_msg = f"Received file: {filename} (saved to {save_path})"
                    self.chat_logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [IP: {ssl_client.getsockname()[0]}] [User: File System] => {notify_msg}")
                    self.text_area.config(state='normal')
                    self.text_area.insert('end', notify_msg + "\n")
                    self.text_area.config(state='disabled')
                else:
                    clean_message = strip_ansi_codes(message)
                    # Do not echo back own messages when invisible input is on
                    if self.invisible_input and clean_message.startswith(f"{self.nickname}:"):
                        continue
                    # Don't re-display our own messages (they’re already inserted in write())
                    if clean_message.startswith(f"{self.nickname}:"):
                        continue
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        ip = ssl_client.getsockname()[0]
                    except:
                        ip = "unknown"
                    if ":" in clean_message:
                        user, msg = clean_message.split(":", 1)
                        formatted_log = f"[{timestamp}] [IP: {ip}] [User: {user.strip()}] => {msg.strip()}"
                    else:
                        formatted_log = f"[{timestamp}] [IP: {ip}] {clean_message}"
                    self.chat_logs.append(formatted_log)
                    self.text_area.config(state='normal')
                    self.text_area.insert('end', clean_message + "\n")
                    self.text_area.yview('end')
                    self.text_area.config(state='disabled')
            except:
                ssl_client.close()
                break

    def write(self, event=None):
        msg_content = self.input_area.get()
        message = f"{self.nickname}: {msg_content}"
        self.input_area.delete(0, 'end')

        if msg_content.strip().lower() == "/logs":
            self.save_chat_logs()
            return

        if msg_content.strip().lower() == "/sendfile":
            self.send_file()
            return

        try:
            encrypted_message = server_public_key.encrypt(
                message.encode('ascii'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            encoded_message = base64.b64encode(encrypted_message).decode('ascii')
            ssl_client.send(encoded_message.encode('ascii'))
            # Local display: mask if invisible_input
            if self.invisible_input:
                masked = f"{self.nickname}: " + "*" * len(msg_content)
            else:
                masked = message
            self.text_area.config(state='normal')
            self.text_area.insert('end', masked + "\n")
            self.text_area.yview('end')
            self.text_area.config(state='disabled')
        except:
            messagebox.showerror("Send Failed", "Message could not be sent")

    def save_chat_logs(self):
        log_file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if log_file_path:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.chat_logs))
            messagebox.showinfo("Logs Saved", f"Chat logs saved to {log_file_path}")

    def send_file(self):
        def do_send():
            file_path = filedialog.askopenfilename(filetypes=[("Documents", "*.txt *.pdf *.doc *.docx")])
            if not file_path:
                return

            file_size = os.path.getsize(file_path)
            if file_size > 100 * 1024 * 1024:
                messagebox.showerror("File Too Large", "File size exceeds 100MB limit.")
                return

            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()

                filename = os.path.basename(file_path)
                encoded_data = base64.b64encode(file_data).decode('ascii')

                message = f"{self.nickname} sent a file: {filename}"
                clean_message = strip_ansi_codes(message)

                self.chat_logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [IP: {ssl_client.getsockname()[0]}] [User: {self.nickname}] => sent a file: {filename}")
                self.text_area.config(state='normal')
                self.text_area.insert('end', clean_message + "\n")
                self.text_area.config(state='disabled')

                ssl_client.send(f"FILE:{filename}".encode('ascii'))
                ssl_client.send(encoded_data.encode('ascii'))
            except Exception as e:
                messagebox.showerror("File Send Failed", str(e))

        threading.Thread(target=do_send, daemon=True).start()

    def on_close(self):
        ssl_client.close()
        self.window.destroy()

    def toggle_invisible(self):
        # Toggle masking of input
        if self.invisible_input:
            self.input_area.config(show='')
            self.invisible_input = False
            self.invisible_button.config(relief='raised')
        else:
            self.input_area.config(show='*')
            self.invisible_input = True
            self.invisible_button.config(relief='sunken')

    def set_self_destruct(self):
        # Ask for timer duration
        secs = simpledialog.askinteger("Self-Destruct", "Enter timer in seconds:", minvalue=1, maxvalue=3600)
        if not secs:
            return
        messagebox.showinfo("Self-Destruct", f"Chat will clear in {secs} seconds")
        # Schedule clear
        self.window.after(secs * 1000, self.clear_messages)

    def clear_messages(self):
        # Erase chat history and logs
        self.text_area.config(state='normal')
        self.text_area.delete('1.0', 'end')
        self.text_area.config(state='disabled')
        self.chat_logs.clear()
        messagebox.showinfo("Cleared", "Chat history has been cleared.")


    def open_download_folder(self):
        import subprocess
        download_dir = os.path.join(os.path.expanduser("~"), "ChatDownloads")
        if os.name == 'nt':
            os.startfile(download_dir)
        elif os.name == 'posix':
            subprocess.run(["open", download_dir])
        else:
            messagebox.showinfo("Info", f"Saved in {download_dir}")



    def export_logs(self):
        path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log Files", "*.log")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.chat_logs))
            messagebox.showinfo("Exported", f"Logs saved to {path}")

    def kill_switch(self):
        if messagebox.askyesno("Kill Switch", "Shutdown server and clear all chats?"):
            with send_lock:
                ssl_client.sendall("KILL\n".encode('utf-8'))
            self.clear_messages()
            self.on_close()
            os._exit(0)


if __name__ == "__main__":
    ChatClient()
