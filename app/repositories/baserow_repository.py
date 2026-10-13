import os
import requests
import logging
from typing import Optional, Dict, Any

from app.models.booking import AirtableBookingRecord
from app.repositories.booking_repository import BookingRepository

logger = logging.getLogger(__name__)


class BaserowRepository(BookingRepository):
    """
    Repository implementation for Baserow databases (such as TourCare).
    Implements BookingRepository interface for seamless multi-platform sync.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        table_id: Optional[str] = None,
        token: Optional[str] = None
    ):
        raw_url = base_url or os.getenv("BASEROW_URL", "https://booking.tourcare.ai")
        self.base_url = raw_url.rstrip("/") if raw_url else ""
        self.table_id = str(table_id or os.getenv("BASEROW_TABLE_ID", "1194"))
        self.token = token or os.getenv("BASEROW_TOKEN", "")

        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json"
        }

        self.table_url = (
            f"{self.base_url}/api/database/rows/table/{self.table_id}/"
            if self.base_url and self.table_id
            else ""
        )

    def find_by_booking_number(
        self,
        booking_nr: str
    ) -> Optional[AirtableBookingRecord]:
        if not self.table_url or not self.token:
            logger.warning("Baserow URL or Token not configured, skipping find.")
            return None

        params = {
            "user_field_names": "true",
            "search": booking_nr
        }

        response = requests.get(
            self.table_url,
            headers=self.headers,
            params=params,
            timeout=15
        )

        if not response.ok:
            raise RuntimeError(
                f"Baserow FIND failed: HTTP {response.status_code} | "
                f"Response: {response.text}"
            )

        data = response.json()
        results = data.get("results", [])

        # Match exact booking number
        target_row = None
        for row in results:
            if str(row.get("Booking Nr.", "")).strip() == booking_nr.strip():
                target_row = row
                break

        if not target_row:
            return None

        return AirtableBookingRecord(**target_row)

    def create(self, record: AirtableBookingRecord) -> bool:
        if not self.table_url or not self.token:
            logger.warning("Baserow URL or Token not configured, skipping create.")
            return False

        fields = record.model_dump(
            by_alias=True,
            exclude_none=True
        )

        params = {
            "user_field_names": "true"
        }

        response = requests.post(
            self.table_url,
            headers=self.headers,
            params=params,
            json=fields,
            timeout=15
        )

        if not response.ok:
            raise RuntimeError(
                f"Baserow CREATE failed: HTTP {response.status_code} | "
                f"Response: {response.text}"
            )

        return True

    def update(
        self,
        booking_nr: str,
        changed_fields: Dict[str, Any]
    ) -> bool:
        if not self.table_url or not self.token:
            logger.warning("Baserow URL or Token not configured, skipping update.")
            return False

        # Find row ID by search
        params = {
            "user_field_names": "true",
            "search": booking_nr
        }

        response = requests.get(
            self.table_url,
            headers=self.headers,
            params=params,
            timeout=15
        )

        if not response.ok:
            raise RuntimeError(
                f"Baserow FIND FOR UPDATE failed: "
                f"HTTP {response.status_code} | "
                f"Response: {response.text}"
            )

        data = response.json()
        results = data.get("results", [])

        target_id = None
        for row in results:
            if str(row.get("Booking Nr.", "")).strip() == booking_nr.strip():
                target_id = row.get("id")
                break

        if target_id is None:
            return False

        patch_url = f"{self.table_url}{target_id}/"
        patch_response = requests.patch(
            patch_url,
            headers=self.headers,
            params={"user_field_names": "true"},
            json=changed_fields,
            timeout=15
        )

        if not patch_response.ok:
            raise RuntimeError(
                f"Baserow UPDATE failed: "
                f"HTTP {patch_response.status_code} | "
                f"Response: {patch_response.text}"
            )

        return True
