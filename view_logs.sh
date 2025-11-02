#!/bin/bash
# Script to view logs in real-time

echo "Viewing app logs..."
echo "Press Ctrl+C to stop"
echo "========================"

if [ -f "tmp/app.log" ]; then
    tail -f tmp/app.log
else
    echo "Log file tmp/app.log not found. Run the app first."
fi

