import unittest

from engine import Profile, estimate_federal_income_tax, estimate_payroll_tax, project_profile, scenario_results, progressive_tax
from tax_data import FEDERAL_BRACKETS_2026


class EngineTests(unittest.TestCase):
    def test_progressive_tax_single_2026(self):
        # 2026 single taxable income of 50,400:
        # 10% of 12,400 + 12% of 38,000 = 1,240 + 4,560 = 5,800
        tax = progressive_tax(50400, FEDERAL_BRACKETS_2026["single"])
        self.assertAlmostEqual(tax, 5800, places=2)

    def test_federal_standard_deduction(self):
        res = estimate_federal_income_tax(100000, "single", 0)
        self.assertAlmostEqual(res["taxable_income"], 83900, places=2)
        self.assertGreater(res["federal_income_tax"], 0)

    def test_payroll_tax_cap(self):
        res = estimate_payroll_tax(300000, 0, "single")
        self.assertAlmostEqual(res["social_security_tax"], 184500 * 0.062, places=2)
        self.assertAlmostEqual(res["additional_medicare_tax"], (300000 - 200000) * 0.009, places=2)

    def test_projection_runs(self):
        p = Profile(primary_income=150000, current_investments=100000, monthly_fixed_expenses=2500, monthly_variable_expenses=800)
        projection = project_profile(p)
        self.assertIn("rows", projection)
        self.assertGreater(len(projection["rows"]), 12)
        self.assertGreaterEqual(projection["final_snapshot"]["portfolio"], 0)

    def test_scenarios(self):
        p = Profile()
        scenarios = scenario_results(p)
        self.assertEqual(len(scenarios), 6)
        self.assertEqual(scenarios[0]["name"], "Current plan")


if __name__ == "__main__":
    unittest.main()
