# Book Agent

## Overview

The Book Agent is an autonomous system that observes reading patterns and makes intelligent decisions about book states, reading behavior, and opportunities for engagement.

## Architecture

The agent operates in three phases:

1. **Observe**: Analyze reading data to infer book states
2. **Decide**: Make autonomous decisions based on patterns
3. **Act**: Create suggestions and store them in the database

## Usage

### Basic Usage

```python
from app.agents import BookAgent
from app.database import get_db

# Get database session
db = next(get_db())

# Create and run agent
agent = BookAgent(db, user_id=1)
result = agent.run()

# Result contains:
# - observations: What the agent observed
# - decisions: List of decisions made
# - actions_taken: List of actions performed
print(f"Agent made {result['summary']['total_decisions']} decisions")
```

### Get Suggestions

```python
# Get all unacknowledged suggestions
suggestions = agent.get_suggestions(acknowledged=False)

for suggestion in suggestions:
    print(f"{suggestion.decision_type}: {suggestion.reason}")
    print(f"Supporting data: {suggestion.supporting_data}")
```

### Acknowledge Suggestions

```python
# Mark a suggestion as acknowledged
agent.acknowledge_suggestion(suggestion_id=123)
```

## Agent Decisions

### 1. Stalled Books

**Decision Type**: `stalled_book`

**Trigger**: Book has been partially read (>5% progress) but untouched for 30+ days

**Action**: Creates suggestion to mark as stalled or resume reading

**Example**:
```json
{
  "decision_type": "stalled_book",
  "book_id": 42,
  "reason": "'The Great Gatsby' has been 45% read but untouched for 35 days...",
  "supporting_data": {
    "days_inactive": 35,
    "progress_percent": 45.2,
    "last_activity": "2025-12-10T10:00:00Z"
  }
}
```

### 2. Unrated Finished Books

**Decision Type**: `unrated_finished`

**Trigger**: Book is marked as "read" but has no rating

**Action**: Creates suggestion to rate and reflect on the book

**Example**:
```json
{
  "decision_type": "unrated_finished",
  "book_id": 15,
  "reason": "You finished '1984' but haven't rated it. Take a moment to reflect...",
  "supporting_data": {
    "days_since_finished": 5,
    "finished_date": "2026-01-12T15:00:00Z"
  }
}
```

### 3. Exploration Opportunities

**Decision Type**: `exploration_prompt`

**Trigger**: User has read 3+ books from the same genre/author recently

**Action**: Creates suggestion to explore different genres/authors

**Example**:
```json
{
  "decision_type": "exploration_prompt",
  "book_id": null,
  "reason": "You've read 4 Fantasy books recently. Consider exploring a different genre...",
  "supporting_data": {
    "concentration_type": "genre",
    "concentration_value": "Fantasy",
    "count": 4
  }
}
```

## Book State Awareness

The agent infers the following states:

### Currently Reading
- Has recent activity (< 30 days)
- Status is "currently_reading" or None
- Not marked as "read" or "abandoned"

### Stalled
- No activity for 30+ days
- Progress between 5% and 95%
- Not marked as "read" or "abandoned"

### Finished Unrated
- Status is "read"
- No rating assigned

### Abandoned
- Explicit status is "abandoned"

### Available on Shelf
- Most recent action was "taken" (not "returned")

## Deterministic Behavior

The agent is **deterministic** - given the same data, it will make the same decisions. This makes it:
- **Testable**: Can write unit tests with predictable outcomes
- **Debuggable**: Can trace exactly why a decision was made
- **Reliable**: No randomness or external dependencies

## Configuration

Agent behavior can be configured via thresholds:

```python
agent = BookAgent(db, user_id=1)
agent.stalled_days_threshold = 30  # Days before considering stalled
agent.exploration_similarity_threshold = 3  # Books before suggesting exploration
```

## Integration with API

The agent can be called from API endpoints:

```python
@router.post("/agent/run")
def run_book_agent(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    agent = BookAgent(db, user_id)
    result = agent.run()
    return result
```

## Future Enhancements

- Periodic automatic runs (via background jobs)
- More sophisticated pattern detection
- Learning from user feedback on suggestions
- Integration with recommendation engine

