"""Crash handler for graceful error handling."""
import sys
import traceback
import logging
from typing import Optional, Callable, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class CrashHandler:
    """Handles crashes and unexpected errors gracefully."""

    def __init__(
        self,
        recovery_manager,
        auto_save: bool = True,
        log_file: str = 'crash_logs.txt'
    ):
        """Initialize crash handler.

        Args:
            recovery_manager: RecoveryManager instance
            auto_save: Automatically save state on crash
            log_file: File to log crashes
        """
        self.recovery_manager = recovery_manager
        self.auto_save = auto_save
        self.log_file = Path(log_file)
        self.session_manager = None

    def set_session_manager(self, session_manager):
        """Set session manager for state saving.

        Args:
            session_manager: SessionManager instance
        """
        self.session_manager = session_manager

    def handle_crash(self, error: Exception, context: str = "") -> bool:
        """Handle crash gracefully.

        Args:
            error: Exception that occurred
            context: Context information

        Returns:
            True if recovery possible, False otherwise
        """
        logger.error(f"💥 CRASH DETECTED: {type(error).__name__}: {error}")

        # Log crash details
        self._log_crash(error, context)

        # Auto-save if enabled
        if self.auto_save and self.session_manager:
            try:
                self.session_manager._save_checkpoint()
                logger.info("💾 Emergency checkpoint saved")
            except Exception as save_error:
                logger.error(f"❌ Failed to save emergency checkpoint: {save_error}")

        # Get recovery strategy
        if self.session_manager and self.session_manager.current_session:
            strategy = self.recovery_manager.graceful_degradation(
                self.session_manager.current_session.to_dict(),
                error
            )

            logger.info(f"🔄 Recovery strategy: {strategy['action']}")
            for rec in strategy['recommendations']:
                logger.info(f"   → {rec}")

            return strategy['action'] != 'stop_processing'

        return False

    def _log_crash(self, error: Exception, context: str):
        """Log crash to file.

        Args:
            error: Exception
            context: Context info
        """
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'a') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Crash at: {datetime.now().isoformat()}\n")
                f.write(f"Context: {context}\n")
                f.write(f"Error: {type(error).__name__}: {error}\n")
                f.write(f"Traceback:\n")
                traceback.print_exc(file=f)
                f.write(f"{'='*80}\n")
        except Exception as log_error:
            logger.error(f"Failed to log crash: {log_error}")

    def safe_execute(
        self,
        func: Callable,
        *args,
        context: str = "",
        **kwargs
    ) -> Optional[Any]:
        """Execute function with crash handling.

        Args:
            func: Function to execute
            *args: Function arguments
            context: Context description
            **kwargs: Function keyword arguments

        Returns:
            Function result or None on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            can_recover = self.handle_crash(e, context)
            if not can_recover:
                raise
            return None
