#!/bin/bash

cd /home/ec2-user/Agentic-Health-Monitor/agentic-health-monitor/backend

export GROQ_API_KEY=$(aws ssm get-parameter --name "/agentic-health/prod/groq-api-key" --with-decryption --query "Parameter.Value" --output text)

# Start FastAPI backend
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# Start React frontend
cd ../frontend
nohup npm run dev -- --host 0.0.0.0 > frontend.log 2>&1 &