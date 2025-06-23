#!/bin/bash

# Karaoke Backend - Script Runner
# Simple wrapper to run management scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Available commands
COMMANDS=("start" "stop" "restart" "setup" "health")

show_help() {
    echo -e "${GREEN}🎤 Karaoke Backend - Script Runner${NC}"
    echo -e "${BLUE}Usage: $0 <command>${NC}"
    echo -e "\n${BLUE}Available commands:${NC}"
    echo -e "  ${YELLOW}start${NC}    - Start the server and worker"
    echo -e "  ${YELLOW}stop${NC}     - Stop all services"
    echo -e "  ${YELLOW}restart${NC}  - Clean restart (flushes database)"
    echo -e "  ${YELLOW}setup${NC}    - Initial development setup"
    echo -e "  ${YELLOW}health${NC}   - Check system health"
    echo -e "\n${BLUE}Examples:${NC}"
    echo -e "  $0 start"
    echo -e "  $0 health"
    echo -e "  $0 restart"
    echo -e "\n${BLUE}For more details, see: ${YELLOW}scripts/SCRIPTS_README.md${NC}"
}

# Check if command provided
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

COMMAND=$1

# Execute the appropriate script
case $COMMAND in
    "start")
        exec ./scripts/start_server.sh
        ;;
    "stop")
        exec ./scripts/stop_server.sh
        ;;
    "restart")
        exec ./scripts/restart_clean.sh
        ;;
    "setup")
        exec ./scripts/dev_setup.sh
        ;;
    "health")
        exec ./scripts/health_check.sh
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $COMMAND${NC}"
        echo -e "${YELLOW}💡 Run '$0 help' to see available commands${NC}"
        exit 1
        ;;
esac 