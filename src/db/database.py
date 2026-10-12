"""SQLite Database persistence layer for CloudGuard AI."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sqlite3
import pandas as pd

from src.config import DATABASE_PATH


class DatabaseManager:
    """Manages SQLite database connections, schema initialization, and transactional queries."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DATABASE_PATH
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a connection configured with row factory and foreign key constraints."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Initializes database schema with required tables and indexes."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Datasets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS imported_datasets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    total_cost REAL NOT NULL,
                    currency TEXT NOT NULL,
                    cost_measure TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    notes TEXT
                );
            """)

            # 2. Normalized billing records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS normalized_billing_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL,
                    usage_date TEXT NOT NULL,
                    billing_period TEXT NOT NULL,
                    cloud_provider TEXT NOT NULL DEFAULT 'AWS',
                    service TEXT NOT NULL,
                    usage_type TEXT,
                    region TEXT,
                    resource_id TEXT,
                    usage_quantity REAL,
                    cost_amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    cost_measure TEXT NOT NULL,
                    raw_row_data TEXT,
                    FOREIGN KEY (dataset_id) REFERENCES imported_datasets(id) ON DELETE CASCADE
                );
            """)

            # 3. Detected anomalies
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detected_anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL,
                    detection_date TEXT NOT NULL,
                    billing_period TEXT NOT NULL,
                    service TEXT NOT NULL,
                    resource_id TEXT,
                    actual_cost REAL NOT NULL,
                    baseline_cost REAL NOT NULL,
                    absolute_increase REAL NOT NULL,
                    percentage_increase REAL,
                    detection_method TEXT NOT NULL,
                    trigger_reason TEXT NOT NULL,
                    evidence_level TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Open',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (dataset_id) REFERENCES imported_datasets(id) ON DELETE CASCADE
                );
            """)

            # 4. Forecast results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS forecast_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL,
                    forecast_period TEXT NOT NULL,
                    method TEXT NOT NULL,
                    projected_cost REAL NOT NULL,
                    lower_bound REAL,
                    upper_bound REAL,
                    confidence_note TEXT,
                    generated_at TEXT NOT NULL,
                    FOREIGN KEY (dataset_id) REFERENCES imported_datasets(id) ON DELETE CASCADE
                );
            """)

            # 5. Recommendations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    service TEXT NOT NULL,
                    supporting_evidence TEXT NOT NULL,
                    suggested_action TEXT NOT NULL,
                    estimated_savings REAL,
                    status TEXT NOT NULL DEFAULT 'Open',
                    limitations TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (dataset_id) REFERENCES imported_datasets(id) ON DELETE CASCADE
                );
            """)

            # 6. Analysis run metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id INTEGER NOT NULL,
                    run_timestamp TEXT NOT NULL,
                    parameters_json TEXT,
                    summary_json TEXT,
                    FOREIGN KEY (dataset_id) REFERENCES imported_datasets(id) ON DELETE CASCADE
                );
            """)

            # Indexes for high performance querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_billing_dataset_date ON normalized_billing_records(dataset_id, usage_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_billing_dataset_service ON normalized_billing_records(dataset_id, service);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_billing_dataset_period ON normalized_billing_records(dataset_id, billing_period);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_dataset ON detected_anomalies(dataset_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recs_dataset ON recommendations(dataset_id);")

            conn.commit()

    # -------------------------------------------------------------
    # Dataset Operations
    # -------------------------------------------------------------

    def save_dataset(
        self,
        name: str,
        filename: str,
        row_count: int,
        start_date: str,
        end_date: str,
        total_cost: float,
        currency: str,
        cost_measure: str,
        notes: Optional[str] = None
    ) -> int:
        """Saves a new imported dataset record and returns its id."""
        imported_at = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO imported_datasets (
                    name, filename, row_count, start_date, end_date, total_cost,
                    currency, cost_measure, imported_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, filename, row_count, start_date, end_date, total_cost, currency, cost_measure, imported_at, notes))
            dataset_id = cursor.lastrowid
            conn.commit()
            return dataset_id

    def list_datasets(self) -> List[Dict[str, Any]]:
        """Returns a list of all imported datasets ordered by import date desc."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM imported_datasets ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_dataset(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        """Fetches a specific dataset by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM imported_datasets WHERE id = ?", (dataset_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_dataset(self, dataset_id: int) -> bool:
        """Deletes a dataset and all associated records atomically."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM imported_datasets WHERE id = ?", (dataset_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    # -------------------------------------------------------------
    # Billing Records Operations
    # -------------------------------------------------------------

    def save_billing_records(self, dataset_id: int, records_df: pd.DataFrame) -> int:
        """Inserts normalized billing records in batches for high performance."""
        if records_df.empty:
            return 0

        insert_sql = """
            INSERT INTO normalized_billing_records (
                dataset_id, usage_date, billing_period, cloud_provider, service,
                usage_type, region, resource_id, usage_quantity, cost_amount,
                currency, cost_measure, raw_row_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        rows_to_insert = []
        for _, row in records_df.iterrows():
            raw_data = row.get("raw_row_data")
            raw_str = json.dumps(raw_data) if isinstance(raw_data, (dict, list)) else (str(raw_data) if raw_data is not None else None)
            rows_to_insert.append((
                dataset_id,
                str(row["usage_date"]),
                str(row["billing_period"]),
                str(row.get("cloud_provider", "AWS")),
                str(row["service"]),
                str(row.get("usage_type", "") or ""),
                str(row.get("region", "") or ""),
                str(row.get("resource_id", "") or "") if row.get("resource_id") else None,
                float(row["usage_quantity"]) if pd.notnull(row.get("usage_quantity")) else 0.0,
                float(row["cost_amount"]),
                str(row.get("currency", "USD")),
                str(row.get("cost_measure", "UnblendedCost")),
                raw_str
            ))

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(insert_sql, rows_to_insert)
            count = len(rows_to_insert)
            conn.commit()
            return count

    def get_billing_records_df(
        self,
        dataset_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        services: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        resource_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetches billing records as a Pandas DataFrame with optional filters."""
        query = "SELECT * FROM normalized_billing_records WHERE dataset_id = ?"
        params: List[Any] = [dataset_id]

        if start_date:
            query += " AND usage_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND usage_date <= ?"
            params.append(end_date)
        if services:
            placeholders = ",".join("?" for _ in services)
            query += f" AND service IN ({placeholders})"
            params.extend(services)
        if regions:
            placeholders = ",".join("?" for _ in regions)
            query += f" AND region IN ({placeholders})"
            params.extend(regions)
        if resource_id:
            query += " AND resource_id LIKE ?"
            params.append(f"%{resource_id}%")

        query += " ORDER BY usage_date ASC"

        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["usage_date"] = pd.to_datetime(df["usage_date"]).dt.strftime("%Y-%m-%d")
                df["cost_amount"] = pd.to_numeric(df["cost_amount"], errors="coerce").fillna(0.0)
            return df

    # -------------------------------------------------------------
    # Anomalies Operations
    # -------------------------------------------------------------

    def save_anomalies(self, dataset_id: int, anomalies: List[Dict[str, Any]]) -> int:
        """Saves detected anomalies, avoiding duplicate open anomalies for the exact same event."""
        if not anomalies:
            return 0

        insert_sql = """
            INSERT INTO detected_anomalies (
                dataset_id, detection_date, billing_period, service, resource_id,
                actual_cost, baseline_cost, absolute_increase, percentage_increase,
                detection_method, trigger_reason, evidence_level, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        created_at = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            inserted_count = 0
            for a in anomalies:
                # Check for existing duplicate anomaly for same dataset, date, service, and method
                cursor.execute("""
                    SELECT id FROM detected_anomalies
                    WHERE dataset_id = ? AND detection_date = ? AND service = ? AND detection_method = ?
                """, (dataset_id, a["detection_date"], a["service"], a["detection_method"]))
                if cursor.fetchone():
                    continue

                cursor.execute(insert_sql, (
                    dataset_id,
                    a["detection_date"],
                    a.get("billing_period", a["detection_date"][:7]),
                    a["service"],
                    a.get("resource_id"),
                    float(a["actual_cost"]),
                    float(a["baseline_cost"]),
                    float(a["absolute_increase"]),
                    float(a["percentage_increase"]) if a.get("percentage_increase") is not None else None,
                    a["detection_method"],
                    a["trigger_reason"],
                    a.get("evidence_level", "Confirmed by billing data"),
                    a.get("status", "Open"),
                    created_at
                ))
                inserted_count += 1
            conn.commit()
            return inserted_count

    def get_anomalies(self, dataset_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns detected anomalies for a dataset, optionally filtered by status."""
        query = "SELECT * FROM detected_anomalies WHERE dataset_id = ?"
        params: List[Any] = [dataset_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY absolute_increase DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def update_anomaly_status(self, anomaly_id: int, new_status: str) -> bool:
        """Updates review status of an anomaly."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE detected_anomalies SET status = ? WHERE id = ?", (new_status, anomaly_id))
            updated = cursor.rowcount > 0
            conn.commit()
            return updated

    # -------------------------------------------------------------
    # Recommendations Operations
    # -------------------------------------------------------------

    def save_recommendations(self, dataset_id: int, recommendations: List[Dict[str, Any]]) -> int:
        """Saves recommendations, updating or skipping existing identical ones."""
        if not recommendations:
            return 0

        insert_sql = """
            INSERT INTO recommendations (
                dataset_id, category, title, service, supporting_evidence,
                suggested_action, estimated_savings, status, limitations, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        created_at = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            count = 0
            for r in recommendations:
                cursor.execute("""
                    SELECT id FROM recommendations
                    WHERE dataset_id = ? AND title = ? AND service = ?
                """, (dataset_id, r["title"], r["service"]))
                if cursor.fetchone():
                    continue

                cursor.execute(insert_sql, (
                    dataset_id,
                    r["category"],
                    r["title"],
                    r["service"],
                    r["supporting_evidence"],
                    r["suggested_action"],
                    float(r["estimated_savings"]) if r.get("estimated_savings") is not None else None,
                    r.get("status", "Open"),
                    r.get("limitations", ""),
                    created_at
                ))
                count += 1
            conn.commit()
            return count

    def get_recommendations(self, dataset_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches recommendations for a dataset."""
        query = "SELECT * FROM recommendations WHERE dataset_id = ?"
        params: List[Any] = [dataset_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY estimated_savings DESC NULLS LAST"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    def update_recommendation_status(self, recommendation_id: int, new_status: str) -> bool:
        """Updates recommendation status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE recommendations SET status = ? WHERE id = ?", (new_status, recommendation_id))
            updated = cursor.rowcount > 0
            conn.commit()
            return updated

    # -------------------------------------------------------------
    # Forecast Operations
    # -------------------------------------------------------------

    def save_forecast(
        self,
        dataset_id: int,
        forecast_period: str,
        method: str,
        projected_cost: float,
        lower_bound: Optional[float] = None,
        upper_bound: Optional[float] = None,
        confidence_note: Optional[str] = None
    ) -> int:
        """Saves a forecast calculation."""
        created_at = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Replace previous forecast for the same period and method
            cursor.execute("""
                DELETE FROM forecast_results
                WHERE dataset_id = ? AND forecast_period = ? AND method = ?
            """, (dataset_id, forecast_period, method))

            cursor.execute("""
                INSERT INTO forecast_results (
                    dataset_id, forecast_period, method, projected_cost,
                    lower_bound, upper_bound, confidence_note, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (dataset_id, forecast_period, method, projected_cost, lower_bound, upper_bound, confidence_note, created_at))
            fid = cursor.lastrowid
            conn.commit()
            return fid

    def get_latest_forecast(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        """Fetches the latest forecast result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM forecast_results
                WHERE dataset_id = ?
                ORDER BY id DESC LIMIT 1
            """, (dataset_id,))
            row = cursor.fetchone()
            return dict(row) if row else None


# Module-level singleton helper
_db_instance: Optional[DatabaseManager] = None

def get_db(db_path: Optional[Path] = None) -> DatabaseManager:
    """Returns singleton database manager instance."""
    global _db_instance
    if _db_instance is None or db_path is not None:
        _db_instance = DatabaseManager(db_path)
    return _db_instance
