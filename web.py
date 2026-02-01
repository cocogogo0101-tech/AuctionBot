#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌐 Web Server - Keep Alive
Health check endpoint for Railway

المطور: دارك
"""

from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    """Health check endpoint"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AuctionBot Status</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .status {
                font-size: 72px;
                margin: 20px 0;
            }
            .info {
                font-size: 24px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="status">✅</div>
        <h1>AuctionBot is Running!</h1>
        <p class="info">🔥 السماء الجنوبية</p>
        <p class="info">Status: Online</p>
        <p class="info">Version: 3.0.0 Railway Edition</p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check for monitoring"""
    return {'status': 'ok', 'bot': 'online'}, 200

def run():
    """تشغيل الخادم"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

def keep_alive():
    """تشغيل الخادم في thread منفصل"""
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
