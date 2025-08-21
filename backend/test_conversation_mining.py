#!/usr/bin/env python3
"""Test script for conversation mining and progress extraction."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors.conversation_extractor import ConversationExtractor
from extractors.progress_extractor import ProgressExtractor
from tools.insight_tools import (
    get_conversation_insights,
    get_project_progress,
    get_focused_summary,
    get_actionable_recommendations
)

def test_conversation_extractor():
    """Test the conversation extractor with sample data."""
    print("🧠 Testing Conversation Extractor...")

    extractor = ConversationExtractor()

    # Sample conversation
    sample_text = """
    User: I think we should use React for the frontend and FastAPI for the backend.
    Assistant: That's a great choice! React will give you a modern UI and FastAPI is perfect for rapid API development.
    User: Agreed, let's go with that stack. We also need to make sure everything runs offline for the demo.
    Assistant: Good point! We should use local models like Ollama and store all data locally.
    User: Right, and we need to have a backup plan if the internet goes down during the demo.
    """

    try:
        insights = extractor.extract(sample_text)
        print(f"✅ Extracted {len(insights)} insights")

        for insight in insights[:3]:  # Show first 3
            print(f"  - {insight['category']}: {insight['text'][:60]}...")

        # Test message-based extraction
        sample_messages = [
            {"role": "user", "content": "I think we should use React for the frontend and FastAPI for the backend."},
            {"role": "assistant", "content": "That's a great choice! React will give you a modern UI and FastAPI is perfect for rapid API development."},
            {"role": "user", "content": "Agreed, let's go with that stack."}
        ]

        result = extractor.extract_from_messages(sample_messages)
        print(f"✅ Message extraction: {result['summary']['total_insights']} insights from {result['summary']['message_count']} messages")

        return True

    except Exception as e:
        print(f"❌ Conversation extractor test failed: {e}")
        return False

def test_progress_extractor():
    """Test the progress extractor with sample data."""
    print("\n📊 Testing Progress Extractor...")

    extractor = ProgressExtractor()

    # Sample progress text
    sample_text = """
    User: I finished implementing the user authentication system. All tests are passing and it's ready for integration.
    Assistant: Great work! That's a major milestone completed.
    User: Next, I'll work on the dashboard UI. But we're blocked on the database integration because the schema migration is failing.
    Assistant: Let's troubleshoot that migration issue. What error are you seeing?
    User: The foreign key constraints are causing issues. We might need to redesign the data model.
    """

    try:
        progress_items = extractor.extract(sample_text)
        print(f"✅ Extracted {len(progress_items)} progress items")

        for item in progress_items[:3]:  # Show first 3
            print(f"  - {item['category']}: {item['text'][:60]}...")

        # Test message-based extraction
        sample_messages = [
            {"role": "user", "content": "I finished implementing the user authentication system. All tests are passing."},
            {"role": "user", "content": "Next, I'll work on the dashboard UI."},
            {"role": "user", "content": "We're blocked on the database integration because the schema migration is failing."}
        ]

        result = extractor.extract_from_messages(sample_messages)
        print(f"✅ Message extraction: {result['summary']['total_progress_items']} items, project health: {result['summary']['project_health']}")

        return True

    except Exception as e:
        print(f"❌ Progress extractor test failed: {e}")
        return False

def test_tool_functions():
    """Test the LLM tool functions."""
    print("\n🔧 Testing LLM Tool Functions...")

    # Note: These will fail without a real session_id, but we can test the structure
    test_session_id = "test_session_123"

    try:
        # Test conversation insights (will fail gracefully)
        result = get_conversation_insights(test_session_id, 10)
        print("✅ get_conversation_insights function callable")

        # Test project progress (will fail gracefully)
        result = get_project_progress(test_session_id, 10)
        print("✅ get_project_progress function callable")

        # Test focused summary (will fail gracefully)
        result = get_focused_summary(test_session_id, "decisions")
        print("✅ get_focused_summary function callable")

        # Test actionable recommendations (will fail gracefully)
        result = get_actionable_recommendations(test_session_id)
        print("✅ get_actionable_recommendations function callable")

        return True

    except Exception as e:
        print(f"❌ Tool function test failed: {e}")
        return False

def test_langextract_availability():
    """Test if LangExtract is available and working."""
    print("\n🚀 Testing LangExtract Availability...")

    try:
        import langextract as lx
        print("✅ LangExtract imported successfully")

        # Test if our extractors can be created (this is what actually matters)
        from extractors.conversation_extractor import ConversationExtractor
        from extractors.progress_extractor import ProgressExtractor

        conv_extractor = ConversationExtractor()
        prog_extractor = ProgressExtractor()

        print("✅ LangExtract extractors initialized successfully")

        # The actual test is whether the extractors work, which we test separately
        # If we got here, LangExtract is available and configured properly
        return True

    except ImportError:
        print("⚠️  LangExtract not available - will use fallback methods")
        return False
    except Exception as e:
        print(f"⚠️  LangExtract available but configuration failed: {e}")
        print("   Extractors will fall back to heuristic methods")
        return False

def main():
    """Run all tests."""
    print("🧪 Starting Conversation Mining and Progress Extraction Tests\n")

    results = []

    # Test LangExtract availability first
    langextract_available = test_langextract_availability()

    # Test extractors
    results.append(("Conversation Extractor", test_conversation_extractor()))
    results.append(("Progress Extractor", test_progress_extractor()))
    results.append(("Tool Functions", test_tool_functions()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY:")

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    if langextract_available:
        print("🚀 LangExtract: ✅ AVAILABLE")
    else:
        print("🚀 LangExtract: ⚠️  NOT AVAILABLE (fallback methods will be used)")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed! Conversation mining and progress extraction are ready.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)