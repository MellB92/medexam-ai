import logging
from datetime import datetime, timedelta
from typing import Tuple

logger = logging.getLogger(__name__)

class LearningItem:
    """
    Represents a single learning item for spaced repetition.
    
    Attributes:
        item_id (str): Unique identifier for the item
        content (str): The learning content (question/answer)
        easiness_factor (float): SM-2 easiness factor (default 2.5)
        repetitions (int): Number of successful repetitions (default 0)
        interval (int): Current review interval in days (default 1)
        last_review (datetime): Timestamp of last review
        next_review (datetime): Timestamp of next scheduled review
    """
    def __init__(self, item_id: str, content: str, easiness_factor: float = 2.5):
        if easiness_factor < 1.3:
            raise ValueError("Easiness factor must be at least 1.3")
        self.item_id = item_id
        self.content = content
        self.easiness_factor = easiness_factor
        self.repetitions = 0
        self.interval = 1
        self.last_review = None
        self.next_review = None

def calculate_next_interval(
    quality: int, 
    easiness_factor: float, 
    repetitions: int, 
    current_interval: int
) -> Tuple[int, int, float]:
    """
    SM-2 algorithm to calculate next review interval, repetitions, and easiness factor.
    
    Args:
        quality (int): User quality rating (0-5)
        easiness_factor (float): Current easiness factor
        repetitions (int): Current repetitions count
        current_interval (int): Current interval in days
    
    Returns:
        Tuple[int, int, float]: (new_interval, new_repetitions, new_easiness_factor)
    
    Raises:
        ValueError: If quality is not in 0-5 range
    """
    if not isinstance(quality, int) or not 0 <= quality <= 5:
        raise ValueError("Quality rating must be an integer between 0 and 5")
    
    logger.debug(f"Calculating interval: quality={quality}, ef={easiness_factor:.2f}, reps={repetitions}, interval={current_interval}")
    
    if quality < 3:
        # Poor performance: reset to initial state
        new_interval = 1
        new_repetitions = 0
    else:
        # Good performance: progress interval
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(current_interval * easiness_factor)
        new_repetitions = repetitions + 1
    
    # Update easiness factor (SM-2 formula)
    new_easiness = max(
        1.3, 
        easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    )
    
    logger.info(
        f"SM-2 calculation: quality={quality} -> interval={new_interval}, "
        f"reps={new_repetitions}, ef={new_easiness:.2f}"
    )
    
    return new_interval, new_repetitions, new_easiness

def review_item(item: LearningItem, quality: int) -> LearningItem:
    """
    Process a user review for a LearningItem and update its schedule.
    
    Args:
        item (LearningItem): The learning item to review
        quality (int): User-assessed quality (0-5)
    
    Returns:
        LearningItem: Updated item with new schedule
    """
    if not isinstance(item, LearningItem):
        raise TypeError("item must be a LearningItem instance")
    
    new_interval, new_reps, new_easiness = calculate_next_interval(
        quality, item.easiness_factor, item.repetitions, item.interval
    )
    
    # Update item state
    item.easiness_factor = new_easiness
    item.repetitions = new_reps
    item.interval = new_interval
    item.last_review = datetime.now()
    item.next_review = datetime.now() + timedelta(days=new_interval)
    
    logger.info(
        f"Item {item.item_id} reviewed (quality={quality}): "
        f"next_review={item.next_review.isoformat()}, interval={new_interval}"
    )
    
    return item

# Example usage (for testing)
if __name__ == "__main__":
    item = LearningItem("test1", "What is Anaphylaxie?")
    print(f"Initial: {item.__dict__}")
    
    item = review_item(item, 5)
    print(f"After perfect review: {item.__dict__}")
    
    item = review_item(item, 4)
    print(f"After good review: {item.__dict__}")
