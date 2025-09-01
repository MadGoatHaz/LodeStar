from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from verifier import DataVerifier
from websocket_server import WebSocketServer, integrate_with_api
from flagging_service import FlaggingService
from search_api import SearchAPI
from historical_api import HistoricalAPI
from volunteer_dashboard_api import VolunteerDashboardAPI
import os
import threading

app = Flask(__name__)
verifier = DataVerifier()
flagging_service = FlaggingService()

# Initialize WebSocket server
websocket_server = WebSocketServer()

# Integrate WebSocket server with API
integrate_with_api(app, websocket_server)

# Initialize Search API
search_api = SearchAPI()
search_api.init_app(app)

# Initialize Historical API
historical_api = HistoricalAPI()
historical_api.init_app(app)

# Initialize Volunteer Dashboard API
volunteer_api = VolunteerDashboardAPI(app)

# Start WebSocket server in a separate thread
def start_websocket_server():
    websocket_server.run()

ws_thread = threading.Thread(target=start_websocket_server)
ws_thread.daemon = True
ws_thread.start()

@app.route('/api/verify', methods=['POST'])
def verify_data():
    """API endpoint for verifying IPFS data"""
    try:
        data = request.get_json()
        ipfs_hash = data.get('ipfs_hash')
        
        if not ipfs_hash:
            return jsonify({'error': 'Missing ipfs_hash parameter'}), 400
        
        # Verify the data
        is_verified = verifier.verify_ipfs_data(ipfs_hash)
        
        # If verified, add to broadcast queue
        if is_verified:
            websocket_server.add_content(ipfs_hash)
        
        return jsonify({
            'ipfs_hash': ipfs_hash,
            'verified': is_verified
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add_trusted_key', methods=['POST'])
def add_trusted_key():
    """API endpoint for adding trusted keys"""
    try:
        data = request.get_json()
        public_key = data.get('public_key')
        
        if not public_key:
            return jsonify({'error': 'Missing public_key parameter'}), 400
        
        verifier.add_trusted_key(public_key)
        
        return jsonify({'status': 'success', 'message': 'Trusted key added'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def system_status():
    """API endpoint for system status"""
    try:
        # Get number of trusted keys
        trusted_keys_count = len(verifier.trusted_keys)
        
        # Get IPFS connection status
        try:
            ipfs_version = verifier.ipfs_client.version()
            ipfs_connected = True
        except:
            ipfs_version = None
            ipfs_connected = False
        
        return jsonify({
            'trusted_keys_count': trusted_keys_count,
            'ipfs_connected': ipfs_connected,
            'ipfs_version': ipfs_version
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Flagging API endpoints
@app.route('/api/flag', methods=['POST'])
def submit_flag():
    """API endpoint for submitting content flags"""
    try:
        data = request.get_json()
        ipfs_hash = data.get('ipfs_hash')
        reason = data.get('reason')
        description = data.get('description', '')
        user_id = data.get('user_id')
        
        if not ipfs_hash or not reason:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        result = flagging_service.submit_flag(
            ipfs_hash=ipfs_hash,
            reason=reason,
            description=description,
            user_id=user_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/flags/<ipfs_hash>')
def get_flags_for_content(ipfs_hash):
    """API endpoint for getting flags for specific content"""
    try:
        flags = flagging_service.get_flags_for_content(ipfs_hash)
        return jsonify({'flags': flags})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/flags')
def get_all_flags():
    """API endpoint for getting all flags (moderator only)"""
    try:
        status = request.args.get('status')
        flags = flagging_service.get_all_flags(status)
        return jsonify({'flags': flags})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/moderation/queue')
def get_moderation_queue():
    """API endpoint for getting moderation queue (moderator only)"""
    try:
        queue = flagging_service.get_moderation_queue()
        return jsonify({'queue': queue})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/moderation/action', methods=['POST'])
def update_flag_status():
    """API endpoint for updating flag status (moderator only)"""
    try:
        data = request.get_json()
        flag_id = data.get('flag_id')
        status = data.get('status')
        moderator_id = data.get('moderator_id')
        
        if not flag_id or not status:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        result = flagging_service.update_flag_status(
            flag_id=flag_id,
            status=status,
            moderator_id=moderator_id
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)