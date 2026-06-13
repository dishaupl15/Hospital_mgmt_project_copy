# deploy.sh

#!/bin/bash

echo "=============================="
echo "Starting Deployment"
echo "=============================="

yum update -y

yum install nginx -y

systemctl enable nginx

systemctl restart nginx

echo "Deployment completed successfully"
