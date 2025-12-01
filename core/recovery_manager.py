"""Recovery manager for crash recovery and graceful degradation."""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RecoveryManager:
    """Manages crash recovery and graceful degradation."""
    
    def __init__(
        self,
        checkpoint_dir: str = 'checkpoints',
        max_recovery_age_hours: int = 24
    ):
        """Initialize recovery manager.
        
        Args:
            checkpoint_dir: Directory with checkpoint files
            max_recovery_age_hours: Maximum age of recoverable sessions
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_recovery_age_hours = max_recovery_age_hours
    
    def detect_orphaned_sessions(self) -> List[Dict[str, Any]]:
        """Detect sessions that may need recovery.
        
        Returns:
            List of orphaned session info dicts
        """
        if not self.checkpoint_dir.exists():
            logger.info("No checkpoint directory found")
            return []
        
        orphaned = []
        checkpoint_files = list(self.checkpoint_dir.glob('checkpoint_*.json'))
        
        for checkpoint_path in checkpoint_files:
            try:
                with open(checkpoint_path, 'r') as f:
                    session_data = json.load(f)
                
                # Check if session is still active
                if session_data.get('status') == 'active':
                    started_at = datetime.fromisoformat(session_data['started_at'])
                    age_hours = (datetime.now() - started_at).total_seconds() / 3600
                    
                    if age_hours <= self.max_recovery_age_hours:
                        orphaned.append({
                            'session_id': session_data['id'],
                            'checkpoint_path': str(checkpoint_path),
                            'age_hours': age_hours,
                            'docs_processed': len(session_data.get('processed_docs', [])),
                            'tokens_used': session_data.get('context_tokens', 0)
                        })
                        logger.info(
                            f"🔍 Found orphaned session: {session_data['id']} "
                            f"({age_hours:.1f}h old, {len(session_data.get('processed_docs', []))} docs)"
                        )
            except Exception as e:
                logger.warning(f"⚠️ Could not read checkpoint {checkpoint_path}: {e}")
        
        return orphaned
    
    def recover_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recover session from checkpoint.
        
        Args:
            session_id: Session ID to recover
            
        Returns:
            Recovered session data or None
        """
        checkpoint_path = self.checkpoint_dir / f"checkpoint_{session_id}.json"
        
        if not checkpoint_path.exists():
            logger.error(f"❌ No checkpoint found for session {session_id}")
            return None
        
        try:
            with open(checkpoint_path, 'r') as f:
                session_data = json.load(f)
            
            logger.info(
                f"✅ Recovered session {session_id}: "
                f"{len(session_data.get('processed_docs', []))} docs, "
                f"{session_data.get('context_tokens', 0)} tokens"
            )
            
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Failed to recover session {session_id}: {e}")
            return None
    
    def verify_recovery(self, session_data: Dict[str, Any]) -> bool:
        """Verify recovered session is valid.
        
        Args:
            session_data: Recovered session data
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['id', 'started_at', 'max_context_tokens']
        
        for field in required_fields:
            if field not in session_data:
                logger.error(f"❌ Missing required field: {field}")
                return False
        
        # Validate processed_docs structure
        if 'processed_docs' in session_data:
            for doc in session_data['processed_docs']:
                if not isinstance(doc, dict) or 'path' not in doc:
                    logger.error(f"❌ Invalid document entry: {doc}")
                    return False
        
        logger.info(f"✅ Session {session_data['id']} verified successfully")
        return True
    
    def graceful_degradation(
        self,
        session_data: Dict[str, Any],
        error: Exception
    ) -> Dict[str, Any]:
        """Apply graceful degradation strategies.
        
        Args:
            session_data: Current session data
            error: Error that occurred
            
        Returns:
            Recovery strategy recommendations
        """
        strategy = {
            'action': 'unknown',
            'reason': str(error),
            'recommendations': []
        }
        
        error_type = type(error).__name__
        
        if 'Memory' in error_type or 'MemoryError' in str(error):
            strategy['action'] = 'reduce_batch_size'
            strategy['recommendations'] = [
                'Reduce document batch size',
                'Process documents one at a time',
                'Clear processed documents from memory',
                'Consider checkpoint more frequently'
            ]
        
        elif 'Timeout' in error_type or 'timeout' in str(error).lower():
            strategy['action'] = 'retry_with_timeout'
            strategy['recommendations'] = [
                'Increase timeout duration',
                'Retry with exponential backoff',
                'Switch to alternative provider',
                'Skip problematic document if persistent'
            ]
        
        elif 'Budget' in error_type or 'budget' in str(error).lower():
            strategy['action'] = 'stop_processing'
            strategy['recommendations'] = [
                'Budget limit reached - stop processing',
                'Create handover for continuation',
                'Review processed documents',
                'Wait for budget reset or increase limit'
            ]
        
        else:
            strategy['action'] = 'generic_recovery'
            strategy['recommendations'] = [
                'Save current progress',
                'Log error details',
                'Attempt recovery from last checkpoint',
                'Continue with next document if possible'
            ]
        
        logger.warning(
            f"⚠️ Graceful degradation: {strategy['action']} due to {error_type}"
        )
        
        return strategy
    
    def auto_recover_all(self) -> List[Dict[str, Any]]:
        """Automatically recover all orphaned sessions.
        
        Returns:
            List of recovery results
        """
        orphaned = self.detect_orphaned_sessions()
        results = []
        
        if not orphaned:
            logger.info("✅ No orphaned sessions found")
            return results
        
        logger.info(f"🔄 Found {len(orphaned)} orphaned sessions, attempting recovery...")
        
        for session_info in orphaned:
            session_id = session_info['session_id']
            session_data = self.recover_session(session_id)
            
            if session_data and self.verify_recovery(session_data):
                results.append({
                    'session_id': session_id,
                    'status': 'recovered',
                    'docs_processed': len(session_data.get('processed_docs', [])),
                    'can_continue': True
                })
            else:
                results.append({
                    'session_id': session_id,
                    'status': 'failed',
                    'can_continue': False
                })
        
        logger.info(
            f"✅ Recovery complete: {len([r for r in results if r['status'] == 'recovered'])}/{len(results)} successful"
        )
        
        return results



















