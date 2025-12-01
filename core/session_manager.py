"""Session management with memory bank for context tracking."""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Session:
    """Represents a processing session."""
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        max_context_tokens: int = 100_000
    ):
        """Initialize session.
        
        Args:
            session_id: Unique session ID (auto-generated if None)
            max_context_tokens: Maximum context tokens before handover
        """
        self.id = session_id or str(uuid.uuid4())
        self.started_at = datetime.now()
        self.max_context_tokens = max_context_tokens
        self.context_tokens = 0
        self.processed_docs = []
        self.current_provider = None
        self.budget_used = 0.0
        self.status = 'active'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            'id': self.id,
            'started_at': self.started_at.isoformat(),
            'max_context_tokens': self.max_context_tokens,
            'context_tokens': self.context_tokens,
            'processed_docs': self.processed_docs,
            'current_provider': self.current_provider,
            'budget_used': self.budget_used,
            'status': self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create session from dictionary."""
        session = cls(
            session_id=data['id'],
            max_context_tokens=data.get('max_context_tokens', 100_000)
        )
        session.started_at = datetime.fromisoformat(data['started_at'])
        session.context_tokens = data.get('context_tokens', 0)
        session.processed_docs = data.get('processed_docs', [])
        session.current_provider = data.get('current_provider')
        session.budget_used = data.get('budget_used', 0.0)
        session.status = data.get('status', 'active')
        return session


class SessionManager:
    """Manages sessions with automatic handover and checkpointing."""
    
    def __init__(
        self,
        checkpoint_dir: str = 'checkpoints',
        checkpoint_interval: int = 10,
        handover_threshold: float = 0.8
    ):
        """Initialize session manager.
        
        Args:
            checkpoint_dir: Directory for checkpoint files
            checkpoint_interval: Save checkpoint every N documents
            handover_threshold: Create handover at this % of context (0.8 = 80%)
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.checkpoint_interval = checkpoint_interval
        self.handover_threshold = handover_threshold
        self.current_session: Optional[Session] = None
    
    def start_session(
        self,
        session_id: Optional[str] = None,
        max_context_tokens: int = 100_000
    ) -> Session:
        """Start new session or resume existing.
        
        Args:
            session_id: Resume existing session if provided
            max_context_tokens: Max tokens before handover
            
        Returns:
            Session object
        """
        if session_id:
            # Try to resume existing session
            session = self._load_session(session_id)
            if session:
                logger.info(f"✅ Resumed session {session_id}")
                self.current_session = session
                return session
        
        # Create new session
        session = Session(session_id, max_context_tokens)
        self.current_session = session
        logger.info(f"✅ Started new session {session.id}")
        return session
    
    def track_document(
        self,
        doc_path: str,
        tokens_used: int,
        results: Any,
        provider: str
    ) -> Dict[str, Any]:
        """Track processed document.
        
        Args:
            doc_path: Path to document
            tokens_used: Tokens used for this document
            results: Processing results
            provider: Provider used
            
        Returns:
            Dict with status info (handover_needed, checkpoint_saved)
        """
        if not self.current_session:
            raise RuntimeError("No active session. Call start_session() first.")
        
        session = self.current_session
        session.context_tokens += tokens_used
        session.current_provider = provider
        
        doc_info = {
            'path': doc_path,
            'tokens': tokens_used,
            'timestamp': datetime.now().isoformat(),
            'provider': provider,
            'results_count': len(results) if isinstance(results, list) else 0
        }
        session.processed_docs.append(doc_info)
        
        logger.info(
            f"📄 Tracked: {doc_path} ({tokens_used} tokens) | "
            f"Total: {session.context_tokens}/{session.max_context_tokens}"
        )
        
        status = {
            'handover_needed': False,
            'checkpoint_saved': False
        }
        
        # Check for handover
        if self._should_create_handover():
            self._create_handover()
            status['handover_needed'] = True
        
        # Check for checkpoint
        if len(session.processed_docs) % self.checkpoint_interval == 0:
            self._save_checkpoint()
            status['checkpoint_saved'] = True
        
        return status
    
    def _should_create_handover(self) -> bool:
        """Check if handover is needed."""
        if not self.current_session:
            return False
        
        usage_percent = (
            self.current_session.context_tokens / 
            self.current_session.max_context_tokens
        )
        return usage_percent >= self.handover_threshold
    
    def _create_handover(self):
        """Generate handover document."""
        if not self.current_session:
            return
        
        session = self.current_session
        
        handover = {
            'session_id': session.id,
            'timestamp': datetime.now().isoformat(),
            'processed_count': len(session.processed_docs),
            'total_tokens': session.context_tokens,
            'usage_percent': (session.context_tokens / session.max_context_tokens * 100),
            'summary': self._generate_summary(),
            'next_steps': self._generate_next_steps(),
            'critical_findings': self._extract_critical_findings()
        }
        
        handover_path = self.checkpoint_dir / f"handover_{session.id}.json"
        with open(handover_path, 'w') as f:
            json.dump(handover, f, indent=2)
        
        logger.warning(
            f"⚠️ HANDOVER CREATED: {session.context_tokens}/{session.max_context_tokens} tokens used "
            f"({handover['usage_percent']:.1f}%) | File: {handover_path}"
        )
    
    def _generate_summary(self) -> str:
        """Generate session summary."""
        if not self.current_session:
            return ""
        
        session = self.current_session
        return (
            f"Session {session.id}: Processed {len(session.processed_docs)} documents, "
            f"used {session.context_tokens:,} tokens with {session.current_provider}"
        )
    
    def _generate_next_steps(self) -> List[str]:
        """Generate next steps."""
        return [
            "Review handover document",
            "Start new session if needed",
            "Continue with remaining documents"
        ]
    
    def _extract_critical_findings(self) -> List[str]:
        """Extract critical findings from session."""
        # Placeholder - could analyze results for important info
        return ["Session progressing normally"]
    
    def _save_checkpoint(self):
        """Save current session state."""
        if not self.current_session:
            return
        
        checkpoint_path = self.checkpoint_dir / f"checkpoint_{self.current_session.id}.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(self.current_session.to_dict(), f, indent=2)
        
        logger.info(f"💾 Checkpoint saved: {checkpoint_path}")
    
    def _load_session(self, session_id: str) -> Optional[Session]:
        """Load session from checkpoint."""
        checkpoint_path = self.checkpoint_dir / f"checkpoint_{session_id}.json"
        
        if not checkpoint_path.exists():
            logger.warning(f"No checkpoint found for session {session_id}")
            return None
        
        with open(checkpoint_path, 'r') as f:
            data = json.load(f)
        
        return Session.from_dict(data)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        if not self.current_session:
            return {'error': 'No active session'}
        
        session = self.current_session
        usage_percent = (session.context_tokens / session.max_context_tokens * 100)
        
        return {
            'session_id': session.id,
            'status': session.status,
            'documents_processed': len(session.processed_docs),
            'total_tokens': session.context_tokens,
            'max_tokens': session.max_context_tokens,
            'usage_percent': usage_percent,
            'current_provider': session.current_provider,
            'needs_handover': usage_percent >= (self.handover_threshold * 100)
        }
