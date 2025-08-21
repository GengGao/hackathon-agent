# LangExtract Integration Plan

## Overview
This document outlines the integration of LangExtract into the hackathon assistant project to enhance structured information extraction capabilities. LangExtract will replace heuristic-based processing with precise, grounded extraction of structured information from documents, conversations, and web content.

## Current State vs. Enhanced State

### Current Limitations
- Simple blank-line chunking for RAG
- Keyword-based technology detection
- Heuristic artifact generation
- Raw text extraction from files/URLs
- Manual rule parsing

### Enhanced Capabilities with LangExtract
- Structured document processing with source grounding
- Intelligent rule categorization and extraction
- Precise technology and requirement identification
- Multi-pass extraction for improved recall
- Semantic chunking based on content structure

## Implementation Roadmap

### Phase 1: High-Impact, Low-Effort (Priority 1)

#### 1.1 Enhanced Rule Processing ❌ REVERTED
**Status**: REVERTED - Rule extraction was too slow for RAG integration

**What was implemented**:
- ✅ Base extractor infrastructure (`backend/extractors/`)
- ✅ Rule extraction schemas and examples
- ✅ LangExtract configuration
- ❌ RAG integration (reverted due to performance)

**What was reverted**:
- Async rule extraction in RAG rebuild process
- Database schema changes for extraction metadata
- Frontend status display for rule extraction
- RAG chunking integration with LangExtract

**Infrastructure kept for future use**:
- `backend/extractors/base_extractor.py` - Base extraction classes
- `backend/extractors/rule_extractor.py` - Rule extraction logic
- `backend/schemas/rule_schemas.py` - Extraction schemas
- `backend/examples/rule_examples.py` - Few-shot examples
- `backend/config/langextract_config.py` - Configuration

**Estimated Effort**: ~~2-3 days~~ COMPLETED (infrastructure ready for other use cases)

#### 1.2 Smart File Upload Processing
**Goal**: Extract structured information from uploaded hackathon documents

**Current State**: `backend/api/common.py` - `extract_text_from_file()` returns raw text

**Implementation Steps**:
1. **Create Document Extractor** (`backend/extractors/document_extractor.py`)
   - Define schemas for different document types
   - Hackathon briefs: requirements, constraints, deliverables, timeline
   - Technical specs: technologies, architecture, APIs

2. **Enhance File Processing Pipeline**
   - Modify `extract_text_from_file()` to use LangExtract
   - Add document type detection
   - Return structured data instead of raw text

3. **Update Context Storage**
   - Modify `add_rule_context()` to handle structured extractions
   - Store extraction metadata for UI display

**Files to Modify**:
- `backend/api/common.py` - Enhance file processing
- `backend/api/context.py` - Update context storage
- `backend/models/db.py` - Add structured data fields

**Estimated Effort**: 3-4 days

#### 1.3 Conversation Mining
**Goal**: Extract structured insights from chat history

**Current State**: `backend/tools/artifacts.py` uses keyword matching and basic prompts

**Implementation Steps**:
1. **Create Conversation Extractor** (`backend/extractors/conversation_extractor.py`)
   - Schema: decisions_made, technologies_chosen, problems_solved, requirements_identified
   - Extract from user messages and assistant responses
   - Track conversation flow and context

2. **Enhance Artifact Generation**
   - Replace keyword-based detection in `create_tech_stack()`
   - Use structured extraction for `derive_project_idea()`
   - Improve `summarize_chat_history()` with precise extraction

3. **Add Real-time Extraction**
   - Process new messages as they arrive
   - Update project artifacts incrementally

**Files to Modify**:
- `backend/tools/artifacts.py` - Replace heuristic methods
- `backend/api/router.py` - Add real-time processing hooks

**Estimated Effort**: 4-5 days

### Phase 2: Medium-Effort Enhancements (Priority 2)

#### 2.1 Document Intelligence
**Goal**: Process images/PDFs to extract structured hackathon information

**Implementation Steps**:
1. **Enhanced OCR Processing**
   - Integrate LangExtract with existing Tesseract OCR
   - Extract structured information from whiteboard images
   - Process wireframes and technical diagrams

2. **Multi-modal Document Processing**
   - Combine text and image extraction
   - Handle mixed-content documents (PDFs with images)
   - Extract tables, lists, and structured content

3. **Specialized Extractors**
   - Wireframe extractor: UI components, user flows
   - Architecture diagram extractor: services, data flow
   - Requirements document extractor: functional/non-functional requirements

**Files to Create**:
- `backend/extractors/image_extractor.py`
- `backend/extractors/multimodal_extractor.py`
- `backend/extractors/diagram_extractor.py`

**Estimated Effort**: 5-7 days

#### 2.2 Progress Extraction
**Goal**: Automatically track project progress and blockers

**Implementation Steps**:
1. **Progress Schema Definition**
   - Categories: completed_tasks, current_blockers, next_steps, decisions_pending
   - Timeline tracking and milestone identification
   - Risk assessment and mitigation strategies

2. **Continuous Monitoring**
   - Real-time extraction from ongoing conversations
   - Integration with existing todo system
   - Automatic progress reports

3. **Visualization Integration**
   - Structured data for frontend progress displays
   - Timeline views and milestone tracking
   - Blocker identification and resolution tracking

**Files to Create**:
- `backend/extractors/progress_extractor.py`
- `backend/api/progress.py` - New API endpoints
- Frontend integration points

**Estimated Effort**: 6-8 days

#### 2.3 Enhanced URL Content Processing
**Goal**: Structured extraction from web content

**Implementation Steps**:
1. **Web Content Extractor** (`backend/extractors/web_extractor.py`)
   - API documentation extraction
   - Tutorial step identification
   - Technical specification parsing

2. **Multi-pass Web Processing**
   - Use LangExtract's multiple passes for long pages
   - Improved recall for technical documentation
   - Structured extraction from GitHub repos, documentation sites

3. **Content Type Specialization**
   - API docs: endpoints, parameters, examples
   - Tutorials: steps, code snippets, prerequisites
   - Documentation: concepts, implementation details

**Files to Modify**:
- `backend/api/common.py` - Enhance `build_url_block()`
- Create specialized web extractors

**Estimated Effort**: 4-6 days

## Technical Implementation Details

### Directory Structure
```
backend/
├── extractors/
│   ├── __init__.py
│   ├── base_extractor.py          # Base classes and utilities
│   ├── rule_extractor.py          # Hackathon rule processing
│   ├── document_extractor.py      # File upload processing
│   ├── conversation_extractor.py  # Chat history mining
│   ├── image_extractor.py         # OCR + structured extraction
│   ├── web_extractor.py           # URL content processing
│   └── progress_extractor.py      # Progress tracking
├── schemas/
│   ├── __init__.py
│   ├── rule_schemas.py            # Rule extraction schemas
│   ├── document_schemas.py        # Document type schemas
│   └── conversation_schemas.py    # Chat extraction schemas
└── examples/
    ├── rule_examples.py           # Few-shot examples for rules
    ├── document_examples.py       # Document extraction examples
    └── conversation_examples.py   # Chat mining examples
```

### Configuration Management
```python
# backend/config/langextract_config.py
LANGEXTRACT_CONFIG = {
    "model_id": "gemma2:2b",  # Use local Ollama model
    "model_url": "http://localhost:11434",
    "fence_output": False,
    "use_schema_constraints": False,
    "extraction_passes": 3,
    "max_workers": 10,
    "max_char_buffer": 1000
}
```

### Database Schema Updates
```sql
-- Add structured extraction support
ALTER TABLE rule_context ADD COLUMN extraction_data TEXT; -- JSON field
ALTER TABLE rule_context ADD COLUMN extraction_schema TEXT;
ALTER TABLE rule_context ADD COLUMN extraction_version INTEGER DEFAULT 1;

-- New table for extraction metadata
CREATE TABLE extraction_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    extraction_type TEXT,
    schema_version INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON field
);
```

## Testing Strategy

### Unit Tests
- Test each extractor independently
- Validate schema compliance
- Test fallback mechanisms

### Integration Tests
- End-to-end extraction pipelines
- RAG system with structured chunks
- API endpoint responses

### Performance Tests
- Large document processing
- Concurrent extraction requests
- Cache effectiveness

## Rollout Plan

### Phase 1 Rollout (Weeks 1-2)
1. Deploy rule extraction enhancement
2. Monitor RAG performance improvements
3. Gather user feedback on structured rule display

### Phase 2 Rollout (Weeks 3-4)
1. Enable enhanced file processing
2. Deploy conversation mining features
3. A/B test artifact generation quality

### Phase 3 Rollout (Weeks 5-6)
1. Full document intelligence deployment
2. Progress tracking features
3. Enhanced web content processing

## Success Metrics

### Quality Metrics
- Extraction accuracy vs. manual annotation
- User satisfaction with generated artifacts
- Reduction in manual rule interpretation time

### Performance Metrics
- Processing time for large documents
- RAG retrieval relevance scores
- Cache hit rates for extractions

### Usage Metrics
- Adoption rate of structured features
- Frequency of artifact regeneration
- User engagement with extracted insights

## Risk Mitigation

### Technical Risks
- **LangExtract dependency**: Implement fallback to current heuristic methods
- **Performance impact**: Implement async processing and caching
- **Model compatibility**: Test with multiple Ollama models

### User Experience Risks
- **Learning curve**: Gradual feature rollout with clear documentation
- **Over-complexity**: Maintain simple interfaces with advanced features optional
- **Reliability**: Comprehensive testing and graceful degradation

## Dependencies and Prerequisites

### Required Dependencies
```txt
langextract>=0.1.0
ollama  # Already present
sentence-transformers  # Already present
```

### System Requirements
- Ollama running with gemma2:2b model (or compatible)
- Sufficient memory for concurrent extractions
- Updated Python environment (3.11+)

### Development Prerequisites
- Understanding of LangExtract API
- Familiarity with existing RAG pipeline
- Knowledge of project's tool calling system

## Conclusion

This integration plan transforms the hackathon assistant from a keyword-based system to an intelligent, structured information extraction platform. The phased approach ensures manageable implementation while delivering immediate value through enhanced rule processing and document understanding.

The integration leverages the project's existing offline-first architecture while significantly improving the quality and reliability of extracted information, ultimately providing better support for hackathon teams in understanding requirements, tracking progress, and preparing submissions.