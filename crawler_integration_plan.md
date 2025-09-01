# Lodestar Crawler Integration Plan

## Current Issues

1. **IPFS Connectivity**: The WebSocket server and crawler are having issues connecting to IPFS due to version incompatibility
2. **Content Broadcasting**: Crawled content is not being broadcasted to the frontend
3. **Frontend Display**: The frontend is not receiving or displaying crawled content

## Integration Steps

### Step 1: Fix IPFS Connectivity
The current IPFS client version is incompatible with the installed IPFS daemon. We need to:
1. Update the ipfshttpclient library to a compatible version
2. Modify the connection parameters to work with the current IPFS daemon

### Step 2: Implement Content Broadcasting
The crawler stores content to IPFS but doesn't notify the WebSocket server to broadcast it. We need to:
1. Modify the `store_to_ipfs` function to notify the WebSocket server
2. Create a mechanism for the crawler to communicate with the WebSocket server

### Step 3: Enhance Frontend Display
The frontend needs to properly display PolitiFact content. We need to:
1. Verify the content processing in the WebSocket server
2. Ensure the frontend can render PolitiFact content correctly

## Detailed Implementation

### 1. IPFS Connectivity Fix
```python
# In websocket_server.py and crawler.py
# Update IPFS client connection
try:
    # Try connecting with version check disabled
    self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001', offline=True)
except Exception as e:
    print(f"Could not connect to IPFS: {e}")
    # Fallback to offline mode for testing
    self.ipfs_client = None
```

### 2. Content Broadcasting Implementation
We need to modify the crawler to notify the WebSocket server when new content is stored:

```python
# In crawler.py
def store_to_ipfs(data):
    """Store data as IPFS object with signature verification"""
    # ... existing code ...
    
    if ipfs_hash and hasattr(store_to_ipfs, 'websocket_server'):
        # Notify WebSocket server about new content
        store_to_ipfs.websocket_server.add_content(ipfs_hash)
    
    return ipfs_hash
```

### 3. Frontend Display Enhancement
The WebSocket server already has logic to process PolitiFact content, but we need to ensure it's working correctly:

```python
# In websocket_server.py
def _process_content(self, content, ipfs_hash):
    """Process content for broadcasting"""
    # ... existing code ...
    
    # Enhanced PolitiFact processing
    if content.get('type') == 'politifact':
        broadcast_data['title'] = content.get('title', 'PolitiFact Article')
        broadcast_data['summary'] = f"{content.get('claim', '')} - Rating: {content.get('rating', 'Unknown')}"
        broadcast_data['claim'] = content.get('claim', '')
        broadcast_data['rating'] = content.get('rating', 'Unknown')
        
    # ... existing code ...
```

## Testing Plan

1. Run the IPFS daemon separately to ensure it's working
2. Test the crawler with a simple PolitiFact crawl
3. Verify content is stored in IPFS
4. Check that the WebSocket server receives and broadcasts the content
5. Confirm the frontend displays the content correctly

## Next Steps

1. First, we'll create a simple test to verify IPFS connectivity
2. Then, we'll implement the content broadcasting mechanism
3. Finally, we'll test the entire pipeline from crawl to display