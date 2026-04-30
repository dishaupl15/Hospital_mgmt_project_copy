#!/bin/bash

cd /home/ec2-user/Agentic-Health-Monitor/agentic-health-monitor

sudo yum update -y

# Install Python
sudo yum install -y python3
sudo pip3 install --upgrade pip

# Install Node.js properly
curl -sL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Backend setup
cd backend
pip3 install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
npm run build