# Real-Time Data Aggregation System Design

## Overview
This document outlines the design for Lodestar's real-time data aggregation system, which will continuously monitor IPFS for new content from volunteer crawlers and update the frontend in real-time.

## System Architecture

### 1. IPFS Monitoring Service
- **Component**: ipfs_monitor.py
- **Purpose**: Continuously monitor IPFS for new content hashes
- **Implementation**:
  - Use IPFS pubsub mechanism for distributed notifications
  - Subscribe to a dedicated topic (e.g., "lodestar.new_content")
  - Maintain a local cache of recently processed hashes to avoid duplicates
  - Integrate with the existing DataVerifier for signature validation

### 2. WebSocket Server
- **Component**: websocket_server.py
- **Purpose**: Push real-time updates to connected frontend clients
- **Implementation**:
  - Use Flask-SocketIO for WebSocket support
  - Broadcast verified content to all connected clients
  - Handle client connection/disconnection events
  - Implement room-based subscriptions for content filtering

### 3. Data Synchronization Layer
- **Component**: sync_manager.py
- **Purpose**: Coordinate data flow between IPFS monitoring and WebSocket broadcasting
- **Implementation**:
  - Queue system for processing new content
  - Integration with verification system
  - Content categorization and metadata extraction
  - Error handling and retry mechanisms

### 4. Frontend Integration
- **Component**: frontend/js/realtime.js
- **Purpose**: Receive and display real-time updates in the browser
- **Implementation**:
  - WebSocket client connection to backend
  - Dynamic content rendering without page refresh
  - Notification system for new verified content
  - User preference settings for update frequency

## Data Flow

1. Volunteer crawler publishes new content to IPFS
2. Crawler sends IPFS hash to pubsub topic "lodestar.new_content"
3. IPFS monitoring service receives hash notification
4. Monitor retrieves content from IPFS and queues for verification
5. DataVerifier validates cryptographic signature
6. Verified content is processed and categorized
7. Sync manager pushes content to WebSocket server
8. WebSocket server broadcasts to all connected clients
9. Frontend receives update and dynamically renders new content

## Technical Requirements

### Backend Dependencies
- flask-socketio
- gevent-websocket (for async WebSocket handling)
- Additional IPFS pubsub handling

### Frontend Implementation
- JavaScript WebSocket client
- Dynamic DOM manipulation for new content
- User notification system (optional audio/visual alerts)

## Security Considerations

- Only verified content should be broadcast to clients
- WebSocket connections should be authenticated (if needed)
- Rate limiting to prevent abuse
- Content filtering to prevent inappropriate data from reaching clients

## Scalability Features

- Horizontal scaling of monitoring services
- Load balancing for WebSocket connections
- Caching of frequently accessed content
- Database optimization for content metadata

## Implementation Phases

### Phase 1: Basic IPFS Monitoring
- Implement ipfs_monitor.py with pubsub subscription
- Basic verification integration
- Simple console output for testing

### Phase 2: WebSocket Integration
- Add Flask-SocketIO to api.py
- Create websocket_server.py for content broadcasting
- Implement basic frontend WebSocket client

### Phase 3: Full Integration
- Connect monitoring service to WebSocket server
- Implement content categorization
- Add user preference settings
- Comprehensive error handling

## API Endpoints

### WebSocket Events

**Server to Client:**
- `content_update`: New verified content available
  ```json
  {
    "id": "unique_content_id",
    "type": "tweet|video|article",
    "title": "Content title",
    "summary": "Brief summary",
    "source": "Original source",
    "timestamp": "ISO timestamp",
    "ipfs_hash": "Qm..."
  }
  ```

**Client to Server:**
- `subscribe_preferences`: User content preferences
  ```json
  {
    "categories": ["politics", "economy"],
    "sources": ["trusted_news"],
    "real_time": true
  }
  ```

## Configuration

### Environment Variables
- `IPFS_MONITOR_TOPIC`: Pubsub topic name (default: "lodestar.new_content")
- `WEBSOCKET_SECRET_KEY`: Secret for WebSocket authentication
- `CONTENT_CACHE_SIZE`: Number of recent hashes to cache (default: 1000)

### Configuration File
Create `realtime_config.json`:
```json
{
  "monitoring": {
    "polling_interval": 5,
    "pubsub_topic": "lodestar.new_content",
    "max_concurrent_verifications": 10
  },
  "websocket": {
    "port": 5001,
    "cors_allowed_origins": ["http://localhost:8000"],
    "ping_timeout": 60
  },
  "caching": {
    "max_cache_size": 1000,
    "cache_ttl": 3600
  }
}