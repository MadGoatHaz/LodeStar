import json
import requests
import os
from datetime import datetime
from urllib.parse import urljoin
import ipfshttpclient

class HistoricalCollector:
    def __init__(self, data_dir='historical_data'):
        """Initialize historical data collector"""
        self.data_dir = data_dir
        self.ipfs_client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # Initialize data storage
        self.statements_file = os.path.join(self.data_dir, 'statements.json')
        self.timeline_file = os.path.join(self.data_dir, 'timeline.json')
        self.statements = self.load_statements()
        self.timeline = self.load_timeline()
        
    def load_statements(self):
        """Load historical statements from file"""
        try:
            if os.path.exists(self.statements_file):
                with open(self.statements_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading statements: {e}")
        return {}
        
    def save_statements(self):
        """Save historical statements to file"""
        try:
            with open(self.statements_file, 'w') as f:
                json.dump(self.statements, f, indent=2)
        except Exception as e:
            print(f"Error saving statements: {e}")
            
    def load_timeline(self):
        """Load timeline from file"""
        try:
            if os.path.exists(self.timeline_file):
                with open(self.timeline_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading timeline: {e}")
        return []
        
    def save_timeline(self):
        """Save timeline to file"""
        try:
            with open(self.timeline_file, 'w') as f:
                json.dump(self.timeline, f, indent=2)
        except Exception as e:
            print(f"Error saving timeline: {e}")
            
    def add_statement(self, statement_data):
        """Add a historical statement to the repository"""
        # Generate unique ID if not provided
        if 'id' not in statement_data:
            statement_data['id'] = f"hist_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.statements)}"
            
        # Add timestamp if not provided
        if 'date' not in statement_data:
            statement_data['date'] = datetime.now().isoformat()
            
        # Add to statements dictionary
        statement_id = statement_data['id']
        self.statements[statement_id] = statement_data
        
        # Save to file
        self.save_statements()
        
        # Add to IPFS
        try:
            ipfs_hash = self.ipfs_client.add_json(statement_data)
            statement_data['ipfs_hash'] = ipfs_hash
            self.statements[statement_id] = statement_data
            self.save_statements()
            return ipfs_hash
        except Exception as e:
            print(f"Error adding statement to IPFS: {e}")
            return None
            
    def add_timeline_entry(self, entry_data):
        """Add a timeline entry"""
        # Generate unique ID if not provided
        if 'id' not in entry_data:
            entry_data['id'] = f"timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.timeline)}"
            
        # Add timestamp if not provided
        if 'date' not in entry_data:
            entry_data['date'] = datetime.now().isoformat()
            
        # Add to timeline
        self.timeline.append(entry_data)
        
        # Save to file
        self.save_timeline()
        
        return entry_data['id']
        
    def get_statement(self, statement_id):
        """Get a specific historical statement"""
        return self.statements.get(statement_id)
        
    def get_statements(self, filters=None):
        """Get historical statements with optional filtering"""
        if not filters:
            return list(self.statements.values())
            
        # Apply filters
        filtered_statements = []
        for statement in self.statements.values():
            match = True
            
            # Administration filter
            if 'administration' in filters:
                if statement.get('administration') != filters['administration']:
                    match = False
                    
            # Date range filter
            if 'date_range' in filters:
                date_range = filters['date_range']
                start_date = date_range.get('start')
                end_date = date_range.get('end')
                
                if start_date or end_date:
                    statement_date = datetime.fromisoformat(statement.get('date', '').replace('Z', '+00:00'))
                    
                    if start_date:
                        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        if statement_date < start:
                            match = False
                            
                    if end_date:
                        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        if statement_date > end:
                            match = False
                            
            # Topic filter
            if 'topic' in filters:
                if statement.get('topic') != filters['topic']:
                    match = False
                    
            # Category filter
            if 'category' in filters:
                if statement.get('category') != filters['category']:
                    match = False
                    
            if match:
                filtered_statements.append(statement)
                
        return filtered_statements
        
    def get_timeline(self, filters=None):
        """Get timeline entries with optional filtering"""
        if not filters:
            return self.timeline
            
        # Apply filters
        filtered_timeline = []
        for entry in self.timeline:
            match = True
            
            # Date range filter
            if 'date_range' in filters:
                date_range = filters['date_range']
                start_date = date_range.get('start')
                end_date = date_range.get('end')
                
                if start_date or end_date:
                    entry_date = datetime.fromisoformat(entry.get('date', '').replace('Z', '+00:00'))
                    
                    if start_date:
                        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        if entry_date < start:
                            match = False
                            
                    if end_date:
                        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        if entry_date > end:
                            match = False
                            
            # Type filter
            if 'type' in filters:
                if entry.get('type') != filters['type']:
                    match = False
                    
            if match:
                filtered_timeline.append(entry)
                
        return filtered_timeline
        
    def import_from_api(self, api_url, api_key=None):
        """Import historical data from an API"""
        try:
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
                
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Process imported data
            imported_count = 0
            if isinstance(data, list):
                for item in data:
                    if self.add_statement(item):
                        imported_count += 1
            elif isinstance(data, dict):
                if self.add_statement(data):
                    imported_count += 1
                    
            return {
                'status': 'success',
                'imported_count': imported_count,
                'message': f'Successfully imported {imported_count} statements'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error importing from API: {e}'
            }
            
    def import_from_file(self, file_path):
        """Import historical data from a JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Process imported data
            imported_count = 0
            if isinstance(data, list):
                for item in data:
                    if self.add_statement(item):
                        imported_count += 1
            elif isinstance(data, dict):
                if 'statements' in data:
                    for item in data['statements']:
                        if self.add_statement(item):
                            imported_count += 1
                else:
                    if self.add_statement(data):
                        imported_count += 1
                        
            return {
                'status': 'success',
                'imported_count': imported_count,
                'message': f'Successfully imported {imported_count} statements'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error importing from file: {e}'
            }
            
    def link_statements(self, statement_id1, statement_id2, relationship):
        """Link two historical statements with a relationship"""
        if statement_id1 not in self.statements or statement_id2 not in self.statements:
            return {
                'status': 'error',
                'message': 'One or both statements not found'
            }
            
        # Add relationship to first statement
        if 'related_statements' not in self.statements[statement_id1]:
            self.statements[statement_id1]['related_statements'] = []
            
        self.statements[statement_id1]['related_statements'].append({
            'id': statement_id2,
            'relationship': relationship
        })
        
        # Add reverse relationship to second statement
        if 'related_statements' not in self.statements[statement_id2]:
            self.statements[statement_id2]['related_statements'] = []
            
        self.statements[statement_id2]['related_statements'].append({
            'id': statement_id1,
            'relationship': relationship
        })
        
        # Save changes
        self.save_statements()
        
        return {
            'status': 'success',
            'message': f'Statements {statement_id1} and {statement_id2} linked with relationship: {relationship}'
        }
        
    def get_related_statements(self, statement_id):
        """Get statements related to a specific statement"""
        if statement_id not in self.statements:
            return []
            
        related_ids = self.statements[statement_id].get('related_statements', [])
        related_statements = []
        
        for related in related_ids:
            related_id = related['id']
            if related_id in self.statements:
                related_statement = self.statements[related_id].copy()
                related_statement['relationship'] = related['relationship']
                related_statements.append(related_statement)
                
        return related_statements
        
    def search_statements(self, query):
        """Search historical statements by text"""
        matching_statements = []
        
        for statement in self.statements.values():
            # Search in statement text
            if query.lower() in statement.get('statement', '').lower():
                matching_statements.append(statement)
                continue
                
            # Search in title/context
            if query.lower() in statement.get('title', '').lower():
                matching_statements.append(statement)
                continue
                
            # Search in topic
            if query.lower() in statement.get('topic', '').lower():
                matching_statements.append(statement)
                continue
                
        return matching_statements

# Example usage
if __name__ == "__main__":
    collector = HistoricalCollector()
    
    # Example: Add a historical statement
    # statement = {
    #     'administration': 'Obama',
    #     'president': 'Barack Obama',
    #     'date': '2010-03-23T00:00:00Z',
    #     'statement': 'This is a sample historical statement.',
    #     'topic': 'Healthcare',
    #     'category': 'Policy Announcement',
    #     'context': 'During healthcare reform discussions',
    #     'sources': ['https://example.com/speech']
    # }
    # collector.add_statement(statement)
    # 
    # # Example: Search statements
    # results = collector.search_statements('healthcare')
    # print(results)