"""Unsupervised Isolation Forest anomaly detector for thermal behaviour."""

import os
from typing import Dict, List, Optional, Tuple, Union, Any
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "isolation_forest_pipeline.joblib"
)

# Valid numerical event-level features (excludes raw lat/lon to prevent spatial bias)
NUMERICAL_FEATURE_COLS = [
    "mean_frp",
    "max_frp",
    "mean_brightness",
    "max_brightness",
    "mean_ti4_ti5_diff",
    "observation_count",
    "unique_detection_days",
    "event_duration_hours",
    "detections_7d",
    "detections_30d",
    "detections_90d",
    "mean_confidence_score"
]


class ThermalAnomalyDetector:
    """Unsupervised Isolation Forest model detecting unusual thermal behavior.

    NOTE: This model identifies statistical outliers in thermal intensity and temporal
    persistence. It does NOT classify fire type (e.g. industrial vs vegetation).
    """

    def __init__(
        self,
        feature_cols: Optional[List[str]] = None,
        contamination: float = 0.05,
        random_state: int = 42,
        n_estimators: int = 100
    ):
        self.feature_cols = feature_cols or NUMERICAL_FEATURE_COLS
        self.contamination = contamination
        self.random_state = random_state
        self.n_estimators = n_estimators
        self.pipeline: Optional[Pipeline] = None
        self.is_fitted = False

    def _build_pipeline(self) -> Pipeline:
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("forest", IsolationForest(
                n_estimators=self.n_estimators,
                contamination=self.contamination,
                random_state=self.random_state,
                n_jobs=-1
            ))
        ])

    def fit(self, df: pd.DataFrame) -> "ThermalAnomalyDetector":
        """Train Isolation Forest on event features."""
        if df is None or len(df) == 0:
            raise ValueError("Cannot train ThermalAnomalyDetector on empty dataset.")

        missing_cols = [c for c in self.feature_cols if c not in df.columns]
        if missing_cols:
            raise KeyError(f"Missing required training features: {missing_cols}")

        X = df[self.feature_cols].copy()
        self.pipeline = self._build_pipeline()
        self.pipeline.fit(X)
        self.is_fitted = True
        return self

    def predict(
        self,
        features: Union[pd.DataFrame, Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Predict anomaly flag and normalized anomaly score.

        Returns:
            Tuple of (anomaly_flags: bool array, anomaly_scores: float array in [0, 1])
        """
        if not self.is_fitted or self.pipeline is None:
            raise RuntimeError("ThermalAnomalyDetector must be fitted or loaded before prediction.")

        if isinstance(features, dict):
            df_in = pd.DataFrame([features])
        else:
            df_in = features.copy()

        # Fill any missing feature columns with NaN so imputer can handle them safely
        for c in self.feature_cols:
            if c not in df_in.columns:
                df_in[c] = np.nan

        X = df_in[self.feature_cols]

        forest: IsolationForest = self.pipeline.named_steps["forest"]
        imputer: SimpleImputer = self.pipeline.named_steps["imputer"]
        X_imp = imputer.transform(X)

        # raw_preds: 1 for inlier, -1 for outlier/anomaly
        raw_preds = forest.predict(X_imp)
        anomaly_flags = (raw_preds == -1)

        # decision_function: lower means more abnormal
        dec_scores = forest.decision_function(X_imp)
        # Convert decision scores into a 0.0 - 1.0 anomaly scale (1.0 = most anomalous)
        # Typically decision_function is in [-0.5, 0.5]
        # Using sigmoid-like transformation centered at 0
        norm_scores = 1.0 / (1.0 + np.exp(4.0 * dec_scores))
        norm_scores = np.round(np.clip(norm_scores, 0.0, 1.0), 3)

        return anomaly_flags, norm_scores

    def save(self, model_path: str = DEFAULT_MODEL_PATH) -> str:
        """Save trained pipeline to disk."""
        if not self.is_fitted or self.pipeline is None:
            raise RuntimeError("Cannot save unfitted model.")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump({
            "pipeline": self.pipeline,
            "feature_cols": self.feature_cols,
            "contamination": self.contamination,
            "random_state": self.random_state
        }, model_path)
        return model_path

    @classmethod
    def load(cls, model_path: str = DEFAULT_MODEL_PATH) -> "ThermalAnomalyDetector":
        """Load trained pipeline from disk."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        data = joblib.load(model_path)
        detector = cls(
            feature_cols=data["feature_cols"],
            contamination=data.get("contamination", 0.05),
            random_state=data.get("random_state", 42)
        )
        detector.pipeline = data["pipeline"]
        detector.is_fitted = True
        return detector


def train_and_save_detector(
    events_df: pd.DataFrame,
    output_model_path: str = DEFAULT_MODEL_PATH,
    contamination: float = 0.05
) -> ThermalAnomalyDetector:
    """Convenience function to train and serialize the anomaly detector."""
    detector = ThermalAnomalyDetector(contamination=contamination)
    detector.fit(events_df)
    detector.save(output_model_path)
    return detector
