from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.crm.connectors.salesforce import SalesforceConnector
from app.crm.connectors.hubspot import HubSpotConnector

class ConnectorManager:
    def __init__(self):
        self.connectors = {
            "salesforce": SalesforceConnector(),
            "hubspot": HubSpotConnector(),
        }

    def list_connectors(self) -> List[Dict[str, Any]]:
        results = []
        for key, conn in self.connectors.items():
            results.append({
                "id": key,
                "name": conn.name,
                "status": conn.status,
                "last_synced_at": conn.last_synced_at,
                "error_message": conn.error_message,
            })
        return results

    def test_connector(self, connector_id: str) -> Dict[str, Any]:
        if connector_id not in self.connectors:
            return {"success": False, "error": f"Unknown connector '{connector_id}'"}
        return self.connectors[connector_id].test_connection()

    def sync_all(self, db: Session) -> Dict[str, Any]:
        sync_results = []
        for key, conn in self.connectors.items():
            try:
                res = conn.sync_to_local_db(db)
                sync_results.append(res)
            except Exception as e:
                sync_results.append({
                    "connector": conn.name,
                    "error": str(e),
                    "status": "failed",
                })
        return {
            "status": "success",
            "connectors_synced": len(sync_results),
            "details": sync_results,
        }

crm_connectors = ConnectorManager()
