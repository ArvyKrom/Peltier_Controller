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

class SerialMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Monitor")

        self.serial_port = None
        self.read_thread = None
        self.stop_event = threading.Event()
        self.last_port_list = []  # Track last known ports
        self.recording = False  # Track recording state
        self.record_file = None  # File handle for recording
        self.record_file_path = None  # Store the file path for recording
        self.profile_thread = None  # Thread for profile sending
        self.temp_queue = queue.Queue()  # Queue for temperature updates from read_serial
        self.current_temp = None  # Current temperature from serial input
        self.current_setpoint = None  # Current setpoint being sent

        self.setup_ui()
        self.update_ports()
        self.refresh_ports_periodically()

        # Prevent window resizing
        self.root.resizable(False, False)

    def setup_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.grid()

        # Section 1: COM Port and Buttons
        ttk.Label(frame, text="COM Port:").grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar()
        self.port_menu = ttk.Combobox(frame, textvariable=self.port_var, width=20, state="readonly")
        self.port_menu.grid(row=0, column=1, sticky="w")

        self.connect_button = ttk.Button(frame, text="Connect", command=self.connect_serial)
        self.connect_button.grid(row=0, column=2, padx=5)

        self.disconnect_button = ttk.Button(frame, text="Disconnect", command=self.disconnect_serial, state="disabled")
        self.disconnect_button.grid(row=0, column=3, padx=5)

        # Separator between Section 1 and Section 2
        separator1 = ttk.Separator(frame, orient="horizontal")
        separator1.grid(row=1, column=0, columnspan=5, sticky="ew", pady=5)

        # Section 2: Terminal, Record Button, and View Button
        self.text_area = tk.Text(frame, width=60, height=20, wrap="word")
        self.text_area.grid(row=2, column=0, columnspan=4, pady=10, padx=(0, 5))
        self.text_area.config(state="disabled")

        # Custom style for Record and View buttons with adjusted font
        style = ttk.Style()
        style.configure("Record.TButton", font=("Helvetica", 12))

        # Record button with original padding
        self.record_button = ttk.Button(
            frame,
            text="Record",
            command=self.toggle_recording,
            width=10,
            style="Record.TButton"
        )
        self.record_button.grid(row=2, column=4, padx=(0, 50), pady=(0, 125))

        # View button (same style as Record button)
        self.view_button = ttk.Button(
            frame,
            text="View",
            command=self.view_recording,
            width=10,
            style="Record.TButton"
        )
        self.view_button.grid(row=2, column=4, padx=(0, 50), pady=(0, 0))

        # Separator between Section 2 and Section 3
        separator2 = ttk.Separator(frame, orient="horizontal")
        separator2.grid(row=3, column=0, columnspan=5, sticky="ew", pady=5)

        # Section 3: Temperature Controls
        ttk.Label(frame, text="Temperature (°C):").grid(row=4, column=0, sticky="e", pady=5)
        self.temperature_var = tk.DoubleVar()
        self.temperature_slider = ttk.Scale(
            frame,
            from_=5.0,
            to=70.0,
            orient="horizontal",
            variable=self.temperature_var,
            length=400,
            command=lambda x: self.update_temperature_from_slider(x)
        )
        self.temperature_slider.grid(row=4, column=1, columnspan=2, pady=5, padx=(0, 10))
        self.temperature_var.set(5.0)

        self.temperature_values = [str(i) for i in range(5, 71, 5)]
        self.temperature_combobox_var = tk.StringVar()
        self.temperature_combobox = ttk.Combobox(
            frame,
            textvariable=self.temperature_combobox_var,
            values=[f"{val} °C" for val in self.temperature_values],
            width=10
        )
        self.temperature_combobox.grid(row=4, column=3, sticky="w", padx=(0, 5))
        self.temperature_combobox_var.set("5 °C")
        self.temperature_combobox.bind("<Return>", self.update_temperature_from_combobox)
        self.temperature_combobox.bind("<FocusOut>", self.update_temperature_from_combobox)
        self.temperature_combobox.bind("<<ComboboxSelected>>", self.update_temperature_from_combobox)

        self.send_button = ttk.Button(frame, text="Send", command=self.send_command)
        self.send_button.grid(row=4, column=4, padx=5, pady=5)

        # Advanced Temperature Profile button
        self.advanced_profile_button = ttk.Button(
            frame,
            text="Advanced Temperature Profile",
            command=self.open_advanced_profile_window
        )
        self.advanced_profile_button.grid(row=5, column=4, padx=5, pady=5)

    def open_advanced_profile_window(self):
        profile_window = tk.Toplevel(self.root)
        profile_window.title("Advanced Temperature Profile")
        profile_window.resizable(True, True)

        control_frame = ttk.Frame(profile_window, padding=10)
        control_frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(control_frame, text="Time (s):").grid(row=0, column=0, sticky="e", pady=5)
        self.time_var = tk.StringVar()
        time_entry = ttk.Entry(control_frame, textvariable=self.time_var, width=10)
        time_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="Temperature (°C):").grid(row=1, column=0, sticky="e", pady=5)
        self.profile_temp_var = tk.StringVar()
        temp_entry = ttk.Entry(control_frame, textvariable=self.profile_temp_var, width=10)
        temp_entry.grid(row=1, column=1, padx=5, pady=5)

        add_button = ttk.Button(
            control_frame,
            text="Add Point",
            command=lambda: self.add_profile_point(profile_window)
        )
        add_button.grid(row=2, column=0, columnspan=2, pady=10)

        self.profile_listbox = tk.Listbox(control_frame, width=30, height=10)
        self.profile_listbox.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        delete_button = ttk.Button(
            control_frame,
            text="Delete Selected",
            command=lambda: self.delete_profile_point(profile_window)
        )
        delete_button.grid(row=4, column=0, columnspan=2, pady=5)

        save_button = ttk.Button(
            control_frame,
            text="Save Profile",
            command=self.save_profile
        )
        save_button.grid(row=5, column=0, columnspan=2, pady=5)

        load_button = ttk.Button(
            control_frame,
            text="Load Profile",
            command=lambda: self.load_profile(profile_window)
        )
        load_button.grid(row=6, column=0, columnspan=2, pady=5)

        send_profile_button = ttk.Button(
            control_frame,
            text="Send Profile",
            command=self.start_profile_sending
        )
        send_profile_button.grid(row=7, column=0, columnspan=2, pady=5)

        self.profile_points = []

        self.profile_fig = plt.figure(figsize=(6, 4))
        self.profile_ax = self.profile_fig.add_subplot(111)
        self.profile_ax.set_title("Temperature Profile")
        self.profile_ax.set_xlabel("Time (s)")
        self.profile_ax.set_ylabel("Temperature (°C)")
        self.profile_ax.grid(True)
        self.profile_fig.tight_layout()

        self.profile_canvas = FigureCanvasTkAgg(self.profile_fig, master=profile_window)
        self.profile_canvas.draw()
        self.profile_canvas.get_tk_widget().grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        toolbar = NavigationToolbar2Tk(self.profile_canvas, profile_window)
        toolbar.update()
        toolbar.grid(row=1, column=1, pady=5, sticky="ew")

        close_button = ttk.Button(
            profile_window,
            text="Close",
            command=lambda: [plt.close(self.profile_fig), profile_window.destroy()]
        )
        close_button.grid(row=2, column=1, pady=10)

        profile_window.grid_columnconfigure(0, weight=1)
        profile_window.grid_columnconfigure(1, weight=2)
        profile_window.grid_rowconfigure(0, weight=1)

        self.update_profile_graph()

    def add_profile_point(self, profile_window):
        try:
            time_str = self.time_var.get().strip()
            temp_str = self.profile_temp_var.get().strip()
            if not time_str or not temp_str:
                messagebox.showerror("Error", "Please enter both time and temperature.")
                return
            time = float(time_str)
            temperature = float(temp_str)
            if time < 0:
                messagebox.showerror("Error", "Time cannot be negative.")
                return
            if not (5 <= temperature <= 70):
                messagebox.showerror("Error", "Temperature must be between 5 and 70 °C.")
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
            messagebox.showerror("Error", "Please enter valid numbers for time and temperature.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add point: {str(e)}")

    def update_profile_graph(self):
        try:
            self.profile_ax.clear()
            self.profile_ax.set_title("Temperature Profile and Sent Setpoints")
            self.profile_ax.set_xlabel("Time (s)")
            self.profile_ax.set_ylabel("Temperature (°C)")
            self.profile_ax.grid(True)

            if self.profile_points:
                times, temps = zip(*self.profile_points)
                self.profile_ax.plot(times, temps, marker='o', linestyle='-', color='blue', label='Intended Profile')

                lag_offset = 150.0
                total_time = self.profile_points[-1][0]
                lagged_times = list(range(0, int(total_time) + 1))
                lagged_temps = []
                for t in lagged_times:
                    if t == 0:
                        temp = self.profile_points[0][1]
                    else:
                        temp = self.interpolate_temperature(t + lag_offset)
                    lagged_temps.append(temp)
                self.profile_ax.plot(
                    lagged_times,
                    lagged_temps,
                    linestyle='--',
                    color='orange',
                    label='Sent Setpoints (150s lag)'
                )

            else:
                self.profile_ax.plot([], [], marker='o', linestyle='-', color='blue', label='Intended Profile')

            self.profile_ax.set_xlim(-10, 100) if not self.profile_points else self.profile_ax.set_xlim(-10, max([t for t, _ in self.profile_points]) + 10)
            self.profile_ax.set_ylim(0, 80) if not self.profile_points else self.profile_ax.set_ylim(min([temp for _, temp in self.profile_points]) - 5, max([temp for _, temp in self.profile_points]) + 5)
            self.profile_ax.legend()
            self.profile_fig.tight_layout()
            self.profile_canvas.draw()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update graph: {str(e)}")

    def save_profile(self):
        if not self.profile_points:
            messagebox.showinfo("Info", "No profile points to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save temperature profile"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for time, temp in self.profile_points:
                    f.write(f"{time},{temp}\n")
            messagebox.showinfo("Success", "Profile saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile: {str(e)}")

    def load_profile(self, profile_window):
        file_path = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Load temperature profile"
        )
        if not file_path:
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
            messagebox.showinfo("Success", "Profile loaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {str(e)}")
            self.profile_points = []
            self.profile_listbox.delete(0, tk.END)
            self.update_profile_graph()

    def start_profile_sending(self):
        if self.profile_thread and self.profile_thread.is_alive():
            messagebox.showinfo("Info", "Profile sending is already in progress.")
            return

        if not self.profile_points:
            messagebox.showinfo("Info", "No profile points to send.")
            return

        if not self.serial_port or not self.serial_port.is_open:
            messagebox.showerror("Error", "Serial port is not open.")
            return

        self.stop_event.clear()
        self.profile_thread = threading.Thread(target=self.send_profile)
        self.profile_thread.daemon = True
        self.profile_thread.start()

    def send_profile(self):
        try:
            self.profile_points.sort(key=lambda x: x[0])
            total_time = self.profile_points[-1][0]
            current_time = 0.0
            first_point_sent = False
            lag_offset = 150.0

            while current_time <= total_time and not self.stop_event.is_set():
                if not first_point_sent:
                    target_temp = self.profile_points[0][1]
                    temp = target_temp
                else:
                    temp = self.interpolate_temperature(current_time + lag_offset)

                timestamp = datetime.datetime.now().strftime('[%H:%M:%S] ')
                command = f"{temp:.1f}\n"

                if not first_point_sent:
                    if self.current_setpoint != temp:
                        self.display_output(f"{timestamp}Sending first point: {command} (Waiting for {target_temp}°C)\n")
                        self.serial_port.write(command.encode('utf-8'))
                        self.current_setpoint = temp
                        if self.current_temp is not None:
                            if self.current_temp <= target_temp:
                                while self.current_temp < target_temp and not self.stop_event.is_set():
                                    time.sleep(0.5)
                            else:
                                while self.current_temp > target_temp and not self.stop_event.is_set():
                                    time.sleep(0.5)
                        first_point_sent = True
                        self.display_output(f"{timestamp}First point reached {self.current_temp}°C, continuing profile.\n")
                else:
                    if self.current_setpoint != temp:
                        self.serial_port.write(command.encode('utf-8'))
                        self.display_output(f"{timestamp}Sent: {command}")
                        self.current_setpoint = temp

                time.sleep(1)
                current_time += 1.0

                if current_time + lag_offset > total_time:
                    self.display_output(f"{timestamp}Profile transmission completed (with lag compensation).\n")
                    break

            self.stop_event.clear()
        except Exception as e:
            self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Send Error: {str(e)}\n")
        finally:
            self.stop_event.clear()

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
            messagebox.showinfo("Info", "Please select a point to delete.")
            return
        index = selection[0]
        del self.profile_points[index]
        self.profile_listbox.delete(0, tk.END)
        for time, temp in self.profile_points:
            self.profile_listbox.insert(tk.END, f"Time: {time:.1f}s, Temp: {temp:.1f}°C")
        self.update_profile_graph()

    def toggle_recording(self):
        if not self.recording:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Select file to save terminal recording"
            )
            if not file_path:
                return
            try:
                self.record_file = open(file_path, "a", encoding="utf-8")
                self.record_file_path = file_path
                self.recording = True
                self.record_button.config(text="Stop Recording")
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to open file for recording: {str(e)}")
                self.recording = False
                self.record_file = None
        else:
            if self.record_file is not None:
                try:
                    self.record_file.close()
                except Exception as e:
                    messagebox.showerror("File Error", f"Failed to close recording file: {str(e)}")
                finally:
                    self.record_file = None
            self.recording = False
            self.record_button.config(text="Record")

    def view_recording(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Select recording file to view"
        )
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
                messagebox.showinfo("No Data", "No valid temperature data found in the file.")
                view_window.destroy()
                return

            start_time = timestamps[0]
            relative_times = [(t - start_time).total_seconds() for t in timestamps]

            profile_times = []
            profile_temps = []
            profile_start_time = 0.0
            if messagebox.askyesno("Load Profile", "Would you like to load a thermal profile to overlay on the graph?"):
                profile_path = filedialog.askopenfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                    title="Select thermal profile file"
                )
                if profile_path:
                    try:
                        start_time_input = simpledialog.askstring(
                            "Profile Start Time",
                            "Enter the profile start time (seconds) relative to the recording start:",
                            parent=view_window
                        )
                        if start_time_input is None:
                            raise ValueError("Profile start time input cancelled.")
                        try:
                            profile_start_time = float(start_time_input)
                            if profile_start_time < 0:
                                raise ValueError("Start time cannot be negative.")
                        except ValueError as e:
                            raise ValueError(f"Invalid start time: {str(e)}")

                        with open(profile_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                time, temp = map(float, line.split(","))
                                if time < 0:
                                    raise ValueError("Time cannot be negative.")
                                if not (5 <= temp <= 70):
                                    raise ValueError("Temperature must be between 5 and 70 °C.")
                                shifted_time = time + profile_start_time
                                if shifted_time < 0:
                                    raise ValueError("Shifted time cannot be negative.")
                                profile_times.append(shifted_time)
                                profile_temps.append(temp)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to load profile: {str(e)}")
                        profile_times = []
                        profile_temps = []

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.plot(relative_times, inside_temps, linestyle='-', label='Inside')
            ax.plot(relative_times, outside_temps, linestyle='-', label='Outside')
            if set_inside_temps:
                ax.plot(relative_times, set_inside_temps, linestyle='-', label='Set')
            if profile_times and profile_temps:
                ax.plot(
                    profile_times,
                    profile_temps,
                    linestyle='--',
                    color='red',
                    marker='o',
                    label=f'Profile (start t={profile_start_time:.1f}s)'
                )
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
            messagebox.showerror("Error", f"Failed to process file: {str(e)}")
            view_window.destroy()

    def update_temperature_from_slider(self, value):
        temp = round(float(value) / 0.1) * 0.1
        temp = round(temp, 1)
        temp = max(5.0, min(70.0, temp))
        self.temperature_var.set(temp)
        self.temperature_combobox_var.set(f"{temp} °C")

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
            messagebox.showerror("Error", "Please select a COM port.")
            return

        self.disconnect_serial()

        try:
            self.serial_port = serial.Serial(port, 115200, timeout=1)
            self.root.after(0, lambda: self.connect_button.config(state="disabled"))
            self.root.after(0, lambda: self.disconnect_button.config(state="normal"))
            self.stop_event.clear()
            self.read_thread = threading.Thread(target=self.read_serial)
            self.read_thread.daemon = True
            self.read_thread.start()
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def disconnect_serial(self):  # Fixed: Corrected name from 'contestants_serial' and indentation
        self.stop_event.set()
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1)
        if self.profile_thread and self.profile_thread.is_alive():
            self.profile_thread.join(timeout=1)
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        self.serial_port = None
        self.read_thread = None
        self.profile_thread = None
        self.current_temp = None
        self.current_setpoint = None
        self.temp_queue.queue.clear()
        self.root.after(0, lambda: self.connect_button.config(state="normal"))
        self.root.after(0, lambda: self.disconnect_button.config(state="disabled"))

    def read_serial(self):
        while not self.stop_event.is_set():
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode("utf-8", errors="replace").strip()
                    if line:  # Check if line is not empty
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
                else:
                    # Small sleep to prevent CPU overuse when no data is available
                    time.sleep(0.01)
            except (serial.SerialException, IOError) as e:
                self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Error: Device disconnected ({str(e)})\n")
                self.root.after(0, self.disconnect_serial)
                break
            except Exception as e:
                self.display_output(f"{datetime.datetime.now().strftime('[%H:%M:%S] ')}Error: {str(e)})\n")
                break

    def send_command(self):
        temperature = self.temperature_var.get()
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        command = f"{temperature:.1f}\n"
        try:
            if self.serial_port and self.serial_port.is_open:
                if self.current_setpoint != temperature:
                    self.serial_port.write(command.encode('utf-8'))
                    self.display_output(f"{timestamp}Sent: {command}")
                    self.current_setpoint = temperature
            else:
                messagebox.showerror("Error", "Serial port is not open.")
        except Exception as e:
            messagebox.showerror("Send Error", f"Failed to send command: {str(e)}")

    def display_output(self, display_message, record_message=None):
        def update_text():
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
                    self.record_button.config(text="Record")
                    messagebox.showerror("File Error", f"Failed to write to file: {str(e)}")
        self.root.after(0, update_text)

    def on_close(self):
        if self.recording and self.record_file is not None:
            try:
                self.record_file.close()
            except Exception as e:
                messagebox.showerror("File Error", f"Failed to close recording file: {str(e)}")
            finally:
                self.record_file = None
        self.disconnect_serial()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()