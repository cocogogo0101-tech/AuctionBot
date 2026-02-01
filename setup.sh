#!/bin/bash
# AuctionBot Setup Script
# المطور: دارك

echo "=================================================="
echo "🚀 AuctionBot Setup - السماء الجنوبية"
echo "=================================================="
echo ""

# التحقق من Python
echo "🔍 Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found!"
    echo "💡 Install Python 3.11+ first"
    exit 1
fi

# التحقق من pip
echo ""
echo "🔍 Checking pip..."
if command -v pip3 &> /dev/null; then
    echo "✅ pip3 found"
else
    echo "❌ pip3 not found!"
    exit 1
fi

# تثبيت المكتبات
echo ""
echo "📦 Installing requirements..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Requirements installed successfully"
else
    echo "❌ Failed to install requirements"
    exit 1
fi

# إنشاء .env إذا لم يكن موجوداً
echo ""
echo "📝 Setting up environment..."
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✅ .env created"
    echo "⚠️  Please edit .env and add your tokens"
else
    echo "✅ .env already exists"
fi

# اختبار الكود
echo ""
echo "🧪 Running tests..."
python3 test.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅✅✅ Setup Complete! ✅✅✅"
    echo "=================================================="
    echo ""
    echo "📝 Next steps:"
    echo "1. Edit .env file with your tokens"
    echo "2. Run: python3 bot.py"
    echo ""
    echo "🔥 بالتوفيق يا دارك! 🔥"
    echo "=================================================="
else
    echo ""
    echo "❌ Tests failed! Please fix errors above."
    exit 1
fi
