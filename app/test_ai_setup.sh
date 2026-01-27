#!/bin/bash

echo "==================================="
echo "🔍 AI PARSING SETUP VERIFICATION"
echo "==================================="
echo ""

# Check .env file exists
echo "1️⃣ Checking .env file..."
if [ -f ".env" ]; then
    echo "   ✅ .env file exists"
else
    echo "   ❌ .env file NOT FOUND!"
    exit 1
fi

# Check API key is set (without showing it)
echo ""
echo "2️⃣ Checking environment variables..."
source .env
if [ -n "$OPENAI_API_KEY" ]; then
    echo "   ✅ OPENAI_API_KEY is set (${OPENAI_API_KEY:0:10}...)"
else
    echo "   ❌ OPENAI_API_KEY is NOT SET!"
fi

if [ "$USE_AI_PARSING" = "true" ]; then
    echo "   ✅ USE_AI_PARSING = true"
else
    echo "   ⚠️  USE_AI_PARSING = $USE_AI_PARSING (should be 'true')"
fi

# Check python packages
echo ""
echo "3️⃣ Checking Python packages..."
pip3 list | grep -E "(dotenv|requests)" || echo "   ⚠️  Missing packages!"

# Test AI parsing with a simple comment
echo ""
echo "4️⃣ Testing parser (this will use OpenAI)..."
echo ""
python3 reddit_parser.py "https://www.reddit.com/r/PokemonRaffles/comments/1ql9whl/nm_pre_ripapalooza_pull_the_sunby_36_loose_packs/" 10 2>&1 | head -20

echo ""
echo "==================================="
echo "Look for '🤖 Using OpenAI AI parsing' messages above"
echo "==================================="
