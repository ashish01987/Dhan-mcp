"""
Alert Manager Module
Manages price alerts, volume alerts, P&L alerts, and other trading notifications.
Alerts are stored in-memory (session-based, cleared at end of day).
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
import uuid


class AlertManager:
    """In-memory alert management system"""

    def __init__(self):
        self.alerts: Dict[str, Dict] = {}
        self.triggered_alerts: List[str] = []

    def create_price_alert(self, security_id: str, price: float, direction: str, description: str = "") -> Dict:
        """
        Create a price alert

        Args:
            security_id: Security to monitor
            price: Alert trigger price
            direction: "above", "below", "equals"
            description: Optional description
        """
        if direction not in ["above", "below", "equals"]:
            return {"error": "Invalid direction. Use: above, below, equals"}

        alert_id = str(uuid.uuid4())[:8]

        self.alerts[alert_id] = {
            "id": alert_id,
            "type": "price",
            "security_id": security_id,
            "trigger_price": price,
            "direction": direction,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "triggered_at": None
        }

        return {
            "alert_id": alert_id,
            "status": "created",
            "type": "price",
            "security_id": security_id,
            "trigger_price": price,
            "direction": direction
        }

    def create_volume_alert(self, security_id: str, volume_threshold: int) -> Dict:
        """Create a volume spike alert"""
        if volume_threshold <= 0:
            return {"error": "Volume threshold must be positive"}

        alert_id = str(uuid.uuid4())[:8]

        self.alerts[alert_id] = {
            "id": alert_id,
            "type": "volume",
            "security_id": security_id,
            "volume_threshold": volume_threshold,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "triggered_at": None
        }

        return {
            "alert_id": alert_id,
            "status": "created",
            "type": "volume",
            "security_id": security_id,
            "volume_threshold": volume_threshold
        }

    def create_position_alert(self, security_id: str, pnl_threshold: float) -> Dict:
        """
        Create a P&L alert (triggered when position P&L exceeds threshold)

        Args:
            security_id: Position identifier
            pnl_threshold: P&L limit (positive for profit target, negative for loss limit)
        """
        alert_id = str(uuid.uuid4())[:8]

        self.alerts[alert_id] = {
            "id": alert_id,
            "type": "pnl",
            "security_id": security_id,
            "pnl_threshold": pnl_threshold,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "triggered_at": None
        }

        return {
            "alert_id": alert_id,
            "status": "created",
            "type": "pnl",
            "security_id": security_id,
            "pnl_threshold": pnl_threshold
        }

    def create_order_alert(self, order_id: str, status_to_watch: str) -> Dict:
        """Create an order status alert"""
        alert_id = str(uuid.uuid4())[:8]

        self.alerts[alert_id] = {
            "id": alert_id,
            "type": "order",
            "order_id": order_id,
            "status_to_watch": status_to_watch,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "triggered_at": None
        }

        return {
            "alert_id": alert_id,
            "status": "created",
            "type": "order",
            "order_id": order_id,
            "status_to_watch": status_to_watch
        }

    def check_and_trigger_alerts(self, current_data: Dict) -> Dict:
        """
        Check all active alerts against current market data and trigger if conditions met

        Args:
            current_data: {
                security_id: {price, volume, ...},
                order_id: {status, ...},
                ...
            }
        """
        triggered = []

        for alert_id, alert in list(self.alerts.items()):
            if alert["status"] != "active":
                continue

            alert_type = alert.get("type")
            triggered_flag = False

            # Price alerts
            if alert_type == "price":
                security_id = alert.get("security_id")
                current_price = current_data.get(security_id, {}).get("price")

                if current_price is not None:
                    trigger_price = alert.get("trigger_price")
                    direction = alert.get("direction")

                    if direction == "above" and current_price > trigger_price:
                        triggered_flag = True
                    elif direction == "below" and current_price < trigger_price:
                        triggered_flag = True
                    elif direction == "equals" and abs(current_price - trigger_price) < 0.01:
                        triggered_flag = True

            # Volume alerts
            elif alert_type == "volume":
                security_id = alert.get("security_id")
                current_volume = current_data.get(security_id, {}).get("volume")

                if current_volume is not None:
                    threshold = alert.get("volume_threshold")
                    if current_volume > threshold:
                        triggered_flag = True

            # P&L alerts
            elif alert_type == "pnl":
                security_id = alert.get("security_id")
                current_pnl = current_data.get(security_id, {}).get("pnl")

                if current_pnl is not None:
                    threshold = alert.get("pnl_threshold")
                    if threshold > 0 and current_pnl > threshold:  # Profit target hit
                        triggered_flag = True
                    elif threshold < 0 and current_pnl < threshold:  # Loss limit hit
                        triggered_flag = True

            # Order alerts
            elif alert_type == "order":
                order_id = alert.get("order_id")
                order_status = current_data.get(order_id, {}).get("status")

                if order_status is not None:
                    status_to_watch = alert.get("status_to_watch")
                    if order_status.upper() == status_to_watch.upper():
                        triggered_flag = True

            # Mark as triggered
            if triggered_flag:
                alert["status"] = "triggered"
                alert["triggered_at"] = datetime.now().isoformat()
                self.triggered_alerts.append(alert_id)
                triggered.append(alert)

        return {
            "triggered_count": len(triggered),
            "triggered_alerts": triggered,
            "timestamp": datetime.now().isoformat()
        }

    def get_active_alerts(self) -> Dict:
        """Get all active (non-triggered) alerts"""
        active = [a for a in self.alerts.values() if a["status"] == "active"]

        return {
            "active_count": len(active),
            "alerts": active,
            "timestamp": datetime.now().isoformat()
        }

    def get_triggered_alerts(self) -> Dict:
        """Get all triggered alerts"""
        triggered = [self.alerts[aid] for aid in self.triggered_alerts if aid in self.alerts]

        return {
            "triggered_count": len(triggered),
            "alerts": triggered,
            "timestamp": datetime.now().isoformat()
        }

    def clear_alert(self, alert_id: str) -> Dict:
        """Remove an alert"""
        if alert_id in self.alerts:
            alert = self.alerts.pop(alert_id)
            if alert_id in self.triggered_alerts:
                self.triggered_alerts.remove(alert_id)
            return {"status": "deleted", "alert_id": alert_id}
        return {"error": f"Alert {alert_id} not found"}

    def clear_all_alerts(self) -> Dict:
        """Clear all alerts (end of day)"""
        count = len(self.alerts)
        self.alerts.clear()
        self.triggered_alerts.clear()
        return {"status": "all_cleared", "alerts_cleared": count}

    def get_alert_summary(self) -> Dict:
        """Get summary of all alerts"""
        active = [a for a in self.alerts.values() if a["status"] == "active"]
        triggered = [a for a in self.alerts.values() if a["status"] == "triggered"]

        return {
            "total_alerts": len(self.alerts),
            "active_count": len(active),
            "triggered_count": len(triggered),
            "by_type": {
                "price": len([a for a in self.alerts.values() if a["type"] == "price"]),
                "volume": len([a for a in self.alerts.values() if a["type"] == "volume"]),
                "pnl": len([a for a in self.alerts.values() if a["type"] == "pnl"]),
                "order": len([a for a in self.alerts.values() if a["type"] == "order"])
            }
        }


# Global alert manager instance
_alert_manager = AlertManager()


def create_price_alert(security_id: str, price: float, direction: str, description: str = "") -> Dict:
    """Wrapper function"""
    return _alert_manager.create_price_alert(security_id, price, direction, description)


def create_volume_alert(security_id: str, volume_threshold: int) -> Dict:
    """Wrapper function"""
    return _alert_manager.create_volume_alert(security_id, volume_threshold)


def create_position_alert(security_id: str, pnl_threshold: float) -> Dict:
    """Wrapper function"""
    return _alert_manager.create_position_alert(security_id, pnl_threshold)


def create_order_alert(order_id: str, status_to_watch: str) -> Dict:
    """Wrapper function"""
    return _alert_manager.create_order_alert(order_id, status_to_watch)


def check_and_trigger_alerts(current_data: Dict) -> Dict:
    """Wrapper function"""
    return _alert_manager.check_and_trigger_alerts(current_data)


def get_active_alerts() -> Dict:
    """Wrapper function"""
    return _alert_manager.get_active_alerts()


def get_triggered_alerts() -> Dict:
    """Wrapper function"""
    return _alert_manager.get_triggered_alerts()


def clear_alert(alert_id: str) -> Dict:
    """Wrapper function"""
    return _alert_manager.clear_alert(alert_id)


def clear_all_alerts() -> Dict:
    """Wrapper function"""
    return _alert_manager.clear_all_alerts()


def get_alert_summary() -> Dict:
    """Wrapper function"""
    return _alert_manager.get_alert_summary()
