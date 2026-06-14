#!/bin/bash

# Start Ollama server in the background
ollama serve &
PID=$!

echo "Waiting for Ollama to start..."
# Native Bash way to loop until port 11434 answers locally
while ! exec 3<>/dev/tcp/127.0.0.1/11434 2>/dev/null; do   
  sleep 1
done
# Clean up the file descriptor
exec 3>&-

if ! ollama list | grep -q "llama3.2"; then
    echo "Pulling llama3.2..."
    ollama pull llama3.2
fi

# Keep container alive tracking the main process
wait $PID

