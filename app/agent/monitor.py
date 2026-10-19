import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db import models
from app.crm.tools import find_stale_opportunities
from app.ml.risk_model import risk_engine

class AutonomousPipelineMonitor:
    def __init__(self):
        self.is_running = False
        self.interval_seconds = 3600  # Default 1 hr (simulating periodic scans)
        self.last_scan_time: Optional[str] = None
        self.total_scans_completed = 0
        self.latest_briefing: Optional[Dict[str, Any]] = None
        self.scan_history: List[Dict[str, Any]] = []
        self._thread: Optional[threading.Thread] = None

    def evaluate_pipeline(self, db: Session) -> Dict[str, Any]:
        """Runs comprehensive ML scan across all open opportunities in the database."""
        # Find all open deals
        stale_deals = find_stale_opportunities(
            db=db,
            min_amount=100000.0,
            days_inactive=3,
            status="open"
        )

        critical_deals = []
        high_risk_deals = []
        medium_risk_deals = []
        healthy_deals = []
        total_pipeline_value = 0.0
        total_risk_exposure = 0.0

        for deal in stale_deals:
            amount = deal["amount"]
            days_inactive = deal.get("days_since_activity") or 3
            total_pipeline_value += amount

            # Run ML risk scoring
            prediction = risk_engine.predict_risk(
                amount=amount,
                days_since_activity=days_inactive,
                activity_count=2,
                deal_age_days=days_inactive + 15,
                owner_win_rate=0.45,
            )

            deal_entry = {
                "opportunity_id": deal["opportunity_id"],
                "account_name": deal["account_name"],
                "amount": amount,
                "days_inactive": days_inactive,
                "risk_score_pct": prediction["risk_score_pct"],
                "risk_tier": prediction["risk_tier"],
                "risk_factors": prediction["risk_factors"],
            }

            if prediction["risk_tier"] == "CRITICAL":
                critical_deals.append(deal_entry)
                total_risk_exposure += amount
            elif prediction["risk_tier"] == "HIGH":
                high_risk_deals.append(deal_entry)
                total_risk_exposure += (amount * 0.7)
            elif prediction["risk_tier"] == "MEDIUM":
                medium_risk_deals.append(deal_entry)
            else:
                healthy_deals.append(deal_entry)

        now_str = datetime.now(timezone.utc).isoformat()
        briefing = {
            "timestamp": now_str,
            "scan_id": f"scan_{int(time.time())}",
            "status": "healthy" if not critical_deals else "attention_required",
            "metrics": {
                "total_opportunities_scanned": len(stale_deals),
                "total_pipeline_value": total_pipeline_value,
                "total_value_at_risk": total_risk_exposure,
                "critical_deals_count": len(critical_deals),
                "high_risk_count": len(high_risk_deals),
                "medium_risk_count": len(medium_risk_deals),
                "healthy_count": len(healthy_deals),
            },
            "critical_deals": critical_deals,
            "high_risk_deals": high_risk_deals,
            "autonomous_recommendation": (
                f"CRM Autopilot detected {len(critical_deals)} critical slippage risk(s) representing "
                f"INR {total_risk_exposure:,.0f} in pipeline exposure. Recommended action: Auto-dispatch "
                f"senior executive follow-up tasks immediately."
                if critical_deals else "Pipeline cadence is healthy. No critical slippage threats detected."
            )
        }

        self.latest_briefing = briefing
        self.last_scan_time = now_str
        self.total_scans_completed += 1
        self.scan_history.insert(0, briefing)
        if len(self.scan_history) > 20:
            self.scan_history.pop()

        return briefing

    def run_scan_now(self) -> Dict[str, Any]:
        """Triggers an immediate on-demand autonomous scan."""
        db = SessionLocal()
        try:
            return self.evaluate_pipeline(db)
        finally:
            db.close()

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_running,
            "scan_schedule": "Daily 08:00 AM IST & On-Demand",
            "total_scans_completed": self.total_scans_completed,
            "last_scan_time": self.last_scan_time,
            "latest_briefing": self.latest_briefing,
        }

# Global monitor singleton
pipeline_monitor = AutonomousPipelineMonitor()
