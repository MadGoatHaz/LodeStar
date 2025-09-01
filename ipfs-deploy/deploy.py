import os
import ipfshttpclient
from pathlib import Path

def deploy_to_ipfs():
    """Deploy frontend to IPFS and output gateway URL"""
    IPFS_CLIENT = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
    
    # Add frontend directory to IPFS
    ipfs_hash = IPFS_CLIENT.add('frontend', recursive=True)
    print(f"Frontend deployed to IPFS: {ipfs_hash}")
    
    # Generate public gateway URL
    gateway_url = f"https://ipfs.io/ipfs/{ipfs_hash}"
    print(f"Public URL: {gateway_url}")
    
    # Save to deployment log
    with open('ipfs-deploy/deployment.log', 'a') as log:
        log.write(f"{os.getenv('DATE', 'now')}: {gateway_url}\n")

if __name__ == "__main__":
    deploy_to_ipfs()