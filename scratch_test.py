import re

def extract_field(text, current_label, next_labels):
    start_match = re.search(r'(?:^|\n)\s*' + re.escape(current_label) + r'[\s:]*', text, re.IGNORECASE)
    if not start_match:
        start_match = re.search(re.escape(current_label) + r'[\s:]*', text, re.IGNORECASE)
        if not start_match: return None
    start_idx = start_match.end()
    end_idx = len(text)
    for label in next_labels:
        match = re.search(r'(?:^|\n)\s*' + re.escape(label) + r'[\s:]*', text[start_idx:], re.IGNORECASE)
        if match:
            found_pos = start_idx + match.start()
            if found_pos < end_idx: end_idx = found_pos
    extracted = text[start_idx:end_idx].strip()
    return extracted if extracted else None

text = """
Reference number
GYG83W783H7V

Date
October 15, 2026 6:00 PM

Number of participants
2 x Adults (Age 10 - 99)

Main customer
Shangar Sentharajah
"""
all_labels = ["Reference number", "Date", "Number of participants", "Main customer"]
next_labels = [l for l in all_labels if l != "Number of participants"]
print("Result:", repr(extract_field(text, "Number of participants", next_labels)))
