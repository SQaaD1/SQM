import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import socket
import threading
import json
import asyncio
import websockets
from datetime import datetime

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Client - Internet")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Connection variables
        self.websocket = None
        self.connected = False
        self.username = None
        self.receive_thread = None
        self.loop = None
        
        # Create GUI
        self.create_widgets()
        
    def create_widgets(self):
        """Create the GUI widgets"""
        # Connection frame
        connection_frame = tk.Frame(self.root, padx=10, pady=10)
        connection_frame.pack(fill=tk.X)
        
        # Server address
        tk.Label(connection_frame, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.server_entry = tk.Entry(connection_frame, width=30)
        self.server_entry.insert(0, "wss://your-server.herokuapp.com")
        self.server_entry.grid(row=0, column=1, padx=5, columnspan=2)
        
        # Connect button
        self.connect_btn = tk.Button(
            connection_frame, 
            text="Connect", 
            command=self.connect_to_server,
            bg="#4CAF50",
            fg="white",
            padx=20
        )
        self.connect_btn.grid(row=0, column=3, padx=10)
        
        # Disconnect button
        self.disconnect_btn = tk.Button(
            connection_frame, 
            text="Disconnect", 
            command=self.disconnect_from_server,
            bg="#f44336",
            fg="white",
            padx=20,
            state=tk.DISABLED
        )
        self.disconnect_btn.grid(row=0, column=4, padx=10)
        
        # Chat display area
        chat_frame = tk.Frame(self.root, padx=10, pady=5)
        chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Chat text widget with scrollbar
        self.chat_display = tk.Text(chat_frame, wrap=tk.WORD, state=tk.DISABLED, height=20)
        scrollbar = tk.Scrollbar(chat_frame, command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=scrollbar.set)
        
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure tags for different message types
        self.chat_display.tag_config("system", foreground="gray", font=("Arial", 9, "italic"))
        self.chat_display.tag_config("chat", foreground="black", font=("Arial", 10))
        self.chat_display.tag_config("own_message", foreground="#0066CC", font=("Arial", 10, "bold"))
        
        # Message input frame
        input_frame = tk.Frame(self.root, padx=10, pady=10)
        input_frame.pack(fill=tk.X)
        
        # Message entry
        self.message_entry = tk.Entry(input_frame, font=("Arial", 11))
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        self.message_entry.config(state=tk.DISABLED)
        
        # Send button
        self.send_btn = tk.Button(
            input_frame, 
            text="Send", 
            command=self.send_message,
            bg="#2196F3",
            fg="white",
            padx=20,
            state=tk.DISABLED
        )
        self.send_btn.pack(side=tk.RIGHT)
        
        # Status bar
        self.status_bar = tk.Label(self.root, text="Not connected", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def connect_to_server(self):
        """Connect to the chat server"""
        server_url = self.server_entry.get().strip()
        
        if not server_url:
            messagebox.showerror("Error", "Please enter server URL")
            return
        
        # Ask for username
        if not self.username:
            self.username = simpledialog.askstring("Username", "Enter your username:", parent=self.root)
            if not self.username:
                return
        
        # Start connection in a separate thread
        self.connect_btn.config(state=tk.DISABLED)
        self.status_bar.config(text="Connecting...")
        
        connect_thread = threading.Thread(
            target=self._connect_async,
            args=(server_url,),
            daemon=True
        )
        connect_thread.start()
    
    def _connect_async(self, server_url):
        """Async connection handler"""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Build WebSocket URL
            if not server_url.startswith(('ws://', 'wss://')):
                server_url = f"wss://{server_url}/ws/{self.username}"
            else:
                server_url = f"{server_url}/ws/{self.username}"
            
            # Connect to WebSocket
            self.loop.run_until_complete(self._websocket_connect(server_url))
            
        except Exception as e:
            self.root.after(0, self._connection_failed, str(e))
    
    async def _websocket_connect(self, server_url):
        """WebSocket connection coroutine"""
        try:
            async with websockets.connect(server_url) as websocket:
                self.websocket = websocket
                self.connected = True
                
                # Update UI
                self.root.after(0, self._connection_success)
                
                # Receive messages
                async for message in websocket:
                    data = json.loads(message)
                    self.root.after(0, self.process_message, data)
                    
        except Exception as e:
            if self.connected:
                self.root.after(0, self._connection_failed, str(e))
    
    def _connection_success(self):
        """Handle successful connection"""
        self.connect_btn.config(state=tk.DISABLED)
        self.disconnect_btn.config(state=tk.NORMAL)
        self.send_btn.config(state=tk.NORMAL)
        self.message_entry.config(state=tk.NORMAL)
        self.server_entry.config(state=tk.DISABLED)
        
        self.status_bar.config(text=f"Connected as {self.username}")
        self.add_message("system", f"Connected to server as {self.username}")
    
    def _connection_failed(self, error):
        """Handle failed connection"""
        self.connected = False
        self.connect_btn.config(state=tk.NORMAL)
        self.status_bar.config(text="Connection failed")
        messagebox.showerror("Connection Error", f"Failed to connect: {error}")
    
    def disconnect_from_server(self):
        """Disconnect from the server"""
        self.connected = False
        
        if self.websocket:
            try:
                if self.loop and not self.loop.is_closed():
                    self.loop.run_until_complete(self.websocket.close())
            except:
                pass
            self.websocket = None
        
        if self.loop and not self.loop.is_closed():
            self.loop.close()
        
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.message_entry.config(state=tk.DISABLED)
        self.server_entry.config(state=tk.NORMAL)
        
        self.status_bar.config(text="Disconnected")
        self.add_message("system", "Disconnected from server")
    
    def process_message(self, message):
        """Process received message and update UI"""
        msg_type = message.get('type')
        
        if msg_type == 'chat':
            username = message.get('username')
            text = message.get('message')
            timestamp = message.get('timestamp', '')
            
            # Highlight own messages
            if username == self.username:
                self.add_message("own_message", f"[{timestamp}] {username}: {text}")
            else:
                self.add_message("chat", f"[{timestamp}] {username}: {text}")
                
        elif msg_type == 'system':
            text = message.get('message')
            timestamp = message.get('timestamp', '')
            self.add_message("system", f"[{timestamp}] {text}")
    
    def send_message(self):
        """Send a message to the server"""
        if not self.connected or not self.websocket:
            return
        
        message_text = self.message_entry.get().strip()
        if not message_text:
            return
        
        try:
            message = {
                'type': 'chat',
                'message': message_text
            }
            
            # Send via event loop
            if self.loop and not self.loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps(message)),
                    self.loop
                )
            
            self.message_entry.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send message: {str(e)}")
            self.disconnect_from_server()
    
    def add_message(self, msg_type, text):
        """Add a message to the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, text + "\n", msg_type)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def on_closing(self):
        """Handle window closing"""
        if self.connected:
            self.disconnect_from_server()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ChatClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
