#!/bin/bash

ollama serve &
PID=$!

echo "Waiting for Ollama to start..."
sleep 10

if ! ollama list | grep -q "llama3.2"; then
    echo "Pulling llama3.2..."
    ollama pull llama3.2
fi

wait $PID
