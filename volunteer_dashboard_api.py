from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import jwt
import hashlib
import os
import json

class VolunteerDashboardAPI:
    def __init__(self, app=None, secret_key=None):
        """Initialize volunteer dashboard API"""
        self.app = app
        self.secret_key = secret_key or os.environ.get('SECRET_KEY', 'default_secret_key')
        self.volunteers_file = 'volunteers.json'
        self.notifications_file = 'notifications.json'
        self.volunteers = self.load_volunteers()
        self.notifications = self.load_notifications()
        
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize with Flask app"""
        # Add volunteer dashboard endpoints
        app.add_url_rule('/api/volunteer/register', 'volunteer_register', self.volunteer_register, methods=['POST'])
        app.add_url_rule('/api/volunteer/login', 'volunteer_login', self.volunteer_login, methods=['POST'])
        app.add_url_rule('/api/volunteer/profile', 'volunteer_profile', self.volunteer_profile, methods=['GET'])
        app.add_url_rule('/api/volunteer/status', 'volunteer_status', self.volunteer_status, methods=['GET', 'POST'])
        app.add_url_rule('/api/volunteer/metrics', 'volunteer_metrics', self.volunteer_metrics, methods=['GET'])
        app.add_url_rule('/api/volunteer/content', 'volunteer_content', self.volunteer_content, methods=['GET'])
        app.add_url_rule('/api/volunteer/notifications', 'volunteer_notifications', self.volunteer_notifications, methods=['GET'])
        app.add_url_rule('/api/volunteer/notifications/read', 'volunteer_mark_read', self.volunteer_mark_read, methods=['POST'])
        app.add_url_rule('/api/volunteer/heartbeat', 'volunteer_heartbeat', self.volunteer_heartbeat, methods=['POST'])
        
        # Add administrator dashboard endpoints
        app.add_url_rule('/api/admin/login', 'admin_login', self.admin_login, methods=['POST'])
        app.add_url_rule('/api/admin/network', 'admin_network', self.admin_network, methods=['GET'])
        app.add_url_rule('/api/admin/crawlers', 'admin_crawlers', self.admin_crawlers, methods=['GET'])
        app.add_url_rule('/api/admin/crawlers/<volunteer_id>', 'admin_crawler', self.admin_crawler, methods=['GET'])
        app.add_url_rule('/api/admin/metrics', 'admin_metrics', self.admin_metrics, methods=['GET'])
        app.add_url_rule('/api/admin/messages', 'admin_messages', self.admin_messages, methods=['POST'])
        app.add_url_rule('/api/admin/announcements', 'admin_announcements', self.admin_announcements, methods=['POST'])
        
    def load_volunteers(self):
        """Load volunteers from file"""
        try:
            if os.path.exists(self.volunteers_file):
                with open(self.volunteers_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading volunteers: {e}")
        return {}
        
    def save_volunteers(self):
        """Save volunteers to file"""
        try:
            with open(self.volunteers_file, 'w') as f:
                json.dump(self.volunteers, f, indent=2)
        except Exception as e:
            print(f"Error saving volunteers: {e}")
            
    def load_notifications(self):
        """Load notifications from file"""
        try:
            if os.path.exists(self.notifications_file):
                with open(self.notifications_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading notifications: {e}")
        return {}
        
    def save_notifications(self):
        """Save notifications to file"""
        try:
            with open(self.notifications_file, 'w') as f:
                json.dump(self.notifications, f, indent=2)
        except Exception as e:
            print(f"Error saving notifications: {e}")
            
    def generate_token(self, volunteer_id, is_admin=False):
        """Generate JWT token for volunteer"""
        payload = {
            'volunteer_id': volunteer_id,
            'is_admin': is_admin,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
        
    def verify_token(self, token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
            
    def get_volunteer_from_request(self):
        """Get volunteer ID from request token"""
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
            
        try:
            token = auth_header.split(' ')[1]
            payload = self.verify_token(token)
            if payload:
                return payload['volunteer_id']
        except:
            pass
            
        return None
        
    def volunteer_register(self):
        """Register a new volunteer"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No registration data provided'}), 400
                
            # Required fields
            required_fields = ['name', 'email', 'public_key']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
                    
            # Check if email already exists
            for volunteer in self.volunteers.values():
                if volunteer.get('email') == data['email']:
                    return jsonify({'error': 'Email already registered'}), 400
                    
            # Generate volunteer ID
            volunteer_id = hashlib.sha256(data['email'].encode()).hexdigest()[:16]
            
            # Create volunteer profile
            volunteer_profile = {
                'id': volunteer_id,
                'name': data['name'],
                'email': data['email'],
                'public_key': data['public_key'],
                'registered_date': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'status': 'active',
                'crawler_version': data.get('crawler_version', '1.0.0'),
                'system_info': data.get('system_info', {})
            }
            
            # Save volunteer
            self.volunteers[volunteer_id] = volunteer_profile
            self.save_volunteers()
            
            # Generate token
            token = self.generate_token(volunteer_id)
            
            return jsonify({
                'status': 'success',
                'message': 'Volunteer registered successfully',
                'volunteer_id': volunteer_id,
                'token': token
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def volunteer_login(self):
        """Volunteer login"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No login data provided'}), 400
                
            email = data.get('email')
            if not email:
                return jsonify({'error': 'Email required'}), 400
                
            # Find volunteer by email
            volunteer_id = None
            for vid, volunteer in self.volunteers.items():
                if volunteer.get('email') == email:
                    volunteer_id = vid
                    break
                    
            if not volunteer_id:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            # Update last seen
            self.volunteers[volunteer_id]['last_seen'] = datetime.now().isoformat()
            self.save_volunteers()
            
            # Generate token
            token = self.generate_token(volunteer_id)
            
            return jsonify({
                'status': 'success',
                'message': 'Login successful',
                'volunteer_id': volunteer_id,
                'token': token
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def volunteer_profile(self):
        """Get volunteer profile"""
        try:
            volunteer_id = self.get_volunteer_from_request()
            if not volunteer_id:
                return jsonify({'error': 'Authentication required'}), 401
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            # Return profile without sensitive information
            profile = self.volunteers[volunteer_id].copy()
            profile.pop('email', None)
            
            return jsonify(profile)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def volunteer_status(self):
        """Get or update volunteer crawler status"""
        try:
            volunteer_id = self.get_volunteer_from_request()
            if not volunteer_id:
                return jsonify({'error': 'Authentication required'}), 401
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            if request.method == 'GET':
                # Return current status (in a real implementation, this would come from a database)
                status = {
                    'volunteer_id': volunteer_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'running',
                    'uptime': 3600,  # 1 hour in seconds
                    'last_heartbeat': datetime.now().isoformat(),
                    'content_collected': {
                        'today': 150,
                        'total': 12500
                    },
                    'errors': {
                        'today': 2,
                        'total': 45
                    },
                    'performance': {
                        'cpu_usage': 25.5,
                        'memory_usage': 128,  # MB
                        'network_usage': 1.2  # MB/s
                    }
                }
                
                return jsonify(status)
                
            elif request.method == 'POST':
                # Update status
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No status data provided'}), 400
                    
                # In a real implementation, we would save this to a database
                # For now, we'll just acknowledge the update
                return jsonify({
                    'status': 'success',
                    'message': 'Status updated successfully'
                })
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def volunteer_metrics(self):
        """Get volunteer performance metrics"""
        try:
            volunteer_id = self.get_volunteer_from_request()
            if not volunteer_id:
                return jsonify({'error': 'Authentication required'}), 401
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            # Return metrics (in a real implementation, this would come from a database)
            metrics = {
                'volunteer_id': volunteer_id,
                'period': 'day',
                'metrics': {
                    'content_collected': 1500,
                    'errors': 12,
                    'uptime_percentage': 98.5,
                    'average_response_time': 1.2,
                    'data_processed': 250  # MB
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return jsonify(metrics)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def volunteer_content(self):
        """Get volunteer content statistics"""
        try:
            volunteer_id = self.get_volunteer_from_request()
            if not volunteer_id:
                return jsonify({'error': 'Authentication required'}), 401
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            # Return content statistics (in a real implementation, this would come from a database)
            content_stats = {
                'volunteer_id': volunteer_id,
                'sources': {
                    'youtube': 450,
                    'twitter': 320,
                    'brave_search': 280,
                    'other': 150
                },
                'types': {
                    'statement': 800,
                    'action': 450
                },
                'total_collected': 1200,
                'today_collected': 150
            }
            
            return jsonify(content_stats)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def volunteer_notifications(self):
        """Get volunteer notifications"""
        try:
            volunteer_id = self.get_volunteer_from_request()
            if not volunteer_id:
                return jsonify({'error': 'Authentication required'}), 401
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            # Get notifications for this volunteer
            volunteer_notifications = self.notifications.get(volunteer_id, [])
            
            return jsonify({
                'notifications': volunteer_notifications
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def volunteer_mark_read(self):
        """Mark notification as read"""
        try:
            volunteer_id = self.get_volunteer_from_request()
            if not volunteer_id:
                return jsonify({'error': 'Authentication required'}), 401
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            data = request.get_json()
            notification_id = data.get('notification_id')
            
            if not notification_id:
                return jsonify({'error': 'Notification ID required'}), 400
                
            # Mark notification as read
            if volunteer_id in self.notifications:
                for notification in self.notifications[volunteer_id]:
                    if notification.get('id') == notification_id:
                        notification['read'] = True
                        self.save_notifications()
                        break
                        
            return jsonify({
                'status': 'success',
                'message': 'Notification marked as read'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def volunteer_heartbeat(self):
        """Receive crawler heartbeat"""
        try:
            volunteer_id = self.get_volunteer_from_request()
            if not volunteer_id:
                return jsonify({'error': 'Authentication required'}), 401
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No heartbeat data provided'}), 400
                
            # Update last seen
            self.volunteers[volunteer_id]['last_seen'] = datetime.now().isoformat()
            self.save_volunteers()
            
            # Update status if provided
            if 'status' in data:
                # In a real implementation, we would save this to a database
                pass
                
            return jsonify({
                'status': 'success',
                'message': 'Heartbeat received'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def admin_login(self):
        """Administrator login"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No login data provided'}), 400
                
            # In a real implementation, we would verify admin credentials
            # For now, we'll just check for a special email
            email = data.get('email')
            if email != 'admin@lodestar.org':
                return jsonify({'error': 'Invalid credentials'}), 401
                
            # Generate admin token
            token = self.generate_token('admin', is_admin=True)
            
            return jsonify({
                'status': 'success',
                'message': 'Admin login successful',
                'token': token
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def admin_network(self):
        """Get network overview"""
        try:
            # Verify admin token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authentication required'}), 401
                
            try:
                token = auth_header.split(' ')[1]
                payload = self.verify_token(token)
                if not payload or not payload.get('is_admin'):
                    return jsonify({'error': 'Admin access required'}), 403
            except:
                return jsonify({'error': 'Invalid token'}), 401
                
            # Return network overview
            total_volunteers = len(self.volunteers)
            active_crawlers = sum(1 for v in self.volunteers.values() if v.get('status') == 'active')
            inactive_crawlers = total_volunteers - active_crawlers
            
            network_overview = {
                'total_volunteers': total_volunteers,
                'active_crawlers': active_crawlers,
                'inactive_crawlers': inactive_crawlers,
                'content_collected_today': 187500,
                'errors_today': 245,
                'average_uptime': 85.5,
                'load_distribution': {
                    'youtube': 35,
                    'twitter': 25,
                    'brave_search': 20,
                    'other': 20
                }
            }
            
            return jsonify(network_overview)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def admin_crawlers(self):
        """Get all crawler statuses"""
        try:
            # Verify admin token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authentication required'}), 401
                
            try:
                token = auth_header.split(' ')[1]
                payload = self.verify_token(token)
                if not payload or not payload.get('is_admin'):
                    return jsonify({'error': 'Admin access required'}), 403
            except:
                return jsonify({'error': 'Invalid token'}), 401
                
            # Return crawler statuses (simplified for demo)
            crawler_statuses = []
            for volunteer_id, volunteer in self.volunteers.items():
                status = {
                    'volunteer_id': volunteer_id,
                    'name': volunteer.get('name'),
                    'status': volunteer.get('status', 'unknown'),
                    'last_seen': volunteer.get('last_seen'),
                    'content_collected': 12500,
                    'uptime_percentage': 95.2
                }
                crawler_statuses.append(status)
                
            return jsonify({
                'crawlers': crawler_statuses
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def admin_crawler(self, volunteer_id):
        """Get specific crawler status"""
        try:
            # Verify admin token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authentication required'}), 401
                
            try:
                token = auth_header.split(' ')[1]
                payload = self.verify_token(token)
                if not payload or not payload.get('is_admin'):
                    return jsonify({'error': 'Admin access required'}), 403
            except:
                return jsonify({'error': 'Invalid token'}), 401
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            # Return detailed crawler status
            volunteer = self.volunteers[volunteer_id]
            status = {
                'volunteer_id': volunteer_id,
                'name': volunteer.get('name'),
                'email': volunteer.get('email'),
                'status': volunteer.get('status', 'unknown'),
                'registered_date': volunteer.get('registered_date'),
                'last_seen': volunteer.get('last_seen'),
                'crawler_version': volunteer.get('crawler_version'),
                'system_info': volunteer.get('system_info', {}),
                'content_collected': {
                    'today': 150,
                    'total': 12500
                },
                'performance': {
                    'cpu_usage': 25.5,
                    'memory_usage': 128,
                    'network_usage': 1.2
                }
            }
            
            return jsonify(status)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def admin_metrics(self):
        """Get network performance metrics"""
        try:
            # Verify admin token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authentication required'}), 401
                
            try:
                token = auth_header.split(' ')[1]
                payload = self.verify_token(token)
                if not payload or not payload.get('is_admin'):
                    return jsonify({'error': 'Admin access required'}), 403
            except:
                return jsonify({'error': 'Invalid token'}), 401
                
            # Return network metrics (simplified for demo)
            network_metrics = {
                'period': 'day',
                'total_content_collected': 187500,
                'average_content_per_crawler': 150,
                'error_rate': 0.13,
                'average_uptime': 95.2,
                'performance_trends': {
                    'cpu_usage': [22.5, 24.1, 25.5, 23.8, 26.2],
                    'memory_usage': [120, 125, 128, 122, 130],
                    'network_usage': [1.0, 1.1, 1.2, 1.0, 1.3]
                }
            }
            
            return jsonify(network_metrics)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def admin_messages(self):
        """Send message to volunteer"""
        try:
            # Verify admin token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authentication required'}), 401
                
            try:
                token = auth_header.split(' ')[1]
                payload = self.verify_token(token)
                if not payload or not payload.get('is_admin'):
                    return jsonify({'error': 'Admin access required'}), 403
            except:
                return jsonify({'error': 'Invalid token'}), 401
                
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No message data provided'}), 400
                
            volunteer_id = data.get('volunteer_id')
            subject = data.get('subject')
            content = data.get('content')
            
            if not all([volunteer_id, subject, content]):
                return jsonify({'error': 'Missing required fields'}), 400
                
            if volunteer_id not in self.volunteers:
                return jsonify({'error': 'Volunteer not found'}), 404
                
            # Create message
            message = {
                'id': hashlib.sha256(f"{volunteer_id}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
                'from_id': 'admin',
                'to_id': volunteer_id,
                'subject': subject,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'read': False
            }
            
            # Save message as notification
            if volunteer_id not in self.notifications:
                self.notifications[volunteer_id] = []
            self.notifications[volunteer_id].append(message)
            self.save_notifications()
            
            return jsonify({
                'status': 'success',
                'message': 'Message sent successfully',
                'message_id': message['id']
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def admin_announcements(self):
        """Create public announcement"""
        try:
            # Verify admin token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authentication required'}), 401
                
            try:
                token = auth_header.split(' ')[1]
                payload = self.verify_token(token)
                if not payload or not payload.get('is_admin'):
                    return jsonify({'error': 'Admin access required'}), 403
            except:
                return jsonify({'error': 'Invalid token'}), 401
                
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No announcement data provided'}), 400
                
            title = data.get('title')
            content = data.get('content')
            
            if not all([title, content]):
                return jsonify({'error': 'Missing required fields'}), 400
                
            # Create announcement
            announcement = {
                'id': hashlib.sha256(f"announcement_{datetime.now().isoformat()}".encode()).hexdigest()[:16],
                'type': 'announcement',
                'title': title,
                'message': content,
                'timestamp': datetime.now().isoformat(),
                'read': False
            }
            
            # Send to all volunteers
            for volunteer_id in self.volunteers.keys():
                if volunteer_id not in self.notifications:
                    self.notifications[volunteer_id] = []
                self.notifications[volunteer_id].append(announcement)
                
            self.save_notifications()
            
            return jsonify({
                'status': 'success',
                'message': 'Announcement created successfully',
                'announcement_id': announcement['id']
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Integration function
def integrate_volunteer_dashboard_api(app):
    """Integrate volunteer dashboard API with Flask app"""
    volunteer_api = VolunteerDashboardAPI(app)
    return volunteer_api

# Example usage
if __name__ == "__main__":
    app = Flask(__name__)
    volunteer_api = VolunteerDashboardAPI(app)
    
    @app.route('/')
    def index():
        return "Volunteer Dashboard API is running"
        
    app.run(debug=True)