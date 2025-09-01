from flask import Flask
from flask_socketio import SocketIO, emit
import json
import threading
import queue
import ipfshttpclient

class WebSocketServer:
    def __init__(self, port=5001):
        """Initialize WebSocket server"""
        self.port = port
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'lodestar_secret_key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Try to connect to IPFS
        try:
            self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001', offline=True)
        except Exception as e:
            print(f"Could not connect to IPFS: {e}")
            self.ipfs_client = None
            
        self.content_queue = queue.Queue()
        
        # Set up event handlers
        self.socketio.on_event('connect', self.handle_connect)
        self.socketio.on_event('disconnect', self.handle_disconnect)
        self.socketio.on_event('subscribe_preferences', self.handle_preferences)
        
        # Start content broadcasting thread
        self.broadcast_thread = threading.Thread(target=self._broadcast_worker)
        self.broadcast_thread.daemon = True
        self.broadcast_thread.start()
        
    def handle_connect(self):
        """Handle client connection"""
        print('Client connected')
        emit('status', {'msg': 'Connected to Lodestar real-time server'})
        
    def handle_disconnect(self):
        """Handle client disconnection"""
        print('Client disconnected')
        
    def handle_preferences(self, data):
        """Handle user preference subscription"""
        print(f'User preferences: {data}')
        emit('preferences_ack', {'status': 'Preferences received'})
        
    def add_content(self, ipfs_hash):
        """Add verified content to broadcast queue"""
        self.content_queue.put(ipfs_hash)
        
    def _broadcast_worker(self):
        """Worker thread for broadcasting content to clients"""
        while True:
            try:
                # Get IPFS hash from queue
                ipfs_hash = self.content_queue.get()
                
                # Get content from IPFS
                if self.ipfs_client:
                    content = self.ipfs_client.get_json(ipfs_hash)
                else:
                    # Fallback for when IPFS is not available
                    content = {
                        'type': 'test',
                        'title': 'Test Content',
                        'text': 'This is a test message',
                        'source': 'Test',
                        'timestamp': '2025-01-01T00:00:00Z'
                    }
                
                # Process content for broadcasting
                broadcast_data = self._process_content(content, ipfs_hash)
                
                # Broadcast to all connected clients
                self.socketio.emit('content_update', broadcast_data)
                print(f"Broadcasted content: {ipfs_hash}")
                
                # Mark task as done
                self.content_queue.task_done()
                
            except Exception as e:
                print(f"Error in broadcast worker: {e}")
                
    def _process_content(self, content, ipfs_hash):
        """Process content for broadcasting"""
        # Extract relevant fields for frontend
        broadcast_data = {
            'id': ipfs_hash,
            'type': content.get('type', 'unknown'),
            'title': content.get('title', ''),
            'summary': content.get('text', '')[:200] + '...' if content.get('text') else '',
            'source': content.get('source', ''),
            'timestamp': content.get('timestamp', ''),
            'ipfs_hash': ipfs_hash
        }
        
        # Add specific fields based on content type
        if content.get('type') == 'tweet':
            broadcast_data['title'] = f"Tweet from @{content.get('user', '')}"
            broadcast_data['summary'] = content.get('text', '')[:280]
        elif content.get('type') == 'brave_search':
            broadcast_data['title'] = content.get('title', 'Search Result')
        elif content.get('type') == 'politifact':
            broadcast_data['title'] = content.get('title', 'PolitiFact Article')
            broadcast_data['summary'] = f"{content.get('claim', '')} - Rating: {content.get('rating', 'Unknown')}"
        elif content.get('type') == 'groundnews':
            broadcast_data['title'] = content.get('title', 'Ground News Article')
            
        return broadcast_data
        
    def run(self):
        """Start the WebSocket server"""
        print(f"Starting WebSocket server on port {self.port}")
        self.socketio.run(self.app, port=self.port, host='0.0.0.0')

# Integration with existing API
def integrate_with_api(api_app, websocket_server):
    """Integrate WebSocket server with existing API"""
    
    @api_app.route('/api/broadcast_test')
    def broadcast_test():
        """Test endpoint for broadcasting content"""
        websocket_server.add_content('test_hash')
        return {'status': 'Test broadcast sent'}
        
    # Make websocket_server available to other parts of the application
    api_app.websocket_server = websocket_server

# Example usage
if __name__ == "__main__":
    server = WebSocketServer()
    server.run()