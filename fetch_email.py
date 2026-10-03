from app.gmail.google_client import GoogleGmailClient

client = GoogleGmailClient()
res = client.service.users().messages().get(userId='me', id='1a0f2feb67c3d603', format='full').execute()
msg = client._convert_message(res)
with open('debug_email.txt', 'w', encoding='utf-8') as f:
    f.write(msg.plain_text)
