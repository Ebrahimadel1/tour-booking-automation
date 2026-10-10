from app.parsers.getyourguide import GetYourGuideParser

with open("debug_original_email.txt", "r", encoding="utf-8") as f:
    text = f.read()

try:
    print(GetYourGuideParser.parse(text))
except Exception as e:
    print(f"Error: {e}")
