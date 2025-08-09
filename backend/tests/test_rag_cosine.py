import tempfile
from pathlib import Path
from rag import RuleRAG

RULES_CONTENT = """
Python is a programming language that emphasizes readability.

JavaScript runs primarily in the browser and enables interactive web pages.

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python.

React is a JavaScript library for building user interfaces.
""".strip()

def test_cosine_retrieval_order_and_score_range():
    with tempfile.TemporaryDirectory() as tmpdir:
        rules_path = Path(tmpdir) / "rules.txt"
        rules_path.write_text(RULES_CONTENT, encoding="utf-8")
        rag = RuleRAG(rules_path)

        # Query related to web framework should rank FastAPI or JavaScript/React high
        results = rag.retrieve("Which Python web framework is fast?", k=3)
        assert results, "Expected non-empty retrieval results"
        # Ensure scores are within plausible cosine range [-1, 1]
        for _, score in results:
            assert -1.01 <= score <= 1.01

        # The top chunk should mention FastAPI given the query focus
        top_chunk, top_score = results[0]
        assert "FastAPI" in top_chunk

        # Query about user interfaces should prefer React chunk
        ui_results = rag.retrieve("frontend user interface library", k=2)
        assert ui_results
        assert "React" in ui_results[0][0]

        # Cosine similarity should be higher (better) for top result than second
        if len(ui_results) > 1:
            assert ui_results[0][1] >= ui_results[1][1]
