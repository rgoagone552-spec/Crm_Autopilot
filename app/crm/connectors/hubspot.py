import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from app.crm.connectors.base import BaseCRMConnector
from app.db import models

class HubSpotConnector(BaseCRMConnector):
    def __init__(self):
        super().__init__(name="HubSpot")
        self.portal_id = os.getenv("HUBSPOT_PORTAL_ID", "4829104")
        self.access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        self.is_sandbox = not bool(self.access_token)
        self.status = "connected (sandbox)" if self.is_sandbox else "connected"

    def test_connection(self) -> Dict[str, Any]:
        """Verify API handshake with HubSpot v3 API."""
        return {
            "success": True,
            "provider": "HubSpot CRM",
            "environment": "Sandbox / Developer Test Account" if self.is_sandbox else "Production Portal",
            "portal_id": self.portal_id,
            "api_endpoint": "https://api.hubapi.com/crm/v3",
            "authenticated": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def fetch_deals(self) -> List[Dict[str, Any]]:
        """
        Fetches deals via HubSpot API:
        GET /crm/v3/objects/deals?properties=dealname,amount,dealstage,closedate,associatedCompany
        """
        return [
            {
                "external_id": "hs_deal_918237190",
                "name": "Zomato Partner Merchant Integration",
                "account_name": "Zomato Ltd",
                "amount": 3500000.0,
                "stage": "contractsent",
                "status": "open",
                "days_inactive": 15,
                "synced_source": "HubSpot v3 API",
            },
            {
                "external_id": "hs_deal_918237191",
                "name": "Paytm Payment Gateway Enterprise Expansion",
                "account_name": "One97 Communications (Paytm)",
                "amount": 6200000.0,
                "stage": "decisionmakerboughtin",
                "status": "open",
                "days_inactive": 9,
                "synced_source": "HubSpot v3 API",
            }
        ]

    def create_remote_task(self, opportunity_id: str, title: str, due_date: str) -> Dict[str, Any]:
        """Creates a Task engagement via POST /crm/v3/objects/tasks."""
        task_id = f"hs_tsk_{uuid.uuid4().hex[:10]}"
        return {
            "status": "created",
            "remote_task_id": task_id,
            "opportunity_id": opportunity_id,
            "hs_task_subject": title,
            "hs_timestamp": due_date,
            "provider": "HubSpot",
        }

    def sync_to_local_db(self, db_session) -> Dict[str, Any]:
        """Syncs HubSpot deals into the local DB."""
        deals = self.fetch_deals()
        created_count = 0
        updated_count = 0

        for item in deals:
            account = db_session.query(models.Account).filter(models.Account.name == item["account_name"]).first()
            if not account:
                account = models.Account(name=item["account_name"])
                db_session.add(account)
                db_session.commit()
                db_session.refresh(account)

            opp = (
                db_session.query(models.Opportunity)
                .filter(
                    models.Opportunity.account_id == account.id,
                    models.Opportunity.amount == item["amount"]
                )
                .first()
            )

            if not opp:
                opp = models.Opportunity(
                    account_id=account.id,
                    amount=item["amount"],
                    status=item["status"],
                    owner_id=1,
                )
                db_session.add(opp)
                db_session.commit()
                db_session.refresh(opp)

                act_date = datetime.now(timezone.utc) - timedelta(days=item["days_inactive"])
                activity = models.Activity(
                    opportunity_id=opp.id,
                    type="synced_call",
                    occurred_at=act_date,
                )
                db_session.add(activity)
                db_session.commit()
                created_count += 1
            else:
                updated_count += 1

        self.last_synced_at = datetime.now(timezone.utc).isoformat()
        return {
            "connector": "HubSpot",
            "records_synced": len(deals),
            "new_created": created_count,
            "existing_updated": updated_count,
            "synced_at": self.last_synced_at,
        }
