# EC2 Instance Connect Manager

**EC2 Instance Connect Manager** is a GUI application that simplifies connecting to EC2 instances via [AWS EC2 Instance Connect](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html). Instead of using the AWS CLI, users can browse their instances and initiate secure sessions with just a few clicks.

---

## Features

- 📁 Loads AWS profiles from `~/.aws/config`
- 🔐 Authenticates to the selected profile using the AWS CLI
- 💻 Lists EC2 instances from the chosen AWS account/region
- 🔌 Initiates an EC2 Instance Connect session and assigns a random local port
- 🚀 Automatically launches your default RDP client to connect
- 🪟 Available for both macOS (.dmg) and Windows (.exe)

---

## Requirements

- Python **3.13+**
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) (configured with appropriate IAM permissions)

---

## Installation

### macOS

1. Download the `.dmg` file from the [Releases](#) page.
2. Open the `.dmg` and drag the app into your `Applications` folder.
3. Launch the app from Launchpad or Finder.

### Windows

1. Download the `.exe` installer from the [Releases](#) page.
2. Run the installer and follow the setup instructions.
3. Launch the app from the Start menu or Desktop shortcut.

---

## Usage

1. Ensure you have valid AWS credentials set up in `~/.aws/config` or via the AWS CLI.
2. Open **EC2 Instance Connect Manager**.
3. Select the AWS profile you'd like to use.
4. Browse available EC2 instances.
5. Click **Connect** — your default RDP client will open once the session is established.

---

## Notes

- Make sure your IAM user/role has the necessary EC2 permissions, such as:
  - `ec2:DescribeInstances`
  - `ec2-instance-connect:SendSSHPublicKey`
- The app uses a random local port to tunnel RDP traffic securely through the EC2 instance connect session.

---

## License

MIT License  
© 2025 Prison Fellowship

---

## Contributing

Pull requests and issues are welcome! Please open an issue to discuss any changes or feature requests.

---

## Build Steps  

1. Clone repo  
2. Install Python app packager (py2app for MacOS and pyinstaller for Windows)  
3. Install requirements  
4. Run package command:  
   a. For MacOS: python setup.py py2app (You may need to add the "--deep" option to the _dosign function in ./venv/lib/python3.13/site-packages/py2app/util.py)  
   b. For Windows: pyinstaller --onefile --windowed --icon=icon.ico EC2ICManager.py  

---
