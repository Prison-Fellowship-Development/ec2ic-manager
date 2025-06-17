#!/usr/bin/env python3
"""
AWS RDP Connect - A tool to simplify RDP connections to AWS EC2 instances
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import threading
import json
import os
import sys
import random
import configparser
import time
from pathlib import Path
import platform

# Append AWS CLI path to environment
os.environ["PATH"] += os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin/"

class AwsRdpConnect:
    def __init__(self, root):
        self.root = root
        self.root.title("AWS RDP Connect")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)

        self.aws_profiles = []
        self.ec2_instances = []
        self.current_profile = None
        self.tunnel_process = None
        self.config_dir = os.path.join(str(Path.home()), ".aws_rdp_connect")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.settings = {
            "rdp_client": "",
            "default_profile": "",
            "saved_instances": {},
            "local_port_range": [9800, 9900]
        }

        # Load settings
        self.load_settings()

        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create controls frame
        self.controls_frame = ttk.LabelFrame(self.main_frame, text="Connection Settings", padding="10")
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)

        # AWS Profile selection
        ttk.Label(self.controls_frame, text="AWS Profile:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(self.controls_frame, textvariable=self.profile_var, state="readonly", width=30)
        self.profile_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_selected)

        # Refresh button
        self.refresh_button = ttk.Button(self.controls_frame, text="Refresh", command=self.refresh_profiles)
        self.refresh_button.grid(row=0, column=2, padx=5, pady=5)

        # Login button
        self.login_button = ttk.Button(self.controls_frame, text="Login", command=self.aws_sso_login)
        self.login_button.grid(row=0, column=3, padx=5, pady=5)

        # Instances frame
        self.instances_frame = ttk.LabelFrame(self.main_frame, text="EC2 Instances", padding="10")
        self.instances_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create a tree view for instances
        self.tree_columns = ("Name", "Instance ID", "State", "Type", "Private IP")
        self.tree = ttk.Treeview(self.instances_frame, columns=self.tree_columns, show="headings")

        for col in self.tree_columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        # Add scrollbars
        vsb = ttk.Scrollbar(self.instances_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.instances_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Position tree and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Configure grid weights
        self.instances_frame.grid_columnconfigure(0, weight=1)
        self.instances_frame.grid_rowconfigure(0, weight=1)

        # Buttons frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)

        # Load instances button
        self.load_button = ttk.Button(self.button_frame, text="Load Instances", command=self.load_instances)
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Connect button
        self.connect_button = ttk.Button(self.button_frame, text="Connect RDP", command=self.connect_rdp)
        self.connect_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Save instance button
        self.save_button = ttk.Button(self.button_frame, text="Save Instance", command=self.save_instance)
        self.save_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Settings button
        self.settings_button = ttk.Button(self.button_frame, text="Settings", command=self.open_settings)
        self.settings_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Initialize
        self.refresh_profiles()
        # Load saved instances on startup
        self.load_saved_instances()

        # Set default profile if available
        if self.settings["default_profile"] and self.settings["default_profile"] in self.aws_profiles:
            self.profile_var.set(self.settings["default_profile"])
            self.on_profile_selected(None)

    def load_settings(self):
        """Load settings from the config file"""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.settings = json.load(f)
            else:
                # First time setup, determine default RDP client
                self.detect_rdp_client()
                self.save_settings()
        except Exception as e:
            messagebox.showwarning("Settings Error", f"Failed to load settings: {str(e)}")

    def save_settings(self):
        """Save settings to the config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            messagebox.showwarning("Settings Error", f"Failed to save settings: {str(e)}")

    def detect_rdp_client(self):
        """Auto-detect the RDP client based on the platform"""
        system = platform.system()
        if system == "Windows":
            self.settings["rdp_client"] = "mstsc.exe"
        elif system == "Darwin":  # macOS
            # For macOS, just set the app name instead of the full path
            # Check for Microsoft Remote Desktop
            if os.path.exists("/Applications/Microsoft Remote Desktop.app"):
                self.settings["rdp_client"] = "Microsoft Remote Desktop"
            else:
                self.settings["rdp_client"] = ""
        else:  # Linux
            # Check for common RDP clients
            for client in ["rdesktop", "xfreerdp"]:
                try:
                    path = subprocess.check_output(["which", client], universal_newlines=True).strip()
                    if path:
                        self.settings["rdp_client"] = path
                        break
                except:
                    pass

    def refresh_profiles(self):
        """Refresh the AWS profiles."""
        self.aws_profiles = []
        self.status_var.set("Loading AWS profiles...")

        try:
            # Load AWS config
            aws_config = configparser.ConfigParser()
            aws_config_path = os.path.join(str(Path.home()), ".aws", "config")

            if os.path.exists(aws_config_path):
                aws_config.read(aws_config_path)

                for section in aws_config.sections():
                    if section.startswith("profile "):
                        profile_name = section[8:]  # Remove "profile " prefix
                        self.aws_profiles.append(profile_name)

            self.profile_combo['values'] = self.aws_profiles

            if self.aws_profiles:
                if self.profile_var.get() not in self.aws_profiles:
                    # If the current profile is no longer in the list (due to mode switch), default to the first one.
                    self.profile_var.set(self.aws_profiles[0])
                
                self.current_profile = self.profile_var.get()
                self.status_var.set(f"Loaded {len(self.aws_profiles)} AWS profiles")
            else:
                self.current_profile = None
                self.profile_var.set("")
                mode_text = "standard"
                self.status_var.set(f"No {mode_text} AWS profiles found. Check your AWS CLI configuration.")
        except Exception as e:
            self.status_var.set(f"Error loading profiles: {str(e)}")
            messagebox.showerror("Error", f"Failed to load AWS profiles: {str(e)}")


    def on_profile_selected(self, event):
        """Handle profile selection"""
        self.current_profile = self.profile_var.get()
        self.status_var.set(f"Selected profile: {self.current_profile}")

    def aws_sso_login(self):
        """Perform AWS SSO login."""
        if not self.current_profile:
            messagebox.showwarning("Warning", "Please select an AWS profile first")
            return

        cli_tool = "AWS SSO"
        self.status_var.set(f"Logging in with {cli_tool} using profile {self.current_profile}...")
        self.login_button.configure(state="disabled")

        def login_thread():
            command = []
            command = ["aws", "sso", "login", "--profile", self.current_profile]
            
            cli_name_for_error = "AWS CLI"

            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if result.returncode == 0:
                    self.root.after(0, lambda: self.status_var.set(f"{cli_tool} login successful"))
                else:
                    self.root.after(0, lambda: self.status_var.set(f"{cli_tool} login failed: {result.stderr.strip()}"))
                    self.root.after(0, lambda: messagebox.showerror("Login Failed", result.stderr.strip()))
            except FileNotFoundError:
                self.root.after(0, lambda: self.status_var.set(f"{cli_name_for_error} not found. Please ensure it's installed and in your PATH."))
                self.root.after(0, lambda: messagebox.showerror("Error", f"{cli_name_for_error} not found. Please ensure it's installed and in your PATH."))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"{cli_tool} login error: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Login Error", str(e)))
            finally:
                self.root.after(0, lambda: self.login_button.configure(state="normal"))

        # Run login in a separate thread to keep UI responsive
        threading.Thread(target=login_thread).start()

    def load_instances(self):
        """Load EC2 instances for the selected profile"""
        if not self.current_profile:
            messagebox.showwarning("Warning", "Please select an AWS profile first")
            return

        self.status_var.set(f"Loading instances for profile {self.current_profile}...")
        self.load_button.configure(state="disabled")

        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        def load_thread():
            command = []
            command = ["aws", "ec2", "describe-instances", "--profile", self.current_profile]

            # command = ["aws", "ec2", "describe-instances", "--region", "us-east-2", "--profile", self.current_profile]
            
            cli_name_for_error = "AWS CLI"

            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    instances = []

                    # Process instances
                    for reservation in data.get("Reservations", []):
                        for instance in reservation.get("Instances", []):
                            instance_id = instance.get("InstanceId", "")
                            instance_state = instance.get("State", {}).get("Name", "")
                            instance_type = instance.get("InstanceType", "")
                            private_ip = instance.get("PrivateIpAddress", "")

                            # Get the Name tag
                            name = ""
                            for tag in instance.get("Tags", []):
                                if tag.get("Key") == "Name":
                                    name = tag.get("Value", "")
                                    break

                            instances.append((name, instance_id, instance_state, instance_type, private_ip))

                    # Update UI from the main thread
                    self.root.after(0, lambda: self.update_instances_tree(instances))
                else:
                    self.root.after(0, lambda: self.status_var.set(f"Failed to load instances: {result.stderr.strip()}"))
                    self.root.after(0, lambda: messagebox.showerror("Error", result.stderr.strip()))
            except FileNotFoundError:
                self.root.after(0, lambda: self.status_var.set(f"{cli_name_for_error} not found. Please ensure it's installed and in your PATH."))
                self.root.after(0, lambda: messagebox.showerror("Error", f"{cli_name_for_error} not found. Please ensure it's installed and in your PATH."))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error loading instances: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self.load_button.configure(state="normal"))

        # Run in a separate thread
        threading.Thread(target=load_thread).start()

    def update_instances_tree(self, instances):
        """Update the treeview with instance data"""
        self.ec2_instances = instances

        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add instances to tree
        for instance in instances:
            self.tree.insert("", tk.END, values=instance)

        self.status_var.set(f"Loaded {len(instances)} EC2 instances")

    def get_selected_instance(self):
        """Get the selected instance from the tree"""
        selected_items = self.tree.selection()
        if not selected_items:
            return None

        values = self.tree.item(selected_items[0], "values")
        return values

    def load_saved_instances(self):
        """Load saved instances into the tree, associating them with their profile"""
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add saved instances to tree
        # Iterate through saved instances by profile
        for profile, instances in self.settings.get("saved_instances", {}).items():
             # Ensure the profile exists in the current AWS config before displaying
            if profile in self.aws_profiles:
                for instance in instances:
                    # Insert the instance into the treeview and add the profile as a tag
                    # We add the profile as a tag so we can retrieve it later when connecting
                    self.tree.insert("", tk.END, values=instance, tags=(profile,))
            else:
                print(f"Warning: Profile '{profile}' for saved instances not found in AWS config. Skipping.")


    def save_instance(self):
        """Save the selected instance for quick access"""
        selected_instance = self.get_selected_instance()
        if not selected_instance:
            messagebox.showwarning("Warning", "Please select an instance first")
            return

        if not self.current_profile:
            messagebox.showwarning("Warning", "Please select an AWS profile first")
            return

        # Initialize the profile's saved instances list if needed
        if self.current_profile not in self.settings["saved_instances"]:
            self.settings["saved_instances"][self.current_profile] = []

        # Check if already saved for this profile
        if selected_instance in self.settings["saved_instances"][self.current_profile]:
            messagebox.showinfo("Info", "This instance is already saved for the current profile.")
            return

        # Add to saved instances for the current profile
        self.settings["saved_instances"][self.current_profile].append(selected_instance)
        self.save_settings()

        messagebox.showinfo("Success", f"Instance {selected_instance[0]} ({selected_instance[1]}) saved for profile {self.current_profile}")

        # Refresh the treeview to show the newly saved instance with its tag
        self.load_saved_instances()


    def connect_rdp(self):
        """Connect to the selected instance via RDP"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select an instance first")
            return

        selected_item = selected_items[0]
        values = self.tree.item(selected_item, "values")
        tags = self.tree.item(selected_item, "tags") # Get tags associated with the tree item

        if not values:
            messagebox.showwarning("Warning", "Could not retrieve instance details")
            return

        selected_instance = values

        instance_id = selected_instance[1]
        instance_name = selected_instance[0]

        # Determine the profile to use for connection
        # If the item has a tag, it's a saved instance, use the tagged profile
        # Otherwise, use the currently selected profile
        connection_profile = self.current_profile # Default to current profile
        if tags:
            # Assuming the first tag is the profile name for saved instances
            saved_profile = tags[0] if tags else None
            if saved_profile and saved_profile in self.aws_profiles: # Ensure the saved profile is still valid
                 connection_profile = saved_profile
            elif saved_profile:
                 messagebox.showwarning("Profile Not Found", f"Saved profile '{saved_profile}' not found in your AWS configuration. Using current profile '{self.current_profile}' instead.")


        # Check if the connection profile is different from the current profile
        # If so, switch profile and initiate SSO login
        if connection_profile and connection_profile != self.current_profile:
            messagebox.showinfo("Profile Switch", f"Switching to profile: {connection_profile} for connection.")
            self.profile_var.set(connection_profile) # Update the combobox
            self.current_profile = connection_profile # Update the current profile
            # Initiate SSO login for the new profile
            self.aws_sso_login()
            # Add a small delay to allow the login process to start.
            # WARNING: This is a simple delay. A more robust solution would wait for login completion.
            time.sleep(5) # Giving 5 seconds for login process initiation

        # Ensure a profile is selected before proceeding
        if not self.current_profile:
             messagebox.showwarning("Warning", "No AWS profile selected or available after potential switch.")
             return

        # Check RDP client - but on macOS, we'll try multiple methods even if the path is not found
        system = platform.system()
        if not self.settings["rdp_client"]:
            messagebox.showerror("Error", "RDP client not configured. Please update in Settings.")
            self.open_settings()
            return

        # For non-Mac OS, check if the file exists
        if system != "Darwin" and not os.path.exists(self.settings["rdp_client"]):
            messagebox.showerror("Error", "RDP client not found. Please update path in Settings.")
            self.open_settings()
            return

        # Generate a random local port within the specified range
        local_port = random.randint(
            self.settings["local_port_range"][0],
            self.settings["local_port_range"][1]
        )

        self.status_var.set(f"Connecting to {instance_name} ({instance_id}) using profile {self.current_profile}...")

        # Create and manage the tunnel in a separate thread
        # Pass the current profile to the tunnel setup
        tunnel_thread = threading.Thread(
            target=self.setup_and_connect,
            args=(instance_id, local_port, self.current_profile) # Pass the profile
        )
        tunnel_thread.daemon = True
        tunnel_thread.start()


    def setup_and_connect(self, instance_id, local_port, profile_to_use):
        """Set up the tunnel and launch RDP client using the specified profile"""
        try:
            # Set up the tunnel
            self.root.after(0, lambda: self.status_var.set(f"Setting up tunnel to {instance_id} on port {local_port} using profile {profile_to_use}..."))

            command = []

            command = [
                "aws", "ec2-instance-connect", "open-tunnel",
                "--instance-id", instance_id,
                "--remote-port", "3389",
                "--local-port", str(local_port),
                "--profile", profile_to_use # Use the specified profile
            ]
            
            # command = [
            #     "aws", "ec2-instance-connect", "open-tunnel",
            #     "--instance-id", instance_id,
            #     "--remote-port", "3389",
            #     "--local-port", str(local_port),
            #     "--region", "us-east-2",
            #     "--profile", profile_to_use # Use the specified profile
            # ]

            # Start the tunnel process
            self.tunnel_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Give the tunnel time to initialize
            time.sleep(2)

            # Check if tunnel is running
            if self.tunnel_process.poll() is not None:
                stderr = self.tunnel_process.stderr.read().decode('utf-8').strip()
                self.root.after(0, lambda: self.status_var.set(f"Tunnel setup failed: {stderr}"))
                self.root.after(0, lambda: messagebox.showerror("Tunnel Error", stderr))
                return

            # Launch RDP client
            self.root.after(0, lambda: self.status_var.set("Launching RDP client..."))

            # Launch based on platform
            system = platform.system()
            if system == "Windows":
                # Create a temporary RDP file
                temp_dir = os.environ.get("TEMP", os.path.expanduser("~")) # Use user home as fallback
                rdp_file = os.path.join(temp_dir, f"aws_connect_{instance_id}.rdp")
                try:
                    with open(rdp_file, "w") as f:
                        f.write(f"full address:s:localhost:{local_port}\n")
                        f.write("prompt for credentials:i:1\n")

                    # Launch mstsc with the RDP file
                    subprocess.Popen([self.settings["rdp_client"], rdp_file])
                except Exception as file_error:
                    self.root.after(0, lambda: self.status_var.set(f"Error creating RDP file: {str(file_error)}"))
                    self.root.after(0, lambda: messagebox.showerror("File Error", f"Could not create temporary RDP file: {str(file_error)}"))


            elif system == "Darwin":  # macOS
                # For Microsoft Remote Desktop on macOS
                # Create a temporary RDP file with Mac-friendly .rdp extension
                # Use a standard temp directory or user's home if needed
                temp_dir = os.path.join(os.path.expanduser("~"), ".aws_rdp_connect_temp")
                os.makedirs(temp_dir, exist_ok=True)
                rdp_file = os.path.join(temp_dir, f"aws_connect_{instance_id}.rdp")

                try:
                    with open(rdp_file, "w") as f:
                        f.write(f"full address:s:localhost:{local_port}\n")
                        f.write("prompt for credentials:i:1\n")

                    # Try several approaches to launch Microsoft Remote Desktop
                    try:
                        # Method 1: Use open command with the RDP file
                        subprocess.Popen(["open", rdp_file])
                    except Exception as e1:
                        self.root.after(0, lambda: self.status_var.set(f"Method 1 failed: {str(e1)}, trying method 2..."))
                        try:
                            # Method 2: Open the app directly then the file
                            subprocess.Popen(["open", "-a", "Microsoft Remote Desktop", rdp_file])
                        except Exception as e2:
                            self.root.after(0, lambda: self.status_var.set(f"Method 2 failed: {str(e2)}, trying method 3..."))
                            try:
                                # Method 3: Use the direct URL format
                                subprocess.Popen([
                                    "open",
                                    f"rdp://full%20address=s:localhost:{local_port}"
                                ])
                            except Exception as e3:
                                self.root.after(0, lambda: self.status_var.set(f"All RDP launch methods failed"))
                                self.root.after(0, lambda: messagebox.showinfo(
                                    "Manual Connection Required",
                                    f"Please open your RDP client manually and connect to localhost:{local_port}"
                                ))
                except Exception as file_error:
                    self.root.after(0, lambda: self.status_var.set(f"Error creating RDP file: {str(file_error)}"))
                    self.root.after(0, lambda: messagebox.showerror("File Error", f"Could not create temporary RDP file: {str(file_error)}"))


            else:  # Linux
                # For rdesktop or xfreerdp
                try:
                    if "rdesktop" in self.settings["rdp_client"]:
                        subprocess.Popen([self.settings["rdp_client"], f"localhost:{local_port}"])
                    elif "xfreerdp" in self.settings["rdp_client"]:
                        subprocess.Popen([self.settings["rdp_client"], f"/v:localhost:{local_port}"])
                    else:
                        # Generic approach
                        subprocess.Popen([self.settings["rdp_client"], f"localhost:{local_port}"])
                except FileNotFoundError:
                    self.root.after(0, lambda: self.status_var.set(f"RDP client not found at: {self.settings['rdp_client']}"))
                    self.root.after(0, lambda: messagebox.showerror("Error", f"RDP client not found at: {self.settings['rdp_client']}. Please check settings."))


            self.root.after(0, lambda: self.status_var.set(f"Connected to {instance_id} on port {local_port}"))

        except FileNotFoundError:
            cli_name_for_error = "AWS CLI"
            self.root.after(0, lambda: self.status_var.set(f"{cli_name_for_error} not found. Please ensure it's installed and in your PATH."))
            self.root.after(0, lambda: messagebox.showerror("Error", f"{cli_name_for_error} not found. Please ensure it's installed and in your PATH."))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Connection error: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("Connection Error", str(e)))

            # Clean up if necessary
            if self.tunnel_process and self.tunnel_process.poll() is None:
                self.tunnel_process.terminate()
                self.tunnel_process = None

    def open_settings(self):
        """Open the settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x300")
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Create a notebook for settings tabs
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # General settings tab
        general_frame = ttk.Frame(notebook, padding="10")
        notebook.add(general_frame, text="General")

        # RDP Client
        ttk.Label(general_frame, text="RDP Client Path:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        rdp_client_var = tk.StringVar(value=self.settings.get("rdp_client", ""))
        rdp_client_entry = ttk.Entry(general_frame, textvariable=rdp_client_var, width=40)
        rdp_client_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        # Browse button
        browse_button = ttk.Button(general_frame, text="Browse", command=lambda: self.browse_file(rdp_client_var))
        browse_button.grid(row=0, column=2, padx=5, pady=5)

        # Default profile
        ttk.Label(general_frame, text="Default Profile:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        default_profile_var = tk.StringVar(value=self.settings.get("default_profile", ""))
        default_profile_combo = ttk.Combobox(general_frame, textvariable=default_profile_var, values=self.aws_profiles, state="readonly")
        default_profile_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        # Port range
        ttk.Label(general_frame, text="Local Port Range:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        port_frame = ttk.Frame(general_frame)
        port_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        min_port_var = tk.IntVar(value=self.settings.get("local_port_range", [9800, 9900])[0])
        max_port_var = tk.IntVar(value=self.settings.get("local_port_range", [9800, 9900])[1])

        ttk.Label(port_frame, text="Min:").pack(side=tk.LEFT)
        min_port_entry = ttk.Entry(port_frame, textvariable=min_port_var, width=6)
        min_port_entry.pack(side=tk.LEFT, padx=2)

        ttk.Label(port_frame, text="Max:").pack(side=tk.LEFT, padx=(10, 0))
        max_port_entry = ttk.Entry(port_frame, textvariable=max_port_var, width=6)
        max_port_entry.pack(side=tk.LEFT, padx=2)

        # Buttons frame
        buttons_frame = ttk.Frame(settings_window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        # Save button
        save_button = ttk.Button(buttons_frame, text="Save", command=lambda: self.save_settings_dialog(
            rdp_client_var.get(),
            default_profile_var.get(),
            min_port_var.get(),
            max_port_var.get(),
            settings_window
        ))
        save_button.pack(side=tk.RIGHT, padx=5)

        # Cancel button
        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=settings_window.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)

        # Configure grid weights for general_frame
        general_frame.grid_columnconfigure(1, weight=1)


    def browse_file(self, var):
        """Browse for a file and update the given StringVar"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename()
        if filename:
            var.set(filename)

    def save_settings_dialog(self, rdp_client, default_profile, min_port, max_port, window):
        """Save settings from the dialog"""
        try:
            # Validate port range
            if min_port < 1024 or min_port > 65535 or max_port < 1024 or max_port > 65535 or min_port >= max_port:
                messagebox.showerror("Error", "Invalid port range. Please use ports between 1024 and 65535, with min < max.")
                return

            # Update settings
            self.settings["rdp_client"] = rdp_client
            self.settings["default_profile"] = default_profile
            self.settings["local_port_range"] = [min_port, max_port]

            # Save to file
            self.save_settings()

            # Close the dialog
            window.destroy()

            self.status_var.set("Settings saved successfully")

            # Update the main window's profile combo box if profiles were loaded
            if self.aws_profiles:
                self.profile_combo['values'] = self.aws_profiles
                # If the default profile was set, update the selection
                if self.settings["default_profile"] in self.aws_profiles:
                    self.profile_var.set(self.settings["default_profile"])
                    self.current_profile = self.settings["default_profile"]
                # If the current selected profile is no longer valid, default to the first
                elif self.profile_var.get() not in self.aws_profiles:
                     self.profile_var.set(self.aws_profiles[0])
                     self.current_profile = self.aws_profiles[0]


        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

def main():
    root = tk.Tk()
    app = AwsRdpConnect(root)
    root.mainloop()

    # Cleanup on exit
    if app.tunnel_process and app.tunnel_process.poll() is None:
        try:
            app.tunnel_process.terminate()
        except Exception as e:
            print(f"Error terminating tunnel process: {e}")


if __name__ == "__main__":
    main()