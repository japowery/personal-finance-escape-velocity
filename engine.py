from __future__ import annotations

from dataclasses import dataclass, asdict
from math import exp
from typing import Dict, List, Tuple

from tax_data import (
    FEDERAL_BRACKETS_2026,
    FEDERAL_STANDARD_DEDUCTION_2026,
    LOCAL_TAX_RULES,
    PAYROLL_TAX_2026,
    STATE_TAX_RULES,
    TAX_YEAR,
)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def progressive_tax(taxable_income: float, brackets: List[Tuple[float, float]]) -> float:
    """Calculate tax using lower-bound marginal brackets."""
    income = max(0.0, float(taxable_income))
    total = 0.0
    ordered = sorted(brackets, key=lambda x: x[0])
    for i, (lower, rate) in enumerate(ordered):
        upper = ordered[i + 1][0] if i + 1 < len(ordered) else None
        if income <= lower:
            break
        taxable_slice = (min(income, upper) - lower) if upper is not None else (income - lower)
        if taxable_slice > 0:
            total += taxable_slice * rate
    return total


@dataclass
class Profile:
    name: str = "Sample household"
    filing_status: str = "single"
    state: str = "Pennsylvania"
    city: str = "Hershey"
    age: float = 30.0
    primary_income: float = 95000.0
    spouse_income: float = 0.0
    pre_tax_contributions: float = 12000.0
    current_investments: float = 75000.0
    cash_savings: float = 15000.0
    debt_balance: float = 0.0
    debt_interest_rate: float = 0.07
    monthly_fixed_expenses: float = 2600.0
    monthly_variable_expenses: float = 900.0
    monthly_joy_spending: float = 500.0
    monthly_low_value_spending: float = 250.0
    monthly_debt_payment: float = 0.0
    monthly_cash_savings: float = 250.0
    expected_return: float = 0.07
    expense_growth: float = 0.025
    income_growth: float = 0.03
    withdrawal_rate: float = 0.04
    emergency_months_target: float = 6.0
    projection_years: int = 55

    @property
    def gross_income(self) -> float:
        return max(0.0, self.primary_income) + max(0.0, self.spouse_income)

    @property
    def monthly_lifestyle_spend(self) -> float:
        return (
            max(0.0, self.monthly_fixed_expenses)
            + max(0.0, self.monthly_variable_expenses)
            + max(0.0, self.monthly_joy_spending)
            + max(0.0, self.monthly_low_value_spending)
        )


def normalize_filing_status(status: str) -> str:
    allowed = set(FEDERAL_BRACKETS_2026)
    if status in allowed:
        return status
    lowered = (status or "").strip().lower()
    label_map = {
        "single": "single",
        "married filing jointly": "married_joint",
        "married_joint": "married_joint",
        "married filing separately": "married_separate",
        "married_separate": "married_separate",
        "head of household": "head_household",
        "head_household": "head_household",
    }
    return label_map.get(lowered, "single")


def estimate_federal_income_tax(gross_income: float, filing_status: str, pre_tax_contributions: float) -> Dict[str, float]:
    status = normalize_filing_status(filing_status)
    standard_deduction = FEDERAL_STANDARD_DEDUCTION_2026[status]
    taxable_income = max(0.0, gross_income - max(0.0, pre_tax_contributions) - standard_deduction)
    tax = progressive_tax(taxable_income, FEDERAL_BRACKETS_2026[status])
    return {
        "taxable_income": taxable_income,
        "standard_deduction": standard_deduction,
        "federal_income_tax": tax,
    }


def estimate_payroll_tax(primary_income: float, spouse_income: float, filing_status: str) -> Dict[str, float]:
    status = normalize_filing_status(filing_status)
    ss_base = PAYROLL_TAX_2026["social_security_wage_base"]
    ss_rate = PAYROLL_TAX_2026["social_security_rate"]
    med_rate = PAYROLL_TAX_2026["medicare_rate"]
    addl_rate = PAYROLL_TAX_2026["additional_medicare_rate"]
    threshold = PAYROLL_TAX_2026["additional_medicare_thresholds"][status]

    incomes = [max(0.0, primary_income)]
    if spouse_income > 0:
        incomes.append(max(0.0, spouse_income))

    social_security = sum(min(w, ss_base) * ss_rate for w in incomes)
    wages = sum(incomes)
    medicare = wages * med_rate
    additional_medicare = max(0.0, wages - threshold) * addl_rate
    return {
        "social_security_tax": social_security,
        "medicare_tax": medicare,
        "additional_medicare_tax": additional_medicare,
        "payroll_tax": social_security + medicare + additional_medicare,
    }


def _progressive_range_effective_rate(taxable_income: float, low: float, high: float) -> float:
    """
    Smooth estimator for progressive state systems when exact state brackets are
    not encoded. It keeps low-income effective rates closer to the lower bound
    and high-income effective rates below the stated top marginal rate.
    """
    if taxable_income <= 0:
        return 0.0
    progress = 1 - exp(-taxable_income / 175000.0)
    return low + (high - low) * 0.78 * progress


def estimate_state_tax(gross_income: float, state: str, filing_status: str, pre_tax_contributions: float) -> Dict[str, float | str]:
    rule = STATE_TAX_RULES.get(state, {"type": "none", "rate": 0.0})
    # Conservative simplification: use federal taxable income proxy for state wage income,
    # except PA-style flat states where gross wage tax is common.
    federal = estimate_federal_income_tax(gross_income, filing_status, pre_tax_contributions)
    taxable_proxy = max(0.0, gross_income - max(0.0, pre_tax_contributions))
    federal_taxable_proxy = federal["taxable_income"]

    typ = rule["type"]
    quality = "high" if typ in {"none", "flat", "flat_surtax"} else "estimated"
    if typ == "none":
        tax = 0.0
        label = "No broad wage-income tax modeled"
    elif typ == "flat":
        # PA taxes compensation broadly; most other flat states have deductions/credits.
        base = taxable_proxy if state == "Pennsylvania" else federal_taxable_proxy
        tax = max(0.0, base) * float(rule["rate"])
        label = f"Flat state estimate at {float(rule['rate']) * 100:.2f}%"
    elif typ == "flat_surtax":
        base = federal_taxable_proxy
        tax = base * float(rule["rate"])
        if base > float(rule.get("surtax_threshold", 10**12)):
            tax += (base - float(rule["surtax_threshold"])) * float(rule.get("surtax_rate", 0.0))
        label = f"Flat state estimate at {float(rule['rate']) * 100:.2f}% plus surtax if applicable"
    else:
        low = float(rule["low"])
        high = float(rule["high"])
        eff_rate = _progressive_range_effective_rate(federal_taxable_proxy, low, high)
        tax = federal_taxable_proxy * eff_rate
        label = f"Progressive state estimate; modeled effective rate {eff_rate * 100:.2f}%"
    return {
        "state_income_tax": max(0.0, tax),
        "state_tax_label": label,
        "state_tax_quality": quality,
    }


def estimate_local_tax(gross_income: float, state: str, city: str) -> Dict[str, float | str]:
    city_clean = (city or "").strip()
    rule = LOCAL_TAX_RULES.get((state, city_clean))
    if not rule:
        return {
            "local_income_tax": 0.0,
            "local_tax_rate": 0.0,
            "local_tax_label": "No local wage-income tax in starter database",
            "local_tax_quality": "unknown/none",
        }
    rate = float(rule["rate"])
    return {
        "local_income_tax": max(0.0, gross_income) * rate,
        "local_tax_rate": rate,
        "local_tax_label": str(rule["label"]),
        "local_tax_quality": "starter-table",
    }


def estimate_total_taxes(profile: Profile) -> Dict[str, float | str]:
    gross = profile.gross_income
    federal = estimate_federal_income_tax(gross, profile.filing_status, profile.pre_tax_contributions)
    payroll = estimate_payroll_tax(profile.primary_income, profile.spouse_income, profile.filing_status)
    state = estimate_state_tax(gross, profile.state, profile.filing_status, profile.pre_tax_contributions)
    local = estimate_local_tax(gross, profile.state, profile.city)
    total = (
        federal["federal_income_tax"]
        + payroll["payroll_tax"]
        + float(state["state_income_tax"])
        + float(local["local_income_tax"])
    )
    after_tax_cash = gross - max(0.0, profile.pre_tax_contributions) - total
    return {
        **federal,
        **payroll,
        **state,
        **local,
        "total_tax": total,
        "effective_tax_rate": total / gross if gross > 0 else 0.0,
        "after_tax_cash_income": after_tax_cash,
        "tax_year": TAX_YEAR,
    }


def emergency_fund_status(profile: Profile) -> Dict[str, float]:
    monthly_need = profile.monthly_lifestyle_spend
    target = monthly_need * max(0.0, profile.emergency_months_target)
    progress = clamp(profile.cash_savings / target if target else 1.0, 0.0, 1.0)
    return {
        "emergency_target": target,
        "emergency_progress": progress,
        "emergency_gap": max(0.0, target - profile.cash_savings),
    }


def calc_current_snapshot(profile: Profile) -> Dict[str, float | str]:
    taxes = estimate_total_taxes(profile)
    monthly_after_tax = float(taxes["after_tax_cash_income"]) / 12.0
    monthly_required = (
        profile.monthly_lifestyle_spend
        + max(0.0, profile.monthly_debt_payment)
        + max(0.0, profile.monthly_cash_savings)
    )
    recommended_monthly_investment = max(0.0, monthly_after_tax - monthly_required)
    annual_lifestyle_spend = profile.monthly_lifestyle_spend * 12.0
    fi_number_today = annual_lifestyle_spend / max(0.001, profile.withdrawal_rate)
    fi_progress = clamp(profile.current_investments / fi_number_today if fi_number_today else 0.0, 0.0, 1.0)
    savings_rate = (
        (profile.pre_tax_contributions + recommended_monthly_investment * 12 + profile.monthly_cash_savings * 12)
        / profile.gross_income
        if profile.gross_income > 0 else 0.0
    )
    investment_rate = (
        (profile.pre_tax_contributions + recommended_monthly_investment * 12) / profile.gross_income
        if profile.gross_income > 0 else 0.0
    )
    return {
        **taxes,
        **emergency_fund_status(profile),
        "monthly_after_tax_cash": monthly_after_tax,
        "monthly_lifestyle_spend": profile.monthly_lifestyle_spend,
        "monthly_required_outflow": monthly_required,
        "recommended_monthly_investment": recommended_monthly_investment,
        "annual_lifestyle_spend": annual_lifestyle_spend,
        "fi_number_today": fi_number_today,
        "fi_progress": fi_progress,
        "savings_rate": savings_rate,
        "investment_rate": investment_rate,
        "net_worth": profile.current_investments + profile.cash_savings - profile.debt_balance,
    }


def project_profile(profile: Profile, scenario: Dict[str, float] | None = None) -> Dict[str, object]:
    """Monthly projection with annual recalculation of taxes/income/expenses."""
    scenario = scenario or {}
    p = Profile(**asdict(profile))

    # Scenario adjustments.
    p.monthly_low_value_spending = max(0.0, p.monthly_low_value_spending + scenario.get("monthly_low_value_delta", 0.0))
    p.monthly_fixed_expenses = max(0.0, p.monthly_fixed_expenses + scenario.get("monthly_fixed_delta", 0.0))
    p.monthly_variable_expenses = max(0.0, p.monthly_variable_expenses + scenario.get("monthly_variable_delta", 0.0))
    p.pre_tax_contributions = max(0.0, p.pre_tax_contributions + scenario.get("annual_pretax_delta", 0.0))
    extra_monthly_investment = scenario.get("extra_monthly_investment", 0.0)
    return_override = scenario.get("return_delta", 0.0)
    income_growth_delta = scenario.get("income_growth_delta", 0.0)

    months = int(max(1, p.projection_years) * 12)
    current_portfolio = max(0.0, p.current_investments)
    current_debt = max(0.0, p.debt_balance)
    monthly_return = (1 + max(-0.99, p.expected_return + return_override)) ** (1 / 12) - 1
    monthly_debt_rate = max(0.0, p.debt_interest_rate) / 12

    rows = []
    fi_month = None
    final_snapshot = None

    for month in range(months + 1):
        year = month // 12
        month_in_year = month % 12
        if month_in_year == 0:
            primary_income_y = p.primary_income * ((1 + p.income_growth + income_growth_delta) ** year)
            spouse_income_y = p.spouse_income * ((1 + p.income_growth + income_growth_delta) ** year)
            pretax_y = p.pre_tax_contributions * ((1 + p.income_growth + income_growth_delta) ** year)
            expense_multiplier = (1 + p.expense_growth) ** year
            monthly_fixed_y = p.monthly_fixed_expenses * expense_multiplier
            monthly_variable_y = p.monthly_variable_expenses * expense_multiplier
            monthly_joy_y = p.monthly_joy_spending * expense_multiplier
            monthly_low_value_y = p.monthly_low_value_spending * expense_multiplier
            temp_profile = Profile(**asdict(p))
            temp_profile.primary_income = primary_income_y
            temp_profile.spouse_income = spouse_income_y
            temp_profile.pre_tax_contributions = pretax_y
            temp_profile.monthly_fixed_expenses = monthly_fixed_y
            temp_profile.monthly_variable_expenses = monthly_variable_y
            temp_profile.monthly_joy_spending = monthly_joy_y
            temp_profile.monthly_low_value_spending = monthly_low_value_y
            tax_y = estimate_total_taxes(temp_profile)
            monthly_after_tax_y = float(tax_y["after_tax_cash_income"]) / 12.0
            monthly_lifestyle_y = temp_profile.monthly_lifestyle_spend
            annual_lifestyle_y = monthly_lifestyle_y * 12.0
            fi_need_y = annual_lifestyle_y / max(0.001, p.withdrawal_rate)
            monthly_cash_savings_y = p.monthly_cash_savings * expense_multiplier
            annual_pretax_portfolio_contrib_y = pretax_y

        if month > 0:
            # Debt amortization. Payment ends when debt is gone, freeing cash flow.
            debt_payment_y = 0.0
            if current_debt > 0:
                current_debt = current_debt * (1 + monthly_debt_rate)
                debt_payment_y = min(current_debt, max(0.0, p.monthly_debt_payment))
                current_debt -= debt_payment_y
            freed_debt_payment = max(0.0, p.monthly_debt_payment - debt_payment_y)

            baseline_surplus = monthly_after_tax_y - monthly_lifestyle_y - monthly_cash_savings_y - debt_payment_y
            monthly_investment = max(0.0, baseline_surplus + freed_debt_payment + extra_monthly_investment)
            # Pretax contribution enters portfolio monthly; after-tax cash already subtracts annual pretax.
            monthly_investment += annual_pretax_portfolio_contrib_y / 12.0
            current_portfolio = current_portfolio * (1 + monthly_return) + monthly_investment

        row = {
            "month": month,
            "age": p.age + month / 12,
            "year": year,
            "portfolio": current_portfolio,
            "debt": current_debt,
            "annual_spending": annual_lifestyle_y,
            "fi_need": fi_need_y,
            "monthly_after_tax": monthly_after_tax_y,
        }
        rows.append(row)
        final_snapshot = row
        if fi_month is None and current_portfolio >= fi_need_y:
            fi_month = month

    if fi_month is not None:
        fi_age = p.age + fi_month / 12.0
        years_to_fi = fi_month / 12.0
    else:
        fi_age = None
        years_to_fi = None

    return {
        "rows": rows,
        "fi_month": fi_month,
        "fi_age": fi_age,
        "years_to_fi": years_to_fi,
        "final_snapshot": final_snapshot,
    }


def scenario_results(profile: Profile) -> List[Dict[str, object]]:
    scenarios = [
        ("Current plan", {}),
        ("Invest +$250/mo", {"extra_monthly_investment": 250}),
        ("Invest +$500/mo", {"extra_monthly_investment": 500}),
        ("Cut low-value $250", {"monthly_low_value_delta": -250, "extra_monthly_investment": 250}),
        ("Lower return", {"return_delta": -0.02}),
        ("Higher income growth", {"income_growth_delta": 0.02}),
    ]
    output = []
    for name, adjustments in scenarios:
        projection = project_profile(profile, adjustments)
        output.append({
            "name": name,
            "adjustments": adjustments,
            "fi_age": projection["fi_age"],
            "years_to_fi": projection["years_to_fi"],
            "final_portfolio": projection["final_snapshot"]["portfolio"],
            "fi_need_end": projection["final_snapshot"]["fi_need"],
        })
    return output


def generate_insights(profile: Profile, snapshot: Dict[str, float | str], projection: Dict[str, object], scenarios: List[Dict[str, object]]) -> List[str]:
    insights: List[str] = []
    fi_age = projection["fi_age"]
    if fi_age is None:
        insights.append("At the current savings path, projected investments do not reach escape velocity inside the modeled window.")
    else:
        insights.append(f"At the current path, escape velocity is projected around age {fi_age:.1f}.")

    rec = float(snapshot["recommended_monthly_investment"])
    insights.append(f"Estimated maximum monthly investment capacity is {format_currency(rec)} after taxes, spending, debt payments, and cash savings.")

    eff_tax = float(snapshot["effective_tax_rate"])
    insights.append(f"Estimated all-in tax load is {eff_tax:.1%}, including federal, payroll, state, and any known local wage tax.")

    low_value = profile.monthly_low_value_spending
    if low_value > 0:
        insights.append(f"Low-value spending is modeled at {format_currency(low_value)} per month. Redirecting it is one of the cleanest levers because it improves both savings rate and FI number.")

    emergency_progress = float(snapshot["emergency_progress"])
    if emergency_progress < 1:
        insights.append(f"Emergency fund is {emergency_progress:.0%} funded against the current target. Build this before taking avoidable risk.")
    else:
        insights.append("Emergency fund is fully funded against the current target, so excess cash can be more deliberately assigned.")

    current_age = scenarios[0]["fi_age"]
    plus_500_age = scenarios[2]["fi_age"]
    if current_age is not None and plus_500_age is not None:
        delta = float(current_age) - float(plus_500_age)
        if delta > 0.1:
            insights.append(f"Adding $500/month is projected to move escape velocity earlier by about {delta:.1f} years.")

    insights.append("Use the budget as permission to spend on what matters. Cut what does not add meaning, joy, convenience, or freedom.")
    return insights[:7]


def format_currency(value: float, decimals: int = 0) -> str:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    sign = "-" if v < 0 else ""
    v = abs(v)
    if decimals == 0:
        return f"{sign}${v:,.0f}"
    return f"{sign}${v:,.{decimals}f}"


def format_percent(value: float) -> str:
    try:
        return f"{float(value):.1%}"
    except Exception:
        return "0.0%"
