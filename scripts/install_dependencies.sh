# #!/bin/bash

# cd /home/ec2-user/Agentic-Health-Monitor/agentic-health-monitor

# sudo yum update -y

# # Install Python 3.11 properly
# sudo amazon-linux-extras enable python3.11
# sudo yum install -y python3.11 python3.11-pip

# # Set python3 to python3.11
# sudo alternatives --set python3 /usr/bin/python3.11

# # Upgrade pip
# python3 -m pip install --upgrade pip

# # Install Node.js properly
# curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
# sudo yum install -y nodejs

# # Verify installations
# python3 --version
# node -v
# npm -v

# # Backend setup
# cd backend
# pip3 install -r requirements.txt

# # Frontend setup
# cd ../frontend
# npm install
# npm run build

#!/bin/bash

cd /home/ec2-user/Agentic-Health-Monitor

npm install

npm run build

sudo rm -rf /usr/share/nginx/html/*

sudo cp -r dist/* /usr/share/nginx/html/