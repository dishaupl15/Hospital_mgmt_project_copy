#!/bin/bash

yum update -y

yum install nginx -y
yum install git -y
yum install nodejs -y

systemctl start nginx
systemctl enable nginx