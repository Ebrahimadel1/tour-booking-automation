import re
import html
from datetime import datetime
from typing import Optional, Dict

from app.models.booking import NormalizedBooking
from app.models.operations import OperationType
from app.gmail.google_client import GoogleGmailClient

MONTHS_RU: Dict[str, int] = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
}

TRIP_NAME_MAPPING: Dict[str, str] = {
    "вечерний круиз по нилу в каире с ужином и шоу": "Cairo: Opal Nile Romantic Dinner Cruise & Live Entertainment"
}
DEFAULT_TRIP_NAME = "Cairo: Opal Nile Romantic Dinner Cruise & Live Entertainment"


class TripsterParser:
    """
    Parser for booking notification emails from Tripster (experience.tripster.ru).
    Handles Russian format, extracts prices in USD, customer name, date/time,
    and sets Option to transfer details or 'Excluding Transfer'.
    """

    @classmethod
    def parse(cls, text: str, html_content: Optional[str] = None) -> NormalizedBooking:
        # If plain text is empty or missing, convert HTML
        clean_text = text or ""
        if (not clean_text or "Личный кабинет" not in clean_text) and html_content:
            clean_text = GoogleGmailClient._html_to_text(html_content)

        clean_text = html.unescape(clean_text)

        # 1. Operation Type
        operation = OperationType.CREATE
        if "новый заказ" in clean_text.lower():
            operation = OperationType.CREATE
        elif "отменен" in clean_text.lower() or "отмена" in clean_text.lower():
            operation = OperationType.CANCEL
        elif "изменен" in clean_text.lower() or "изменение" in clean_text.lower():
            operation = OperationType.UPDATE

        # 2. Booking Number (e.g. №7409111)
        booking_nr = None
        nr_match = re.search(r'№\s*(\d+)', clean_text)
        if nr_match:
            booking_nr = nr_match.group(1).strip()

        # 3. Date & Time (e.g. "На 8 ноября в 18:00")
        date_obj = None
        date_match = re.search(
            r'На\s+(\d{1,2})\s+([а-яёА-ЯЁ]+)\s+в\s+(\d{1,2}:\d{2})',
            clean_text,
            re.IGNORECASE
        )
        if date_match:
            day_str, month_name, time_str = date_match.groups()
            month_num = MONTHS_RU.get(month_name.lower())
            if month_num:
                now = datetime.now()
                year = now.year
                # If booking month is in the past compared to current month, it might belong to next year
                if month_num < now.month and now.month >= 11:
                    year += 1
                hour, minute = map(int, time_str.split(':'))
                date_obj = datetime(year, month_num, int(day_str), hour, minute)

        # 4. Trip Name
        trip_name = DEFAULT_TRIP_NAME
        trip_match = re.search(r'«(.*?)»', clean_text)
        if trip_match:
            raw_title = trip_match.group(1).strip()
            trip_name = TRIP_NAME_MAPPING.get(raw_title.lower(), DEFAULT_TRIP_NAME)

        # 5. Customer Name (appears directly before 'Путешественник')
        customer_name = None
        cust_match = re.search(r'(?:^|\n)\s*([^\n\r]+)\s*\n\s*Путешественник', clean_text)
        if cust_match:
            customer_name = cust_match.group(1).strip()

        # 6. Option / Transfer (Translated to English)
        option = "Excluding Transfer (Pickup & Drop-off)"
        trans_match = re.search(r'Трансфер[^\n\r]*', clean_text, re.IGNORECASE)
        if trans_match:
            trans_line = trans_match.group(0).lower()
            if "седан" in trans_line:
                option = "Round-trip transfer: Sedan (1–3 persons)"
            elif "минивэн" in trans_line or "минивен" in trans_line:
                option = "Round-trip transfer: Minivan (4–8 persons)"
            else:
                option = "Including Transfer (Pickup & Drop-off)"

        # 7. Participants breakdown (Default to 0 if omitted)
        adt = 0
        chd = 0
        std = 0
        inf = 0
        youth = 0

        adt_match = re.search(r'(\d+)\s*·\s*Стандартный', clean_text, re.IGNORECASE)
        if adt_match:
            adt = int(adt_match.group(1))

        chd_match = re.search(r'(\d+)\s*·\s*Дети[^\n\r]*', clean_text, re.IGNORECASE)
        if chd_match:
            chd = int(chd_match.group(1))

        # 8. Prices (USD)
        # Total price: e.g. "$240" preceding "$58.6 на Трипстере"
        total_price_usd = None
        collecting_usd = None

        tot_match = re.search(r'\$(\d+(?:\.\d+)?)\s*(?:\n|\r|\s)*\$[0-9.]+\s*на Трипстере', clean_text)
        if tot_match:
            total_price_usd = float(tot_match.group(1))
        else:
            # Fallback: find first dollar amount in participants/price section
            fallback_tot = re.search(r'\$(\d+(?:\.\d+)?)', clean_text)
            if fallback_tot:
                total_price_usd = float(fallback_tot.group(1))

        col_match = re.search(r'\$(\d+(?:\.\d+)?)\s*оплата вам', clean_text)
        if col_match:
            collecting_usd = float(col_match.group(1))

        return NormalizedBooking(
            provider="Tripster",
            booking_number=booking_nr or "",
            operation=operation,
            date_trip=date_obj,
            trip_name=trip_name,
            option=option,
            add_ons=None,
            customer_name=customer_name,
            customer_email=None,
            customer_phone=None,
            guide=None,
            total_price=total_price_usd,
            total_price_usd=total_price_usd,
            collecting_usd=collecting_usd,
            currency="USD",
            adt=adt,
            std=std,
            chd=chd,
            inf=inf,
            youth=youth,
            booking_status="PENDING"
        )

