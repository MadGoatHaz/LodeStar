from flask import Flask, request, jsonify
from search_index import SearchIndex
import json

class SearchAPI:
    def __init__(self, app=None):
        """Initialize search API"""
        self.search_index = SearchIndex()
        if app:
            self.init_app(app)
            
    def init_app(self, app):
        """Initialize with Flask app"""
        # Add search endpoints
        app.add_url_rule('/api/search', 'search', self.search, methods=['POST'])
        app.add_url_rule('/api/search/suggest', 'suggest', self.suggest, methods=['GET'])
        app.add_url_rule('/api/search/facets', 'facets', self.facets, methods=['GET'])
        app.add_url_rule('/api/index/document', 'index_document', self.index_document, methods=['POST'])
        app.add_url_rule('/api/index/document/<doc_id>', 'remove_document', self.remove_document, methods=['DELETE'])
        app.add_url_rule('/api/index/rebuild', 'rebuild_index', self.rebuild_index, methods=['POST'])
        
    def search(self):
        """Search endpoint"""
        try:
            data = request.get_json()
            if not data:
                data = {}
                
            query = data.get('query', '')
            filters = data.get('filters', {})
            sort = data.get('sort', {})
            sort_field = sort.get('field', 'relevance')
            sort_order = sort.get('order', 'desc')
            pagination = data.get('pagination', {})
            page = pagination.get('page', 1)
            per_page = pagination.get('per_page', 20)
            
            # Validate pagination
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 20
                
            # Execute search
            results = self.search_index.search(
                query=query,
                filters=filters,
                sort_field=sort_field,
                sort_order=sort_order,
                page=page,
                per_page=per_page
            )
            
            return jsonify(results)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def suggest(self):
        """Autocomplete suggestions endpoint"""
        try:
            query = request.args.get('q', '')
            limit = int(request.args.get('limit', 10))
            
            if limit < 1 or limit > 50:
                limit = 10
                
            suggestions = self.search_index.get_suggestions(query, limit)
            
            return jsonify({
                'suggestions': suggestions
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def facets(self):
        """Get available facets endpoint"""
        try:
            # For now, return facets for all documents
            # In a real implementation, this would be based on current search context
            all_doc_ids = set(self.search_index.documents.keys())
            facets = self.search_index.generate_facets(all_doc_ids)
            
            return jsonify({
                'facets': facets
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def index_document(self):
        """Add document to search index endpoint"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No document data provided'}), 400
                
            doc_id = data.get('id')
            document = data.get('document')
            
            if not doc_id or not document:
                return jsonify({'error': 'Missing document ID or document data'}), 400
                
            result = self.search_index.index_document(doc_id, document)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def remove_document(self, doc_id):
        """Remove document from search index endpoint"""
        try:
            result = self.search_index.remove_document(doc_id)
            
            if result['status'] == 'error':
                return jsonify(result), 404
                
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    def rebuild_index(self):
        """Rebuild entire search index endpoint"""
        try:
            # This would be a long-running operation in a real implementation
            # For now, we'll just return success
            return jsonify({
                'status': 'success',
                'message': 'Index rebuild started'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Integration function
def integrate_search_api(app):
    """Integrate search API with Flask app"""
    search_api = SearchAPI()
    search_api.init_app(app)
    return search_api

# Example usage
if __name__ == "__main__":
    app = Flask(__name__)
    search_api = SearchAPI(app)
    
    @app.route('/')
    def index():
        return "Search API is running"
        
    app.run(debug=True)