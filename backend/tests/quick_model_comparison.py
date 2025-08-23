#!/usr/bin/env python3
"""
Quick comparison script for sentence transformer models.
Usage: python quick_model_comparison.py [model1] [model2]
"""
import sys
import time
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

# Sample data for quick comparison
SAMPLE_TEXTS = [
    "Python is a programming language that emphasizes readability.",
    "JavaScript runs primarily in the browser and enables interactive web pages.",
    "FastAPI is a modern web framework for building APIs with Python.",
    "React is a JavaScript library for building user interfaces.",
    "Machine learning models require significant computational resources."
]

SAMPLE_QUERIES = [
    "What is a good programming language for beginners?",
    "Which framework should I use for web development?",
    "How do I build user interfaces?"
]

def benchmark_model(model_name: str, texts: list, queries: list):
    """Quick benchmark of a single model."""
    print(f"\n🔬 Testing {model_name}...")

    # Load model
    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()

    # Measure embedding time
    start_time = time.time()
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    embed_time = time.time() - start_time

    # Build FAISS index
    start_time = time.time()
    faiss.normalize_L2(embeddings)
    embeddings = embeddings.astype('float32')
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    index_time = time.time() - start_time

    # Query performance
    query_times = []
    scores = []
    for query in queries:
        start_time = time.time()
        query_vec = model.encode([query])[0].astype('float32')
        query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-12)
        D, I = index.search(np.array([query_vec]), 2)
        query_time = time.time() - start_time
        query_times.append(query_time)
        scores.extend(D[0])

    return {
        'model': model_name,
        'dimension': dim,
        'embed_time': embed_time,
        'index_time': index_time,
        'avg_query_time': np.mean(query_times),
        'avg_score': np.mean(scores)
    }

def main():
    # Default models if none provided
    models = sys.argv[1:] if len(sys.argv) > 1 else [
        "all-MiniLM-L6-v2",
        "paraphrase-MiniLM-L3-v2"
    ]

    print("🚀 Quick Model Comparison")
    print(f"📊 Comparing: {', '.join(models)}")

    results = []
    for model in models:
        try:
            result = benchmark_model(model, SAMPLE_TEXTS, SAMPLE_QUERIES)
            results.append(result)
        except Exception as e:
            print(f"❌ Error with {model}: {e}")

    if len(results) < 2:
        print("❌ Need at least 2 models for comparison")
        return

    # Print comparison
    print("\n📈 RESULTS")
    print("-" * 70)
    print(f"{'Model':<30} {'Dim':<5} {'Embed(s)':<10} {'Query(ms)':<12} {'Avg Score':<10}")
    print("-" * 70)

    for r in results:
        print(f"{r['model']:<30} {r['dimension']:<5} {r['embed_time']:<10.3f} {r['avg_query_time']*1000:<12.1f} {r['avg_score']:<10.3f}")

    # Performance comparison
    if len(results) == 2:
        r1, r2 = results[0], results[1]
        embed_ratio = r1['embed_time'] / r2['embed_time']
        query_ratio = r1['avg_query_time'] / r2['avg_query_time']
        score_diff = r1['avg_score'] - r2['avg_score']

        print(f"\n🏁 COMPARISON")
        print(f"   Speed: {r1['model']} is {embed_ratio:.1f}x {'faster' if embed_ratio > 1 else 'slower'} for embeddings")
        print(f"   Query: {r1['model']} is {query_ratio:.1f}x {'faster' if query_ratio > 1 else 'slower'} for queries")
        print(f"   Quality: {r1['model']} {'better' if score_diff > 0 else 'worse'} by {abs(score_diff):.3f}")

if __name__ == "__main__":
    main()
