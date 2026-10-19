from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class BaseCRMConnector(ABC):
    def __init__(self, name: str):
        self.name = name
        self.status = "disconnected"
        self.last_synced_at: Optional[str] = None
        self.error_message: Optional[str] = None

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test authentication and API connectivity to the CRM."""
        pass

    @abstractmethod
    def fetch_deals(self) -> List[Dict[str, Any]]:
        """Fetch remote deal records from the CRM provider."""
        pass

    @abstractmethod
    def create_remote_task(self, opportunity_id: str, title: str, due_date: str) -> Dict[str, Any]:
        """Create a task in the remote CRM system."""
        pass

    @abstractmethod
    def sync_to_local_db(self, db_session) -> Dict[str, Any]:
        """Sync remote records into the local database with deduplication."""
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "last_synced_at": self.last_synced_at,
            "error_message": self.error_message,
        }
