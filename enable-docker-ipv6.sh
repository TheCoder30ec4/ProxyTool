#!/bin/bash

# Script to enable IPv6 in Docker
# This requires sudo privileges

echo "Creating /etc/docker/daemon.json with IPv6 configuration..."

# Create the directory if it doesn't exist
sudo mkdir -p /etc/docker

# Create or update daemon.json with IPv6 configuration
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "ipv6": true,
  "fixed-cidr-v6": "2001:db8:1::/64"
}
EOF

echo "Configuration file created. Contents:"
sudo cat /etc/docker/daemon.json

echo ""
echo "Restarting Docker service..."
sudo systemctl restart docker

echo "Waiting for Docker to restart..."
sleep 3

echo ""
echo "Checking IPv6 status:"
docker info | grep -A 5 "IPv6" || echo "IPv6 information not found in docker info"

echo ""
echo "Done! Docker IPv6 should now be enabled."
echo "You can now run your container and it should be able to connect to Supabase via IPv6."



