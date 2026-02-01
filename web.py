# web.py
from flask import Flask
import threading
import os

app = Flask("keep_alive")

@app.route("/")
def home():
    return "Bot is alive 🚀"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
