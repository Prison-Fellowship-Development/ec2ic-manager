#!/usr/bin/env python3
"""
AWS Connect - A cross-platform GUI tool for managing AWS EC2 and RDS connections.

This application provides a unified interface for connecting to AWS resources using:
- RDP connections to Windows EC2 instances
- SSH connections to Linux EC2 instances  
- SSM tunneling for EC2-hosted databases
- RDS database tunneling through bastion hosts

Features:
- Multi-region support (configurable)
- AWS SSO integration with auto-login
- Progress indicators for long operations
- Port collision detection and management
- Multiple simultaneous tunnel tracking
- Cross-platform support (macOS, Windows, Linux)

Architecture:
- SettingsManager: Configuration and preferences handling
- AwsResourceManager: AWS API interactions and resource discovery
- ConnectionManager: Connection logic and tunnel management
- MainWindow: User interface and event handling
- ProgressDialog: Progress indication for long operations

Requirements:
- Python 3.7+
- tkinter (usually included with Python)
- AWS CLI v2
- SSM Session Manager plugin (for tunneling)

Author: AWS Connect Development Team
Version: 1.3.0
License: MIT
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
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
import socket

# Configuration Constants
DEFAULT_PORT_RANGE = [9800, 9900]  # Default local port range for tunnels
DEFAULT_REGIONS = ["us-east-1", "us-east-2"]  # Default AWS regions to scan
CONFIG_DIR_NAME = ".aws_rdp_connect"  # Configuration directory name
CONFIG_FILE_NAME = "config.json"  # Configuration file name

# Append AWS CLI path to environment for macOS Homebrew and standard installations
os.environ["PATH"] += os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin/"


class ProgressDialog:
    """
    A modal progress dialog for displaying progress of long-running operations.
    
    This class creates a centered, modal dialog window that shows:
    - A progress bar with percentage completion
    - Status text describing the current operation
    - Detail text with additional information
    
    The dialog prevents user interaction with the parent window until closed.
    
    Attributes:
        parent (tk.Widget): Parent window for the dialog
        total_steps (int): Total number of steps for the operation
        current_step (int): Current step number (0-based)
        dialog (tk.Toplevel): The dialog window
        progress_var (tk.DoubleVar): Variable controlling progress bar
        status_label (ttk.Label): Label showing main status text
        detail_label (ttk.Label): Label showing detail text
    """
    
    def __init__(self, parent, title="Loading...", total_steps=1):
        """
        Initialize the progress dialog.
        
        Args:
            parent (tk.Widget): Parent window for the dialog
            title (str, optional): Dialog window title. Defaults to "Loading...".
            total_steps (int, optional): Total number of steps. Defaults to 1.
        """
        self.parent = parent
        self.total_steps = total_steps
        self.current_step = 0
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x120")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (120 // 2)
        self.dialog.geometry(f"400x120+{x}+{y}")
        
        # Create widgets
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_label = ttk.Label(main_frame, text="Initializing...", font=("", 10))
        self.status_label.pack(pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=100, 
            length=350,
            mode='determinate'
        )
        self.progress_bar.pack(pady=(0, 10))
        
        self.detail_label = ttk.Label(main_frame, text="", font=("", 8), foreground="gray")
        self.detail_label.pack()
        
        # Make dialog modal
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # Disable close button
        
    def update_progress(self, step, status_text, detail_text=""):
        """
        Update the progress bar and status text.
        
        Args:
            step (int): Current step number (1-based)
            status_text (str): Main status message to display
            detail_text (str, optional): Additional detail text. Defaults to "".
        """
        self.current_step = step
        progress_percent = (step / self.total_steps) * 100
        
        self.progress_var.set(progress_percent)
        self.status_label.config(text=status_text)
        self.detail_label.config(text=detail_text)
        
        self.dialog.update_idletasks()
        
    def increment_progress(self, status_text, detail_text=""):
        """
        Increment progress by one step and update display.
        
        Args:
            status_text (str): Main status message to display
            detail_text (str, optional): Additional detail text. Defaults to "".
        """
        self.update_progress(self.current_step + 1, status_text, detail_text)
        
    def close(self):
        """
        Close the progress dialog and release resources.
        
        This method safely closes the dialog window and releases the grab,
        allowing user interaction with the parent window to resume.
        """
        try:
            self.dialog.grab_release()
            self.dialog.destroy()
        except:
            pass


class SettingsManager:
    """
    Manages application configuration and user settings.
    
    This class handles loading, saving, and managing all application settings
    including client paths, profiles, port ranges, and AWS regions. Settings
    are stored in a JSON file in the user's home directory.
    
    The settings file is located at: ~/.aws_rdp_connect/config.json
    
    Default Settings:
        - rdp_client: Auto-detected RDP client path
        - ssh_client: Auto-detected SSH client path  
        - default_profile: Default AWS profile to select
        - saved_instances: Per-profile saved instance data
        - local_port_range: Port range for tunnel assignments [9800, 9900]
        - regions: AWS regions to scan ["us-east-1", "us-east-2"]
    
    Attributes:
        config_dir (str): Directory path for configuration files
        config_file (str): Full path to the configuration file
        settings (dict): Dictionary containing all application settings
    """
    
    def __init__(self):
        """
        Initialize the SettingsManager with default configuration.
        
        Sets up the configuration directory path, default settings, and
        automatically loads existing settings or creates new ones with
        auto-detected client paths.
        """
        self.config_dir = os.path.join(str(Path.home()), ".aws_rdp_connect")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.settings = {
            "rdp_client": "",
            "ssh_client": "",
            "default_profile": "",
            "saved_instances": {},
            "local_port_range": [9800, 9900],
            "regions": ["us-east-1", "us-east-2"]
        }
        self.load_settings()

    def load_settings(self):
        """
        Load settings from the configuration file.
        
        If the configuration file doesn't exist, creates it with default
        settings and auto-detected client paths. If loading fails, shows
        a warning dialog to the user.
        
        Raises:
            Exception: If file operations fail (handled gracefully with user notification)
        """
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.settings = json.load(f)
            else:
                # First time setup, determine default clients
                self.detect_clients()
                self.save_settings()
        except Exception as e:
            messagebox.showwarning("Settings Error", f"Failed to load settings: {str(e)}")

    def save_settings(self):
        """
        Save current settings to the configuration file.
        
        Writes the settings dictionary to the JSON configuration file with
        proper formatting. If saving fails, shows a warning dialog to the user.
        
        Raises:
            Exception: If file operations fail (handled gracefully with user notification)
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            messagebox.showwarning("Settings Error", f"Failed to save settings: {str(e)}")

    def detect_clients(self):
        """
        Auto-detect RDP and SSH clients based on the current platform.
        
        This method calls both detect_rdp_client() and detect_ssh_client()
        to automatically configure client paths for the current operating system.
        """
        self.detect_rdp_client()
        self.detect_ssh_client()

    def detect_rdp_client(self):
        """
        Auto-detect the RDP client based on the current platform.
        
        Platform-specific detection:
        - Windows: Uses built-in mstsc.exe
        - macOS: Looks for Microsoft Remote Desktop app
        - Linux: Searches for rdesktop or xfreerdp in PATH
        
        Updates the 'rdp_client' setting with the detected path or app name.
        """
        system = platform.system()
        if system == "Windows":
            self.settings["rdp_client"] = "mstsc.exe"
        elif system == "Darwin":  # macOS
            if os.path.exists("/Applications/Microsoft Remote Desktop.app"):
                self.settings["rdp_client"] = "Microsoft Remote Desktop"
            else:
                self.settings["rdp_client"] = ""
        else:  # Linux
            for client in ["rdesktop", "xfreerdp"]:
                try:
                    path = subprocess.check_output(["which", client], universal_newlines=True).strip()
                    if path:
                        self.settings["rdp_client"] = path
                        break
                except:
                    pass

    def detect_ssh_client(self):
        """
        Auto-detect the SSH client based on the current platform.
        
        Platform-specific detection:
        - Windows: Uses 'where ssh' to find OpenSSH
        - macOS/Linux: Uses 'which ssh' to find SSH in PATH
        
        Updates the 'ssh_client' setting with the detected path.
        Falls back to 'ssh' if detection fails.
        """
        system = platform.system()
        try:
            if system == "Windows":
                result = subprocess.run(["where", "ssh"], capture_output=True, text=True)
                if result.returncode == 0:
                    self.settings["ssh_client"] = "ssh"
            else:
                result = subprocess.run(["which", "ssh"], capture_output=True, text=True)
                if result.returncode == 0:
                    self.settings["ssh_client"] = result.stdout.strip()
        except:
            self.settings["ssh_client"] = "ssh"

    def get(self, key, default=None):
        """
        Get a setting value by key.
        
        Args:
            key (str): The setting key to retrieve
            default (Any, optional): Default value if key not found. Defaults to None.
            
        Returns:
            Any: The setting value or default if not found
        """
        return self.settings.get(key, default)

    def set(self, key, value):
        """
        Set a setting value by key.
        
        Args:
            key (str): The setting key to set
            value (Any): The value to set for the key
        """
        self.settings[key] = value

    def update_settings(self, new_settings):
        """
        Update multiple settings at once and save to file.
        
        Args:
            new_settings (dict): Dictionary of setting key-value pairs to update
        """
        self.settings.update(new_settings)
        self.save_settings()


class AwsResourceManager:
    """
    Manages AWS API interactions and resource discovery.
    
    This class handles all interactions with AWS services including:
    - AWS profile management and discovery
    - AWS SSO authentication
    - EC2 instance discovery and metadata extraction
    - RDS instance discovery and metadata extraction
    - Bastion host discovery for RDS tunneling
    
    The class uses the AWS CLI for all operations and supports multiple
    regions and profiles. All AWS operations are performed via subprocess
    calls to the AWS CLI.
    
    Attributes:
        settings_manager (SettingsManager): Reference to settings manager
        aws_profiles (list): List of available AWS profiles
        current_profile (str): Currently selected AWS profile
    """
    
    def __init__(self, settings_manager):
        """
        Initialize the AWS Resource Manager.
        
        Args:
            settings_manager (SettingsManager): Reference to the settings manager
        """
        self.settings_manager = settings_manager
        self.aws_profiles = []
        self.current_profile = None

    def refresh_profiles(self):
        """
        Refresh the list of available AWS profiles.
        
        Reads the AWS configuration file (~/.aws/config) and extracts all
        profile names. Profiles are identified by sections starting with "profile ".
        
        Returns:
            list: List of available AWS profile names
            
        Raises:
            Exception: If AWS config file cannot be read or parsed
        """
        self.aws_profiles = []
        
        try:
            aws_config = configparser.ConfigParser()
            aws_config_path = os.path.join(str(Path.home()), ".aws", "config")

            if os.path.exists(aws_config_path):
                aws_config.read(aws_config_path)
                for section in aws_config.sections():
                    if section.startswith("profile "):
                        profile_name = section[8:]  # Remove "profile " prefix
                        self.aws_profiles.append(profile_name)

            return self.aws_profiles
        except Exception as e:
            raise Exception(f"Failed to load AWS profiles: {str(e)}")

    def sso_login(self, profile):
        """
        Perform AWS SSO login for the specified profile.
        
        Executes the AWS CLI SSO login command and waits for completion.
        This will typically open a browser window for authentication.
        
        Args:
            profile (str): AWS profile name to authenticate with
            
        Returns:
            bool: True if login successful
            
        Raises:
            Exception: If AWS CLI not found or login fails
        """
        command = ["aws", "sso", "login", "--profile", profile]
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        if result.returncode != 0:
            raise Exception(result.stderr.strip())
        
        return True

    def load_resources(self, profile, regions=None, progress_callback=None):
        """
        Load EC2 and RDS instances for the specified profile and regions.
        
        This method discovers AWS resources across multiple regions by calling
        the AWS CLI to describe EC2 and RDS instances. It extracts metadata
        including names, states, platforms, and connection details.
        
        Args:
            profile (str): AWS profile name to use for API calls
            regions (list, optional): List of AWS regions to scan. 
                                    Defaults to configured regions.
            progress_callback (callable, optional): Callback function for progress updates.
                                                  Called with (step, status, detail).
        
        Returns:
            list: List of resource tuples in format:
                 (type, name, platform, state, region, endpoint, identifier, port)
                 
        Note:
            Each resource tuple contains:
            - type: "EC2" or "RDS"
            - name: Resource name from Name tag or identifier
            - platform: "Windows"/"Linux" for EC2, engine type for RDS
            - state: Instance state (running, stopped, etc.)
            - region: AWS region
            - endpoint: IP address or RDS endpoint
            - identifier: Instance ID or RDS identifier
            - port: 0 for EC2, database port for RDS
        """
        if regions is None:
            regions = self.settings_manager.get("regions", ["us-east-1", "us-east-2"])
            
        all_resources = []
        total_operations = len(regions) * 2  # EC2 + RDS for each region
        current_operation = 0
        
        # Load EC2 instances from all regions
        for region in regions:
            current_operation += 1
            if progress_callback:
                progress_callback(current_operation, f"Loading EC2 instances from {region}...", f"Region {current_operation}/{total_operations}")
            
            try:
                ec2_resources = self._load_ec2_instances(profile, region)
                all_resources.extend(ec2_resources)
            except Exception as e:
                print(f"Error loading EC2 instances from {region}: {e}")
        
        # Load RDS instances from all regions
        for region in regions:
            current_operation += 1
            if progress_callback:
                progress_callback(current_operation, f"Loading RDS instances from {region}...", f"Region {current_operation}/{total_operations}")
            
            try:
                rds_resources = self._load_rds_instances(profile, region)
                all_resources.extend(rds_resources)
            except Exception as e:
                print(f"Error loading RDS instances from {region}: {e}")
        
        return all_resources

    def _load_ec2_instances(self, profile, region):
        """Load EC2 instances from a specific region"""
        resources = []
        
        ec2_command = ["aws", "ec2", "describe-instances", "--region", region, "--profile", profile]
        ec2_result = subprocess.run(
            ec2_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if ec2_result.returncode == 0:
            data = json.loads(ec2_result.stdout)
            
            for reservation in data.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance.get("InstanceId", "")
                    instance_state = instance.get("State", {}).get("Name", "")
                    private_ip = instance.get("PrivateIpAddress", "")
                    
                    # Detect OS
                    platform_field = instance.get("Platform", "")
                    platform_details = instance.get("PlatformDetails", "")
                    
                    if platform_field == "windows" or "Windows" in platform_details:
                        os_type = "Windows"
                    elif "Linux" in platform_details or "RHEL" in platform_details or "Ubuntu" in platform_details:
                        os_type = "Linux"
                    else:
                        os_type = "Linux"  # Default to Linux

                    # Get the Name tag
                    name = ""
                    for tag in instance.get("Tags", []):
                        if tag.get("Key") == "Name":
                            name = tag.get("Value", "")
                            break

                    # Store as tuple: (type, name, platform, state, region, endpoint, identifier, port)
                    resources.append(("EC2", name, os_type, instance_state, region, private_ip, instance_id, 0))
        
        return resources

    def _load_rds_instances(self, profile, region):
        """Load RDS instances from a specific region"""
        resources = []
        
        rds_command = ["aws", "rds", "describe-db-instances", "--region", region, "--profile", profile]
        rds_result = subprocess.run(
            rds_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if rds_result.returncode == 0:
            data = json.loads(rds_result.stdout)
            
            for db_instance in data.get("DBInstances", []):
                db_identifier = db_instance.get("DBInstanceIdentifier", "")
                db_status = db_instance.get("DBInstanceStatus", "")
                endpoint_obj = db_instance.get("Endpoint", {})
                endpoint = endpoint_obj.get("Address", "")
                port = endpoint_obj.get("Port", 0)
                engine = db_instance.get("Engine", "")
                
                # Store as tuple: (type, name, platform, state, region, endpoint, identifier, port)
                resources.append(("RDS", db_identifier, engine, db_status, region, endpoint, db_identifier, port))
        
        return resources

    def find_bastion_host(self, profile, region):
        """Find the bastion host instance ID for the given profile and region"""
        try:
            command = ["aws", "ec2", "describe-instances", "--region", region, "--profile", profile,
                      "--filters", "Name=tag:Name,Values=*bastion*", "Name=instance-state-name,Values=running"]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                for reservation in data.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        return instance.get("InstanceId", "")
            
            return None
        except Exception as e:
            print(f"Error finding bastion host: {e}")
            return None


class ConnectionManager:
    """
    Manages all connection types and tunnel operations.
    
    This class handles the creation and management of various connection types:
    - RDP connections to Windows EC2 instances via EC2 Instance Connect tunnels
    - SSH connections to Linux EC2 instances via EC2 Instance Connect
    - SSM tunnels to EC2 instances for database access
    - RDS tunnels through bastion hosts using SSM port forwarding
    
    Key Features:
    - Port collision detection and automatic port assignment
    - Multiple simultaneous tunnel tracking
    - Cross-platform terminal command launching
    - Process lifecycle management
    - Resource cleanup and port management
    
    Attributes:
        settings_manager (SettingsManager): Reference to settings manager
        resource_manager (AwsResourceManager): Reference to resource manager
        tunnel_processes (dict): Dictionary tracking active tunnels
        assigned_ports (set): Set of currently assigned local ports
    """
    
    def __init__(self, settings_manager, resource_manager):
        self.settings_manager = settings_manager
        self.resource_manager = resource_manager
        self.tunnel_processes = {}  # Track multiple tunnel processes: {tunnel_id: {'process': process, 'port': port, 'type': type}}
        self.assigned_ports = set()  # Track ports assigned in this session

    def is_port_available(self, port, host='localhost'):
        """Check if a port is available for use"""
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, port))
                return True
        except (socket.error, OSError):
            return False

    def find_available_port(self, preferred_port=None, max_attempts=50):
        """Find an available port within the configured range"""
        port_range = self.settings_manager.get("local_port_range", [9800, 9900])
        min_port, max_port = port_range
        
        # If a preferred port is specified and available, use it
        if preferred_port and min_port <= preferred_port <= max_port:
            if self.is_port_available(preferred_port) and preferred_port not in self.assigned_ports:
                self.assigned_ports.add(preferred_port)
                return preferred_port
        
        # Try random ports within the range
        for attempt in range(max_attempts):
            port = random.randint(min_port, max_port)
            if port not in self.assigned_ports and self.is_port_available(port):
                self.assigned_ports.add(port)
                return port
        
        # If no random port found, try sequential search
        for port in range(min_port, max_port + 1):
            if port not in self.assigned_ports and self.is_port_available(port):
                self.assigned_ports.add(port)
                return port
        
        # If still no port found, provide detailed error message
        used_ports = []
        for port in range(min_port, min(max_port + 1, min_port + 20)):  # Check first 20 ports for diagnostics
            if not self.is_port_available(port):
                used_ports.append(port)
        
        error_msg = f"No available ports found in range {min_port}-{max_port}."
        if used_ports:
            error_msg += f"\n\nPorts currently in use: {', '.join(map(str, used_ports[:10]))}"
            if len(used_ports) > 10:
                error_msg += f" (and {len(used_ports) - 10} more)"
        error_msg += "\n\nPlease:\n• Close applications using ports in this range\n• Expand your port range in Settings\n• Or try again in a moment"
        
        raise Exception(error_msg)

    def launch_terminal_command(self, command, description="command"):
        """Launch a command in a new terminal window based on platform"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # Escape quotes properly for AppleScript
            escaped_command = command.replace('"', '\\"')
            applescript = f'''tell application "Terminal"
    do script "{escaped_command}"
    activate
end tell'''
            try:
                result = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Failed to open terminal: {result.stderr}")
            except Exception as e:
                raise Exception(f"Failed to launch terminal: {str(e)}")
                
        elif system == "Windows":
            subprocess.Popen(["start", "cmd", "/k", command], shell=True)
            
        else:  # Linux
            terminals = [
                ["gnome-terminal", "--", "bash", "-c", f"{command}; exec bash"],
                ["xterm", "-e", f"{command}; exec bash"],
                ["konsole", "-e", f"{command}; exec bash"],
            ]
            
            launched = False
            for term_cmd in terminals:
                try:
                    subprocess.Popen(term_cmd)
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            
            if not launched:
                raise Exception(f"No terminal emulator found. Please run manually:\n\n{command}")

    def connect_rdp(self, instance_id, instance_name, region, profile):
        """
        Establish an RDP connection to a Windows EC2 instance.
        
        This method creates an EC2 Instance Connect tunnel to port 3389 (RDP)
        and launches the appropriate RDP client for the current platform.
        The tunnel process is tracked for proper resource management.
        
        Process:
        1. Validates RDP client configuration
        2. Finds an available local port
        3. Creates EC2 Instance Connect tunnel
        4. Launches platform-specific RDP client
        5. Registers tunnel for tracking
        
        Args:
            instance_id (str): EC2 instance ID to connect to
            instance_name (str): Human-readable instance name
            region (str): AWS region where instance is located
            profile (str): AWS profile to use for authentication
            
        Returns:
            int: Local port number assigned for the tunnel
            
        Raises:
            Exception: If RDP client not configured, not found, or tunnel setup fails
        """
        rdp_client = self.settings_manager.get("rdp_client")
        if not rdp_client:
            raise Exception("RDP client not configured. Please update in Settings.")

        system = platform.system()
        if system != "Darwin" and not os.path.exists(rdp_client):
            raise Exception("RDP client not found. Please update path in Settings.")

        # Find an available local port
        local_port = self.find_available_port()

        # Set up the tunnel
        command = [
            "aws", "ec2-instance-connect", "open-tunnel",
            "--instance-id", instance_id,
            "--remote-port", "3389",
            "--local-port", str(local_port),
            "--region", region,
            "--profile", profile
        ]

        # Start the tunnel process
        tunnel_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Give the tunnel time to initialize
        time.sleep(2)

        # Check if tunnel is running
        if tunnel_process.poll() is not None:
            stderr = tunnel_process.stderr.read().decode('utf-8').strip()
            raise Exception(f"Tunnel setup failed: {stderr}")

        # Store the tunnel process with enhanced tracking
        tunnel_id = self.generate_tunnel_id("rdp", instance_id, local_port)
        self.register_tunnel(tunnel_id, tunnel_process, local_port, "RDP")

        # Launch RDP client based on platform
        self._launch_rdp_client(instance_id, local_port, system)

        return local_port

    def _launch_rdp_client(self, instance_id, local_port, system):
        """Launch the appropriate RDP client for the platform"""
        rdp_client = self.settings_manager.get("rdp_client")
        
        if system == "Windows":
            temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
            rdp_file = os.path.join(temp_dir, f"aws_connect_{instance_id}.rdp")
            try:
                with open(rdp_file, "w") as f:
                    f.write(f"full address:s:localhost:{local_port}\n")
                    f.write("prompt for credentials:i:1\n")
                subprocess.Popen([rdp_client, rdp_file])
            except Exception as e:
                raise Exception(f"Could not create temporary RDP file: {str(e)}")

        elif system == "Darwin":  # macOS
            temp_dir = os.path.join(os.path.expanduser("~"), ".aws_rdp_connect_temp")
            os.makedirs(temp_dir, exist_ok=True)
            rdp_file = os.path.join(temp_dir, f"aws_connect_{instance_id}.rdp")

            try:
                with open(rdp_file, "w") as f:
                    f.write(f"full address:s:localhost:{local_port}\n")
                    f.write("prompt for credentials:i:1\n")

                # Try multiple methods to launch RDP client
                methods = [
                    lambda: subprocess.Popen(["open", rdp_file]),
                    lambda: subprocess.Popen(["open", "-a", "Microsoft Remote Desktop", rdp_file]),
                    lambda: subprocess.Popen(["open", f"rdp://full%20address=s:localhost:{local_port}"])
                ]

                for method in methods:
                    try:
                        method()
                        return
                    except Exception:
                        continue
                
                raise Exception(f"Please open your RDP client manually and connect to localhost:{local_port}")
                
            except Exception as e:
                raise Exception(f"Could not create temporary RDP file: {str(e)}")

        else:  # Linux
            try:
                if "rdesktop" in rdp_client:
                    subprocess.Popen([rdp_client, f"localhost:{local_port}"])
                elif "xfreerdp" in rdp_client:
                    subprocess.Popen([rdp_client, f"/v:localhost:{local_port}"])
                else:
                    subprocess.Popen([rdp_client, f"localhost:{local_port}"])
            except FileNotFoundError:
                raise Exception(f"RDP client not found at: {rdp_client}. Please check settings.")

    def connect_ssh(self, instance_id, instance_name, region, profile):
        """Connect to an EC2 instance via SSH"""
        ssh_client = self.settings_manager.get("ssh_client")
        if not ssh_client:
            raise Exception("SSH client not configured. Please update in Settings.")

        command = f"aws ec2-instance-connect ssh --instance-id {instance_id} --region {region} --profile {profile}"
        self.launch_terminal_command(command, f"SSH connection to {instance_name}")

    def create_ec2_ssm_tunnel(self, instance_id, instance_name, remote_port, region, profile):
        """Create an SSM tunnel to an EC2 instance with custom port"""
        local_port = self.find_available_port()

        # Build command with platform-specific parameter quoting
        if platform.system() == "Windows":
            # Windows CMD requires different quoting for JSON-like parameters
            command = f'aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters portNumber={remote_port},localPortNumber={local_port} --region {region} --profile {profile}'
        else:
            # Unix shells can handle quoted parameters
            command = f'aws ssm start-session --target {instance_id} --document-name AWS-StartPortForwardingSession --parameters "portNumber={remote_port},localPortNumber={local_port}" --region {region} --profile {profile}'
        
        self.launch_terminal_command(command, f"SSM tunnel to {instance_name}:{remote_port}")
        
        # Track the tunnel (no process object for terminal-launched commands)
        tunnel_id = self.generate_tunnel_id("ssm_ec2", instance_id, local_port)
        self.register_tunnel(tunnel_id, None, local_port, f"SSM EC2 ({instance_name}:{remote_port})")
        
        return local_port

    def create_rds_tunnel(self, db_name, endpoint, db_port, region, profile):
        """Create an SSM tunnel to RDS instance through bastion host"""
        # Find the bastion host
        bastion_id = self.resource_manager.find_bastion_host(profile, region)
        
        if not bastion_id:
            raise Exception("Could not find a running bastion host in this account. Please ensure a bastion host with 'bastion' in its name tag is running.")

        # Try to use the same port as the database if available locally
        local_port = self.find_available_port(preferred_port=db_port)

        # Build command with platform-specific parameter quoting
        if platform.system() == "Windows":
            # Windows CMD requires different quoting for JSON-like parameters
            command = f'aws ssm start-session --target {bastion_id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host={endpoint},portNumber={db_port},localPortNumber={local_port} --region {region} --profile {profile}'
        else:
            # Unix shells can handle quoted parameters
            command = f'aws ssm start-session --target {bastion_id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host="{endpoint}",portNumber="{db_port}",localPortNumber="{local_port}" --region {region} --profile {profile}'
        
        self.launch_terminal_command(command, f"RDS tunnel to {db_name}")
        
        # Track the tunnel (no process object for terminal-launched commands)
        tunnel_id = self.generate_tunnel_id("ssm_rds", db_name.replace("-", "_"), local_port)
        self.register_tunnel(tunnel_id, None, local_port, f"RDS ({db_name})")
        
        return local_port

    def generate_tunnel_id(self, tunnel_type, resource_id, port):
        """Generate a unique tunnel ID"""
        return f"{tunnel_type}_{resource_id}_{port}"

    def register_tunnel(self, tunnel_id, process, port, tunnel_type):
        """Register a tunnel process for tracking"""
        self.tunnel_processes[tunnel_id] = {
            'process': process,
            'port': port,
            'type': tunnel_type,
            'created_at': time.time()
        }

    def is_terminal_tunnel_active(self, port):
        """Check if a terminal-launched tunnel is likely still active by checking port usage"""
        try:
            # Try to bind to the port - if it fails, something is using it (likely our tunnel)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('localhost', port))
                return False  # Port is free, tunnel likely not active
        except (socket.error, OSError):
            return True  # Port is in use, tunnel likely active

    def get_active_tunnels(self):
        """Get list of active tunnels"""
        active_tunnels = {}
        for tunnel_id, tunnel_info in list(self.tunnel_processes.items()):
            process = tunnel_info['process']
            
            if process is None:
                # Terminal-launched tunnels (SSH, SSM) - check if port is still in use
                port = tunnel_info['port']
                if self.is_terminal_tunnel_active(port):
                    active_tunnels[tunnel_id] = tunnel_info
                # Note: We don't auto-remove inactive terminal tunnels since they might be starting up
            elif process.poll() is None:
                # Process-based tunnels (RDP) - check if still running
                active_tunnels[tunnel_id] = tunnel_info
            else:
                # Dead process - clean up
                self.release_tunnel(tunnel_id)
        return active_tunnels

    def release_tunnel(self, tunnel_id):
        """Release a specific tunnel and its resources"""
        if tunnel_id in self.tunnel_processes:
            tunnel_info = self.tunnel_processes[tunnel_id]
            process = tunnel_info['process']
            port = tunnel_info['port']
            
            # Terminate process if still running
            if process and process.poll() is None:
                try:
                    process.terminate()
                except Exception as e:
                    print(f"Error terminating tunnel {tunnel_id}: {e}")
            
            # Release port
            self.assigned_ports.discard(port)
            
            # Remove from tracking
            del self.tunnel_processes[tunnel_id]

    def release_port(self, port):
        """Release a port from the assigned ports set"""
        self.assigned_ports.discard(port)

    def cleanup_tunnels(self):
        """Clean up all tunnel processes"""
        tunnel_ids = list(self.tunnel_processes.keys())
        for tunnel_id in tunnel_ids:
            self.release_tunnel(tunnel_id)

    def get_tunnel_status_summary(self):
        """Get a summary of active tunnels for display"""
        active_tunnels = self.get_active_tunnels()
        if not active_tunnels:
            return "No active tunnels"
        
        summary = []
        for tunnel_id, tunnel_info in active_tunnels.items():
            tunnel_type = tunnel_info['type']
            port = tunnel_info['port']
            summary.append(f"{tunnel_type} (localhost:{port})")
        
        return f"Active tunnels: {', '.join(summary)}"


class MainWindow:
    """
    Main application window and user interface controller.
    
    This class creates and manages the main application window, handling:
    - User interface creation and layout
    - Event handling for user interactions
    - Coordination between different manager classes
    - Progress dialog management
    - Settings dialog management
    - Active tunnels management dialog
    
    The window provides:
    - AWS profile selection and SSO login
    - Resource loading with progress indication
    - Resource tree view with context menus
    - Connection management through right-click actions
    - Status bar with tunnel count information
    - Settings and tunnel management dialogs
    
    Attributes:
        root (tk.Tk): Main tkinter window
        settings_manager (SettingsManager): Application settings manager
        resource_manager (AwsResourceManager): AWS resource manager
        connection_manager (ConnectionManager): Connection and tunnel manager
        resources (list): Currently loaded AWS resources
        current_profile (str): Currently selected AWS profile
        Various UI components (frames, buttons, tree view, etc.)
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("AWS Connect")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # Set taskbar icon (required for Windows taskbar display)
        self._set_taskbar_icon()

        # Initialize managers
        self.settings_manager = SettingsManager()
        self.resource_manager = AwsResourceManager(self.settings_manager)
        self.connection_manager = ConnectionManager(self.settings_manager, self.resource_manager)

        # UI state
        self.resources = []
        self.current_profile = None

        # Create UI
        self.create_ui()
        
        # Initialize
        self.refresh_profiles()
        self.load_saved_instances()
        
        # Set default profile if available
        default_profile = self.settings_manager.get("default_profile")
        if default_profile and default_profile in self.resource_manager.aws_profiles:
            self.profile_var.set(default_profile)
            self.on_profile_selected(None)


    def _set_taskbar_icon(self):
        """
        Set the taskbar icon for Windows.
        
        On Windows, the taskbar icon is controlled by the window's iconbitmap
        setting. This will show the icon in both the taskbar and title bar.
        """
        try:
            # Only set icon on Windows
            if platform.system() == "Windows":
                # Get the base path for the application
                if getattr(sys, 'frozen', False):
                    # Running as PyInstaller bundle
                    base_path = sys._MEIPASS
                else:
                    # Running as script
                    base_path = os.path.dirname(os.path.abspath(__file__))
                
                icon_file = os.path.join(base_path, "icon.ico")
                
                if os.path.exists(icon_file):
                    # Set the icon for both taskbar and title bar
                    self.root.iconbitmap(icon_file)
                    print(f"Icon loaded from: {icon_file}")
                else:
                    print(f"Warning: Icon file '{icon_file}' not found.")
                    print(f"Searched in: {base_path}")
                    # List files in base_path for debugging
                    try:
                        files = os.listdir(base_path)
                        print(f"Files in base_path: {files}")
                    except:
                        pass
                    
        except Exception as e:
            print(f"Warning: Could not set taskbar icon: {e}")
            import traceback
            traceback.print_exc()

    def create_ui(self):
        """Create the main user interface"""
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Controls frame
        self.controls_frame = ttk.LabelFrame(self.main_frame, text="Connection Settings", padding="10")
        self.controls_frame.pack(fill=tk.X, padx=5, pady=5)

        # AWS Profile selection
        ttk.Label(self.controls_frame, text="AWS Profile:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(self.controls_frame, textvariable=self.profile_var, state="readonly", width=30)
        self.profile_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_selected)

        # Buttons
        self.refresh_button = ttk.Button(self.controls_frame, text="Refresh", command=self.refresh_profiles)
        self.refresh_button.grid(row=0, column=2, padx=5, pady=5)

        self.login_button = ttk.Button(self.controls_frame, text="Login", command=self.aws_sso_login)
        self.login_button.grid(row=0, column=3, padx=5, pady=5)

        # Resources frame
        self.instances_frame = ttk.LabelFrame(self.main_frame, text="Resources", padding="10")
        self.instances_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Instruction label
        instruction_label = ttk.Label(self.instances_frame, text="💡 Right-click to connect to a resource", font=("", 11, "italic"))
        instruction_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=(0, 5))

        # Tree view for resources
        self.tree_columns = ("Resource Type", "Name", "Platform", "State")
        self.tree = ttk.Treeview(self.instances_frame, columns=self.tree_columns, show="headings")

        for col in self.tree_columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        # Scrollbars
        vsb = ttk.Scrollbar(self.instances_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.instances_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Position tree and scrollbars
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")

        # Configure grid weights
        self.instances_frame.grid_columnconfigure(0, weight=1)
        self.instances_frame.grid_rowconfigure(1, weight=1)

        # Event bindings
        self.tree.bind("<Double-Button-1>", self.on_tree_double_click)
        self.tree.bind("<Button-2>" if platform.system() == "Darwin" else "<Button-3>", self.on_tree_right_click)

        # Bottom buttons frame
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.load_button = ttk.Button(self.button_frame, text="Load Resources", command=self.load_instances)
        self.load_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.tunnels_button = ttk.Button(self.button_frame, text="Active Tunnels", command=self.show_active_tunnels)
        self.tunnels_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.settings_button = ttk.Button(self.button_frame, text="Settings", command=self.open_settings)
        self.settings_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def refresh_profiles(self):
        """Refresh the AWS profiles"""
        self.status_var.set("Loading AWS profiles...")
        
        try:
            profiles = self.resource_manager.refresh_profiles()
            self.profile_combo['values'] = profiles

            if profiles:
                if self.profile_var.get() not in profiles:
                    self.profile_var.set(profiles[0])
                
                self.current_profile = self.profile_var.get()
                self.status_var.set(f"Loaded {len(profiles)} AWS profiles")
            else:
                self.current_profile = None
                self.profile_var.set("")
                self.status_var.set("No AWS profiles found. Check your AWS CLI configuration.")
        except Exception as e:
            self.status_var.set(f"Error loading profiles: {str(e)}")
            messagebox.showerror("Error", str(e))

    def on_profile_selected(self, event):
        """Handle profile selection"""
        self.current_profile = self.profile_var.get()
        self.status_var.set(f"Selected profile: {self.current_profile}")

    def aws_sso_login(self):
        """Perform AWS SSO login"""
        if not self.current_profile:
            messagebox.showwarning("Warning", "Please select an AWS profile first")
            return

        self.status_var.set(f"Logging in with AWS SSO using profile {self.current_profile}...")
        self.login_button.configure(state="disabled")

        def login_thread():
            login_progress = None
            try:
                # Create progress dialog for login
                self.root.after(0, lambda: self._create_login_progress_dialog())
                time.sleep(0.1)  # Wait for dialog creation
                
                # Update progress
                if hasattr(self, '_login_progress_dialog') and self._login_progress_dialog:
                    self.root.after(0, lambda: self._login_progress_dialog.update_progress(1, "Authenticating with AWS SSO...", "Please complete authentication in your browser"))
                
                self.resource_manager.sso_login(self.current_profile)
                
                # Update progress
                if hasattr(self, '_login_progress_dialog') and self._login_progress_dialog:
                    self.root.after(0, lambda: self._login_progress_dialog.update_progress(2, "Login successful! Loading resources...", ""))
                
                self.root.after(0, lambda: self.status_var.set("SSO login successful! Loading resources..."))
                self.root.after(0, lambda: self.load_instances())
                
            except FileNotFoundError:
                self.root.after(0, lambda: self.status_var.set("AWS CLI not found. Please ensure it's installed and in your PATH."))
                self.root.after(0, lambda: messagebox.showerror("Error", "AWS CLI not found. Please ensure it's installed and in your PATH."))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"SSO login failed: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Login Failed", str(e)))
            finally:
                self.root.after(0, lambda: self._close_login_progress_dialog())
                self.root.after(0, lambda: self.login_button.configure(state="normal"))

        threading.Thread(target=login_thread, daemon=True).start()

    def _create_login_progress_dialog(self):
        """Create login progress dialog on main thread"""
        self._login_progress_dialog = ProgressDialog(self.root, "AWS SSO Login", 2)
        
    def _close_login_progress_dialog(self):
        """Close login progress dialog on main thread"""
        if hasattr(self, '_login_progress_dialog') and self._login_progress_dialog:
            self._login_progress_dialog.close()
            self._login_progress_dialog = None

    def load_instances(self):
        """Load EC2 and RDS instances for the selected profile"""
        if not self.current_profile:
            messagebox.showwarning("Warning", "Please select an AWS profile first")
            return

        self.status_var.set(f"Loading resources for profile {self.current_profile}...")
        self.load_button.configure(state="disabled")

        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Calculate total steps for progress
        regions = self.settings_manager.get("regions", ["us-east-1", "us-east-2"])
        total_steps = len(regions) * 2  # EC2 + RDS for each region
        
        # Create progress dialog
        progress_dialog = None

        def load_thread():
            nonlocal progress_dialog
            try:
                # Create progress dialog on main thread
                self.root.after(0, lambda: self._create_progress_dialog(total_steps))
                
                # Wait a bit for dialog to be created
                time.sleep(0.1)
                
                def progress_callback(step, status, detail):
                    if hasattr(self, '_progress_dialog') and self._progress_dialog:
                        self.root.after(0, lambda: self._progress_dialog.update_progress(step, status, detail))
                
                resources = self.resource_manager.load_resources(self.current_profile, progress_callback=progress_callback)
                self.root.after(0, lambda: self.update_instances_tree(resources))
                
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"Error loading resources: {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self._close_progress_dialog())
                self.root.after(0, lambda: self.load_button.configure(state="normal"))

        threading.Thread(target=load_thread, daemon=True).start()

    def _create_progress_dialog(self, total_steps):
        """Create progress dialog on main thread"""
        self._progress_dialog = ProgressDialog(self.root, "Loading AWS Resources", total_steps)
        
    def _close_progress_dialog(self):
        """Close progress dialog on main thread"""
        if hasattr(self, '_progress_dialog') and self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

    def update_instances_tree(self, resources):
        """Update the treeview with resource data"""
        self.resources = resources

        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add resources to tree
        for resource in resources:
            self.tree.insert("", tk.END, values=resource)

        # Auto-fit column widths
        self.autofit_columns()

        self.status_var.set(f"Loaded {len(resources)} resources")

    def autofit_columns(self):
        """Auto-fit column widths based on content"""
        import tkinter.font as tkfont
        
        font = tkfont.Font()
        
        for col_index, col in enumerate(self.tree_columns):
            max_width = font.measure(col) + 20  # Header width + padding
            
            for item in self.tree.get_children():
                values = self.tree.item(item, "values")
                if col_index < len(values):
                    cell_value = str(values[col_index])
                    cell_width = font.measure(cell_value) + 20
                    max_width = max(max_width, cell_width)
            
            max_width = min(max_width, 400)  # Cap at 400px
            self.tree.column(col, width=max_width)

    def load_saved_instances(self):
        """Load saved instances into the tree"""
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add saved instances to tree
        saved_instances = self.settings_manager.get("saved_instances", {})
        for profile, instances in saved_instances.items():
            if profile in self.resource_manager.aws_profiles:
                for instance in instances:
                    self.tree.insert("", tk.END, values=instance, tags=(profile,))

    def get_selected_resource(self):
        """Get the selected resource from the tree"""
        selected_items = self.tree.selection()
        if not selected_items:
            return None, None

        selected_item = selected_items[0]
        values = self.tree.item(selected_item, "values")
        tags = self.tree.item(selected_item, "tags")
        
        return values, tags

    def on_tree_double_click(self, event):
        """Handle double-click on tree item to auto-connect"""
        values, tags = self.get_selected_resource()
        if not values:
            return

        resource_type = values[0]
        platform = values[2]

        try:
            if resource_type == "EC2":
                if platform == "Windows":
                    self.connect_rdp()
                else:
                    self.connect_ssh()
            elif resource_type == "RDS":
                self.connect_rds_tunnel()
            else:
                messagebox.showinfo("Info", "Connection not supported for this resource type")
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def on_tree_right_click(self, event):
        """Handle right-click on tree item to show context menu"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            values = self.tree.item(item, "values")
            
            if not values:
                return
            
            resource_type = values[0]
            
            # Create context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            
            if resource_type == "EC2":
                platform = values[2]
                
                if platform == "Windows":
                    context_menu.add_command(label="Connect via RDP", command=self.connect_rdp)
                else:
                    context_menu.add_command(label="Connect via SSH", command=self.connect_ssh)
                
                context_menu.add_separator()
                context_menu.add_command(label="Create SSM Tunnel (Custom Port)...", command=self.connect_ec2_ssm_tunnel)
                
            elif resource_type == "RDS":
                context_menu.add_command(label="Create Database Tunnel", command=self.connect_rds_tunnel)
            
            # Show the context menu
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

    def connect_rdp(self):
        """Connect to the selected instance via RDP"""
        values, tags = self.get_selected_resource()
        if not values:
            messagebox.showwarning("Warning", "Please select a resource first")
            return

        resource_type = values[0]
        instance_name = values[1]
        region = values[4]
        instance_id = values[6]
        
        if resource_type != "EC2":
            messagebox.showwarning("Warning", "RDP connection is only supported for EC2 instances")
            return

        # Determine profile to use
        connection_profile = self.current_profile
        if tags:
            saved_profile = tags[0] if tags else None
            if saved_profile and saved_profile in self.resource_manager.aws_profiles:
                connection_profile = saved_profile

        try:
            self.status_var.set(f"Connecting to {instance_name} ({instance_id}) via RDP...")
            local_port = self.connection_manager.connect_rdp(instance_id, instance_name, region, connection_profile)
            tunnel_count = len(self.connection_manager.get_active_tunnels())
            self.status_var.set(f"Connected to {instance_name} on port {local_port} ({tunnel_count} active tunnels)")
        except Exception as e:
            self.status_var.set(f"RDP connection error: {str(e)}")
            messagebox.showerror("RDP Connection Error", str(e))

    def connect_ssh(self):
        """Connect to the selected instance via SSH"""
        values, tags = self.get_selected_resource()
        if not values:
            messagebox.showwarning("Warning", "Please select a resource first")
            return

        resource_type = values[0]
        instance_name = values[1]
        region = values[4]
        instance_id = values[6]
        
        if resource_type != "EC2":
            messagebox.showwarning("Warning", "SSH connection is only supported for EC2 instances")
            return

        # Determine profile to use
        connection_profile = self.current_profile
        if tags:
            saved_profile = tags[0] if tags else None
            if saved_profile and saved_profile in self.resource_manager.aws_profiles:
                connection_profile = saved_profile

        try:
            self.status_var.set(f"Connecting to {instance_name} ({instance_id}) via SSH...")
            self.connection_manager.connect_ssh(instance_id, instance_name, region, connection_profile)
            tunnel_count = len(self.connection_manager.get_active_tunnels())
            self.status_var.set(f"SSH connection opened to {instance_name} ({tunnel_count} active tunnels)")
        except Exception as e:
            self.status_var.set(f"SSH connection error: {str(e)}")
            messagebox.showerror("SSH Connection Error", str(e))

    def connect_ec2_ssm_tunnel(self):
        """Create an SSM tunnel to an EC2 instance with custom port"""
        values, tags = self.get_selected_resource()
        if not values:
            messagebox.showwarning("Warning", "Please select an EC2 instance first")
            return

        resource_type = values[0]
        instance_name = values[1]
        region = values[4]
        instance_id = values[6]

        if resource_type != "EC2":
            messagebox.showwarning("Warning", "SSM tunnel is only supported for EC2 instances")
            return

        # Show port selection dialog
        self.show_port_dialog(instance_name, instance_id, region, tags)

    def show_port_dialog(self, instance_name, instance_id, region, tags):
        """Show dialog for port selection"""
        port_dialog = tk.Toplevel(self.root)
        port_dialog.title("SSM Tunnel Configuration")
        port_dialog.geometry("550x250")
        port_dialog.transient(self.root)
        port_dialog.grab_set()

        ttk.Label(port_dialog, text=f"Create SSM tunnel to: {instance_name}", font=("", 10, "bold")).pack(pady=10)
        ttk.Label(port_dialog, text="Enter the remote port on the EC2 instance:").pack(pady=5)

        # Port entry
        port_frame = ttk.Frame(port_dialog)
        port_frame.pack(pady=5)

        port_var = tk.StringVar(value="5432")
        port_entry = ttk.Entry(port_frame, textvariable=port_var, width=10)
        port_entry.pack(side=tk.LEFT, padx=5)

        # Quick select buttons
        common_ports = [
            ("PostgreSQL (5432)", "5432"),
            ("MySQL (3306)", "3306"),
            ("MSSQL (1433)", "1433"),
        ]

        button_frame = ttk.Frame(port_dialog)
        button_frame.pack(pady=10)

        for label, port in common_ports:
            ttk.Button(button_frame, text=label, command=lambda p=port: port_var.set(p)).pack(side=tk.LEFT, padx=2)

        def create_tunnel():
            try:
                remote_port = int(port_var.get())
                if remote_port < 1 or remote_port > 65535:
                    messagebox.showerror("Invalid Port", "Port must be between 1 and 65535")
                    return
                
                port_dialog.destroy()
                
                # Determine profile to use
                connection_profile = self.current_profile
                if tags:
                    saved_profile = tags[0] if tags else None
                    if saved_profile and saved_profile in self.resource_manager.aws_profiles:
                        connection_profile = saved_profile

                self.status_var.set(f"Setting up SSM tunnel to {instance_name}:{remote_port}...")
                
                local_port = self.connection_manager.create_ec2_ssm_tunnel(
                    instance_id, instance_name, remote_port, region, connection_profile
                )
                
                tunnel_count = len(self.connection_manager.get_active_tunnels())
                self.status_var.set(f"SSM tunnel opened: Connect to localhost:{local_port} ({tunnel_count} active tunnels)")
                messagebox.showinfo(
                    "Tunnel Established",
                    f"SSM tunnel to {instance_name} is now active!\n\nConnect your client to:\nHost: localhost\nPort: {local_port}\n\nThe tunnel will remain open in the terminal window."
                )
                
            except ValueError:
                messagebox.showerror("Invalid Port", "Please enter a valid port number")
            except Exception as e:
                self.status_var.set(f"SSM tunnel error: {str(e)}")
                messagebox.showerror("SSM Tunnel Error", str(e))

        ttk.Button(port_dialog, text="Create Tunnel", command=create_tunnel).pack(pady=10)
        ttk.Button(port_dialog, text="Cancel", command=port_dialog.destroy).pack()

    def connect_rds_tunnel(self):
        """Connect to the selected RDS instance via SSM tunnel through bastion host"""
        values, tags = self.get_selected_resource()
        if not values:
            messagebox.showwarning("Warning", "Please select an RDS instance first")
            return

        resource_type = values[0]
        db_name = values[1]
        region = values[4]
        endpoint = values[5]
        db_port = int(values[7]) if len(values) > 7 else 5432

        # Determine profile to use
        connection_profile = self.current_profile
        if tags:
            saved_profile = tags[0] if tags else None
            if saved_profile and saved_profile in self.resource_manager.aws_profiles:
                connection_profile = saved_profile

        try:
            self.status_var.set(f"Setting up tunnel to {db_name} via bastion host...")
            
            local_port = self.connection_manager.create_rds_tunnel(
                db_name, endpoint, db_port, region, connection_profile
            )
            
            tunnel_count = len(self.connection_manager.get_active_tunnels())
            self.status_var.set(f"RDS tunnel opened: Connect to localhost:{local_port} ({tunnel_count} active tunnels)")
            messagebox.showinfo(
                "Tunnel Established",
                f"RDS tunnel is now active!\n\nConnect your database client to:\nHost: localhost\nPort: {local_port}\n\nThe tunnel will remain open in the terminal window."
            )
        except Exception as e:
            self.status_var.set(f"RDS tunnel error: {str(e)}")
            messagebox.showerror("RDS Tunnel Error", str(e))

    def open_settings(self):
        """Open the settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x450")
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Create notebook for settings tabs
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # General settings tab
        general_frame = ttk.Frame(notebook, padding="10")
        notebook.add(general_frame, text="General")

        # RDP Client
        ttk.Label(general_frame, text="RDP Client Path:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        rdp_client_var = tk.StringVar(value=self.settings_manager.get("rdp_client", ""))
        rdp_client_entry = ttk.Entry(general_frame, textvariable=rdp_client_var, width=40)
        rdp_client_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        browse_rdp_button = ttk.Button(general_frame, text="Browse", command=lambda: self.browse_file(rdp_client_var))
        browse_rdp_button.grid(row=0, column=2, padx=5, pady=5)

        # SSH Client
        ttk.Label(general_frame, text="SSH Client Path:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ssh_client_var = tk.StringVar(value=self.settings_manager.get("ssh_client", ""))
        ssh_client_entry = ttk.Entry(general_frame, textvariable=ssh_client_var, width=40)
        ssh_client_entry.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        browse_ssh_button = ttk.Button(general_frame, text="Browse", command=lambda: self.browse_file(ssh_client_var))
        browse_ssh_button.grid(row=1, column=2, padx=5, pady=5)

        # Default profile
        ttk.Label(general_frame, text="Default Profile:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        default_profile_var = tk.StringVar(value=self.settings_manager.get("default_profile", ""))
        default_profile_combo = ttk.Combobox(general_frame, textvariable=default_profile_var, values=self.resource_manager.aws_profiles, state="readonly")
        default_profile_combo.grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        # Port range
        ttk.Label(general_frame, text="Local Port Range:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        port_frame = ttk.Frame(general_frame)
        port_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        port_range = self.settings_manager.get("local_port_range", [9800, 9900])
        min_port_var = tk.IntVar(value=port_range[0])
        max_port_var = tk.IntVar(value=port_range[1])

        ttk.Label(port_frame, text="Min:").pack(side=tk.LEFT)
        min_port_entry = ttk.Entry(port_frame, textvariable=min_port_var, width=6)
        min_port_entry.pack(side=tk.LEFT, padx=2)

        ttk.Label(port_frame, text="Max:").pack(side=tk.LEFT, padx=(10, 0))
        max_port_entry = ttk.Entry(port_frame, textvariable=max_port_var, width=6)
        max_port_entry.pack(side=tk.LEFT, padx=2)

        # AWS Regions
        ttk.Label(general_frame, text="AWS Regions:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        regions_var = tk.StringVar(value=", ".join(self.settings_manager.get("regions", ["us-east-1", "us-east-2"])))
        regions_entry = ttk.Entry(general_frame, textvariable=regions_var, width=40)
        regions_entry.grid(row=4, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Help text for regions
        ttk.Label(general_frame, text="(comma-separated, e.g., us-east-1, us-west-2)", font=("", 8)).grid(row=5, column=1, sticky=tk.W, padx=5, pady=(0, 5))

        # Buttons frame
        buttons_frame = ttk.Frame(settings_window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)

        def save_settings():
            try:
                min_port = min_port_var.get()
                max_port = max_port_var.get()
                
                if min_port < 1024 or min_port > 65535 or max_port < 1024 or max_port > 65535 or min_port >= max_port:
                    messagebox.showerror("Error", "Invalid port range. Please use ports between 1024 and 65535, with min < max.")
                    return

                # Parse regions from comma-separated string
                regions_text = regions_var.get().strip()
                if regions_text:
                    regions = [region.strip() for region in regions_text.split(",") if region.strip()]
                    if not regions:
                        messagebox.showerror("Error", "Please enter at least one AWS region.")
                        return
                else:
                    messagebox.showerror("Error", "Please enter at least one AWS region.")
                    return

                new_settings = {
                    "rdp_client": rdp_client_var.get(),
                    "ssh_client": ssh_client_var.get(),
                    "default_profile": default_profile_var.get(),
                    "local_port_range": [min_port, max_port],
                    "regions": regions
                }
                
                self.settings_manager.update_settings(new_settings)
                settings_window.destroy()
                self.status_var.set("Settings saved successfully")

                # Update profile combo if needed
                if self.resource_manager.aws_profiles:
                    self.profile_combo['values'] = self.resource_manager.aws_profiles
                    default_profile = self.settings_manager.get("default_profile")
                    if default_profile in self.resource_manager.aws_profiles:
                        self.profile_var.set(default_profile)
                        self.current_profile = default_profile

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

        save_button = ttk.Button(buttons_frame, text="Save", command=save_settings)
        save_button.pack(side=tk.RIGHT, padx=5)

        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=settings_window.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)

        # Configure grid weights
        general_frame.grid_columnconfigure(1, weight=1)

    def show_active_tunnels(self):
        """Show active tunnels management dialog"""
        tunnels_window = tk.Toplevel(self.root)
        tunnels_window.title("Active Tunnels")
        tunnels_window.geometry("750x450")
        tunnels_window.transient(self.root)
        tunnels_window.grab_set()

        # Main frame
        main_frame = ttk.Frame(tunnels_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(main_frame, text="Active Tunnels", font=("", 12, "bold")).pack(pady=(0, 10))

        # Tunnels list
        columns = ("Type", "Local Port", "Description", "Status")
        tunnels_tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            tunnels_tree.heading(col, text=col)
            tunnels_tree.column(col, width=120)

        # Scrollbar for tunnels list
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tunnels_tree.yview)
        tunnels_tree.configure(yscrollcommand=scrollbar.set)

        # Pack tree and scrollbar
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tunnels_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_tunnels():
            """Refresh the tunnels list"""
            # Clear existing items
            for item in tunnels_tree.get_children():
                tunnels_tree.delete(item)

            # Get active tunnels
            active_tunnels = self.connection_manager.get_active_tunnels()
            
            if not active_tunnels:
                tunnels_tree.insert("", tk.END, values=("No active tunnels", "", "", ""))
                return

            for tunnel_id, tunnel_info in active_tunnels.items():
                tunnel_type = tunnel_info['type']
                port = tunnel_info['port']
                process = tunnel_info['process']
                
                # Determine status
                if process is None:
                    # Terminal-launched tunnel - check if port is in use
                    if self.connection_manager.is_terminal_tunnel_active(port):
                        status = "Active (Terminal)"
                    else:
                        status = "Inactive (Terminal)"
                elif process.poll() is None:
                    status = "Running"
                else:
                    status = "Stopped"

                # Create description
                description = f"localhost:{port}"
                
                tunnels_tree.insert("", tk.END, values=(tunnel_type, port, description, status), tags=(tunnel_id,))

        def close_selected_tunnel():
            """Close the selected tunnel"""
            selected_items = tunnels_tree.selection()
            if not selected_items:
                messagebox.showwarning("Warning", "Please select a tunnel to close")
                return

            selected_item = selected_items[0]
            tunnel_id = tunnels_tree.item(selected_item, "tags")[0]
            
            if tunnel_id and tunnel_id != "No active tunnels":
                self.connection_manager.release_tunnel(tunnel_id)
                refresh_tunnels()
                self.status_var.set(f"Closed tunnel: {tunnel_id}")

        def close_all_tunnels():
            """Close all tunnels"""
            self.connection_manager.cleanup_tunnels()
            refresh_tunnels()
            self.status_var.set("All tunnels closed")

        def remove_inactive_tunnels():
            """Remove inactive terminal tunnels from tracking"""
            removed_count = 0
            tunnel_ids = list(self.connection_manager.tunnel_processes.keys())
            
            for tunnel_id in tunnel_ids:
                tunnel_info = self.connection_manager.tunnel_processes[tunnel_id]
                process = tunnel_info['process']
                port = tunnel_info['port']
                
                # Only remove terminal tunnels that are inactive
                if process is None and not self.connection_manager.is_terminal_tunnel_active(port):
                    self.connection_manager.release_tunnel(tunnel_id)
                    removed_count += 1
            
            refresh_tunnels()
            if removed_count > 0:
                self.status_var.set(f"Removed {removed_count} inactive tunnel(s)")
            else:
                self.status_var.set("No inactive tunnels found")

        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(buttons_frame, text="Refresh", command=refresh_tunnels).pack(pady=2, fill=tk.X)
        ttk.Button(buttons_frame, text="Close Selected", command=close_selected_tunnel).pack(pady=2, fill=tk.X)
        ttk.Button(buttons_frame, text="Remove Inactive", command=remove_inactive_tunnels).pack(pady=2, fill=tk.X)
        ttk.Button(buttons_frame, text="Close All", command=close_all_tunnels).pack(pady=2, fill=tk.X)
        ttk.Button(buttons_frame, text="Close Window", command=tunnels_window.destroy).pack(pady=2, fill=tk.X)

        # Initial refresh
        refresh_tunnels()

    def browse_file(self, var):
        """Browse for a file and update the given StringVar"""
        filename = filedialog.askopenfilename()
        if filename:
            var.set(filename)

    def cleanup(self):
        """Clean up resources on exit"""
        self.connection_manager.cleanup_tunnels()


def main():
    """
    Main application entry point.
    
    Creates the main tkinter window, initializes the MainWindow application,
    sets up proper cleanup handling for window close events, and starts
    the tkinter event loop.
    
    The cleanup handler ensures that all active tunnels are properly
    terminated when the application is closed.
    """
    root = tk.Tk()
    app = MainWindow(root)
    
    def on_closing():
        """Handle application close event with proper cleanup."""
        app.cleanup()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()