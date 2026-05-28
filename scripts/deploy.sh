#!/bin/bash

echo "=============================="
echo "Starting Deployment"
echo "=============================="

# Update packages
yum update -y

# Install nginx if missing
yum install nginx -y

# Restart nginx
systemctl restart nginx

# Enable nginx on boot
systemctl enable nginx

echo "Deployment completed successfully"