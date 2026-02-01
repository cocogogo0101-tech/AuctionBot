#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Test Script - AuctionBot
للتحقق من عدم وجود أخطاء في الأكواد

المطور: دارك
"""

import sys
import os

def test_imports():
    """اختبار الاستيرادات"""
    print("🔍 Testing imports...")
    
    try:
        import discord
        print("  ✅ discord.py")
    except ImportError as e:
        print(f"  ❌ discord.py: {e}")
        return False
    
    try:
        import asyncpg
        print("  ✅ asyncpg")
    except ImportError as e:
        print(f"  ❌ asyncpg: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("  ✅ python-dotenv")
    except ImportError as e:
        print(f"  ❌ python-dotenv: {e}")
        return False
    
    try:
        import flask
        print("  ✅ flask")
    except ImportError as e:
        print(f"  ❌ flask: {e}")
        return False
    
    return True

def test_syntax():
    """اختبار الـ syntax"""
    print("\n🔍 Testing syntax...")
    
    files = ['bot.py', 'db.py', 'web.py']
    
    for file in files:
        if not os.path.exists(file):
            print(f"  ❌ {file}: File not found")
            return False
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                compile(f.read(), file, 'exec')
            print(f"  ✅ {file}")
        except SyntaxError as e:
            print(f"  ❌ {file}: Syntax error on line {e.lineno}")
            print(f"     {e.msg}")
            return False
    
    return True

def test_environment():
    """اختبار متغيرات البيئة"""
    print("\n🔍 Testing environment...")
    
    # محاكاة البيئة
    os.environ['DISCORD_TOKEN'] = 'TEST_TOKEN_123456789'
    os.environ['DATA'] = 'postgresql://test:test@localhost:5432/test'
    
    try:
        # استيراد bot للتحقق من معالجة المتغيرات
        import bot
        print("  ✅ Environment variable handling")
        
        # التحقق من التنظيف
        if bot.TOKEN == 'TEST_TOKEN_123456789':
            print("  ✅ Token cleaning works")
        else:
            print(f"  ❌ Token cleaning failed: {bot.TOKEN}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Environment test failed: {e}")
        return False

def test_database():
    """اختبار وحدة قاعدة البيانات"""
    print("\n🔍 Testing database module...")
    
    try:
        import db
        print("  ✅ db.py imports successfully")
        
        # التحقق من وجود الدوال المطلوبة
        functions = [
            'init_pool', 'create_tables', 'insert_auction',
            'end_auction', 'cancel_auction', 'insert_bid',
            'get_bids_for_auction', 'get_auction_history'
        ]
        
        for func in functions:
            if hasattr(db, func):
                print(f"  ✅ {func}() exists")
            else:
                print(f"  ❌ {func}() missing")
                return False
        
        return True
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False

def test_web():
    """اختبار الخادم"""
    print("\n🔍 Testing web server...")
    
    try:
        import web
        print("  ✅ web.py imports successfully")
        
        if hasattr(web, 'keep_alive'):
            print("  ✅ keep_alive() exists")
        else:
            print("  ❌ keep_alive() missing")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Web test failed: {e}")
        return False

def test_files():
    """اختبار وجود الملفات المطلوبة"""
    print("\n🔍 Testing required files...")
    
    required_files = [
        'bot.py',
        'db.py',
        'web.py',
        'requirements.txt',
        'Procfile',
        'runtime.txt',
        '.env.example',
        '.gitignore',
        'README.md',
        'RAILWAY.md'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}: Missing")
            all_exist = False
    
    return all_exist

def main():
    """الاختبار الرئيسي"""
    print("=" * 60)
    print("🧪 AuctionBot - Code Testing")
    print("=" * 60)
    
    tests = [
        ("Files", test_files),
        ("Syntax", test_syntax),
        ("Imports", test_imports),
        ("Database Module", test_database),
        ("Web Server", test_web),
        ("Environment", test_environment),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} test crashed: {e}")
            results.append((name, False))
    
    # النتائج النهائية
    print("\n" + "=" * 60)
    print("📊 Test Results")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name:.<40} {status}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉🎉🎉 ALL TESTS PASSED! 🎉🎉🎉")
        print("✅ الكود جاهز للـ Deploy على Railway")
        print("=" * 60)
        return 0
    else:
        print("\n❌ بعض الاختبارات فشلت!")
        print("💡 راجع الأخطاء أعلاه")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
