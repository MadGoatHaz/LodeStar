import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
import ipfshttpclient

class DataVerifier:
    def __init__(self, trusted_keys_file='trusted_keys.json'):
        """Initialize verifier with trusted public keys"""
        self.trusted_keys_file = trusted_keys_file
        self.trusted_keys = self.load_trusted_keys()
        self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
    
    def load_trusted_keys(self):
        """Load trusted public keys from JSON file"""
        try:
            with open(self.trusted_keys_file, 'r') as f:
                data = json.load(f)
                return [key.encode('utf-8') for key in data['keys']]
        except FileNotFoundError:
            print(f"Warning: {self.trusted_keys_file} not found. No trusted keys loaded.")
            return []
        except Exception as e:
            print(f"Error loading trusted keys: {e}")
            return []
    
    def verify_signature(self, data, signature_b64, public_key_pem):
        """Verify signature using a specific public key"""
        try:
            # Remove signature from data for verification
            data_copy = data.copy()
            if 'signature' in data_copy:
                del data_copy['signature']
            
            # Convert data to JSON string for verification
            json_data = json.dumps(data_copy, sort_keys=True).encode('utf-8')
            
            # Decode signature
            signature = base64.b64decode(signature_b64)
            
            # Load public key
            public_key = serialization.load_pem_public_key(public_key_pem)
            
            # Verify signature
            public_key.verify(
                signature,
                json_data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            # Signature verification failed
            return False
    
    def verify_ipfs_data(self, ipfs_hash):
        """Verify data from IPFS using trusted keys"""
        try:
            # Get data from IPFS
            data = self.ipfs_client.get_json(ipfs_hash)
            
            # Check if data has signature
            if 'signature' not in data:
                print(f"Data {ipfs_hash} has no signature")
                return False
            
            # Try to verify with each trusted key
            signature = data['signature']
            for public_key_pem in self.trusted_keys:
                if self.verify_signature(data, signature, public_key_pem):
                    print(f"Data {ipfs_hash} verified with trusted key")
                    return True
            
            # No trusted key could verify the data
            print(f"Data {ipfs_hash} signature not verified by any trusted key")
            return False
            
        except Exception as e:
            print(f"Error verifying IPFS data {ipfs_hash}: {e}")
            return False
    
    def add_trusted_key(self, public_key_pem):
        """Add a new trusted public key"""
        if isinstance(public_key_pem, str):
            public_key_pem = public_key_pem.encode('utf-8')
            
        if public_key_pem not in self.trusted_keys:
            self.trusted_keys.append(public_key_pem)
            self.save_trusted_keys()
            print("Trusted key added successfully")
        else:
            print("Key already in trusted list")
    
    def save_trusted_keys(self):
        """Save trusted keys to JSON file"""
        try:
            keys_data = {
                'keys': [key.decode('utf-8') if isinstance(key, bytes) else key for key in self.trusted_keys]
            }
            with open(self.trusted_keys_file, 'w') as f:
                json.dump(keys_data, f, indent=2)
        except Exception as e:
            print(f"Error saving trusted keys: {e}")

# Example usage
if __name__ == "__main__":
    verifier = DataVerifier()
    
    # Example: verify data from IPFS
    # result = verifier.verify_ipfs_data('QmExampleHash')
    # print(f"Verification result: {result}")
    
    # Example: add a new trusted key
    # with open('new_key.pub', 'r') as f:
    #     new_key = f.read()
    # verifier.add_trusted_key(new_key)