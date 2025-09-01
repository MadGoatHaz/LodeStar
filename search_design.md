# Advanced Search and Filtering System Design

## Overview
This document outlines the design for Lodestar's advanced search and filtering system, which will provide users with powerful tools to find and filter content based on various criteria.

## Current Limitations
1. **Basic Search**: Simple text matching without advanced operators
2. **Limited Filters**: Only basic category filtering (verified, contradicted, historical)
3. **No Sorting**: Content displayed in chronological order only
4. **No Faceted Search**: Unable to combine multiple filters
5. **No Date Filtering**: No way to filter by date ranges
6. **No Source Filtering**: No way to filter by content source

## Requirements

### 1. Advanced Search Features
- **Full-Text Search**: Comprehensive text search across all content fields
- **Search Operators**: Support for quotes, +, -, AND, OR, NOT operators
- **Field-Specific Search**: Search within specific fields (title, content, source)
- **Fuzzy Search**: Handle typos and variations in search terms
- **Autocomplete**: Suggest search terms as user types

### 2. Advanced Filtering
- **Date Range Filter**: Filter by publication date ranges
- **Source Filter**: Filter by content source (YouTube, Twitter, etc.)
- **Content Type Filter**: Filter by content type (statement, action, etc.)
- **Credibility Score Filter**: Filter by community credibility ratings
- **Flag Status Filter**: Filter by moderation status
- **Combined Filters**: Ability to combine multiple filters

### 3. Sorting Options
- **Relevance**: Sort by search relevance
- **Date**: Sort by publication date (newest/oldest first)
- **Credibility**: Sort by community credibility score
- **Popularity**: Sort by engagement (views, votes, flags)

### 4. Faceted Search
- **Dynamic Facets**: Show available filters based on current search results
- **Facet Counting**: Show count of results for each filter option
- **Multi-Select Facets**: Allow selection of multiple facet values
- **Facet Exclusion**: Allow exclusion of specific facet values

## System Architecture

### 1. Search Index
- **Component**: search_index.py
- **Purpose**: Maintain searchable index of all content
- **Implementation**:
  - Inverted index for fast text search
  - Field-specific indexing
  - Real-time updates for new content
  - Support for faceted search

### 2. Search API
- **Component**: search_api.py
- **Purpose**: Provide REST API for search and filtering
- **Implementation**:
  - Query parsing and validation
  - Search execution against index
  - Result filtering and sorting
  - Pagination support

### 3. Frontend Search Interface
- **Component**: search_interface.js
- **Purpose**: Provide user interface for search and filtering
- **Implementation**:
  - Search input with autocomplete
  - Filter panels with dynamic facets
  - Sorting controls
  - Result display with pagination

### 4. Query Parser
- **Component**: query_parser.py
- **Purpose**: Parse advanced search queries
- **Implementation**:
  - Support for search operators
  - Field-specific search parsing
  - Boolean logic processing
  - Error handling for invalid queries

## Data Models

### Search Document
```json
{
  "id": "unique_document_id",
  "ipfs_hash": "Qm...",
  "title": "Content title",
  "content": "Full content text",
  "source": "youtube|twitter|brave_search|...",
  "type": "statement|action|...",
  "timestamp": "ISO timestamp",
  "tags": ["tag1", "tag2"],
  "credibility_score": 0.85,
  "flag_count": 0,
  "vote_count": 0,
  "view_count": 0
}
```

### Search Query
```json
{
  "query": "search terms",
  "filters": {
    "date_range": {
      "start": "ISO timestamp",
      "end": "ISO timestamp"
    },
    "sources": ["youtube", "twitter"],
    "types": ["statement"],
    "credibility_min": 0.5,
    "flagged": false
  },
  "sort": {
    "field": "relevance|date|credibility|popularity",
    "order": "asc|desc"
  },
  "pagination": {
    "page": 1,
    "per_page": 20
  }
}
```

### Search Result
```json
{
  "results": [
    {
      "document": { /* search document */ },
      "score": 0.95,
      "highlights": {
        "title": "Highlighted <em>search</em> terms",
        "content": "Content with <em>search</em> terms highlighted"
      }
    }
  ],
  "total": 1250,
  "facets": {
    "sources": [
      {"value": "youtube", "count": 450},
      {"value": "twitter", "count": 320}
    ],
    "types": [
      {"value": "statement", "count": 800},
      {"value": "action", "count": 450}
    ]
  },
  "pagination": {
    "current_page": 1,
    "total_pages": 63,
    "per_page": 20
  }
}
```

## API Endpoints

### Search
- `POST /api/search` - Execute search with filters and sorting
- `GET /api/search/suggest?q={term}` - Get autocomplete suggestions
- `GET /api/search/facets` - Get available facets for current context

### Index Management
- `POST /api/index/document` - Add document to search index
- `DELETE /api/index/document/{id}` - Remove document from search index
- `POST /api/index/rebuild` - Rebuild entire search index

## Implementation Phases

### Phase 1: Basic Search Index
- Implement search_index.py with inverted index
- Create basic search API endpoint
- Add document indexing for new content
- Implement simple text search

### Phase 2: Advanced Search Features
- Implement query_parser.py for search operators
- Add field-specific search capabilities
- Implement fuzzy search
- Add autocomplete suggestions

### Phase 3: Filtering and Sorting
- Add filter support to search API
- Implement date range filtering
- Add source and type filtering
- Implement sorting options

### Phase 4: Faceted Search
- Implement facet generation
- Add dynamic facet display
- Enable multi-select facets
- Add facet exclusion support

## Performance Considerations

### 1. Index Optimization
- **Index Compression**: Compress index to reduce memory usage
- **Caching**: Cache frequently accessed index segments
- **Sharding**: Split index across multiple files for parallel access

### 2. Query Optimization
- **Query Caching**: Cache results for common queries
- **Early Termination**: Stop search when enough results are found
- **Parallel Processing**: Use multiple threads for large searches

### 3. Memory Management
- **Lazy Loading**: Load index segments on demand
- **Memory Limits**: Set limits on index memory usage
- **Garbage Collection**: Regular cleanup of unused index data

## Integration Points

### 1. Content Pipeline
- **Index Updates**: Automatically index new content from IPFS
- **Real-time Updates**: Update index when content is modified
- **Batch Processing**: Bulk index historical content

### 2. Frontend Integration
- **Search Interface**: JavaScript components for search UI
- **Real-time Updates**: WebSocket integration for live results
- **User Preferences**: Store search preferences in localStorage

### 3. Moderation System
- **Flag Integration**: Filter content based on flag status
- **Credibility Scores**: Use community voting in search ranking

## Security Considerations

### 1. Query Validation
- **Input Sanitization**: Prevent injection attacks
- **Query Limits**: Limit query complexity and result size
- **Rate Limiting**: Prevent abuse of search API

### 2. Access Control
- **Public Search**: Allow public search with limitations
- **Authenticated Search**: Enhanced features for logged-in users
- **Admin Search**: Full access for administrators

## Privacy Considerations

### 1. Search Logging
- **Anonymous Queries**: Don't log user identifiers with searches
- **Aggregate Analytics**: Collect only aggregate search statistics
- **Data Retention**: Clear search logs after defined period

### 2. User Privacy
- **No Tracking**: Don't track individual search behavior
- **Local Storage**: Store preferences locally when possible
- **Opt-out Options**: Allow users to disable search features

## Scalability Features

### 1. Distributed Indexing
- **Index Sharding**: Split index across multiple nodes
- **Load Balancing**: Distribute search queries across nodes
- **Replication**: Replicate index for redundancy

### 2. Caching Strategy
- **CDN Integration**: Cache search results at edge locations
- **Browser Caching**: Use HTTP caching for static search assets
- **Application Caching**: Cache search results in application layer

## Future Enhancements

### 1. AI-Powered Search
- **Semantic Search**: Use embeddings for meaning-based search
- **Natural Language Queries**: Support conversational search
- **Personalization**: Customize results based on user behavior

### 2. Advanced Analytics
- **Search Analytics**: Track search effectiveness
- **Query Analysis**: Identify common search patterns
- **Performance Monitoring**: Monitor search performance metrics

### 3. Mobile Optimization
- **Voice Search**: Support voice input for searches
- **Location-Based Search**: Filter results by geographic relevance
- **Offline Search**: Enable searching cached content offline