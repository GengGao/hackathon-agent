"""
Benchmark script to compare sentence transformer models for RAG system.
Tests all-MiniLM-L6-v2 vs paraphrase-MiniLM-L3-v2 across multiple dimensions.
"""
import tempfile
import time
import tracemalloc
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any
import gc
from dataclasses import dataclass, asdict

from sentence_transformers import SentenceTransformer
import faiss

# Optional dependency for memory monitoring
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

# Test data - comprehensive set of hackathon-related rules and queries
TEST_RULES_CONTENT = """
Rule 1.1 – Eligibility
Participants must adhere to the hackathon eligibility criteria as defined by the organizer.

Rule 2.1 – Offline Demo Requirement
All demos must run locally without relying on cloud APIs. Allowed: Ollama, local models, local files.

Rule 3.1 – Submission Format
Provide title, short description, project URL (optional), eligibility summary, technical stack (include Ollama + gpt‑oss‑20b), weekly timeline, and offline demo plan.

Rule 4.1 – Team Size
Teams of up to 4 members are allowed unless specified otherwise.

Rule 5.1 – Use of External Resources
Open-source libraries are allowed with proper attribution. Do not use proprietary resources without license.

Rule 6.1 – Project Documentation
All projects must include comprehensive documentation explaining the architecture, setup instructions, and usage guidelines.

Rule 7.1 – Code Quality
Submitted code should follow best practices, include proper error handling, and be well-structured with appropriate comments.

Rule 8.1 – Innovation Criteria
Projects should demonstrate innovation and solve real problems. Technical implementation should be sound and well-executed.

Rule 9.1 – Presentation Requirements
Teams must prepare a clear presentation demonstrating their project functionality and explaining technical decisions.

Rule 10.1 – Judging Criteria
Projects will be evaluated based on innovation, technical difficulty, completeness, presentation quality, and adherence to rules.
""".strip()

TEST_QUERIES = [
    "What are the eligibility requirements for participants?",
    "Can I use cloud APIs in my hackathon project?",
    "What information should be included in project submission?",
    "How many people can be in a team?",
    "Are open-source libraries allowed in the project?",
    "What documentation is required for the project?",
    "What are the code quality expectations?",
    "How are projects judged and evaluated?",
    "What should be included in the project presentation?",
    "How important is innovation in the judging criteria?"
]

@dataclass
class BenchmarkResult:
    """Container for benchmark results."""
    model_name: str
    embedding_dim: int
    avg_embedding_time: float
    total_embedding_time: float
    peak_memory_mb: float
    index_build_time: float
    avg_query_time: float
    retrieval_scores: List[float]
    index_size_mb: float
    cache_size_mb: float

class EmbeddingModelBenchmark:
    """Benchmark class for comparing sentence transformer models."""

    def __init__(self, models: List[str]):
        self.models = models
        self.test_data = self._prepare_test_data()
        self.results: Dict[str, BenchmarkResult] = {}

    def _prepare_test_data(self) -> Dict[str, Any]:
        """Prepare test data by splitting rules into chunks."""
        # Split by double newlines to create chunks
        chunks = [chunk.strip() for chunk in TEST_RULES_CONTENT.split('\n\n') if chunk.strip()]
        return {
            'chunks': chunks,
            'queries': TEST_QUERIES,
            'num_chunks': len(chunks),
            'num_queries': len(TEST_QUERIES)
        }

    def _measure_embedding_performance(self, model: SentenceTransformer, chunks: List[str]) -> Dict[str, float]:
        """Measure embedding generation performance and memory usage."""
        tracemalloc.start()

        start_time = time.time()
        embeddings = model.encode(chunks, batch_size=32, show_progress_bar=False)
        embedding_time = time.time() - start_time

        # Memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Get additional memory info if psutil is available
        peak_memory_mb = peak / 1024 / 1024

        return {
            'total_time': embedding_time,
            'avg_time': embedding_time / len(chunks),
            'peak_memory_mb': peak_memory_mb,
            'embeddings': embeddings
        }

    def _build_faiss_index(self, embeddings: np.ndarray) -> Tuple[faiss.Index, float]:
        """Build FAISS index and measure time."""
        start_time = time.time()

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        embeddings = embeddings.astype('float32')

        # Create index
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)

        build_time = time.time() - start_time
        return index, build_time

    def _measure_query_performance(self, model: SentenceTransformer, index: faiss.Index, queries: List[str], k: int = 3) -> Dict[str, Any]:
        """Measure query performance and retrieval quality."""
        query_times = []
        all_scores = []

        for query in queries:
            # Encode query
            query_start = time.time()
            query_vec = model.encode([query])[0].astype('float32')
            query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-12)  # normalize

            # Search
            D, I = index.search(np.array([query_vec]), k)
            query_time = time.time() - query_start
            query_times.append(query_time)

            # Collect scores
            for score in D[0]:
                if score != -1:  # Valid result
                    all_scores.append(float(score))

        return {
            'avg_query_time': np.mean(query_times),
            'total_query_time': np.sum(query_times),
            'retrieval_scores': all_scores,
            'avg_score': np.mean(all_scores) if all_scores else 0.0
        }

    def _calculate_index_size(self, index: faiss.Index) -> float:
        """Calculate approximate size of FAISS index in MB."""
        # This is an approximation - FAISS doesn't provide direct size info
        try:
            # Try to get index size through internal structures
            if hasattr(index, 'ntotal'):
                # Rough estimation: each vector is 4 bytes (float32) * dimension
                vectors_size = index.ntotal * 4 * index.d
                overhead = 1024 * 1024  # 1MB overhead estimation
                return (vectors_size + overhead) / 1024 / 1024
        except:
            pass
        return 0.0

    def benchmark_model(self, model_name: str) -> BenchmarkResult:
        """Run comprehensive benchmark for a single model."""
        print(f"\n🔬 Benchmarking {model_name}...")

        # Load model
        model = SentenceTransformer(model_name)

        # Get embedding performance
        embedding_metrics = self._measure_embedding_performance(model, self.test_data['chunks'])

        # Build FAISS index
        index, build_time = self._build_faiss_index(embedding_metrics['embeddings'])

        # Query performance
        query_metrics = self._measure_query_performance(
            model, index, self.test_data['queries']
        )

        # Calculate sizes
        index_size = self._calculate_index_size(index)

        # Cache size (approximate - would be measured in real scenario)
        cache_size = 0.0

        result = BenchmarkResult(
            model_name=model_name,
            embedding_dim=model.get_sentence_embedding_dimension(),
            avg_embedding_time=embedding_metrics['avg_time'],
            total_embedding_time=embedding_metrics['total_time'],
            peak_memory_mb=embedding_metrics['peak_memory_mb'],
            index_build_time=build_time,
            avg_query_time=query_metrics['avg_query_time'],
            retrieval_scores=query_metrics['retrieval_scores'],
            index_size_mb=index_size,
            cache_size_mb=cache_size
        )

        # Cleanup
        del model, index, embedding_metrics, query_metrics
        gc.collect()

        return result

    def run_benchmark(self) -> Dict[str, BenchmarkResult]:
        """Run benchmark for all models."""
        print("🚀 Starting Embedding Model Benchmark")
        print(f"📊 Test data: {self.test_data['num_chunks']} chunks, {self.test_data['num_queries']} queries")

        for model_name in self.models:
            try:
                result = self.benchmark_model(model_name)
                self.results[model_name] = result
                print(f"✅ Completed {model_name}")
            except Exception as e:
                print(f"❌ Failed to benchmark {model_name}: {e}")

        return self.results

    def generate_report(self) -> str:
        """Generate a comprehensive benchmark report."""
        if not self.results:
            return "No benchmark results available."

        report_lines = []
        report_lines.append("📈 EMBEDDING MODEL BENCHMARK REPORT")
        report_lines.append("=" * 50)

        # Summary table
        report_lines.append("\n📊 PERFORMANCE SUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"{'Model':<25} {'Dim':<5} {'Embed Time (s)':<15} {'Query Time (ms)':<15} {'Memory (MB)':<12}")
        report_lines.append("-" * 80)

        for model_name, result in self.results.items():
            report_lines.append(
                f"{model_name:<25} {result.embedding_dim:<5} "
                ".4f"
                ".2f"
                ".1f"
            )

        # Detailed analysis
        report_lines.append("\n🔍 DETAILED ANALYSIS")
        report_lines.append("-" * 30)

        if len(self.results) >= 2:
            models = list(self.results.keys())
            model1, model2 = models[0], models[1]
            result1, result2 = self.results[model1], self.results[model2]

            # Performance comparison
            embed_speedup = result1.total_embedding_time / result2.total_embedding_time
            query_speedup = result1.avg_query_time / result2.avg_query_time
            memory_ratio = result1.peak_memory_mb / result2.peak_memory_mb

            report_lines.append(f"\n🏁 PERFORMANCE COMPARISON ({model1} vs {model2})")
            report_lines.append(f"   Embedding Speed: {model1} is {embed_speedup:.2f}x {'faster' if embed_speedup > 1 else 'slower'}")
            report_lines.append(f"   Query Speed: {model1} is {query_speedup:.2f}x {'faster' if query_speedup > 1 else 'slower'}")
            report_lines.append(f"   Memory Usage: {model1} uses {memory_ratio:.2f}x {'more' if memory_ratio > 1 else 'less'} memory")

            # Quality comparison
            scores1 = np.array(result1.retrieval_scores)
            scores2 = np.array(result2.retrieval_scores)

            if len(scores1) > 0 and len(scores2) > 0:
                avg_score1 = np.mean(scores1)
                avg_score2 = np.mean(scores2)
                score_diff = avg_score1 - avg_score2

                report_lines.append(f"\n🎯 RETRIEVAL QUALITY")
                report_lines.append(f"   {model1} average score: {avg_score1:.4f}")
                report_lines.append(f"   {model2} average score: {avg_score2:.4f}")
                report_lines.append(f"   Score difference: {score_diff:.4f}")
        # Recommendations
        report_lines.append("\n💡 RECOMMENDATIONS")
        report_lines.append("-" * 20)

        if self.results:
            # Find best model for different criteria
            fastest_embed = min(self.results.values(), key=lambda x: x.total_embedding_time)
            fastest_query = min(self.results.values(), key=lambda x: x.avg_query_time)
            lowest_memory = min(self.results.values(), key=lambda x: x.peak_memory_mb)

            report_lines.append(f"🔥 Fastest embedding: {fastest_embed.model_name}")
            report_lines.append(f"⚡ Fastest queries: {fastest_query.model_name}")
            report_lines.append(f"🧠 Lowest memory: {lowest_memory.model_name}")

        return "\n".join(report_lines)

def main():
    """Main benchmark function."""
    # Models to benchmark
    models = [
        "all-MiniLM-L6-v2",
        "paraphrase-MiniLM-L3-v2"
    ]

    # Run benchmark
    benchmark = EmbeddingModelBenchmark(models)
    results = benchmark.run_benchmark()

    # Generate and print report
    report = benchmark.generate_report()
    print("\n" + report)

    # Save detailed results
    print("\n💾 Saving detailed results...")
    with open("/Users/genggao/Documents/Projects/hackathon-agent/backend/tests/benchmark_results.json", "w") as f:
        import json
        json.dump({k: asdict(v) for k, v in results.items()}, f, indent=2, default=str)

    print("✅ Benchmark completed! Results saved to benchmark_results.json")

if __name__ == "__main__":
    main()
