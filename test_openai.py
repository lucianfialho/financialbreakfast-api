#!/usr/bin/env python3
"""
Test OpenAI API connection and basic functionality
"""
import os
import sys

def test_openai_api():
    """Test OpenAI API key and basic functionality"""

    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        print("❌ OPENAI_API_KEY not set!")
        print("\n📋 Set it with:")
        print("   export OPENAI_API_KEY='sk-...'")
        return False

    if not api_key.startswith('sk-'):
        print("⚠️  API key format seems incorrect (should start with 'sk-')")
        return False

    print(f"✅ API Key found: {api_key[:7]}...{api_key[-4:]}")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # Test basic API call
        print("\n🧪 Testing OpenAI API connection...")

        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API working' in 2 words"}],
            max_tokens=10
        )

        print(f"✅ API Response: {response.choices[0].message.content}")

        # Test embeddings
        print("\n🧪 Testing embeddings...")
        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input="Test text for embedding"
        )

        embedding_dim = len(embedding_response.data[0].embedding)
        print(f"✅ Embeddings working: {embedding_dim} dimensions")

        print("\n🎉 OpenAI API is working correctly!")
        print("\n📋 Next steps:")
        print("1. Add to GitHub Secrets:")
        print(f"   gh secret set OPENAI_API_KEY --body '{api_key}' --repo lucianfialho/financialbreakfast-api")
        print("\n2. Add DATABASE_URL when PostgreSQL is ready:")
        print("   gh secret set DATABASE_URL --body 'postgresql://...' --repo lucianfialho/financialbreakfast-api")
        print("\n3. Trigger the workflow:")
        print("   gh workflow run '🎙️ Quarterly Earnings Call Processor' --repo lucianfialho/financialbreakfast-api")

        return True

    except ImportError:
        print("❌ OpenAI library not installed")
        print("   Run: pip install openai")
        return False

    except Exception as e:
        print(f"❌ Error testing API: {e}")

        if "Incorrect API key" in str(e):
            print("   The API key is invalid. Please check your key.")
        elif "quota" in str(e).lower():
            print("   You may have exceeded your quota or need to add billing.")
        elif "rate" in str(e).lower():
            print("   Rate limit hit. The API key is valid but being throttled.")

        return False

if __name__ == "__main__":
    print("🔑 OpenAI API Test")
    print("=" * 40)

    success = test_openai_api()

    if not success:
        sys.exit(1)