#!/bin/bash
# AuctionBot Startup Script
# Railway Edition

echo "🚀 Starting AuctionBot..."
echo "=========================="

# التحقق من Python
python --version

# التحقق من المكتبات
echo "📦 Checking requirements..."
pip list | grep discord
pip list | grep asyncpg

# تشغيل البوت
echo "🤖 Starting bot..."
python bot.py
