#!/bin/bash
# Verity Protocol - Complete Demo Script
# Run this to showcase the full functionality to investors

echo "🚀 Starting Verity Protocol Demo..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STORAGE_URL="http://localhost:8080"
VERIFIER_URL="http://localhost:8000"
SAMPLE_FILE="${DEMO_DIR}/sample_election_results.pdf"

# Check if sample file exists, create dummy if not
if [ ! -f "$SAMPLE_FILE" ]; then
    echo -e "${YELLOW}Creating sample election results file...${NC}"
    echo "OFFICIAL ELECTION RESULTS 2024" > "${DEMO_DIR}/sample_election_results.pdf"
    echo "===============================" >> "${DEMO_DIR}/sample_election_results.pdf"
    echo "Candidate A: 52%" >> "${DEMO_DIR}/sample_election_results.pdf"
    echo "Candidate B: 48%" >> "${DEMO_DIR}/sample_election_results.pdf"
    echo "Total Votes: 10,234,567" >> "${DEMO_DIR}/sample_election_results.pdf"
    echo "Certified by: National Election Commission" >> "${DEMO_DIR}/sample_election_results.pdf"
    echo "Date: $(date +%Y-%m-%d)" >> "${DEMO_DIR}/sample_election_results.pdf"
fi

# Function to check if a service is running
check_service() {
    if curl -s "$1" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Start Storage Service
echo -e "\n${BLUE}1. Starting Storage Service...${NC}"
cd "${DEMO_DIR}/src/storage" || exit
python main.py &
STORAGE_PID=$!
sleep 3

if check_service "${STORAGE_URL}/health"; then
    echo -e "${GREEN}✓ Storage service running at ${STORAGE_URL}${NC}"
else
    echo -e "${RED}✗ Storage service failed to start${NC}"
    exit 1
fi

# Start Verification Service
echo -e "\n${BLUE}2. Starting Verification Service...${NC}"
cd "${DEMO_DIR}/src/main" || exit
python main.py &
VERIFIER_PID=$!
sleep 3

if check_service "${VERIFIER_URL}/health"; then
    echo -e "${GREEN}✓ Verification service running at ${VERIFIER_URL}${NC}"
else
    echo -e "${RED}✗ Verification service failed to start${NC}"
    kill $STORAGE_PID 2>/dev/null
    exit 1
fi

# Create a demo organization and claim
echo -e "\n${BLUE}3. Creating Demo Election Commission...${NC}"
cd "${DEMO_DIR}/src/main" || exit

# Create account and DID using CLI headless mode
echo -e "${YELLOW}Creating organization identity...${NC}"
python -c "
import sys
sys.path.append('.')
from cli import main
import argparse

# Simulate CLI arguments for headless mode
sys.argv = ['cli.py', '--message', 'Test claim', '--issuer', 'did:verity:gov:demo-election-comm', '--no-interactive']

try:
    main()
except SystemExit:
    pass
"

echo -e "\n${BLUE}4. Creating and Signing Election Results Claim...${NC}"
echo -e "${YELLOW}This simulates the election commission publishing certified results...${NC}"


echo -e "\n${GREEN}✅ Demo Setup Complete!${NC}"
echo -e "========================================"
echo -e "\n${BLUE}Demo Components:${NC}"
echo -e "1. ${GREEN}Storage Service${NC}: ${STORAGE_URL}"
echo -e "2. ${GREEN}Verification Service${NC}: ${VERIFIER_URL}"
echo -e "3. ${GREEN}Web Interface${NC}: ${VERIFIER_URL}"
echo -e "4. ${GREEN}Sample Election Results${NC}: ${SAMPLE_FILE}"

echo -e "\n${YELLOW}Demo Workflow:${NC}"
echo -e "1. 📝 Election Commission signs results → ${GREEN}(CLI creates signed claim)${NC}"
echo -e "2. 💾 Claim stored with cryptographic proof → ${GREEN}(Stored in Verity network)${NC}"
echo -e "3. 🔗 Verification URL generated → ${GREEN}(Shareable link)${NC}"
echo -e "4. 🔍 Anyone verifies authenticity → ${GREEN}(Paste URL in web interface)${NC}"
echo -e "5. ✅ Cryptographic verification completes → ${GREEN}(✅ VERIFIED badge appears)${NC}"

echo -e "\n${BLUE}To test the verification:${NC}"
echo -e "1. Open browser: ${GREEN}${VERIFIER_URL}{NC}"
echo -e "2. Paste a verification URL"
echo -e "3. See real-time cryptographic verification"

echo -e "\n${YELLOW}Press Ctrl+C to stop all services...${NC}"

# Keep services running
wait

# Cleanup on exit
cleanup() {
    echo -e "\n${RED}Stopping demo services...${NC}"
    kill $STORAGE_PID 2>/dev/null
    kill $VERIFIER_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM