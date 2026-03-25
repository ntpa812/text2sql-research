import sys
import unittest
from copy import deepcopy

import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from domain_router.registry_loader import load_domain_registry
from domain_router.selector import route_domains
from pipeline import pipeline_runner as pr
from pipeline.query_cache import clear_query_cache


class DomainRoutingTests(unittest.TestCase):
    def setUp(self):
        clear_query_cache()
        pr._registry = None
        pr._domain_resources = {}

        self._orig_extract_entities_local = pr.extract_entities_local
        self._orig_normalize_entities = pr.normalize_entities
        self._orig_generate_sql = pr.generate_sql
        self._orig_explain_query = pr.explain_query
        self._orig_execute_query = pr.execute_query
        self._orig_generate_explain = pr.generate_explain

        pr.extract_entities_local = lambda question: {}
        pr.normalize_entities = lambda entities: entities
        pr.generate_sql = lambda prompt: "SELECT 1;"
        pr.explain_query = lambda sql, db_config=None: (True, "")
        pr.execute_query = lambda sql, params=None, row_limit=100, timeout=30, db_config=None: (
            True,
            [{"ok": 1}],
            "",
        )
        pr.generate_explain = lambda **kwargs: "ok"

    def tearDown(self):
        pr.extract_entities_local = self._orig_extract_entities_local
        pr.normalize_entities = self._orig_normalize_entities
        pr.generate_sql = self._orig_generate_sql
        pr.explain_query = self._orig_explain_query
        pr.execute_query = self._orig_execute_query
        pr.generate_explain = self._orig_generate_explain

    def test_route_banking_question_to_banking_domain(self):
        registry = load_domain_registry()
        question = "Tra cứu giao dịch chuyển tiền trong tháng này"
        result = route_domains(question, registry, use_embedding=False)
        self.assertEqual(result["candidate_domains"], ["banking"])
        self.assertEqual(result["selected_domain"], "banking")

    def test_route_hrm_question_to_hrm_domain(self):
        registry = load_domain_registry()
        question = "Liệt kê nhân viên thuộc phòng kinh doanh"
        result = route_domains(question, registry, use_embedding=False)
        self.assertEqual(result["candidate_domains"], ["hrm"])
        self.assertEqual(result["selected_domain"], "hrm")

    def test_forced_domain_bypasses_router(self):
        question = "Liệt kê nhân viên thuộc phòng kinh doanh"
        result = pr.run_pipeline(question, explain=False, forced_domain="hrm")
        self.assertEqual(result["domain"], "hrm")
        self.assertEqual(result["candidate_domains"], ["hrm"])
        self.assertEqual(result["validator"], "PASS")

    def test_mixed_question_can_be_marked_domain_ambiguous(self):
        question = "Xem giao dịch của nhân viên"
        result = pr.run_pipeline(question, explain=False)
        self.assertEqual(result["validator"], "DOMAIN_AMBIGUOUS")
        self.assertIsNone(result["domain"])
        self.assertEqual(result["candidate_domains"], ["banking", "hrm"])

    def test_query_cache_is_isolated_by_domain(self):
        sample = {
            "validator": "PASS",
            "tables": ["employee"],
            "intent": "tra_cuu",
            "entities": {},
            "sql": "SELECT 1;",
            "domain": "hrm",
        }
        from pipeline.query_cache import cache_result, get_cached_result

        cache_result("same question", deepcopy(sample), domain_id="hrm")
        self.assertIsNotNone(get_cached_result("same question", "hrm"))
        self.assertIsNone(get_cached_result("same question", "banking"))

    def test_demo_mode_can_fallback_when_models_are_unavailable(self):
        original_generate_sql = pr.generate_sql
        pr.generate_sql = lambda prompt: (_ for _ in ()).throw(RuntimeError("model unavailable"))
        try:
            result = pr.run_pipeline("Tra cuu giao dich chuyen tien", explain=False, demo_mode=True)
        finally:
            pr.generate_sql = original_generate_sql

        self.assertEqual(result["validator"], "PASS")
        self.assertEqual(result["domain"], "banking")
        self.assertIn("SELECT", result["sql"])
        self.assertEqual(result["model_info"]["active_model"], "demo-sql-fallback")


if __name__ == "__main__":
    unittest.main()
