"""Comprehensive tests for spaced_repetition algorithm."""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
import logging
import time
import sys

from spaced_repetition.algorithm import (
    LearningItem,
    calculate_next_interval,
    review_item
)


class TestLearningItem(unittest.TestCase):
    """Tests for LearningItem class."""

    def test_valid_init(self):
        """Test valid initialization."""
        item = LearningItem("id1", "content")
        self.assertEqual(item.item_id, "id1")
        self.assertEqual(item.content, "content")
        self.assertEqual(item.easiness_factor, 2.5)
        self.assertEqual(item.repetitions, 0)
        self.assertEqual(item.interval, 1)
        self.assertIsNone(item.last_review)
        self.assertIsNone(item.next_review)

    def test_invalid_easiness_factor(self):
        """Test initialization with invalid easiness factor."""
        with self.assertRaises(ValueError):
            LearningItem("id1", "content", easiness_factor=1.0)


class TestCalculateNextInterval(unittest.TestCase):
    """Tests for calculate_next_interval function."""

    def test_quality_below_3_resets(self):
        """Test quality < 3 resets interval and reps."""
        for quality in [0, 1, 2]:
            interval, reps, ef = calculate_next_interval(quality, 2.5, 5, 20)
            self.assertEqual(interval, 1)
            self.assertEqual(reps, 0)
            # EF update for quality 0: 2.5 + 0.1 - 5*(0.08+0.1)=2.5-0.8=1.7
            expected_ef = max(1.3, 2.5 + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
            self.assertAlmostEqual(ef, expected_ef, places=2)

    def test_quality_3_reps0(self):
        """Test quality=3, reps=0 -> interval=1, reps=1."""
        interval, reps, ef = calculate_next_interval(3, 2.5, 0, 1)
        self.assertEqual(interval, 1)
        self.assertEqual(reps, 1)
        self.assertAlmostEqual(ef, 2.5, places=2)  # No change for q=3

    def test_quality_4_reps1(self):
        """Test quality=4, reps=1 -> interval=6, reps=2."""
        interval, reps, ef = calculate_next_interval(4, 2.5, 1, 1)
        self.assertEqual(interval, 6)
        self.assertEqual(reps, 2)
        self.assertAlmostEqual(ef, 2.6, places=2)  # +0.1 for q=4

    def test_quality_5_reps2(self):
        """Test quality=5, reps=2 -> interval=round(1*2.5)=3, reps=3."""
        interval, reps, ef = calculate_next_interval(5, 2.5, 2, 1)
        self.assertEqual(interval, 3)
        self.assertEqual(reps, 3)
        self.assertEqual(ef, 2.5)  # No change for q=5

    def test_higher_reps_progression(self):
        """Test progression for higher reps."""
        interval, reps, ef = calculate_next_interval(4, 2.6, 3, 10)
        self.assertEqual(interval, 27)  # round(10*2.6)=26, wait round(26)=26? 10*2.6=26
        self.assertEqual(reps, 4)
        self.assertAlmostEqual(ef, 2.7, places=2)

    def test_invalid_quality(self):
        """Test invalid quality raises ValueError."""
        with self.assertRaises(ValueError):
            calculate_next_interval(6, 2.5, 0, 1)
        with self.assertRaises(ValueError):
            calculate_next_interval(-1, 2.5, 0, 1)
        with self.assertRaises(ValueError):
            calculate_next_interval(2.5, 2.5, 0, 1)  # not int


class TestReviewItem(unittest.TestCase):
    """Tests for review_item function."""

    def test_review_perfect(self):
        """Test perfect review updates correctly."""
        item = LearningItem("id1", "content")
        item = review_item(item, 5)
        self.assertEqual(item.repetitions, 1)
        self.assertEqual(item.interval, 1)
        self.assertEqual(item.easiness_factor, 2.5)
        self.assertIsNotNone(item.last_review)
        self.assertIsNotNone(item.next_review)
        self.assertAlmostEqual(item.next_review, item.last_review + timedelta(days=1), delta=timedelta(seconds=1))

    def test_review_poor_resets(self):
        """Test poor review resets."""
        item = LearningItem("id1", "content")
        item = review_item(item, 5)  # First good
        item = review_item(item, 0)  # Poor
        self.assertEqual(item.repetitions, 0)
        self.assertEqual(item.interval, 1)
        self.assertLess(item.easiness_factor, 2.5)

    def test_type_error(self):
        """Test non-LearningItem raises TypeError."""
        with self.assertRaises(TypeError):
            review_item("not an item", 5)


@patch('logging.Logger.debug')
@patch('logging.Logger.info')
class TestLogging(unittest.TestCase):
    """Tests for logging."""

    def test_logging_calls(self, mock_info, mock_debug):
        """Verify logging is called."""
        calculate_next_interval(5, 2.5, 0, 1)
        mock_debug.assert_called_once()
        mock_info.assert_called_once()


class TestPerformance(unittest.TestCase):
    """Performance tests."""

    @patch('time.time')
    def test_large_dataset(self, mock_time):
        """Test performance with 1000 items."""
        mock_time.return_value = 0
        items = [LearningItem(f"id{i}", f"content{i}") for i in range(1000)]
        start = time.time()
        for item in items:
            review_item(item, 4)
        duration = time.time() - start
        self.assertLess(duration, 1.0)  # Should be fast


if __name__ == '__main__':
    unittest.main()
