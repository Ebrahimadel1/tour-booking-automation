import logging
from typing import Optional, Dict, Any

from app.models.booking import AirtableBookingRecord
from app.repositories.booking_repository import BookingRepository

logger = logging.getLogger(__name__)


class DualBookingRepository(BookingRepository):
    """
    Composite repository that dispatches booking operations to both Airtable and Baserow.
    Allows enabling/disabling either repository independently via configuration toggles.
    Includes error boundaries so that temporary unavailability of one platform does not
    prevent data from reaching the other.
    """
    def __init__(
        self,
        airtable_repo: Optional[BookingRepository] = None,
        baserow_repo: Optional[BookingRepository] = None,
        enable_airtable: bool = True,
        enable_baserow: bool = True
    ):
        self.airtable_repo = airtable_repo
        self.baserow_repo = baserow_repo
        self.enable_airtable = enable_airtable and (airtable_repo is not None)
        self.enable_baserow = enable_baserow and (baserow_repo is not None)

        logger.info(
            f"DualBookingRepository initialized -> "
            f"Airtable enabled: {self.enable_airtable}, "
            f"Baserow enabled: {self.enable_baserow}"
        )

    def find_by_booking_number(self, booking_nr: str) -> Optional[AirtableBookingRecord]:
        """
        Looks up a booking in enabled repositories.
        Tries Airtable first (if enabled), falling back to Baserow (if enabled).
        """
        if self.enable_airtable and self.airtable_repo:
            try:
                rec = self.airtable_repo.find_by_booking_number(booking_nr)
                if rec:
                    return rec
            except Exception as e:
                logger.error(f"Error finding booking {booking_nr} in Airtable: {e}")

        if self.enable_baserow and self.baserow_repo:
            try:
                rec = self.baserow_repo.find_by_booking_number(booking_nr)
                if rec:
                    return rec
            except Exception as e:
                logger.error(f"Error finding booking {booking_nr} in Baserow: {e}")

        return None

    def create(self, record: AirtableBookingRecord) -> bool:
        """
        Creates the booking record in all enabled repositories.
        Returns True if at least one enabled repository succeeded.
        """
        if not self.enable_airtable and not self.enable_baserow:
            logger.warning("No repositories are enabled for creation.")
            return False

        airtable_success = False
        baserow_success = False

        if self.enable_airtable and self.airtable_repo:
            try:
                airtable_success = self.airtable_repo.create(record)
                logger.info(f"Booking {record.booking_nr} created in Airtable.")
            except Exception as e:
                logger.error(f"Failed to create booking {record.booking_nr} in Airtable: {e}")

        if self.enable_baserow and self.baserow_repo:
            try:
                baserow_success = self.baserow_repo.create(record)
                logger.info(f"Booking {record.booking_nr} created in Baserow.")
            except Exception as e:
                logger.error(f"Failed to create booking {record.booking_nr} in Baserow: {e}")

        # If only Airtable is enabled, result depends on Airtable
        if self.enable_airtable and not self.enable_baserow:
            return airtable_success

        # If only Baserow is enabled, result depends on Baserow
        if self.enable_baserow and not self.enable_airtable:
            return baserow_success

        # If both are enabled, consider successful if at least one succeeded
        return airtable_success or baserow_success

    def update(self, booking_nr: str, changed_fields: Dict[str, Any]) -> bool:
        """
        Updates the booking record in all enabled repositories.
        Returns True if at least one enabled repository succeeded.
        """
        if not self.enable_airtable and not self.enable_baserow:
            logger.warning("No repositories are enabled for update.")
            return False

        airtable_success = False
        baserow_success = False

        if self.enable_airtable and self.airtable_repo:
            try:
                airtable_success = self.airtable_repo.update(booking_nr, changed_fields)
                logger.info(f"Booking {booking_nr} updated in Airtable: {changed_fields}")
            except Exception as e:
                logger.error(f"Failed to update booking {booking_nr} in Airtable: {e}")

        if self.enable_baserow and self.baserow_repo:
            try:
                baserow_success = self.baserow_repo.update(booking_nr, changed_fields)
                logger.info(f"Booking {booking_nr} updated in Baserow: {changed_fields}")
            except Exception as e:
                logger.error(f"Failed to update booking {booking_nr} in Baserow: {e}")

        if self.enable_airtable and not self.enable_baserow:
            return airtable_success

        if self.enable_baserow and not self.enable_airtable:
            return baserow_success

        return airtable_success or baserow_success
