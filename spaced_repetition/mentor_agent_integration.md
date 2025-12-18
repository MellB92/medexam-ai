# Mentor Agent Integration Sketch

## Overview
This document outlines the integration approach between the Spaced Repetition system and the Mentor Agent architecture. The integration will enable the mentor agent to leverage spaced repetition principles for optimized learning schedules and knowledge reinforcement.

## Integration Architecture

### System Components
```
┌───────────────────────────────────────────────────────┐
│                   Mentor Agent System                 │
├───────────────────┬───────────────────┬───────────────┤
│   User Interface  │  Mentor Agent     │ Spaced Repetition│
│                   │  Core Logic       │   System        │
└─────────┬─────────┴─────────┬─────────┴─────────┬───────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────┐
│  User Interaction │ │ Learning Schedule │ │ SM-2 Algorithm │
│  & Feedback       │ │  Management       │ │ Implementation │
└───────────────────┘ └───────────────────┘ └───────────────┘
```

### Integration Points

#### 1. Learning Item Management
**Purpose:** Synchronize learning items between Mentor Agent and Spaced Repetition system

**API Endpoints:**
```python
# Create new learning item
POST /api/learning-items
{
    "item_id": "unique_id",
    "content": "Learning content",
    "category": "medicine/surgery/other",
    "difficulty": 2.5,
    "metadata": {
        "source": "textbook/lecture/exam",
        "priority": "high/medium/low"
    }
}

# Update existing learning item
PUT /api/learning-items/{item_id}
{
    "content": "Updated content",
    "difficulty": 3.0,
    "metadata": {...}
}

# Get learning items due for review
GET /api/learning-items/due
{
    "limit": 10,
    "category_filter": "all/medicine/surgery",
    "priority_filter": "all/high"
}

# Get learning item by ID
GET /api/learning-items/{item_id}
```

#### 2. Review Processing
**Purpose:** Process user reviews and update scheduling

**API Endpoints:**
```python
# Submit review result
POST /api/reviews
{
    "item_id": "unique_id",
    "quality_rating": 3,  # 0-5 scale
    "review_timestamp": "ISO_timestamp",
    "user_feedback": "optional text feedback",
    "review_duration": 120  # seconds
}

# Get review history for item
GET /api/reviews/{item_id}
{
    "limit": 10,
    "include_analytics": true
}
```

#### 3. Statistics and Analytics
**Purpose:** Provide learning progress analytics to Mentor Agent

**API Endpoints:**
```python
# Get user learning statistics
GET /api/statistics/user/{user_id}
{
    "time_range": "week/month/all",
    "category_filter": "all/medicine/surgery"
}

# Get item-specific statistics
GET /api/statistics/items/{item_id}

# Get system performance metrics
GET /api/statistics/system
```

## Data Flow

### 1. Learning Item Creation Flow
```
┌─────────────┐       ┌───────────────────┐       ┌───────────────────┐
│             │       │                   │       │                   │
│  User       │──────▶│  Mentor Agent     │──────▶│ Spaced Repetition │
│  Interaction│       │  (Content Analysis)│       │ (Item Creation)   │
│             │       │                   │       │                   │
└─────────────┘       └─────────┬─────────┘       └─────────┬─────────┘
                              │                           │
                              ▼                           ▼
                    ┌───────────────────┐       ┌───────────────────┐
                    │  Learning Item    │       │  SM-2 Scheduling  │
                    │  Database         │       │  Algorithm        │
                    └───────────────────┘       └───────────────────┘
```

### 2. Review Processing Flow
```
┌─────────────┐       ┌───────────────────┐       ┌───────────────────┐
│             │       │                   │       │                   │
│  User       │◀──────│  Mentor Agent     │◀──────│ Spaced Repetition │
│  Review     │       │  (Review Analysis) │       │ (Interval Update) │
│             │       │                   │       │                   │
└─────────────┘       └─────────┬─────────┘       └─────────┬─────────┘
                              │                           │
                              ▼                           ▼
                    ┌───────────────────┐       ┌───────────────────┐
                    │  Review History    │       │  Updated Learning │
                    │  Database          │       │  Schedule          │
                    └───────────────────┘       └───────────────────┘
```

## Integration Implementation

### Python Integration Example

```python
from spaced_repetition.algorithm import LearningItem, review_item
from spaced_repetition.mentor_agent import MentorAgentClient

class SpacedRepetitionMentorIntegration:
    """
    Integration class for connecting Mentor Agent with Spaced Repetition system.
    """

    def __init__(self, mentor_agent_url, api_key):
        """
        Initialize integration with Mentor Agent API.
        """
        self.client = MentorAgentClient(mentor_agent_url, api_key)
        self.learning_items = {}  # Local cache of learning items

    def create_learning_item(self, content, category, difficulty=2.5, metadata=None):
        """
        Create a new learning item in both systems.
        """
        # Create in Spaced Repetition system
        item = LearningItem(
            item_id=f"item_{len(self.learning_items)+1}",
            content=content,
            difficulty=difficulty,
            metadata=metadata or {}
        )

        # Sync with Mentor Agent
        response = self.client.create_learning_item(
            item_id=item.item_id,
            content=content,
            category=category,
            difficulty=difficulty,
            metadata=metadata
        )

        if response.success:
            self.learning_items[item.item_id] = item
            return item
        else:
            raise Exception(f"Failed to create learning item: {response.error}")

    def process_user_review(self, item_id, quality_rating, feedback=None):
        """
        Process a user review and update both systems.
        """
        if item_id not in self.learning_items:
            raise ValueError(f"Learning item {item_id} not found")

        item = self.learning_items[item_id]

        # Process review in Spaced Repetition system
        updated_item = review_item(item, quality_rating)

        # Sync with Mentor Agent
        response = self.client.submit_review(
            item_id=item_id,
            quality_rating=quality_rating,
            user_feedback=feedback
        )

        if response.success:
            self.learning_items[item_id] = updated_item
            return updated_item
        else:
            raise Exception(f"Failed to process review: {response.error}")

    def get_due_items(self, limit=10, category=None):
        """
        Get learning items that are due for review.
        """
        # Get from Mentor Agent
        response = self.client.get_due_learning_items(limit=limit, category_filter=category)

        if response.success:
            due_items = []
            for item_data in response.items:
                if item_data['item_id'] in self.learning_items:
                    # Update local item with latest data
                    local_item = self.learning_items[item_data['item_id']]
                    if local_item.next_review != item_data['next_review']:
                        local_item.next_review = datetime.datetime.fromisoformat(item_data['next_review'])
                    due_items.append(local_item)
            return due_items
        else:
            raise Exception(f"Failed to get due items: {response.error}")

    def get_learning_statistics(self, time_range="week"):
        """
        Get learning statistics for the user.
        """
        response = self.client.get_learning_statistics(time_range=time_range)

        if response.success:
            return {
                'total_items': response.stats['total_items'],
                'due_items': response.stats['due_items'],
                'overdue_items': response.stats['overdue_items'],
                'avg_easiness': response.stats['avg_easiness'],
                'completion_rate': response.stats['completion_rate'],
                'improvement_trend': response.stats['improvement_trend']
            }
        else:
            raise Exception(f"Failed to get statistics: {response.error}")
```

### Error Handling and Recovery

```python
def handle_integration_error(self, error, operation="unknown"):
    """
    Handle integration errors with retry logic and fallback mechanisms.
    """
    logger.error(f"Integration error in {operation}: {str(error)}")

    # Retry transient errors
    if isinstance(error, (requests.ConnectionError, requests.Timeout)):
        logger.info("Retrying operation due to transient error...")
        try:
            time.sleep(2)  # Wait before retry
            return self._retry_operation(operation)
        except Exception as retry_error:
            logger.error(f"Retry failed: {str(retry_error)}")

    # Fallback for non-critical operations
    if operation in ["get_statistics", "get_due_items"]:
        logger.warning(f"Using fallback data for {operation}")
        return self._get_fallback_data(operation)

    # Critical error - notify monitoring
    self._notify_monitoring_system(error, operation)
    raise IntegrationError(f"Critical integration failure: {str(error)}")
```

## Testing Strategy

### Integration Test Cases

1. **Learning Item Synchronization Test**
   - Verify items created in Spaced Repetition are synced to Mentor Agent
   - Verify metadata and scheduling information is preserved

2. **Review Processing Test**
   - Test all quality ratings (0-5) are handled correctly
   - Verify review history is maintained in both systems

3. **Error Handling Test**
   - Test network failure scenarios
   - Test API timeout handling
   - Test data consistency after recovery

4. **Performance Test**
   - Measure API response times
   - Test with large numbers of learning items (1000+)
   - Verify system remains responsive under load

## Deployment Considerations

### Configuration Requirements
```json
{
  "mentor_agent": {
    "api_url": "https://mentor-agent.example.com/api",
    "api_key": "secure_api_key_here",
    "timeout": 30,
    "retry_limit": 3,
    "cache_ttl": 300
  },
  "spaced_repetition": {
    "max_items": 5000,
    "default_difficulty": 2.5,
    "logging_level": "INFO"
  }
}
```

### Monitoring and Alerting
- **Metrics to Monitor:**
  - API response times
  - Synchronization success/failure rates
  - Data consistency between systems
  - System resource utilization

- **Alert Thresholds:**
  - Response time > 2s (warning)
  - Response time > 5s (critical)
  - Synchronization failure rate > 1% (warning)
  - Synchronization failure rate > 5% (critical)

## Future Enhancements

1. **Real-time Synchronization**
   - Implement WebSocket-based real-time updates
   - Add conflict resolution mechanisms

2. **Advanced Analytics**
   - Machine learning-based difficulty prediction
   - Personalized learning pace recommendations

3. **Multi-User Support**
   - User-specific learning profiles
   - Collaborative learning features

4. **Mobile Integration**
   - Mobile SDK for iOS/Android
   - Offline mode with sync capabilities

## Documentation and Support

### API Documentation
- Swagger/OpenAPI specification
- Interactive API explorer
- Code examples in Python, JavaScript, Java

### Support Channels
- Developer support forum
- GitHub issue tracker
- Email support for critical issues

### Troubleshooting Guide
```markdown
## Common Issues and Solutions

### Connection Issues
**Symptom:** API calls failing with connection errors
**Solution:**
1. Check network connectivity
2. Verify API URL is correct
3. Check firewall settings
4. Contact support if issue persists

### Synchronization Failures
**Symptom:** Items not syncing between systems
**Solution:**
1. Check error logs for specific failure
2. Verify item IDs are unique
3. Check data format compatibility
4. Manually trigger resync if needed

### Performance Issues
**Symptom:** Slow response times
**Solution:**
1. Check system resource utilization
2. Optimize database queries
3. Implement caching where appropriate
4. Consider horizontal scaling
```

## Conclusion

This integration sketch provides a comprehensive plan for connecting the Spaced Repetition system with the Mentor Agent architecture. The proposed solution includes:

1. **Clear API contracts** for seamless communication
2. **Robust error handling** for reliable operation
3. **Comprehensive testing** to ensure quality
4. **Scalable architecture** for future growth
5. **Complete documentation** for maintenance and support

The integration will enable the Mentor Agent to provide personalized, spaced-repetition-based learning experiences while maintaining data consistency and system reliability.