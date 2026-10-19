import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, List

MODEL_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(MODEL_DIR, "deal_risk_model.joblib")

class DealRiskModel:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = [
            "amount",
            "days_since_activity",
            "activity_count",
            "deal_age_days",
            "owner_win_rate",
        ]
        self._load_or_train()

    def _generate_synthetic_training_data(self, n_samples: int = 1000):
        """Generate realistic B2B sales history for training the risk classifier."""
        np.random.seed(42)
        # Amounts between 1 Lakh and 50 Lakh
        amounts = np.random.uniform(100000, 5000000, n_samples)
        days_since_activity = np.random.exponential(scale=8, size=n_samples)
        activity_count = np.random.poisson(lam=5, size=n_samples)
        deal_age_days = days_since_activity + np.random.uniform(5, 60, n_samples)
        owner_win_rate = np.random.uniform(0.2, 0.8, n_samples)

        # Risk equation: high inactivity + low activity + low rep win rate = high slippage probability
        risk_logits = (
            (days_since_activity * 0.18)
            - (activity_count * 0.25)
            + (amounts / 2500000.0 * 0.3)
            - (owner_win_rate * 2.5)
            + (deal_age_days * 0.02)
        )
        probabilities = 1 / (1 + np.exp(-risk_logits))
        labels = (probabilities > 0.5).astype(int)

        df = pd.DataFrame({
            "amount": amounts,
            "days_since_activity": days_since_activity,
            "activity_count": activity_count,
            "deal_age_days": deal_age_days,
            "owner_win_rate": owner_win_rate,
            "slipped": labels,
        })
        return df

    def _train(self):
        """Train Random Forest classifier on CRM telemetry."""
        df = self._generate_synthetic_training_data()
        X = df[self.feature_names]
        y = df["slipped"]

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        self.model.fit(X_scaled, y)

        joblib.dump({"model": self.model, "scaler": self.scaler}, MODEL_PATH)

    def _load_or_train(self):
        if os.path.exists(MODEL_PATH):
            try:
                data = joblib.load(MODEL_PATH)
                self.model = data["model"]
                self.scaler = data["scaler"]
                return
            except Exception:
                pass
        self._train()

    def predict_risk(
        self,
        amount: float,
        days_since_activity: float,
        activity_count: int = 1,
        deal_age_days: float = 20.0,
        owner_win_rate: float = 0.5,
    ) -> Dict[str, Any]:
        """Predict deal slippage probability and return explainability factors."""
        df_input = pd.DataFrame([{
            "amount": float(amount),
            "days_since_activity": float(days_since_activity),
            "activity_count": int(activity_count),
            "deal_age_days": float(deal_age_days),
            "owner_win_rate": float(owner_win_rate),
        }])
        features_scaled = self.scaler.transform(df_input)
        
        # Predict probability of slippage
        prob = float(self.model.predict_proba(features_scaled)[0][1])
        score_pct = round(prob * 100, 1)

        # Classify risk tier
        if score_pct >= 70:
            tier = "CRITICAL"
        elif score_pct >= 45:
            tier = "HIGH"
        elif score_pct >= 25:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        # Explainability factors
        factors = []
        if days_since_activity >= 7:
            factors.append(f"Inactivity penalty: {int(days_since_activity)} days with zero touchpoints")
        if amount >= 1000000:
            factors.append(f"High-stakes exposure: Deal value INR {amount:,.0f} has elevated revenue impact")
        if activity_count <= 2:
            factors.append(f"Low engagement depth: Only {activity_count} recorded interaction(s)")
        if owner_win_rate < 0.4:
            factors.append(f"Rep historical close rate is below benchmark ({int(owner_win_rate*100)}%)")

        if not factors:
            factors.append("Healthy activity tempo and active communication cadence")

        return {
            "slippage_probability": prob,
            "risk_score_pct": score_pct,
            "risk_tier": tier,
            "risk_factors": factors,
        }

# Global instance for reuse
risk_engine = DealRiskModel()
