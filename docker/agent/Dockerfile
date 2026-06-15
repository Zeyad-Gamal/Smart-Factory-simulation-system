# FROM python:3.11-slim

# WORKDIR /app

# # Install dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy app
# COPY agent.py .

# # Environment variables
# ENV SOC_BASE_URL="http://soc-service:5000"
# ENV OLLAMA_URL="http://ollama-service:11434"
# ENV MODEL="llama3.2"
# ENV POLL_INTERVAL="30"
# ENV MAX_LOGS_BATCH="20"

# CMD ["python", "agent.py"]


FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY agent.py .

# Environment variables (CLOUD LLM ONLY)
ENV SOC_BASE_URL="http://soc-service:5000"
ENV OPENAI_BASE_URL="https://openrouter.ai/api/v1"
ENV MODEL="meta-llama/llama-3.2-3b-instruct:free"

ENV POLL_INTERVAL="30"
ENV MAX_LOGS_BATCH="20"

CMD ["python", "agent.py"]
