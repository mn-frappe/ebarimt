# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Offline Queue Utilities for eBarimt

Provides offline resilience for receipt creation when eBarimt API is unavailable.
Receipts are queued locally and processed when connectivity is restored.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime


class QueueStatus(Enum):
    """Queue item status"""
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass
class QueueItem:
    """Represents a queued receipt"""
    name: str
    invoice_doctype: str
    invoice_name: str
    receipt_data: dict
    status: QueueStatus
    retry_count: int
    last_error: str | None
    created: datetime
    modified: datetime


class OfflineReceiptQueue:
    """
    Manages offline receipt queue for eBarimt.
    
    When the eBarimt API is unavailable, receipts are stored in a local
    queue and processed later by a background job.
    
    Usage:
        queue = OfflineReceiptQueue()
        
        # Add receipt to queue
        queue.enqueue(
            invoice_doctype="Sales Invoice",
            invoice_name="SINV-00001",
            receipt_data={...}
        )
        
        # Process queue (called by scheduler)
        queue.process_queue()
    """
    
    DOCTYPE = "eBarimt Pending Receipt"
    MAX_RETRIES = 5
    
    def __init__(self):
        self._ensure_doctype_exists()
    
    def _ensure_doctype_exists(self):
        """Check if the pending receipt doctype exists"""
        if not frappe.db.table_exists(self.DOCTYPE):
            frappe.logger("ebarimt").warning(
                f"Doctype {self.DOCTYPE} not found. Offline queue disabled."
            )
    
    def enqueue(
        self,
        invoice_doctype: str,
        invoice_name: str,
        receipt_data: dict,
        priority: int = 5
    ) -> str | None:
        """
        Add receipt to offline queue.
        
        Args:
            invoice_doctype: Source document type
            invoice_name: Source document name
            receipt_data: Receipt data to send to eBarimt
            priority: Queue priority (1=highest, 10=lowest)
        
        Returns:
            Queue item name or None if failed
        """
        if not frappe.db.table_exists(self.DOCTYPE):
            # Fallback to cache-based queue
            return self._enqueue_to_cache(invoice_doctype, invoice_name, receipt_data)
        
        try:
            # Check for existing pending item
            existing = frappe.db.exists(
                self.DOCTYPE,
                {
                    "invoice_doctype": invoice_doctype,
                    "invoice_name": invoice_name,
                    "status": ["in", ["Pending", "Processing"]]
                }
            )
            
            if existing:
                frappe.logger("ebarimt").info(
                    f"Receipt already queued for {invoice_doctype}/{invoice_name}"
                )
                return str(existing)
            
            doc = frappe.get_doc({
                "doctype": self.DOCTYPE,
                "invoice_doctype": invoice_doctype,
                "invoice_name": invoice_name,
                "receipt_data": json.dumps(receipt_data, default=str),
                "status": QueueStatus.PENDING.value,
                "priority": priority,
                "retry_count": 0
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            
            frappe.logger("ebarimt").info(
                f"Receipt queued: {doc.name} for {invoice_doctype}/{invoice_name}"
            )
            
            return doc.name
            
        except Exception as e:
            frappe.logger("ebarimt").error(f"Failed to queue receipt: {e}")
            return None
    
    def _enqueue_to_cache(
        self,
        invoice_doctype: str,
        invoice_name: str,
        receipt_data: dict
    ) -> str | None:
        """Fallback cache-based queue when doctype not available"""
        try:
            queue_key = "ebarimt:offline_queue"
            queue = frappe.cache().get_value(queue_key) or []
            
            item = {
                "id": f"{invoice_doctype}:{invoice_name}:{datetime.utcnow().timestamp()}",
                "invoice_doctype": invoice_doctype,
                "invoice_name": invoice_name,
                "receipt_data": receipt_data,
                "created": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
            
            queue.append(item)
            frappe.cache().set_value(queue_key, queue)
            
            return item["id"]
        except Exception as e:
            frappe.logger("ebarimt").error(f"Cache queue failed: {e}")
            return None
    
    def dequeue(self, name: str) -> dict | None:
        """
        Remove item from queue after successful processing.
        
        Args:
            name: Queue item name
        
        Returns:
            The dequeued item data or None
        """
        if not frappe.db.table_exists(self.DOCTYPE):
            return self._dequeue_from_cache(name)
        
        try:
            doc = frappe.get_doc(self.DOCTYPE, name)
            receipt_data_str = getattr(doc, "receipt_data", "{}")
            receipt_data = json.loads(receipt_data_str)
            
            doc.status = QueueStatus.COMPLETED.value  # type: ignore
            doc.processed_at = now_datetime()  # type: ignore
            doc.save(ignore_permissions=True)
            
            return receipt_data
        except Exception as e:
            frappe.logger("ebarimt").error(f"Dequeue failed for {name}: {e}")
            return None
    
    def _dequeue_from_cache(self, item_id: str) -> dict | None:
        """Remove from cache-based queue"""
        try:
            queue_key = "ebarimt:offline_queue"
            queue = frappe.cache().get_value(queue_key) or []
            
            for i, item in enumerate(queue):
                if item.get("id") == item_id:
                    removed = queue.pop(i)
                    frappe.cache().set_value(queue_key, queue)
                    return removed.get("receipt_data")
            
            return None
        except Exception:
            return None
    
    def mark_failed(self, name: str, error: str):
        """
        Mark queue item as failed.
        
        Args:
            name: Queue item name
            error: Error message
        """
        if not frappe.db.table_exists(self.DOCTYPE):
            return
        
        try:
            doc = frappe.get_doc(self.DOCTYPE, name)
            doc.status = QueueStatus.FAILED.value  # type: ignore
            doc.last_error = error[:500] if error else None  # type: ignore
            retry_count = getattr(doc, "retry_count", 0) or 0
            doc.retry_count = retry_count + 1  # type: ignore
            
            # Reset to pending if retries remaining
            if doc.retry_count < self.MAX_RETRIES:  # type: ignore
                doc.status = QueueStatus.PENDING.value  # type: ignore
            
            doc.save(ignore_permissions=True)
        except Exception as e:
            frappe.logger("ebarimt").error(f"mark_failed error: {e}")
    
    def get_pending_items(self, limit: int = 50) -> list[dict]:
        """
        Get pending items for processing.
        
        Args:
            limit: Maximum items to return
        
        Returns:
            List of pending queue items
        """
        if not frappe.db.table_exists(self.DOCTYPE):
            return self._get_pending_from_cache(limit)
        
        items = frappe.get_all(
            self.DOCTYPE,
            filters={
                "status": QueueStatus.PENDING.value,
                "retry_count": ["<", self.MAX_RETRIES]
            },
            fields=["name", "invoice_doctype", "invoice_name", "receipt_data", "retry_count"],
            order_by="priority asc, creation asc",
            limit=limit
        )
        
        for item in items:
            if item.get("receipt_data"):
                item["receipt_data"] = json.loads(item["receipt_data"])
        
        return items
    
    def _get_pending_from_cache(self, limit: int) -> list[dict]:
        """Get pending items from cache queue"""
        queue_key = "ebarimt:offline_queue"
        queue = frappe.cache().get_value(queue_key) or []
        return queue[:limit]
    
    def get_queue_stats(self) -> dict:
        """Get queue statistics"""
        if not frappe.db.table_exists(self.DOCTYPE):
            queue = frappe.cache().get_value("ebarimt:offline_queue") or []
            return {
                "pending": len(queue),
                "processing": 0,
                "failed": 0,
                "completed": 0,
                "source": "cache"
            }
        
        return {
            "pending": frappe.db.count(self.DOCTYPE, {"status": "Pending"}),
            "processing": frappe.db.count(self.DOCTYPE, {"status": "Processing"}),
            "failed": frappe.db.count(self.DOCTYPE, {"status": "Failed"}),
            "completed": frappe.db.count(self.DOCTYPE, {"status": "Completed"}),
            "source": "database"
        }
    
    def process_queue(self, batch_size: int = 10) -> dict:
        """
        Process pending items in queue.
        
        Should be called by a scheduled job.
        
        Args:
            batch_size: Number of items to process in one batch
        
        Returns:
            Processing results summary
        """
        from ebarimt.utils.resilience import ebarimt_pos_circuit_breaker
        
        # Check circuit breaker before processing
        if ebarimt_pos_circuit_breaker.state.value == "open":
            return {
                "processed": 0,
                "success": 0,
                "failed": 0,
                "skipped": True,
                "reason": "Circuit breaker is open"
            }
        
        pending = self.get_pending_items(limit=batch_size)
        results = {"processed": 0, "success": 0, "failed": 0}
        
        for item in pending:
            try:
                # Mark as processing
                if frappe.db.table_exists(self.DOCTYPE):
                    frappe.db.set_value(
                        self.DOCTYPE, 
                        item["name"], 
                        "status", 
                        QueueStatus.PROCESSING.value
                    )
                
                # Attempt to create receipt
                success = self._process_item(item)
                
                if success:
                    self.dequeue(item["name"])
                    results["success"] += 1
                else:
                    self.mark_failed(item["name"], "Processing returned False")
                    results["failed"] += 1
                
                results["processed"] += 1
                
            except Exception as e:
                self.mark_failed(item["name"], str(e))
                results["failed"] += 1
                results["processed"] += 1
                
                frappe.logger("ebarimt").error(
                    f"Queue processing error for {item.get('name')}: {e}"
                )
        
        return results
    
    def _process_item(self, item: dict) -> bool:
        """
        Process a single queue item.
        
        Override this method to implement actual receipt creation.
        """
        try:
            from ebarimt.api import EBarimtClient
            
            client = EBarimtClient()
            receipt_data = item.get("receipt_data", {})
            
            response = client.create_receipt(receipt_data)
            
            if response and response.get("success"):
                # Update source document with receipt info
                self._update_source_document(
                    item["invoice_doctype"],
                    item["invoice_name"],
                    response
                )
                return True
            
            return False
            
        except ImportError:
            frappe.logger("ebarimt").error("EBarimtClient not available")
            return False
        except Exception as e:
            frappe.logger("ebarimt").error(f"Process item error: {e}")
            raise
    
    def _update_source_document(
        self,
        doctype: str,
        docname: str,
        receipt_response: dict
    ):
        """Update source document with receipt information"""
        try:
            doc = frappe.get_doc(doctype, docname)
            
            if hasattr(doc, "ebarimt_qrcode"):
                doc.ebarimt_qrcode = receipt_response.get("qrData")  # type: ignore
            if hasattr(doc, "ebarimt_lottery"):
                doc.ebarimt_lottery = receipt_response.get("lottery")  # type: ignore
            if hasattr(doc, "ebarimt_bill_id"):
                doc.ebarimt_bill_id = receipt_response.get("billId")  # type: ignore
            
            doc.save(ignore_permissions=True)
            
        except Exception as e:
            frappe.logger("ebarimt").warning(
                f"Could not update source document {doctype}/{docname}: {e}"
            )


# Singleton instance
offline_queue = OfflineReceiptQueue()


# Scheduled job function
def process_offline_queue():
    """
    Scheduler hook to process offline queue.
    
    Add to hooks.py:
        scheduler_events = {
            "cron": {
                "*/5 * * * *": [
                    "ebarimt.utils.offline_queue.process_offline_queue"
                ]
            }
        }
    """
    try:
        result = offline_queue.process_queue()
        
        if result.get("processed", 0) > 0:
            frappe.logger("ebarimt").info(
                f"Offline queue processed: {result}"
            )
    except Exception as e:
        frappe.logger("ebarimt").error(f"Offline queue job failed: {e}")


# API endpoints for queue management

@frappe.whitelist()
def get_queue_status():
    """Get offline queue statistics"""
    frappe.only_for(["System Manager", "Administrator"])
    return offline_queue.get_queue_stats()


@frappe.whitelist()
def retry_failed_items():
    """Reset failed items to pending for retry"""
    frappe.only_for(["System Manager", "Administrator"])
    
    if not frappe.db.table_exists(OfflineReceiptQueue.DOCTYPE):
        return {"error": "Queue doctype not available"}
    
    frappe.db.sql("""
        UPDATE `tabeBarimt Pending Receipt`
        SET status = 'Pending', retry_count = 0
        WHERE status = 'Failed'
    """)
    
    frappe.db.commit()
    
    result = list(frappe.db.sql("SELECT ROW_COUNT()", as_dict=False))
    reset_count = result[0][0] if result and result[0] else 0
    return {"reset_count": reset_count}
