# Spaced Repetition Algorithm Design

## 1. Algorithm Overview

The Spaced Repetition Algorithm will be implemented using the SM-2 algorithm, which is specifically mentioned in the architecture document. This algorithm calculates optimal review intervals based on user performance and memory retention principles.

## 2. Core Components

### 2.1 Data Model

The algorithm will work with the following data structure for each learning item:

```python
class LearningItem:
    def __init__(self, item_id, content, difficulty=2.5):
        self.item_id = item_id          # Unique identifier
        self.content = content          # The learning content
        self.difficulty = difficulty    # Initial difficulty factor (2.5)
        self.interval = 1               # Initial review interval in days
        self.repetitions = 0            # Number of successful repetitions
        self.easiness_factor = 2.5      # Initial easiness factor (SM-2 standard)
        self.last_review = None         # Timestamp of last review
        self.next_review = None         # Timestamp of next review
```

### 2.2 SM-2 Algorithm Logic

The core SM-2 algorithm logic:

1. **Initial Review**: When a user first learns an item, it's scheduled for review in 1 day
2. **Review Quality Assessment**: User rates their recall quality (0-5 scale)
3. **Interval Calculation**: Based on the quality rating, calculate the next interval
4. **Easiness Factor Adjustment**: Adjust the easiness factor based on performance

### 2.3 Quality Rating Scale

- 0: Complete blackout
- 1: Incorrect response, but remembered after seeing the answer
- 2: Incorrect response, but easy to recall after seeing the answer
- 3: Correct response, but with difficulty
- 4: Correct response after some hesitation
- 5: Perfect response

## 3. Algorithm Implementation

### 3.1 Core Functions

```python
def calculate_next_interval(quality, easiness_factor, repetitions, current_interval):
    """
    Calculate the next review interval based on SM-2 algorithm
    """
    if quality < 3:
        # Poor performance - reset interval
        new_interval = 1
        new_repetitions = 0
    else:
        # Good performance - increase interval
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(current_interval * easiness_factor)

        new_repetitions = repetitions + 1

    # Update easiness factor
    new_easiness = max(1.3, easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

    return new_interval, new_repetitions, new_easiness
```

### 3.2 Review Process

```python
def review_item(item, quality_rating):
    """
    Process a review of a learning item and update its schedule
    """
    # Calculate new values
    new_interval, new_reps, new_easiness = calculate_next_interval(
        quality_rating,
        item.easiness_factor,
        item.repetitions,
        item.interval
    )

    # Update the item
    item.easiness_factor = new_easiness
    item.repetitions = new_reps
    item.interval = new_interval
    item.last_review = datetime.now()

    # Calculate next review date
    item.next_review = datetime.now() + timedelta(days=new_interval)

    return item
```

## 4. Database Integration

### 4.1 Database Schema

The algorithm will integrate with the existing PostgreSQL database using the following schema:

```sql
CREATE TABLE learning_items (
    item_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    content TEXT NOT NULL,
    difficulty DECIMAL(3,1) DEFAULT 2.5,
    interval INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    easiness_factor DECIMAL(4,2) DEFAULT 2.5,
    last_review TIMESTAMP,
    next_review TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 API Endpoints

The algorithm will be exposed through the following RESTful API endpoints:

- `GET /api/learning-items/due` - Get items due for review
- `POST /api/learning-items/review` - Submit review results
- `GET /api/learning-items/stats` - Get learning statistics
- `POST /api/learning-items` - Create new learning items

## 5. Integration with Mentor-Agent Architecture

### 5.1 Backend Module Integration

The Spaced Repetition Algorithm will be implemented as a separate module within the Node.js backend:

```
backend/
├── modules/
│   ├── spaced_repetition/
│   │   ├── algorithm.js       # Core SM-2 algorithm
│   │   ├── controller.js      # API controllers
│   │   ├── model.js           # Database models
│   │   ├── routes.js          # API routes
│   │   └── service.js         # Business logic
```

### 5.2 Frontend Integration

The frontend will integrate with the algorithm through:

1. **Review Interface**: Display learning items due for review
2. **Quality Rating Input**: Allow users to rate their recall quality
3. **Progress Tracking**: Show learning statistics and progress
4. **Scheduling Visualization**: Display upcoming review schedule

## 6. Testing Strategy

### 6.1 Unit Tests

- Test the core SM-2 algorithm calculations
- Test edge cases (quality ratings 0-5)
- Test interval progression over multiple reviews

### 6.2 Integration Tests

- Test database integration
- Test API endpoint functionality
- Test error handling and validation

### 6.3 End-to-End Tests

- Test complete review workflow
- Test user interface integration
- Test performance with large datasets

## 7. Performance Considerations

- **Caching**: Cache frequently accessed learning items
- **Batch Processing**: Process multiple reviews in batches
- **Indexing**: Proper database indexing for performance
- **Asynchronous Processing**: Use background jobs for heavy calculations
