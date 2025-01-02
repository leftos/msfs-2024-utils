import json
import os
import tkinter as tk
from tkinter import ttk, scrolledtext
from threading import Thread
from sim_time_rate_adjuster_procmem import main, backend_state, state_lock, VERSION

class SimAdjusterUI:
    # config file under appdata
    CONFIG_FILE = "config.json"
    DEFAULT_GEOMETRY = "400x125"
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"Sim Time Rate Adjuster v{VERSION}")
        
        # --- Connection Status ---
        self.connection_status_label = ttk.Label(root, text="Connection Status: Disconnected", foreground="red")
        self.connection_status_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        # --- Simulation Rate ---
        self.sim_rate_label = ttk.Label(root, text="Simulation Rate: N/A")
        self.sim_rate_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        # --- Seconds Offset ---
        self.seconds_offset_label = ttk.Label(root, text="Seconds Offset: N/A")
        self.seconds_offset_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)

        # --- Expandable Output Console ---
        self.expand_button = ttk.Button(root, text="Expand Console", command=self.toggle_console)
        self.expand_button.grid(row=3, column=0, sticky="w", padx=10, pady=5)

        self.console_frame = ttk.Frame(root)
        self.console_text = scrolledtext.ScrolledText(self.console_frame, wrap=tk.WORD, height=10, state='disabled')
        self.console_text.pack(fill=tk.BOTH, expand=True)
        self.auto_scroll = tk.BooleanVar(value=True)
        self.auto_scroll_check = ttk.Checkbutton(self.console_frame, text="Auto-Scroll", variable=self.auto_scroll)
        self.auto_scroll_check.pack(anchor='w')

        self.console_visible = False

        # Restore window geometry from config file
        self.restore_window_position()

        # --- Start Backend Thread ---
        self.backend_thread = Thread(target=main, daemon=True)
        self.backend_thread.start()

        # --- Start UI Update Loop ---
        self.update_ui()

        # --- Save window position on exit ----
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def toggle_console(self):
        if self.console_visible:
            self.console_frame.grid_forget()
            self.expand_button.config(text="Expand Console")
        else:
            self.console_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
            self.expand_button.config(text="Collapse Console")
        self.console_visible = not self.console_visible

    def log_to_console(self, message):
        self.console_text.config(state='normal')
        self.console_text.insert(tk.END, message + "\n")
        if self.auto_scroll.get():
            self.console_text.see(tk.END)
        self.console_text.config(state='disabled')

    def update_ui(self):
        with state_lock:
            self.connection_status_label.config(
                text=f"Connection Status: {backend_state['connection_status']}",
                foreground="green" if backend_state['connection_status'] == "Connected" else "red"
            )
            self.sim_rate_label.config(text=f"Simulation Rate: {backend_state['simulation_rate']}x" if backend_state['connection_status'] == "Connected" else "")
            self.seconds_offset_label.config(text=f"Seconds Offset: {backend_state['seconds_offset']} sec" if backend_state['connection_status'] == "Connected" else "")
            
            while backend_state['logs']:
                self.log_to_console(backend_state['logs'].pop(0))

        self.root.after(1000, self.update_ui)  # Update every 1 second

    def save_window_position(self):
        config = {
            "geometry": self.root.geometry(),
            "console_visible": self.console_visible,
            "auto_scroll": self.auto_scroll.get()
        }
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f)

    def restore_window_position(self):
        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.root.geometry(config.get("geometry", self.DEFAULT_GEOMETRY))
                console_visible = config.get("console_visible", False)
                if console_visible:
                    self.toggle_console()
                self.auto_scroll.set(config.get("auto_scroll", True))
        except (FileNotFoundError, json.JSONDecodeError):
            self.root.geometry(self.DEFAULT_GEOMETRY)
            
    def on_exit(self):
            self.save_window_position()
            self.root.destroy()
            
if __name__ == "__main__":
    root = tk.Tk()
    app = SimAdjusterUI(root)
    root.mainloop()