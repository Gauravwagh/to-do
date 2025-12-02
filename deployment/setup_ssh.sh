#!/bin/bash

# SSH Key Setup Script

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== SSH Key Setup ===${NC}"
echo ""

# Check if SSH key exists
if [ -f ~/.ssh/id_rsa.pub ]; then
    echo -e "${YELLOW}SSH key already exists at ~/.ssh/id_rsa.pub${NC}"
    echo ""
    cat ~/.ssh/id_rsa.pub
else
    echo -e "${YELLOW}Generating new SSH key...${NC}"
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
    echo -e "${GREEN}✓ SSH key generated${NC}"
    echo ""
    cat ~/.ssh/id_rsa.pub
fi

echo ""
echo -e "${YELLOW}Now copying SSH key to server (you'll need to enter password once)...${NC}"
ssh-copy-id -i ~/.ssh/id_rsa.pub root@46.224.109.101

echo ""
echo -e "${GREEN}✓ SSH key copied to server!${NC}"
echo ""
echo "You can now run the deployment script without password prompts:"
echo "  ./deploy.sh"
