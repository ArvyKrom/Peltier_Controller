import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import serial
import serial.tools.list_ports
import threading
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import re
import time
import queue
import os
from PIL import Image, ImageTk

class SerialMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Peltier Controller")

        self.serial_port = None
        self.read_thread = None
        self.stop_event = threading.Event()
        self.last_port_list = []
        self.recording = False
        self.record_file = None
        self.record_file_path = None
        self.temp_queue = queue.Queue()
        self.current_temp = None
        self.current_setpoint = None
        self.profile_running = False
        self.ignore_stop_message = False  # New flag to control STOP message handling

        # Temperature profile state persistence
        self.profile_points = []
        self.time_var = tk.StringVar()
        self.profile_temp_var = tk.StringVar()
        self.profile_window = None
        self.profile_fig = None
        self.profile_ax = None
        self.profile_canvas = None

        self.setup_ui()
        self.update_ports()
        self.refresh_ports_periodically()

        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        self.root.geometry("780x400")
        frame = tk.Frame(self.root, width=780, height=400)
        frame.place(x=0, y=0)

        # COM Port Section
        com_frame = tk.Frame(frame)
        ttk.Label(com_frame, text="COM Port:").pack(side=tk.LEFT, padx=(0, 5))
        self.port_var = tk.StringVar()
        self.port_menu = ttk.Combobox(com_frame, textvariable=self.port_var, width=20, state="readonly")
        self.port_menu.pack(side=tk.LEFT, padx=(0, 5))
        self.connect_button = ttk.Button(com_frame, text="Connect", command=self.connect_serial)
        self.connect_button.pack(side=tk.LEFT)
        com_frame.place(x=20, y=20)

        self.separator1 = ttk.Separator(frame, orient="horizontal")
        self.separator1.place(x=0, y=60, width=780, height=10)

        try:
            original_image = Image.open("SE_icon.png")
            resized_image = original_image.resize((40, 40), Image.Resampling.LANCZOS)
            self.icon_image = ImageTk.PhotoImage(resized_image)
            icon_label = tk.Label(frame, image=self.icon_image, background="white")
            icon_label.place(x=720, y=12, width=40, height=40)
        except Exception:
            pass

        # Terminal Section
        self.text_area = tk.Text(frame, width=50, height=20, wrap="word")
        self.text_area.place(x=20, y=60, width=500, height=290)
        self.text_area.config(state="disabled")

        # Buttons Section
        style = ttk.Style()
        style.configure("Record.TButton", font=("Helvetica", 14), foreground="black", padding=15)
        style.map("Record.TButton", background=[("!disabled", "white"), ("disabled", "gray")])
        style.configure("StopRecording.TButton", font=("Helvetica", 14), foreground="black", padding=15, background="#F16C6C")
        style.map("StopRecording.TButton", background=[("!disabled", "#F16C6C"), ("disabled", "gray")])

        self.record_button = ttk.Button(frame, text="Record", command=self.toggle_recording, width=16, style="Record.TButton")
        self.record_button.place(x=550, y=77)

        self.view_button = ttk.Button(frame, text="Plot", command=self.view_recording, width=16, style="Record.TButton")
        self.view_button.place(x=550, y=142)

        self.advanced_profile_button = ttk.Button(frame, text="Temperature Profile", command=self.open_advanced_profile_window, width=16, style="Record.TButton")
        self.advanced_profile_button.place(x=550, y=207)

        # Options Button with "(Upcoming)" label below
        self.setup_button = ttk.Button(frame, text="Options", command=self.open_setup_window, width=16, style="Record.TButton")
        self.setup_button.place(x=550, y=272)
        # Add a small label below the button for "(Upcoming)"
        options_sublabel = ttk.Label(frame, text="(Upcoming)", font=("Helvetica", 8))
        options_sublabel.place(x=655, y=272 + 59)

        # Arrow pointing from "Upcoming" To "Options" Button
        try:
            arrow_image = Image.open("arrow.png")
            resized_arrow_image = arrow_image.resize((10, 10), Image.Resampling.LANCZOS)
            self.arrow_image = ImageTk.PhotoImage(resized_arrow_image)
            arrow = tk.Label(frame, image=self.arrow_image, background="white")
            arrow.place(x=645, y=272+61, width=10, height=10)
        except Exception:
            pass

        self.separator1 = ttk.Separator(frame, orient="horizontal")
        self.separator1.place(x=0, y=350, width=780, height=10)

        # Temperature Controls Section
        temp_label = ttk.Label(frame, text="Temperature (°C):")
        temp_label.place(x=20, y=360)

        self.temperature_var = tk.DoubleVar(value=5.0)
        self.temperature_slider = ttk.Scale(frame, from_=5.0, to=70.0, orient="horizontal", variable=self.temperature_var, length=400, command=lambda x: self.update_temperature_from_slider(x))
        self.temperature_slider.place(x=120, y=360)

        self.temperature_values = [str(i) for i in range(5, 71, 5)]
        self.temperature_combobox_var = tk.StringVar(value="5.0 °C")
        self.temperature_combobox = ttk.Combobox(frame, textvariable=self.temperature_combobox_var, values=[f"{val} °C" for val in self.temperature_values], width=10)
        self.temperature_combobox.place(x=550, y=360)
        self.temperature_combobox.bind("<Return>", self.update_temperature_from_combobox)
        self.temperature_combobox.bind("<FocusOut>", self.update_temperature_from_combobox)
        self.temperature_combobox.bind("<<ComboboxSelected>>", self.update_temperature_from_combobox)

        self.send_button = ttk.Button(frame, text="Send", command=self.send_command, state="normal")
        self.send_button.place(x=650, y=360)

    def open_advanced_profile_window(self):
        if self.profile_window and self.profile_window.winfo_exists():
            self.profile_window.focus_set()
            self.profile_window.lift()
            return

        self.profile_window = tk.Toplevel(self.root)
        self.profile_window.title("Advanced Temperature Profile")
        self.profile_window.resizable(True, True)
        self.profile_window.geometry("800x520")
        self.profile_window.protocol("WM_DELETE_WINDOW", self.on_profile_window_close)

        main_frame = tk.Frame(self.profile_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        control_frame = tk.Frame(main_frame)
        control_frame.pack(side="left", fill="y", padx=(0, 10))

        input_frame = tk.Frame(control_frame)
        input_frame.pack(anchor="center", pady=(0, 5))

        time_frame = tk.Frame(input_frame)
        time_frame.pack(anchor="center", pady=(5, 5))
        time_label = ttk.Label(time_frame, text="Time (s):", width=17, anchor="e")
        time_label.pack(side="left")
        time_entry = ttk.Entry(time_frame, textvariable=self.time_var, width=10)
        time_entry.pack(side="left", padx=(0, 5))

        temp_frame = tk.Frame(input_frame)
        temp_frame.pack(anchor="center", pady=0)
        temp_label = ttk.Label(temp_frame, text="Temperature (°C):", width=17, anchor="e")
        temp_label.pack(side="left")
        temp_entry = ttk.Entry(temp_frame, textvariable=self.profile_temp_var, width=10)
        temp_entry.pack(side="left", padx=(0, 5))

        top_button_frame = tk.Frame(control_frame)
        top_button_frame.pack(anchor="center", pady=5)

        add_button = ttk.Button(top_button_frame, text="Add Point", command=lambda: self.add_profile_point(self.profile_window), width=30)
        add_button.pack(anchor="center", pady=1)

        delete_button = ttk.Button(top_button_frame, text="Delete Selected", command=lambda: self.delete_profile_point(self.profile_window), width=30)
        delete_button.pack(anchor="center", pady=1)

        listbox_frame = tk.Frame(control_frame)
        listbox_frame.pack(anchor="center", pady=5)

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
        self.profile_listbox = tk.Listbox(listbox_frame, width=27, height=10, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.profile_listbox.yview)
        self.profile_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for time, temp in self.profile_points:
            self.profile_listbox.insert(tk.END, f"Time: {time:.1f}s, Temp: {temp:.1f}°C")

        button_frame = tk.Frame(control_frame)
        button_frame.pack(fill="x", pady=5)

        style = ttk.Style()
        style.configure("AllButtons.TButton", background="white", foreground="black", font=("Helvetica", 9))
        style.configure("SendProfile.TButton", background="white", foreground="black", font=("Helvetica", 9))
        style.configure("Stop.TButton", background="#F16C6C", foreground="black", font=("Helvetica", 9))

        save_button = ttk.Button(button_frame, text="Save Profile", command=self.save_profile, width=26, style="AllButtons.TButton")
        save_button.pack(anchor="center", pady=1)

        load_button = ttk.Button(button_frame, text="Load Profile", command=lambda: self.load_profile(self.profile_window), width=26, style="AllButtons.TButton")
        load_button.pack(anchor="center", pady=1)

        button_text = "Stop" if self.profile_running else "Send Profile"
        button_style = "Stop.TButton" if self.profile_running else "SendProfile.TButton"
        self.send_profile_button = ttk.Button(button_frame, text=button_text, command=self.start_profile_sending, width=26, style=button_style)
        self.send_profile_button.pack(anchor="center", pady=1)

        close_button = ttk.Button(button_frame, text="Close", command=self.on_profile_window_close, width=26, style="AllButtons.TButton")
        close_button.pack(anchor="center", pady=1)

        graph_frame = tk.Frame(main_frame)
        graph_frame.pack(side="right", fill="both", expand=True)

        self.profile_fig = plt.figure(figsize=(6, 4))
        self.profile_ax = self.profile_fig.add_subplot(111)
        self.profile_ax.set_title("Temperature Profile")
        self.profile_ax.set_xlabel("Time (s)")
        self.profile_ax.set_ylabel("Temperature (°C)")
        self.profile_ax.grid(True)
        self.profile_fig.tight_layout()

        self.profile_canvas = FigureCanvasTkAgg(self.profile_fig, master=graph_frame)
        self.profile_canvas.draw()
        self.profile_canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar = NavigationToolbar2Tk(self.profile_canvas, graph_frame)
        toolbar.update()
        toolbar.pack(fill="x")

        self.update_profile_graph()

    def on_profile_window_close(self):
        if self.profile_window:
            self.profile_window.destroy()
        self.profile_window = None

    def add_profile_point(self, profile_window):
        try:
            time_str = self.time_var.get().strip()
            temp_str = self.profile_temp_var.get().strip()
            if not time_str or not temp_str:
                messagebox.showerror("Error", "Please enter both time and temperature.", parent=profile_window)
                profile_window.focus_set()
                profile_window.lift()
                return
            time = float(time_str)
            temperature = float(temp_str)
            if time < 0:
                messagebox.showerror("Error", "Time cannot be negative.", parent=profile_window)
                profile_window.focus_set()
                profile_window.lift()
                return
            if not (5 <= temperature <= 70):
                messagebox.showerror("Error", "Temperature must be between 5 and 70 °C.", parent=profile_window)
                profile_window.focus_set()
                profile_window.lift()
                return
            if any(point[0] == time for point in self.profile_points):
                messagebox.showerror("Error", "A point with this time already exists.", parent=profile_window)
                profile_window.focus_set()
                profile_window.lift()
                return
            self.profile_points.append((time, temperature))
            self.profile_points.sort(key=lambda x: x[0])
            self.profile_listbox.delete(0, tk.END)
            for t, temp in self.profile_points:
                self.profile_listbox.insert(tk.END, f"Time: {t:.1f}s, Temp: {temp:.1f}°C")
            self.time_var.set("")
            self.profile_temp_var.set("")
            self.update_profile_graph()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for time and temperature.", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add point: {str(e)}", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()

    def update_profile_graph(self):
        try:
            self.profile_ax.clear()
            self.profile_ax.set_title("Temperature Profile")
            self.profile_ax.set_xlabel("Time (s)")
            self.profile_ax.set_ylabel("Temperature (°C)")
            self.profile_ax.grid(True)

            if self.profile_points:
                times, temps = zip(*self.profile_points)
                self.profile_ax.plot(times, temps, marker='o', linestyle='-', color='blue', label='Intended Profile')
            else:
                self.profile_ax.plot([], [], marker='o', linestyle='-', color='blue', label='Intended Profile')

            self.profile_ax.set_xlim(-10, 100) if not self.profile_points else self.profile_ax.set_xlim(-10, max([t for t, _ in self.profile_points]) + 10)
            self.profile_ax.set_ylim(0, 80) if not self.profile_points else self.profile_ax.set_ylim(min([temp for _, temp in self.profile_points]) - 5, max([temp for _, temp in self.profile_points]) + 5)
            self.profile_ax.legend()
            self.profile_fig.tight_layout()
            if self.profile_canvas:
                self.profile_canvas.draw()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update graph: {str(e)}", parent=self.profile_canvas.get_tk_widget().winfo_toplevel() if self.profile_canvas else self.root)
            (self.profile_canvas.get_tk_widget().winfo_toplevel() if self.profile_canvas else self.root).focus_set()
            if self.profile_window and self.profile_window.winfo_exists():
                self.profile_window.lift()

    def open_setup_window(self):
        pass  # Placeholder to do nothing

    def save_profile(self):
        if not self.profile_window or not self.profile_window.winfo_exists():
            return
        profile_window = self.profile_window
        if not self.profile_points:
            messagebox.showinfo("Info", "No profile points to save.", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], title="Save temperature profile")
        if not file_path:
            profile_window.focus_set()
            profile_window.lift()
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for time, temp in self.profile_points:
                    f.write(f"{time},{temp}\n")
            messagebox.showinfo("Success", "Profile saved successfully.", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile: {str(e)}", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()

    def load_profile(self, profile_window):
        file_path = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], title="Load temperature profile")
        if not file_path:
            profile_window.focus_set()
            profile_window.lift()
            return

        try:
            self.profile_points = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    time, temp = map(float, line.split(","))
                    if time < 0:
                        raise ValueError("Time cannot be negative.")
                    if not (5 <= temp <= 70):
                        raise ValueError("Temperature must be between 5 and 70 °C.")
                    self.profile_points.append((time, temp))

            self.profile_points.sort(key=lambda x: x[0])
            self.profile_listbox.delete(0, tk.END)
            for time, temp in self.profile_points:
                self.profile_listbox.insert(tk.END, f"Time: {time:.1f}s, Temp: {temp:.1f}°C")
            self.update_profile_graph()
            messagebox.showinfo("Success", "Profile loaded successfully.", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {str(e)}", parent=profile_window)
            self.profile_points = []
            self.profile_listbox.delete(0, tk.END)
            self.update_profile_graph()
            profile_window.focus_set()
            profile_window.lift()

    def start_profile_sending(self):
        if not self.profile_window or not self.profile_window.winfo_exists():
            return
        profile_window = self.profile_window
        if self.profile_running:
            self.stop_event.set()
            self.profile_running = False
            self.ignore_stop_message = True  # Set flag to ignore STOP message after manual stop
            self.root.after(0, lambda: self.send_profile_button.config(text="Send Profile", style="SendProfile.TButton"))
            self.root.after(0, lambda: self.send_button.config(state="normal"))  # Re-enable Send button
            profile_window.focus_set()
            profile_window.lift()
            return

        if not self.profile_points:
            messagebox.showinfo("Info", "No profile points to send.", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()
            return

        if not self.serial_port or not self.serial_port.is_open:
            messagebox.showerror("Error", "Serial port is not open.", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()
            return

        self.stop_event.clear()
        self.profile_running = True
        self.ignore_stop_message = False  # Reset flag when starting a new profile
        self.current_setpoint = None
        self.current_time = 0.0
        self.first_point_sent = False
        self.first_point_message_sent = False
        self.total_time = self.profile_points[-1][0]
        self.last_update_time = time.time()
        self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Starting profile transmission...\n")
        try:
            self.serial_port.write("Profile\n".encode('utf-8'))
            self.serial_port.flush()
            self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Sent: Profile\n")
            time.sleep(1.0)
        except Exception as e:
            self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Error sending Profile command: {str(e)}\n")
            self.profile_running = False
            self.root.after(0, lambda: self.send_profile_button.config(text="Send Profile", style="SendProfile.TButton"))
            self.root.after(0, lambda: self.send_button.config(state="normal"))  # Re-enable Send button
            profile_window.focus_set()
            profile_window.lift()
            return
        self.root.after(0, lambda: self.send_profile_button.config(text="Stop", style="Stop.TButton"))
        self.root.after(0, lambda: self.send_button.config(state="disabled"))  # Disable Send button
        self.profile_points.sort(key=lambda x: x[0])
        self.send_profile_step()

    def send_profile_step(self):
        if not self.profile_running or self.current_time > self.total_time or self.stop_event.is_set():
            timestamp = datetime.datetime.now().strftime('[%H:%M:%S] ')
            if self.stop_event.is_set():
                self.display_output(f"{timestamp}Profile transmission stopped.\n")
            else:
                self.display_output(f"{timestamp}Profile transmission completed.\n")
            self.profile_running = False
            self.stop_event.clear()
            self.root.after(0, lambda: self.send_profile_button.config(text="Send Profile", style="SendProfile.TButton"))
            self.root.after(0, lambda: self.send_button.config(state="normal"))  # Re-enable Send button
            if self.profile_window and self.profile_window.winfo_exists():
                self.profile_window.focus_set()
                self.profile_window.lift()
            return

        try:
            if not self.first_point_sent:
                target_temp = self.profile_points[0][1]
                temp = target_temp
            else:
                temp = self.interpolate_temperature(self.current_time)

            timestamp = datetime.datetime.now().strftime('[%H:%M:%S] ')
            command = f"{temp:.1f}\n"

            if not self.first_point_sent:
                if not self.first_point_message_sent:
                    self.display_output(f"{timestamp}Sending first point: {command} (Waiting for {target_temp}°C)\n")
                    self.first_point_message_sent = True
                self.serial_port.write(command.encode('utf-8'))
                self.serial_port.flush()
                self.current_setpoint = temp
                if self.current_temp is not None:
                    if abs(self.current_temp - target_temp) <= 0.5:
                        self.first_point_sent = True
                        self.first_point_message_sent = False
            else:
                self.display_output(f"{timestamp}Sent: {command}")
                self.serial_port.write(command.encode('utf-8'))
                self.serial_port.flush()
                self.current_setpoint = temp

            current_time = time.time()
            if current_time - self.last_update_time >= 1.0:
                self.current_time += 1.0
                self.last_update_time = current_time

            self.root.after(50, self.send_profile_step)
        except Exception as e:
            self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Send Error: {str(e)}\n")
            self.profile_running = False
            self.stop_event.clear()
            self.root.after(0, lambda: self.send_profile_button.config(text="Send Profile", style="SendProfile.TButton"))
            self.root.after(0, lambda: self.send_button.config(state="normal"))  # Re-enable Send button
            if self.profile_window and self.profile_window.winfo_exists():
                self.profile_window.focus_set()
                self.profile_window.lift()

    def interpolate_temperature(self, current_time):
        if not self.profile_points:
            return 20

        if current_time <= self.profile_points[0][0]:
            return self.profile_points[0][1]
        if current_time >= self.profile_points[-1][0]:
            return self.profile_points[-1][1]

        for i in range(len(self.profile_points) - 1):
            t1, temp1 = self.profile_points[i]
            t2, temp2 = self.profile_points[i + 1]
            if t1 <= current_time <= t2:
                fraction = (current_time - t1) / (t2 - t1)
                interpolated_temp = temp1 + (temp2 - temp1) * fraction
                return round(interpolated_temp, 1)
        return self.profile_points[-1][1]

    def delete_profile_point(self, profile_window):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Please select a point to delete.", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()
            return
        index = selection[0]
        if 0 <= index < len(self.profile_points):
            del self.profile_points[index]
            self.profile_listbox.delete(0, tk.END)
            for time, temp in self.profile_points:
                self.profile_listbox.insert(tk.END, f"Time: {time:.1f}s, Temp: {temp:.1f}°C")
            self.update_profile_graph()
        else:
            messagebox.showerror("Error", "Selected index is invalid.", parent=profile_window)
            profile_window.focus_set()
            profile_window.lift()

    def toggle_recording(self):
        if not self.recording:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], title="Select file to save terminal recording")
            if not file_path:
                return
            try:
                self.record_file = open(file_path, "w", encoding="utf-8")
                self.record_file_path = file_path
                self.recording = True
                self.record_button.config(text="Stop Recording", style="StopRecording.TButton")
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to open file for recording: {str(e)}", parent=self.root)
                self.root.focus_set()
                self.recording = False
                self.record_file = None
        else:
            if self.record_file is not None:
                try:
                    self.record_file.close()
                except Exception as e:
                    messagebox.showerror("File Error", f"Failed to close recording file: {str(e)}", parent=self.root)
                    self.root.focus_set()
                finally:
                    self.record_file = None
            self.recording = False
            self.record_button.config(text="Record", style="Record.TButton")

    def view_recording(self):
        file_path = filedialog.askopenfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], title="Select recording file to view")
        if not file_path:
            return

        view_window = tk.Toplevel(self.root)
        view_window.title("Temperature Graph")
        view_window.resizable(True, True)

        try:
            timestamps = []
            inside_temps = []
            outside_temps = []
            set_inside_temps = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    match_three = re.search(r"\[(\d{2}:\d{2}:\d{2})\]\s*(-?\d+\.\d+), (-?\d+\.\d+), (-?\d+\.\d+)", line)
                    match_two = re.search(r"\[(\d{2}:\d{2}:\d{2})\]\s*(-?\d+\.\d+), (-?\d+\.\d+)(?!,)", line)
                    if match_three:
                        timestamp_str = match_three.group(1)
                        inside_temp = float(match_three.group(2))
                        outside_temp = float(match_three.group(3))
                        set_inside_temp = float(match_three.group(4))
                        timestamp = datetime.datetime.strptime(timestamp_str, "%H:%M:%S")
                        timestamps.append(timestamp)
                        inside_temps.append(inside_temp)
                        outside_temps.append(outside_temp)
                        set_inside_temps.append(set_inside_temp)
                    elif match_two:
                        timestamp_str = match_two.group(1)
                        inside_temp = float(match_two.group(2))
                        outside_temp = float(match_two.group(3))
                        timestamp = datetime.datetime.strptime(timestamp_str, "%H:%M:%S")
                        timestamps.append(timestamp)
                        inside_temps.append(inside_temp)
                        outside_temps.append(outside_temp)
                    else:
                        continue

            if not timestamps or not inside_temps or not outside_temps:
                messagebox.showinfo("No Data", "No valid temperature data found in the file.", parent=view_window)
                view_window.focus_set()
                view_window.lift()
                view_window.destroy()
                return

            start_time = timestamps[0]
            relative_times = [(t - start_time).total_seconds() for t in timestamps]

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.plot(relative_times, inside_temps, linestyle='-', label='Inside')
            ax.plot(relative_times, outside_temps, linestyle='-', label='Outside')
            if set_inside_temps:
                ax.plot(relative_times, set_inside_temps, linestyle='-', label='Set')
            ax.set_title("Temperature Over Time")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Temperature (°C)")
            ax.grid(True)
            ax.legend()
            plt.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=view_window)
            canvas.draw()
            canvas.get_tk_widget().pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

            toolbar = NavigationToolbar2Tk(canvas, view_window)
            toolbar.update()
            toolbar.pack(pady=5)

            close_button = ttk.Button(view_window, text="Close", command=lambda: [plt.close(fig), view_window.destroy()])
            close_button.pack(pady=5)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process file: {str(e)}", parent=view_window)
            view_window.focus_set()
            view_window.lift()
            view_window.destroy()

    def update_temperature_from_slider(self, value):
        temp = round(float(value) / 0.1) * 0.1
        temp = round(temp, 1)
        temp = max(5.0, min(70.0, temp))
        self.temperature_var.set(temp)
        self.temperature_combobox_var.set(f"{temp} °C")
        if self.profile_running:
            self.stop_event.set()
            self.profile_running = False
            self.ignore_stop_message = True  # Set flag to ignore STOP message after manual stop
            self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Profile transmission stopped due to manual temperature adjustment.\n")
            self.root.after(0, lambda: self.send_profile_button.config(text="Send Profile", style="SendProfile.TButton"))
            self.root.after(0, lambda: self.send_button.config(state="normal"))  # Re-enable Send button
            if self.profile_window and self.profile_window.winfo_exists():
                self.profile_window.focus_set()
                self.profile_window.lift()

    def update_temperature_from_combobox(self, event=None):
        try:
            input_str = self.temperature_combobox_var.get().replace(" °C", "").strip()
            temp = int(float(input_str))
            temp = max(5, min(70, temp))
            self.temperature_var.set(temp)
            self.temperature_combobox_var.set(f"{temp} °C")
        except ValueError:
            temp = self.temperature_var.get()
            self.temperature_combobox_var.set(f"{temp} °C")

    def update_ports(self):
        ports = serial.tools.list_ports.comports()
        port_names = [port.device for port in ports]
        if port_names != self.last_port_list:
            self.last_port_list = port_names
            self.port_menu['values'] = port_names
            if port_names:
                if self.port_var.get() in port_names:
                    self.port_menu.set(self.port_var.get())
                else:
                    self.port_menu.current(0)
            else:
                self.port_menu.set("")

    def refresh_ports_periodically(self):
        self.update_ports()
        self.root.after(1000, self.refresh_ports_periodically)

    def connect_serial(self):
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Error", "Please select a COM port.", parent=self.root)
            self.root.focus_set()
            return

        self.disconnect_serial()

        try:
            self.serial_port = serial.Serial(port, 115200, timeout=1, write_timeout=0.5)
            self.connect_button.config(text="Disconnect", command=self.disconnect_serial)
            self.stop_event.clear()
            self.read_thread = threading.Thread(target=self.read_serial)
            self.read_thread.daemon = True
            self.read_thread.start()
        except Exception as e:
            messagebox.showerror("Connection Error", str(e), parent=self.root)
            self.root.focus_set()

    def disconnect_serial(self):
        self.stop_event.set()
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1)
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        self.serial_port = None
        self.read_thread = None
        self.current_temp = None
        self.current_setpoint = None
        self.temp_queue.queue.clear()
        self.connect_button.config(text="Connect", command=self.connect_serial)
        if self.profile_running:
            self.profile_running = False
            self.ignore_stop_message = True  # Set flag to ignore STOP message after disconnect
            self.root.after(0, lambda: self.send_profile_button.config(text="Send Profile", style="SendProfile.TButton"))
            self.root.after(0, lambda: self.send_button.config(state="normal"))  # Re-enable Send button

    def read_serial(self):
        while not self.stop_event.is_set():
            try:
                while self.serial_port and self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode("utf-8", errors="replace")
                    cleaned_line = line.strip().strip('\r\n').strip('\x00')
                    if cleaned_line == "STOP":
                        if self.ignore_stop_message and not self.profile_running:
                            self.ignore_stop_message = False  # Reset flag after ignoring one STOP
                        else:
                            self.stop_event.set()
                            self.profile_running = False
                            self.root.after(0, lambda: self.send_profile_button.config(text="Send Profile", style="SendProfile.TButton"))
                            self.root.after(0, lambda: self.send_button.config(state="normal"))  # Re-enable Send button
                            self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Received STOP command, transmission stopped.\n")
                    else:
                        match = re.search(r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", line)
                        if match:
                            inside_temp = float(match.group(1))
                            self.temp_queue.put(inside_temp)
                            self.current_temp = inside_temp
                            outside_temp = match.group(2)
                            set_inside_temp = match.group(3)
                            timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
                            display_line = f"{timestamp}Inside {inside_temp} °C, Outside {outside_temp} °C, Set {set_inside_temp} °C\n"
                            record_line = f"{timestamp}{inside_temp}, {outside_temp}, {set_inside_temp}\n"
                            self.display_output(display_line, record_line)
                time.sleep(0.005)
            except (serial.SerialException, IOError) as e:
                self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Error: Device disconnected ({str(e)})\n")
                self.root.after(0, self.disconnect_serial)
                break
            except Exception as e:
                self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Error: {str(e)})\n")
                break

    def send_command(self):
        if self.profile_running:
            self.stop_event.set()
            self.profile_running = False
            self.ignore_stop_message = True  # Set flag to ignore STOP message after manual stop
            self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Profile transmission stopped due to manual temperature send.\n")
            self.root.after(0, lambda: self.send_profile_button.config(text="Send Profile", style="SendProfile.TButton"))
            self.root.after(0, lambda: self.send_button.config(state="normal"))  # Re-enable Send button
            if self.profile_window and self.profile_window.winfo_exists():
                self.profile_window.focus_set()
                self.profile_window.lift()

        temperature = self.temperature_var.get()
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        command = f"{temperature:.1f}\n"
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.write(command.encode('utf-8'))
                self.serial_port.flush()
                self.display_output(f"{timestamp}Sent: {command}")
                self.current_setpoint = temperature
            else:
                messagebox.showerror("Error", "Serial port is not open.", parent=self.root)
                self.root.focus_set()
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send command: {str(e)}", parent=self.root)
            self.root.focus_set()

    def display_output(self, display_message, record_message=None):
        def update_text():
            try:
                self.text_area.config(state="normal")
                self.text_area.insert("end", display_message)
                self.text_area.see("end")
                self.text_area.config(state="disabled")
                if self.recording and self.record_file is not None:
                    try:
                        self.record_file.write(record_message if record_message else display_message)
                        self.record_file.flush()
                    except Exception as e:
                        self.recording = False
                        try:
                            self.record_file.close()
                        except Exception:
                            pass
                        self.record_file = None
                        self.record_button.config(text="Record", style="Record.TButton")
                        messagebox.showerror("File Error", f"Failed to write to file: {str(e)}", parent=self.root)
                        self.root.focus_set()
            except tk.TclError:
                pass
        self.root.after(0, update_text)

    def on_close(self):
        if self.recording and self.record_file is not None:
            try:
                self.record_file.close()
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to close recording file: {str(e)}", parent=self.root)
                self.root.focus_set()
            finally:
                self.record_file = None
        self.disconnect_serial()
        if self.profile_window:
            self.profile_window.destroy()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialMonitorApp(root)
    root.mainloop()