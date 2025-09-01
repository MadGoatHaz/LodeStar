from flask import Flask, request, jsonify
from historical_collector import HistoricalCollector
import json

class HistoricalAPI:
    def __init__(self, app=None):
        """Initialize historical data API"""
        self.collector = HistoricalCollector()
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize with Flask app"""
        # Add historical data endpoints
        app.add_url_rule('/api/historical/statements', 'get_statements', self.get_statements, methods=['GET'])
        app.add_url_rule('/api/historical/statements/<statement_id>', 'get_statement', self.get_statement, methods=['GET'])
        app.add_url_rule('/api/historical/statements', 'add_statement', self.add_statement, methods=['POST'])
        app.add_url_rule('/api/historical/timeline', 'get_timeline', self.get_timeline, methods=['GET'])
        app.add_url_rule('/api/historical/timeline', 'add_timeline_entry', self.add_timeline_entry, methods=['POST'])
        app.add_url_rule('/api/historical/search', 'search_statements', self.search_statements, methods=['GET'])
        app.add_url_rule('/api/historical/import', 'import_data', self.import_data, methods=['POST'])
        app.add_url_rule('/api/historical/related/<statement_id>', 'get_related', self.get_related, methods=['GET'])
        app.add_url_rule('/api/historical/link', 'link_statements', self.link_statements, methods=['POST'])
        
    def get_statements(self):
        """Get historical statements with filtering"""
        try:
            # Get filters from query parameters
            filters = {}
            
            administration = request.args.get('administration')
            if administration:
                filters['administration'] = administration
                
            topic = request.args.get('topic')
            if topic:
                filters['topic'] = topic
                
            category = request.args.get('category')
            if category:
                filters['category'] = category
                
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            if start_date or end_date:
                filters['date_range'] = {
                    'start': start_date,
                    'end': end_date
                }
                
            # Get statements
            statements = self.collector.get_statements(filters)
            
            # Pagination
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 20
                
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_statements = statements[start_idx:end_idx]
            
            return jsonify({
                'statements': paginated_statements,
                'total': len(statements),
                'pagination': {
                    'current_page': page,
                    'total_pages': (len(statements) + per_page - 1) // per_page,
                    'per_page': per_page
                }
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def get_statement(self, statement_id):
        """Get specific historical statement"""
        try:
            statement = self.collector.get_statement(statement_id)
            
            if not statement:
                return jsonify({'error': 'Statement not found'}), 404
                
            return jsonify(statement)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def add_statement(self):
        """Add a new historical statement"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No statement data provided'}), 400
                
            # Add statement
            ipfs_hash = self.collector.add_statement(data)
            
            return jsonify({
                'status': 'success',
                'message': 'Statement added successfully',
                'id': data['id'],
                'ipfs_hash': ipfs_hash
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def get_timeline(self):
        """Get historical timeline"""
        try:
            # Get filters from query parameters
            filters = {}
            
            entry_type = request.args.get('type')
            if entry_type:
                filters['type'] = entry_type
                
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            if start_date or end_date:
                filters['date_range'] = {
                    'start': start_date,
                    'end': end_date
                }
                
            # Get timeline entries
            timeline = self.collector.get_timeline(filters)
            
            # Sort by date
            timeline.sort(key=lambda x: x.get('date', ''))
            
            # Pagination
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 20
                
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_timeline = timeline[start_idx:end_idx]
            
            return jsonify({
                'timeline': paginated_timeline,
                'total': len(timeline),
                'pagination': {
                    'current_page': page,
                    'total_pages': (len(timeline) + per_page - 1) // per_page,
                    'per_page': per_page
                }
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def add_timeline_entry(self):
        """Add a new timeline entry"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No timeline data provided'}), 400
                
            # Add timeline entry
            entry_id = self.collector.add_timeline_entry(data)
            
            return jsonify({
                'status': 'success',
                'message': 'Timeline entry added successfully',
                'id': entry_id
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def search_statements(self):
        """Search historical statements"""
        try:
            query = request.args.get('q', '')
            
            if not query:
                return jsonify({'error': 'Search query required'}), 400
                
            # Search statements
            results = self.collector.search_statements(query)
            
            # Pagination
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 20
                
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = results[start_idx:end_idx]
            
            return jsonify({
                'results': paginated_results,
                'total': len(results),
                'query': query,
                'pagination': {
                    'current_page': page,
                    'total_pages': (len(results) + per_page - 1) // per_page,
                    'per_page': per_page
                }
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def import_data(self):
        """Import historical data"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No import data provided'}), 400
                
            # Check if importing from file or API
            if 'file_path' in data:
                result = self.collector.import_from_file(data['file_path'])
            elif 'api_url' in data:
                api_key = data.get('api_key')
                result = self.collector.import_from_api(data['api_url'], api_key)
            else:
                return jsonify({'error': 'Either file_path or api_url required'}), 400
                
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def get_related(self, statement_id):
        """Get related statements"""
        try:
            related = self.collector.get_related_statements(statement_id)
            
            return jsonify({
                'related_statements': related
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def link_statements(self):
        """Link two statements"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No link data provided'}), 400
                
            statement_id1 = data.get('statement_id1')
            statement_id2 = data.get('statement_id2')
            relationship = data.get('relationship')
            
            if not all([statement_id1, statement_id2, relationship]):
                return jsonify({'error': 'Missing required parameters'}), 400
                
            result = self.collector.link_statements(statement_id1, statement_id2, relationship)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Integration function
def integrate_historical_api(app):
    """Integrate historical API with Flask app"""
    historical_api = HistoricalAPI()
    historical_api.init_app(app)
    return historical_api

# Example usage
if __name__ == "__main__":
    app = Flask(__name__)
    historical_api = HistoricalAPI(app)
    
    @app.route('/')
    def index():
        return "Historical Data API is running"
        
    app.run(debug=True)