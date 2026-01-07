#!/bin/bash

# Script to kill processes running on specified ports
# Usage: ./kill_ports.sh [port1] [port2] [port3] ...
# Example: ./kill_ports.sh 6801 6802
# bash ./scripts/kill_ports.sh  6801
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to kill a process on a specific port
kill_port() {
    local port=$1

    # Find process using the port
    local pid=$(lsof -ti:$port 2>/dev/null)

    if [ -z "$pid" ]; then
        echo -e "${YELLOW}⚠️  Port $port: No process found${NC}"
        return 1
    fi

    # Get process name
    local process_name=$(ps -p $pid -o comm= 2>/dev/null)

    echo -e "${YELLOW}🔍 Port $port: Found process PID=$pid ($process_name)${NC}"

    # Try graceful shutdown first (SIGTERM)
    kill $pid 2>/dev/null

    # Wait up to 3 seconds for graceful shutdown
    local count=0
    while [ $count -lt 3 ]; do
        if ! kill -0 $pid 2>/dev/null; then
            echo -e "${GREEN}✅ Port $port: Process killed successfully (graceful)${NC}"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done

    # If still running, force kill (SIGKILL)
    if kill -0 $pid 2>/dev/null; then
        echo -e "${YELLOW}⚡ Port $port: Force killing...${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1

        if ! kill -0 $pid 2>/dev/null; then
            echo -e "${GREEN}✅ Port $port: Process force killed${NC}"
            return 0
        else
            echo -e "${RED}❌ Port $port: Failed to kill process${NC}"
            return 1
        fi
    fi
}

# Main script
echo "========================================="
echo "🔪 Kill Processes on Ports"
echo "========================================="
echo ""

# Default ports if no arguments provided
if [ $# -eq 0 ]; then
    PORTS=(6801 6802)
    echo "No ports specified. Using defaults: ${PORTS[@]}"
else
    PORTS=("$@")
fi

echo "Target ports: ${PORTS[@]}"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0
NOT_FOUND_COUNT=0

# Kill each port
for port in "${PORTS[@]}"; do
    # Validate port number
    if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        echo -e "${RED}❌ Invalid port number: $port${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    kill_port $port
    result=$?

    if [ $result -eq 0 ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    elif [ $result -eq 1 ]; then
        NOT_FOUND_COUNT=$((NOT_FOUND_COUNT + 1))
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo ""
done

# Summary
echo "========================================="
echo "📊 SUMMARY"
echo "========================================="
echo -e "${GREEN}✅ Successfully killed: $SUCCESS_COUNT${NC}"
echo -e "${YELLOW}⚠️  Not found: $NOT_FOUND_COUNT${NC}"
echo -e "${RED}❌ Failed: $FAIL_COUNT${NC}"
echo ""

# Verify all ports are free
echo "Verifying ports are free..."
echo ""
ALL_FREE=true
for port in "${PORTS[@]}"; do
    if lsof -i:$port >/dev/null 2>&1; then
        echo -e "${RED}❌ Port $port still in use!${NC}"
        ALL_FREE=false
    else
        echo -e "${GREEN}✅ Port $port is free${NC}"
    fi
done

echo ""
if [ "$ALL_FREE" = true ]; then
    echo -e "${GREEN}🎉 All ports are now free!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some ports are still in use. Manual intervention may be required.${NC}"
    exit 1
fi
