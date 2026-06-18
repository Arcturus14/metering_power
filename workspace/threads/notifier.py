import requests
from dotenv import load_dotenv
import os

tx_count = 1 

load_dotenv()

env_token = os.environ.get("Token")
env_id = os.environ.get("ID")

def send_telegram_alert(message):
    TOKEN=env_token
    ID=env_id

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": ID, "text": message}, timeout=3)
    except:
        pass
