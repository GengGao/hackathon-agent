#!/usr/bin/env python3
"""Test script for rule extraction functionality."""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_rule_extractor():
    """Test the rule extractor with sample hackathon rules."""

    # Sample rules text from the project
    sample_rules = """Rule 1.1 – Eligibility
Participants must adhere to the hackathon eligibility criteria as defined by the organizer.

Rule 2.1 – Offline Demo Requirement
All demos must run locally without relying on cloud APIs. Allowed: Ollama, local models, local files.

Rule 3.1 – Submission Format
Provide title, short description, project URL (optional), eligibility summary, technical stack (include Ollama + gpt‑oss‑20b), weekly timeline, and offline demo plan.

Rule 4.1 – Team Size
Teams of up to 4 members are allowed unless specified otherwise.

Rule 5.1 – Use of External Resources
Open-source libraries are allowed with proper attribution. Do not use proprietary resources without license."""

    print("Testing Rule Extractor...")

    try:
        from extractors.rule_extractor import RuleExtractor

        # Initialize extractor
        extractor = RuleExtractor()
        print(f"✓ RuleExtractor initialized (LangExtract available: {extractor.langextract_available})")

        # Test extraction
        extracted_rules = extractor._safe_extract(sample_rules)
        print(f"✓ Extracted {len(extracted_rules)} rule chunks")

        # Display results
        for i, rule in enumerate(extracted_rules):
            print(f"\nRule {i+1}:")
            print(f"  Category: {rule['category']}")
            print(f"  Source: {rule['source']}")
            print(f"  Confidence: {rule['confidence']}")
            print(f"  Text: {rule['text'][:100]}...")
            if rule.get('attributes'):
                print(f"  Attributes: {rule['attributes']}")

        # Test semantic chunking
        semantic_chunks = extractor.create_semantic_chunks(extracted_rules)
        print(f"\n✓ Created {len(semantic_chunks)} semantic chunks")

        for i, chunk in enumerate(semantic_chunks):
            print(f"\nSemantic Chunk {i+1}:")
            print(f"  Category: {chunk['category']}")
            print(f"  Rule Count: {chunk['metadata'].get('rule_count', 1)}")
            print(f"  Extraction Method: {chunk['metadata'].get('extraction_source', 'unknown')}")
            print(f"  Text Length: {len(chunk['text'])} chars")

        print("\n✅ Rule extraction test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Rule extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rag_integration():
    """Test RAG integration with rule extractor."""

    print("\nTesting RAG Integration...")

    try:
        from rag import RuleRAG
        from pathlib import Path

        # Create a temporary rules file
        rules_path = Path(__file__).parent / "docs" / "rules.txt"

        # Initialize RAG with rule extractor
        rag = RuleRAG(rules_path=rules_path, lazy=False)
        print(f"✓ RuleRAG initialized with rule extractor: {rag.rule_extractor is not None}")

        # Force rebuild to test extraction
        rebuilt = rag.rebuild(force=True)
        print(f"✓ RAG rebuild completed: {rebuilt}")
        print(f"✓ Created {len(rag.chunks)} chunks with enhanced metadata")

        # Display some chunk metadata
        for i, (chunk, metadata) in enumerate(zip(rag.chunks[:3], rag.metadata[:3])):
            print(f"\nChunk {i+1}:")
            print(f"  Category: {metadata.get('category', 'unknown')}")
            print(f"  Extraction Method: {metadata.get('extraction_method', 'unknown')}")
            print(f"  Length: {metadata.get('length', 0)} chars")
            print(f"  Text: {chunk[:100]}...")

        # Test retrieval
        results = rag.retrieve("team size requirements", k=3, include_metadata=True)
        print(f"\n✓ Retrieved {len(results)} results for 'team size requirements'")

        for i, (text, score, metadata) in enumerate(results):
            print(f"\nResult {i+1} (score: {score:.3f}):")
            print(f"  Category: {metadata.get('category', 'unknown')}")
            print(f"  Text: {text[:100]}...")

        print("\n✅ RAG integration test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ RAG integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Starting LangExtract Integration Tests\n")

    # Test 1: Rule Extractor
    test1_passed = test_rule_extractor()

    # Test 2: RAG Integration
    test2_passed = test_rag_integration()

    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY:")
    print(f"Rule Extractor: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"RAG Integration: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! LangExtract integration is working.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())