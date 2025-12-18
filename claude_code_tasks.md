# Claude Code Tasks - Generation Pipeline Stabilization

## Overview
Stabilize the generation pipeline focusing on KB-Load, web search, model selection, decimal fix, MD-export filtering, and logging/monitoring.

## Specific Tasks

### 1. KB-Load Optimization and Stabilization
**Current Issues:**
- Decimal conversion issues in `core/rag_system.py` lines 666-670, 705-709
- Dimension mismatch handling needs improvement
- Streaming load with ijson has fallback but could be more robust

**Tasks:**
- [ ] Fix decimal conversion to handle edge cases more robustly
- [ ] Improve dimension mismatch error handling and logging
- [ ] Add automatic dimension detection and conversion
- [ ] Implement KB integrity validation after loading
- [ ] Add performance metrics for KB loading

**Files to modify:**
- `core/rag_system.py` (lines 652-731 for load_knowledge_base)
- `core/rag_system.py` (lines 377-392 for _ensure_active_embedding_dim)

### 2. Web Search Integration and Stabilization
**Current Issues:**
- Web search is optional and error-prone (lines 300-310 in generate_answers.py)
- No proper fallback mechanism
- Domain filtering could be more robust

**Tasks:**
- [ ] Implement robust web search with proper error handling
- [ ] Add fallback to local knowledge when web search fails
- [ ] Improve domain filtering and validation
- [ ] Add caching for web search results
- [ ] Implement rate limiting and budget tracking

**Files to modify:**
- `core/web_search.py` (if exists, else create)
- `scripts/generate_answers.py` (lines 300-310)

### 3. Model Selection Logic Improvement
**Current Issues:**
- Model selection logic is basic (lines 419-463 in generate_answers.py)
- No proper fallback when preferred models are unavailable
- Budget tracking could be more sophisticated

**Tasks:**
- [ ] Enhance model selection with availability checking
- [ ] Implement graceful fallback chain
- [ ] Improve budget estimation and tracking
- [ ] Add model performance monitoring
- [ ] Implement automatic model switching based on quality metrics

**Files to modify:**
- `scripts/generate_answers.py` (lines 419-463)
- `core/unified_api_client.py` (for model availability checking)

### 4. Decimal Fix Implementation
**Current Issues:**
- Decimal conversion issues in multiple places
- No centralized decimal handling

**Tasks:**
- [ ] Implement robust decimal-to-float conversion utility
- [ ] Add automatic decimal detection and conversion
- [ ] Implement validation for numerical data
- [ ] Add logging for decimal conversion issues

**Files to create/modify:**
- `core/utils.py` (new utility functions)
- `core/rag_system.py` (decimal handling improvements)

### 5. MD-Export Filter Implementation
**Current Issues:**
- No filtering for empty/questionable answers in MD export
- Quality control happens after generation

**Tasks:**
- [ ] Implement pre-export validation and filtering
- [ ] Add quality scoring for answers
- [ ] Implement automatic rejection of low-quality answers
- [ ] Add MD export validation layer
- [ ] Implement user feedback integration

**Files to modify:**
- `scripts/convert_json_to_md.py` (add validation)
- `core/medical_validator.py` (enhance validation)

### 6. Logging and Monitoring Enhancement
**Current Issues:**
- Logging is basic and not centralized
- No performance monitoring
- Limited error tracking

**Tasks:**
- [ ] Implement centralized logging system
- [ ] Add performance metrics collection
- [ ] Implement error tracking and reporting
- [ ] Add monitoring for KB load times
- [ ] Implement alerting for critical issues

**Files to create/modify:**
- `core/monitoring.py` (new monitoring system)
- `core/logging_config.py` (enhanced logging)
- Various files for logging improvements

## Implementation Priority
1. KB-Load stabilization (critical for pipeline)
2. Decimal fix (prevents data corruption)
3. MD-Export filtering (quality control)
4. Web search stabilization (enhances answer quality)
5. Model selection improvement (optimizes cost/quality)
6. Logging and monitoring (operational excellence)

## Success Criteria
- KB loading completes without dimension errors
- All decimal data properly converted to floats
- No empty/questionable answers pass MD export
- Web search fails gracefully with fallback
- Model selection adapts to budget and availability
- Comprehensive logging and monitoring in place

## Testing Requirements
- Unit tests for all new utility functions
- Integration tests for KB loading scenarios
- End-to-end tests for generation pipeline
- Performance benchmarks for critical operations
- Error handling validation tests