FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY agent.py .

# Environment variables
ENV SOC_BASE_URL="http://soc-service:5000"
ENV OLLAMA_URL="http://ollama-service:11434"
ENV MODEL="llama3.2"
ENV POLL_INTERVAL="30"
ENV MAX_LOGS_BATCH="20"

CMD ["python", "agent.py"]