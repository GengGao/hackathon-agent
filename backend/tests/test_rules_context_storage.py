import tempfile
from pathlib import Path

from models.db import set_db_path, init_db, add_rule_context, list_active_rules
from rag import RuleRAG


def test_add_text_context_and_rebuild_rag():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'app.db'
        set_db_path(db_path)
        init_db()

        # Add custom context
        text = "Drone safety regulations require geofencing and fail-safe landing procedures."
        add_rule_context('text', text)
        active = list_active_rules()
        assert any('Drone safety' in r or 'Drone' in r for r in active)

        rag = RuleRAG()  # Will pull from DB active rules
        results = rag.retrieve('What are requirements for drone landing failsafe?', k=3)
        # Expect at least one result and that drone content surfaces
        assert results
        joined = '\n'.join(c for c,_ in results)
        assert 'drone' in joined.lower()
