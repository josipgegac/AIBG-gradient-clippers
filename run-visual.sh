#!/bin/bash

# Define a cleanup function
cleanup() {
  echo "Cleaning up..."
  # Kill all child processes of this script
  pkill -P $$
  exit 0
}

# Trap EXIT, SIGINT (Ctrl+C), and SIGTERM to run cleanup
trap cleanup EXIT SIGINT SIGTERM

# Start server
cd server || exit 1
npm i
node server.js &
SERVER_PID=$!

# Wait for the server to start
while ! nc -z localhost 3000; do
  sleep 10
done

# Start client
cd ../clients || exit 1
npm i
node agent.js o apple &
CLIENT_PID=$!

# Wait for background jobs (optional: remove these waits if you want the script to exit immediately)
wait $SERVER_PID
wait $CLIENT_PID
