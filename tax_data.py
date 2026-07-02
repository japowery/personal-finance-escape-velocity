"""
Tax data used by Escape Velocity Desktop.

This module intentionally separates data from logic so future versions can swap
in a larger official state/local dataset without touching the app UI.
"""

TAX_YEAR = 2026

FILING_STATUS_LABELS = {
    "single": "Single",
    "married_joint": "Married filing jointly",
    "married_separate": "Married filing separately",
    "head_household": "Head of household",
}

FEDERAL_STANDARD_DEDUCTION_2026 = {
    "single": 16100,
    "married_joint": 32200,
    "married_separate": 16100,
    "head_household": 24150,
}

# Lower-bound marginal brackets on taxable ordinary income.
FEDERAL_BRACKETS_2026 = {
    "single": [
        (0, 0.10), (12400, 0.12), (50400, 0.22), (105700, 0.24),
        (201775, 0.32), (256225, 0.35), (640600, 0.37),
    ],
    "married_joint": [
        (0, 0.10), (24800, 0.12), (100800, 0.22), (211400, 0.24),
        (403550, 0.32), (512450, 0.35), (768700, 0.37),
    ],
    "married_separate": [
        (0, 0.10), (12400, 0.12), (50400, 0.22), (105700, 0.24),
        (201775, 0.32), (256225, 0.35), (384350, 0.37),
    ],
    "head_household": [
        (0, 0.10), (17700, 0.12), (67250, 0.22), (105700, 0.24),
        (201750, 0.32), (256200, 0.35), (640600, 0.37),
    ],
}

PAYROLL_TAX_2026 = {
    "social_security_wage_base": 184500,
    "social_security_rate": 0.062,
    "medicare_rate": 0.0145,
    "additional_medicare_rate": 0.009,
    "additional_medicare_thresholds": {
        "single": 200000,
        "married_joint": 250000,
        "married_separate": 125000,
        "head_household": 200000,
    },
}

NO_INCOME_TAX_STATES = {
    "Alaska", "Florida", "Nevada", "New Hampshire", "South Dakota",
    "Tennessee", "Texas", "Washington", "Wyoming",
}

# Flat-rate and progressive-range state wage-income estimator. Flat-rate states
# are modeled directly. Progressive states use a smoothed effective rate estimate
# based on low/high marginal rates because state deductions, credits, filing rules,
# and local surtaxes vary materially.
STATE_TAX_RULES = {
    "Alabama": {"type": "progressive_range", "low": 0.0200, "high": 0.0500},
    "Alaska": {"type": "none", "rate": 0.0},
    "Arizona": {"type": "flat", "rate": 0.0250},
    "Arkansas": {"type": "progressive_range", "low": 0.0000, "high": 0.0390},
    "California": {"type": "progressive_range", "low": 0.0100, "high": 0.1330},
    "Colorado": {"type": "flat", "rate": 0.0440},
    "Connecticut": {"type": "progressive_range", "low": 0.0200, "high": 0.0699},
    "Delaware": {"type": "progressive_range", "low": 0.0000, "high": 0.0660},
    "District of Columbia": {"type": "progressive_range", "low": 0.0400, "high": 0.1075},
    "Florida": {"type": "none", "rate": 0.0},
    "Georgia": {"type": "flat", "rate": 0.0519},
    "Hawaii": {"type": "progressive_range", "low": 0.0140, "high": 0.1100},
    "Idaho": {"type": "flat", "rate": 0.0530},
    "Illinois": {"type": "flat", "rate": 0.0495},
    "Indiana": {"type": "flat", "rate": 0.0300},
    "Iowa": {"type": "flat", "rate": 0.0380},
    "Kansas": {"type": "progressive_range", "low": 0.0520, "high": 0.0558},
    "Kentucky": {"type": "flat", "rate": 0.0400},
    "Louisiana": {"type": "flat", "rate": 0.0300},
    "Maine": {"type": "progressive_range", "low": 0.0580, "high": 0.0715},
    "Maryland": {"type": "progressive_range", "low": 0.0200, "high": 0.0575},
    "Massachusetts": {"type": "flat_surtax", "rate": 0.0500, "surtax_threshold": 1000000, "surtax_rate": 0.0400},
    "Michigan": {"type": "flat", "rate": 0.0425},
    "Minnesota": {"type": "progressive_range", "low": 0.0535, "high": 0.0985},
    "Mississippi": {"type": "progressive_range", "low": 0.0000, "high": 0.0440},
    "Missouri": {"type": "progressive_range", "low": 0.0000, "high": 0.0470},
    "Montana": {"type": "progressive_range", "low": 0.0470, "high": 0.0590},
    "Nebraska": {"type": "progressive_range", "low": 0.0246, "high": 0.0520},
    "Nevada": {"type": "none", "rate": 0.0},
    "New Hampshire": {"type": "none", "rate": 0.0},
    "New Jersey": {"type": "progressive_range", "low": 0.0140, "high": 0.1075},
    "New Mexico": {"type": "progressive_range", "low": 0.0150, "high": 0.0590},
    "New York": {"type": "progressive_range", "low": 0.0400, "high": 0.1090},
    "North Carolina": {"type": "flat", "rate": 0.0425},
    "North Dakota": {"type": "progressive_range", "low": 0.0000, "high": 0.0250},
    "Ohio": {"type": "progressive_range", "low": 0.0000, "high": 0.0313},
    "Oklahoma": {"type": "progressive_range", "low": 0.0025, "high": 0.0475},
    "Oregon": {"type": "progressive_range", "low": 0.0475, "high": 0.0990},
    "Pennsylvania": {"type": "flat", "rate": 0.0307},
    "Rhode Island": {"type": "progressive_range", "low": 0.0375, "high": 0.0599},
    "South Carolina": {"type": "progressive_range", "low": 0.0000, "high": 0.0600},
    "South Dakota": {"type": "none", "rate": 0.0},
    "Tennessee": {"type": "none", "rate": 0.0},
    "Texas": {"type": "none", "rate": 0.0},
    "Utah": {"type": "flat", "rate": 0.0450},
    "Vermont": {"type": "progressive_range", "low": 0.0335, "high": 0.0875},
    "Virginia": {"type": "progressive_range", "low": 0.0200, "high": 0.0575},
    "Washington": {"type": "none", "rate": 0.0},
    "West Virginia": {"type": "progressive_range", "low": 0.0236, "high": 0.0512},
    "Wisconsin": {"type": "progressive_range", "low": 0.0350, "high": 0.0765},
    "Wyoming": {"type": "none", "rate": 0.0},
}

STATE_NAMES = sorted(STATE_TAX_RULES.keys())

# Local wage-income taxes are highly local. This table covers common examples and
# is intentionally data-driven so it can be expanded. Unknown cities default to 0.
LOCAL_TAX_RULES = {
    ("New York", "New York City"): {"rate": 0.03876, "label": "NYC resident estimate"},
    ("New York", "Yonkers"): {"rate": 0.0160, "label": "Yonkers resident estimate"},
    ("Pennsylvania", "Philadelphia"): {"rate": 0.0375, "label": "Philadelphia resident wage tax estimate"},
    ("Pennsylvania", "Pittsburgh"): {"rate": 0.0300, "label": "Pittsburgh local earned-income estimate"},
    ("Pennsylvania", "Hershey"): {"rate": 0.0100, "label": "Hershey/Derry Township local earned-income estimate"},
    ("Pennsylvania", "Harrisburg"): {"rate": 0.0200, "label": "Harrisburg local earned-income estimate"},
    ("Ohio", "Cleveland"): {"rate": 0.0250, "label": "Cleveland municipal income tax estimate"},
    ("Ohio", "Columbus"): {"rate": 0.0250, "label": "Columbus municipal income tax estimate"},
    ("Ohio", "Cincinnati"): {"rate": 0.0180, "label": "Cincinnati municipal income tax estimate"},
    ("Ohio", "Toledo"): {"rate": 0.0225, "label": "Toledo municipal income tax estimate"},
    ("Ohio", "Akron"): {"rate": 0.0250, "label": "Akron municipal income tax estimate"},
    ("Ohio", "Dayton"): {"rate": 0.0250, "label": "Dayton municipal income tax estimate"},
    ("Michigan", "Detroit"): {"rate": 0.0240, "label": "Detroit resident income tax estimate"},
    ("Missouri", "Kansas City"): {"rate": 0.0100, "label": "Kansas City earnings tax estimate"},
    ("Missouri", "St. Louis"): {"rate": 0.0100, "label": "St. Louis earnings tax estimate"},
    ("Maryland", "Baltimore"): {"rate": 0.0320, "label": "Baltimore local piggyback estimate"},
    ("Kentucky", "Louisville"): {"rate": 0.0220, "label": "Louisville metro occupational estimate"},
    ("Kentucky", "Lexington"): {"rate": 0.0225, "label": "Lexington occupational estimate"},
    ("Oregon", "Portland"): {"rate": 0.0100, "label": "Portland-area local tax placeholder estimate"},
}

SOURCE_NOTES = [
    "Federal tax brackets and standard deductions: IRS 2026 tax inflation adjustments.",
    "Payroll tax: SSA/IRS 2026 OASDI wage base and FICA rates.",
    "State tax rate ranges and flat-rate classifications: USTax Tools 2025-26 bracket summary and Tax Foundation-style state-rate framework.",
    "Local tax rules: compact starter table for common city/local wage taxes; expand tax_data.py for production coverage.",
]
