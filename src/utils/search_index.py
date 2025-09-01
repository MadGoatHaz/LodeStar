import json
import re
import os
from collections import defaultdict
from datetime import datetime
import ipfshttpclient

class SearchIndex:
    def __init__(self, index_file='search_index.json'):
        """Initialize search index"""
        self.index_file = index_file
        self.documents = {}
        self.inverted_index = defaultdict(set)
        self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        self.load_index()
        
    def load_index(self):
        """Load search index from file"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, 'r') as f:
                    data = json.load(f)
                    self.documents = data.get('documents', {})
                    # Convert lists back to sets
                    for term, doc_ids in data.get('inverted_index', {}).items():
                        self.inverted_index[term] = set(doc_ids)
        except Exception as e:
            print(f"Error loading search index: {e}")
            
    def save_index(self):
        """Save search index to file"""
        try:
            # Convert sets to lists for JSON serialization
            serializable_index = {}
            for term, doc_ids in self.inverted_index.items():
                serializable_index[term] = list(doc_ids)
                
            data = {
                'documents': self.documents,
                'inverted_index': serializable_index
            }
            
            with open(self.index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving search index: {e}")
            
    def tokenize(self, text):
        """Tokenize text into terms"""
        if not text:
            return []
            
        # Convert to lowercase and split on whitespace and punctuation
        terms = re.findall(r'\b\w+\b', text.lower())
        return terms
        
    def index_document(self, doc_id, document):
        """Add document to search index"""
        # Store document
        self.documents[doc_id] = document
        
        # Extract text fields for indexing
        text_fields = []
        if 'title' in document:
            text_fields.append(document['title'])
        if 'content' in document:
            text_fields.append(document['content'])
        if 'source' in document:
            text_fields.append(document['source'])
        if 'type' in document:
            text_fields.append(document['type'])
            
        # Combine all text
        full_text = ' '.join(text_fields)
        
        # Tokenize and index terms
        terms = self.tokenize(full_text)
        for term in terms:
            self.inverted_index[term].add(doc_id)
            
        # Save index
        self.save_index()
        
        return {
            'status': 'success',
            'message': f'Document {doc_id} indexed successfully'
        }
        
    def remove_document(self, doc_id):
        """Remove document from search index"""
        if doc_id in self.documents:
            # Remove document
            del self.documents[doc_id]
            
            # Remove document from inverted index
            for term, doc_ids in self.inverted_index.items():
                if doc_id in doc_ids:
                    doc_ids.remove(doc_id)
                    
            # Save index
            self.save_index()
            
            return {
                'status': 'success',
                'message': f'Document {doc_id} removed from index'
            }
        else:
            return {
                'status': 'error',
                'message': f'Document {doc_id} not found in index'
            }
            
    def search(self, query, filters=None, sort_field='relevance', sort_order='desc', page=1, per_page=20):
        """Search documents with filters and sorting"""
        # Tokenize query
        query_terms = self.tokenize(query)
        
        # Find matching documents
        if query_terms:
            # Get documents matching all terms (AND search)
            matching_docs = set(self.inverted_index.get(query_terms[0], set()))
            for term in query_terms[1:]:
                matching_docs = matching_docs.intersection(self.inverted_index.get(term, set()))
        else:
            # If no query, return all documents
            matching_docs = set(self.documents.keys())
            
        # Apply filters
        filtered_docs = self.apply_filters(matching_docs, filters)
        
        # Get document objects
        results = []
        for doc_id in filtered_docs:
            if doc_id in self.documents:
                results.append({
                    'document': self.documents[doc_id],
                    'id': doc_id
                })
                
        # Sort results
        results = self.sort_results(results, sort_field, sort_order)
        
        # Apply pagination
        total_results = len(results)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = results[start_idx:end_idx]
        
        # Generate facets
        facets = self.generate_facets(filtered_docs)
        
        return {
            'results': paginated_results,
            'total': total_results,
            'facets': facets,
            'pagination': {
                'current_page': page,
                'total_pages': (total_results + per_page - 1) // per_page,
                'per_page': per_page
            }
        }
        
    def apply_filters(self, doc_ids, filters):
        """Apply filters to document IDs"""
        if not filters:
            return doc_ids
            
        filtered_ids = set(doc_ids)
        
        # Date range filter
        if 'date_range' in filters:
            date_range = filters['date_range']
            start_date = date_range.get('start')
            end_date = date_range.get('end')
            
            if start_date or end_date:
                filtered_ids = {
                    doc_id for doc_id in filtered_ids
                    if doc_id in self.documents and self._date_in_range(
                        self.documents[doc_id].get('timestamp'), 
                        start_date, 
                        end_date
                    )
                }
                
        # Source filter
        if 'sources' in filters and filters['sources']:
            sources = set(filters['sources'])
            filtered_ids = {
                doc_id for doc_id in filtered_ids
                if doc_id in self.documents and 
                self.documents[doc_id].get('source') in sources
            }
            
        # Type filter
        if 'types' in filters and filters['types']:
            types = set(filters['types'])
            filtered_ids = {
                doc_id for doc_id in filtered_ids
                if doc_id in self.documents and 
                self.documents[doc_id].get('type') in types
            }
            
        # Credibility score filter
        if 'credibility_min' in filters:
            min_credibility = filters['credibility_min']
            filtered_ids = {
                doc_id for doc_id in filtered_ids
                if doc_id in self.documents and 
                self.documents[doc_id].get('credibility_score', 0) >= min_credibility
            }
            
        # Flag status filter
        if 'flagged' in filters:
            flagged = filters['flagged']
            filtered_ids = {
                doc_id for doc_id in filtered_ids
                if doc_id in self.documents and 
                (self.documents[doc_id].get('flag_count', 0) > 0) == flagged
            }
            
        return filtered_ids
        
    def _date_in_range(self, timestamp, start_date, end_date):
        """Check if timestamp is within date range"""
        try:
            doc_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            if start_date:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if doc_date < start:
                    return False
                    
            if end_date:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if doc_date > end:
                    return False
                    
            return True
        except:
            return False
            
    def sort_results(self, results, sort_field, sort_order):
        """Sort search results"""
        reverse = (sort_order == 'desc')
        
        if sort_field == 'relevance':
            # For now, return as-is since we don't have relevance scoring
            return results
        elif sort_field == 'date':
            return sorted(results, key=lambda x: x['document'].get('timestamp', ''), reverse=reverse)
        elif sort_field == 'credibility':
            return sorted(results, key=lambda x: x['document'].get('credibility_score', 0), reverse=reverse)
        elif sort_field == 'popularity':
            def popularity_score(doc):
                return (
                    doc.get('vote_count', 0) * 2 + 
                    doc.get('view_count', 0) + 
                    doc.get('flag_count', 0) * -1
                )
            return sorted(results, key=lambda x: popularity_score(x['document']), reverse=reverse)
        else:
            return results
            
    def generate_facets(self, doc_ids):
        """Generate facets for current search results"""
        sources = defaultdict(int)
        types = defaultdict(int)
        
        for doc_id in doc_ids:
            if doc_id in self.documents:
                doc = self.documents[doc_id]
                if 'source' in doc:
                    sources[doc['source']] += 1
                if 'type' in doc:
                    types[doc['type']] += 1
                    
        # Convert to list format
        source_facets = [
            {'value': source, 'count': count}
            for source, count in sources.items()
        ]
        
        type_facets = [
            {'value': type_val, 'count': count}
            for type_val, count in types.items()
        ]
        
        return {
            'sources': source_facets,
            'types': type_facets
        }
        
    def get_suggestions(self, prefix, limit=10):
        """Get autocomplete suggestions for search prefix"""
        prefix = prefix.lower()
        suggestions = []
        
        # Find terms that start with prefix
        for term in self.inverted_index.keys():
            if term.startswith(prefix):
                suggestions.append(term)
                if len(suggestions) >= limit:
                    break
                    
        return suggestions
        
    def index_ipfs_content(self, ipfs_hash):
        """Index content from IPFS"""
        try:
            # Get content from IPFS
            content = self.ipfs_client.get_json(ipfs_hash)
            
            # Create search document
            document = {
                'id': ipfs_hash,
                'ipfs_hash': ipfs_hash,
                'title': content.get('title', ''),
                'content': content.get('text', content.get('content', '')),
                'source': content.get('source', content.get('type', 'unknown')),
                'type': content.get('type', 'statement'),
                'timestamp': content.get('timestamp', datetime.now().isoformat()),
                'credibility_score': content.get('credibility_score', 0.5),
                'flag_count': content.get('flag_count', 0),
                'vote_count': content.get('vote_count', 0),
                'view_count': content.get('view_count', 0)
            }
            
            # Index document
            return self.index_document(ipfs_hash, document)
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error indexing IPFS content: {e}'
            }

# Example usage
if __name__ == "__main__":
    search_index = SearchIndex()
    
    # Example: index a document
    # document = {
    #     'title': 'Example Statement',
    #     'content': 'This is an example statement about politics',
    #     'source': 'youtube',
    #     'type': 'statement',
    #     'timestamp': '2025-01-01T12:00:00Z',
    #     'credibility_score': 0.8
    # }
    # search_index.index_document('example1', document)
    # 
    # # Example: search
    # results = search_index.search('example politics')
    # print(results)