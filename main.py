from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict, fields
from pathlib import Path
from typing import Dict, List

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from education import EDUCATION_CARDS
from engine import (
    Profile,
    calc_current_snapshot,
    format_currency,
    format_percent,
    generate_insights,
    project_profile,
    scenario_results,
)
from tax_data import FILING_STATUS_LABELS, LOCAL_TAX_RULES, SOURCE_NOTES, STATE_NAMES, TAX_YEAR

APP_TITLE = "Escape Velocity"
APP_DIR = Path.home() / ".escape_velocity"
PROFILE_PATH = APP_DIR / "profile.json"

COLORS = {
    "bg": "#F7F5F0",
    "panel": "#FFFFFF",
    "text": "#171717",
    "muted": "#6B6B6B",
    "line": "#E6E1D8",
    "accent": "#1F6F5B",
    "accent_soft": "#DDEBE5",
    "accent_dark": "#174F41",
    "warning": "#B87900",
    "soft": "#F0EEE8",
}

FONT = "Helvetica"


def safe_float(value, default=0.0):
    try:
        if isinstance(value, str):
            value = value.replace("$", "").replace(",", "").replace("%", "").strip()
            if value == "":
                return default
        return float(value)
    except Exception:
        return default


def pct_to_decimal(value, default=0.0):
    v = safe_float(value, default)
    if abs(v) > 1:
        return v / 100.0
    return v


class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Bg.TFrame")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass


class MetricCard(ttk.Frame):
    def __init__(self, parent, title, value="—", subtitle=""):
        super().__init__(parent, style="Card.TFrame", padding=(18, 16))
        self.title_var = tk.StringVar(value=title)
        self.value_var = tk.StringVar(value=value)
        self.subtitle_var = tk.StringVar(value=subtitle)
        ttk.Label(self, textvariable=self.title_var, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(self, textvariable=self.value_var, style="Metric.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(self, textvariable=self.subtitle_var, style="SmallMuted.TLabel", wraplength=210).pack(anchor="w", pady=(8, 0))

    def update_value(self, value, subtitle=""):
        self.value_var.set(value)
        self.subtitle_var.set(subtitle)


class LineChart(tk.Canvas):
    def __init__(self, parent, height=280):
        super().__init__(parent, height=height, bg=COLORS["panel"], highlightthickness=0)
        self.rows = []
        self.bind("<Configure>", lambda event: self.draw())

    def set_data(self, rows):
        self.rows = rows or []
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width() or 700
        h = self.winfo_height() or 280
        pad_l, pad_r, pad_t, pad_b = 56, 24, 24, 42
        plot_w = max(10, w - pad_l - pad_r)
        plot_h = max(10, h - pad_t - pad_b)
        self.create_rectangle(0, 0, w, h, fill=COLORS["panel"], outline="")
        self.create_text(18, 16, text="Portfolio vs. FI number", anchor="w", font=(FONT, 13, "bold"), fill=COLORS["text"])
        if not self.rows:
            self.create_text(w / 2, h / 2, text="No projection yet", fill=COLORS["muted"], font=(FONT, 12))
            return
        sampled = [r for r in self.rows if r["month"] % 12 == 0]
        if len(sampled) < 2:
            sampled = self.rows
        max_y = max(max(r["portfolio"], r["fi_need"]) for r in sampled) * 1.05
        max_y = max(max_y, 1000)
        max_x = max(r["month"] for r in sampled) or 1

        for i in range(5):
            y = pad_t + plot_h * i / 4
            self.create_line(pad_l, y, pad_l + plot_w, y, fill=COLORS["line"])
            label = format_currency(max_y * (1 - i / 4))
            self.create_text(pad_l - 8, y, text=label, anchor="e", font=(FONT, 9), fill=COLORS["muted"])

        def point(row, key):
            x = pad_l + plot_w * (row["month"] / max_x)
            y = pad_t + plot_h * (1 - row[key] / max_y)
            return x, y

        for key, color, label in [
            ("fi_need", "#9A8F7A", "FI number"),
            ("portfolio", COLORS["accent"], "Portfolio"),
        ]:
            pts = []
            for r in sampled:
                pts.extend(point(r, key))
            if len(pts) >= 4:
                self.create_line(*pts, fill=color, width=3, smooth=True)
            self.create_rectangle(w - 150, 22 if key == "portfolio" else 43, w - 138, 34 if key == "portfolio" else 55, fill=color, outline=color)
            self.create_text(w - 132, 28 if key == "portfolio" else 49, text=label, anchor="w", font=(FONT, 9), fill=COLORS["muted"])

        self.create_line(pad_l, pad_t + plot_h, pad_l + plot_w, pad_t + plot_h, fill=COLORS["line"])
        self.create_text(pad_l, h - 18, text="Today", anchor="w", font=(FONT, 9), fill=COLORS["muted"])
        self.create_text(pad_l + plot_w, h - 18, text=f"Age {sampled[-1]['age']:.0f}", anchor="e", font=(FONT, 9), fill=COLORS["muted"])


class BarChart(tk.Canvas):
    def __init__(self, parent, height=260):
        super().__init__(parent, height=height, bg=COLORS["panel"], highlightthickness=0)
        self.items = []
        self.bind("<Configure>", lambda event: self.draw())

    def set_data(self, items):
        self.items = items or []
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width() or 700
        h = self.winfo_height() or 260
        self.create_rectangle(0, 0, w, h, fill=COLORS["panel"], outline="")
        self.create_text(18, 16, text="Scenario comparison", anchor="w", font=(FONT, 13, "bold"), fill=COLORS["text"])
        valid = [x for x in self.items if x.get("fi_age") is not None]
        if not valid:
            self.create_text(w / 2, h / 2, text="No scenario reaches FI inside the modeled window", fill=COLORS["muted"], font=(FONT, 12))
            return
        min_age = min(float(x["fi_age"]) for x in valid)
        max_age = max(float(x["fi_age"]) for x in valid)
        max_age = max(max_age, min_age + 1)
        left = 160
        right = 28
        top = 52
        row_h = 30
        scale_w = max(10, w - left - right)
        for i, item in enumerate(self.items):
            y = top + i * row_h
            name = item["name"]
            age = item.get("fi_age")
            self.create_text(18, y + 12, text=name, anchor="w", font=(FONT, 10), fill=COLORS["text"])
            if age is None:
                self.create_text(left, y + 12, text="No FI in window", anchor="w", font=(FONT, 10), fill=COLORS["muted"])
                continue
            pct = (float(age) - min_age) / (max_age - min_age)
            bar_w = max(16, scale_w * (1 - pct * 0.75))
            self.create_rectangle(left, y + 4, left + bar_w, y + 22, fill=COLORS["accent_soft"], outline="")
            self.create_rectangle(left, y + 4, left + bar_w, y + 22, fill=COLORS["accent"], outline="")
            self.create_text(left + bar_w + 8, y + 13, text=f"Age {float(age):.1f}", anchor="w", font=(FONT, 10), fill=COLORS["muted"])


class EscapeVelocityApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1180x780")
        self.root.minsize(1040, 680)
        self.root.configure(bg=COLORS["bg"])
        self._setup_style()

        self.profile = self.load_profile()
        self.vars: Dict[str, tk.StringVar] = {}
        self.current_snapshot = None
        self.current_projection = None
        self.current_scenarios = []

        self.shell = ttk.Frame(root, style="Bg.TFrame")
        self.shell.pack(fill="both", expand=True)
        self.sidebar = ttk.Frame(self.shell, style="Side.TFrame", width=230, padding=(18, 22))
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.content = ttk.Frame(self.shell, style="Bg.TFrame")
        self.content.pack(side="right", fill="both", expand=True)

        self.pages: Dict[str, ttk.Frame] = {}
        self.nav_buttons: Dict[str, ttk.Button] = {}
        self._build_sidebar()
        self._build_pages()
        self.show_page("Dashboard")
        self.recalculate(show_errors=False)

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Bg.TFrame", background=COLORS["bg"])
        style.configure("Side.TFrame", background=COLORS["text"])
        style.configure("Card.TFrame", background=COLORS["panel"], relief="flat")
        style.configure("Soft.TFrame", background=COLORS["soft"], relief="flat")
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=(FONT, 11))
        style.configure("Card.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=(FONT, 11))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=(FONT, 26, "bold"))
        style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=(FONT, 12))
        style.configure("Metric.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=(FONT, 22, "bold"))
        style.configure("Muted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=(FONT, 10))
        style.configure("SmallMuted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=(FONT, 9))
        style.configure("SideTitle.TLabel", background=COLORS["text"], foreground="#FFFFFF", font=(FONT, 17, "bold"))
        style.configure("SideSmall.TLabel", background=COLORS["text"], foreground="#BCBCBC", font=(FONT, 9))
        style.configure("TEntry", fieldbackground="#FFFFFF", borderwidth=0, padding=6)
        style.configure("TCombobox", fieldbackground="#FFFFFF", borderwidth=0, padding=6)
        style.configure("Accent.TButton", background=COLORS["accent"], foreground="#FFFFFF", font=(FONT, 10, "bold"), padding=(12, 8), borderwidth=0)
        style.map("Accent.TButton", background=[("active", COLORS["accent_dark"]), ("pressed", COLORS["accent_dark"])])
        style.configure("Ghost.TButton", background=COLORS["soft"], foreground=COLORS["text"], font=(FONT, 10), padding=(10, 7), borderwidth=0)
        style.configure("Nav.TButton", background=COLORS["text"], foreground="#FFFFFF", font=(FONT, 11), anchor="w", padding=(12, 10), borderwidth=0)
        style.map("Nav.TButton", background=[("active", "#2A2A2A"), ("pressed", "#333333")])

    def _build_sidebar(self):
        ttk.Label(self.sidebar, text="Escape\nVelocity", style="SideTitle.TLabel").pack(anchor="w")
        ttk.Label(self.sidebar, text="minimal financial independence dashboard", style="SideSmall.TLabel", wraplength=180).pack(anchor="w", pady=(8, 28))
        for page in ["Dashboard", "Inputs", "Scenarios", "Learn", "Method"]:
            btn = ttk.Button(self.sidebar, text=page, style="Nav.TButton", command=lambda p=page: self.show_page(p))
            btn.pack(fill="x", pady=3)
            self.nav_buttons[page] = btn
        ttk.Frame(self.sidebar, style="Side.TFrame").pack(expand=True, fill="both")
        ttk.Button(self.sidebar, text="Save profile", style="Accent.TButton", command=self.save_profile).pack(fill="x", pady=(0, 8))
        ttk.Button(self.sidebar, text="Export CSV", style="Nav.TButton", command=self.export_projection_csv).pack(fill="x")
        ttk.Label(self.sidebar, text=f"Tax year {TAX_YEAR} estimator", style="SideSmall.TLabel").pack(anchor="w", pady=(16, 0))

    def _page(self, name: str) -> ttk.Frame:
        page = ttk.Frame(self.content, style="Bg.TFrame")
        self.pages[name] = page
        return page

    def _build_pages(self):
        self._build_dashboard_page(self._page("Dashboard"))
        self._build_inputs_page(self._page("Inputs"))
        self._build_scenarios_page(self._page("Scenarios"))
        self._build_learn_page(self._page("Learn"))
        self._build_method_page(self._page("Method"))

    def show_page(self, name):
        for p in self.pages.values():
            p.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

    def header(self, parent, title, subtitle):
        frame = ttk.Frame(parent, style="Bg.TFrame")
        frame.pack(fill="x", padx=28, pady=(24, 14))
        ttk.Label(frame, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text=subtitle, style="Subtitle.TLabel", wraplength=850).pack(anchor="w", pady=(4, 0))
        return frame

    def _build_dashboard_page(self, page):
        self.header(page, "Financial escape velocity", "See how your income, spending, taxes, investments, and assumptions translate into freedom.")
        outer = ScrollFrame(page)
        outer.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        body = outer.inner

        grid = ttk.Frame(body, style="Bg.TFrame")
        grid.pack(fill="x", pady=(0, 14))
        self.metric_cards = {}
        metrics = [
            ("FI age", "fi_age"), ("FI number", "fi_number"), ("Monthly investment capacity", "investment"),
            ("FI progress", "fi_progress"), ("Savings rate", "savings_rate"), ("After-tax income", "after_tax"),
        ]
        for idx, (label, key) in enumerate(metrics):
            card = MetricCard(grid, label)
            card.grid(row=idx // 3, column=idx % 3, sticky="ew", padx=6, pady=6)
            grid.columnconfigure(idx % 3, weight=1)
            self.metric_cards[key] = card

        chart_card = ttk.Frame(body, style="Card.TFrame", padding=(12, 12))
        chart_card.pack(fill="x", pady=(0, 14))
        self.line_chart = LineChart(chart_card, height=300)
        self.line_chart.pack(fill="x")

        lower = ttk.Frame(body, style="Bg.TFrame")
        lower.pack(fill="x")
        lower.columnconfigure(0, weight=1)
        lower.columnconfigure(1, weight=1)

        insights_card = ttk.Frame(lower, style="Card.TFrame", padding=(18, 16))
        insights_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        ttk.Label(insights_card, text="Insights", style="Card.TLabel", font=(FONT, 15, "bold")).pack(anchor="w")
        self.insights_text = tk.Text(insights_card, height=10, wrap="word", bg=COLORS["panel"], fg=COLORS["text"], relief="flat", font=(FONT, 11), padx=0, pady=10)
        self.insights_text.pack(fill="both", expand=True)
        self.insights_text.configure(state="disabled")

        tax_card = ttk.Frame(lower, style="Card.TFrame", padding=(18, 16))
        tax_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        ttk.Label(tax_card, text="Tax estimate", style="Card.TLabel", font=(FONT, 15, "bold")).pack(anchor="w")
        self.tax_text = tk.Text(tax_card, height=10, wrap="word", bg=COLORS["panel"], fg=COLORS["text"], relief="flat", font=(FONT, 11), padx=0, pady=10)
        self.tax_text.pack(fill="both", expand=True)
        self.tax_text.configure(state="disabled")

    def _build_inputs_page(self, page):
        self.header(page, "Inputs", "Only edit the assumptions you know. The tax rate is estimated from filing status, state, and city.")
        outer = ScrollFrame(page)
        outer.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        body = outer.inner

        top = ttk.Frame(body, style="Bg.TFrame")
        top.pack(fill="x", pady=(0, 10))
        ttk.Button(top, text="Recalculate", style="Accent.TButton", command=self.recalculate).pack(side="left")
        ttk.Button(top, text="Load sample", style="Ghost.TButton", command=self.load_sample).pack(side="left", padx=8)
        ttk.Button(top, text="Reset saved profile", style="Ghost.TButton", command=self.reset_saved_profile).pack(side="left")

        self.input_container = ttk.Frame(body, style="Bg.TFrame")
        self.input_container.pack(fill="both", expand=True)
        self._build_input_sections(self.input_container)

    def _input_var(self, key, value):
        var = tk.StringVar(value=str(value))
        self.vars[key] = var
        return var

    def _field(self, parent, label, key, default, kind="entry", values=None, percent=False):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=5)
        ttk.Label(row, text=label, style="Card.TLabel").pack(side="left", anchor="w")
        var = self._input_var(key, default)
        if kind == "combo":
            widget = ttk.Combobox(row, textvariable=var, values=values or [], state="readonly", width=28)
        else:
            widget = ttk.Entry(row, textvariable=var, width=30)
        widget.pack(side="right")
        if key == "state":
            widget.bind("<<ComboboxSelected>>", lambda e: self._refresh_city_values())
        return widget

    def _section(self, parent, title):
        card = ttk.Frame(parent, style="Card.TFrame", padding=(18, 16))
        card.pack(fill="x", pady=8)
        ttk.Label(card, text=title, style="Card.TLabel", font=(FONT, 15, "bold")).pack(anchor="w", pady=(0, 8))
        return card

    def _build_input_sections(self, parent):
        p = self.profile
        section = self._section(parent, "Household")
        self._field(section, "Profile name", "name", p.name)
        self._field(section, "Filing status", "filing_status", p.filing_status, "combo", list(FILING_STATUS_LABELS.keys()))
        self._field(section, "State", "state", p.state, "combo", STATE_NAMES)
        self.city_widget = self._field(section, "City", "city", p.city, "combo", [])
        self._field(section, "Current age", "age", p.age)

        section = self._section(parent, "Income and portfolio")
        self._field(section, "Primary annual income", "primary_income", p.primary_income)
        self._field(section, "Spouse/partner annual income", "spouse_income", p.spouse_income)
        self._field(section, "Annual pre-tax retirement/HSA contributions", "pre_tax_contributions", p.pre_tax_contributions)
        self._field(section, "Current investment portfolio", "current_investments", p.current_investments)
        self._field(section, "Cash savings", "cash_savings", p.cash_savings)

        section = self._section(parent, "Monthly spending")
        self._field(section, "Fixed essentials", "monthly_fixed_expenses", p.monthly_fixed_expenses)
        self._field(section, "Variable essentials", "monthly_variable_expenses", p.monthly_variable_expenses)
        self._field(section, "Joy spending", "monthly_joy_spending", p.monthly_joy_spending)
        self._field(section, "Low-value spending", "monthly_low_value_spending", p.monthly_low_value_spending)
        self._field(section, "Monthly cash savings", "monthly_cash_savings", p.monthly_cash_savings)

        section = self._section(parent, "Debt")
        self._field(section, "Debt balance", "debt_balance", p.debt_balance)
        self._field(section, "Debt interest rate", "debt_interest_rate", p.debt_interest_rate * 100)
        self._field(section, "Monthly debt payment", "monthly_debt_payment", p.monthly_debt_payment)

        section = self._section(parent, "Assumptions")
        self._field(section, "Expected annual investment return", "expected_return", p.expected_return * 100)
        self._field(section, "Annual expense growth", "expense_growth", p.expense_growth * 100)
        self._field(section, "Annual income growth", "income_growth", p.income_growth * 100)
        self._field(section, "Withdrawal rate", "withdrawal_rate", p.withdrawal_rate * 100)
        self._field(section, "Emergency fund target months", "emergency_months_target", p.emergency_months_target)
        self._field(section, "Projection years", "projection_years", p.projection_years)
        self._refresh_city_values()

    def _refresh_city_values(self):
        state = self.vars.get("state", tk.StringVar(value=self.profile.state)).get()
        cities = sorted([city for (st, city) in LOCAL_TAX_RULES.keys() if st == state])
        values = ["Other / no local tax in database"] + cities
        try:
            self.city_widget.configure(values=values, state="normal")
            current = self.vars["city"].get()
            if current == "" or (current not in values and current == "Other / no local tax in database"):
                self.vars["city"].set(values[0])
        except Exception:
            pass

    def _build_scenarios_page(self, page):
        self.header(page, "Scenarios", "Compare how simple changes affect your projected escape velocity age.")
        outer = ScrollFrame(page)
        outer.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        body = outer.inner
        chart_card = ttk.Frame(body, style="Card.TFrame", padding=(12, 12))
        chart_card.pack(fill="x", pady=(0, 14))
        self.bar_chart = BarChart(chart_card, height=260)
        self.bar_chart.pack(fill="x")
        self.scenario_table = ttk.Frame(body, style="Card.TFrame", padding=(18, 16))
        self.scenario_table.pack(fill="x")

    def _build_learn_page(self, page):
        self.header(page, "Savings and investing guide", "Concise explanations placed inside the product so users understand what the numbers mean.")
        outer = ScrollFrame(page)
        outer.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        body = outer.inner
        for title, copy in EDUCATION_CARDS:
            card = ttk.Frame(body, style="Card.TFrame", padding=(18, 16))
            card.pack(fill="x", pady=7)
            ttk.Label(card, text=title, style="Card.TLabel", font=(FONT, 15, "bold")).pack(anchor="w")
            ttk.Label(card, text=copy, style="Card.TLabel", wraplength=850).pack(anchor="w", pady=(6, 0))

    def _build_method_page(self, page):
        self.header(page, "Method", "How the application estimates taxes, projections, and financial independence.")
        outer = ScrollFrame(page)
        outer.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        body = outer.inner
        sections = [
            ("Tax model", [
                f"Uses tax year {TAX_YEAR} federal brackets and standard deduction.",
                "Payroll taxes include Social Security, Medicare, and Additional Medicare thresholds.",
                "State tax is direct for no-tax and flat-rate states; progressive states use a smoothed effective-rate estimate from published low/high marginal rates.",
                "Local tax uses the starter city table in tax_data.py. Unknown cities default to zero local wage tax.",
            ]),
            ("Projection model", [
                "Income, taxes, and expenses are recalculated annually.",
                "Portfolio growth compounds monthly using the expected annual return assumption.",
                "Monthly investment capacity is after-tax cash income minus lifestyle spending, debt payments, and cash savings, plus pre-tax retirement contributions.",
                "Escape velocity occurs when projected portfolio exceeds annual lifestyle spending divided by withdrawal rate.",
            ]),
            ("Sources included in code", SOURCE_NOTES),
        ]
        for title, bullets in sections:
            card = ttk.Frame(body, style="Card.TFrame", padding=(18, 16))
            card.pack(fill="x", pady=7)
            ttk.Label(card, text=title, style="Card.TLabel", font=(FONT, 15, "bold")).pack(anchor="w")
            for b in bullets:
                ttk.Label(card, text=f"• {b}", style="Card.TLabel", wraplength=900).pack(anchor="w", pady=(6, 0))

    def vars_to_profile(self) -> Profile:
        values = {f.name: getattr(Profile(), f.name) for f in fields(Profile)}
        for key, var in self.vars.items():
            val = var.get()
            if key in {"name", "filing_status", "state", "city"}:
                values[key] = val
            elif key in {"debt_interest_rate", "expected_return", "expense_growth", "income_growth", "withdrawal_rate"}:
                values[key] = pct_to_decimal(val, getattr(Profile(), key))
            elif key == "projection_years":
                values[key] = int(max(1, min(80, safe_float(val, getattr(Profile(), key)))))
            else:
                values[key] = safe_float(val, getattr(Profile(), key))
        if values["city"] == "Other / no local tax in database":
            values["city"] = ""
        return Profile(**values)

    def recalculate(self, show_errors=True):
        try:
            self.profile = self.vars_to_profile() if self.vars else self.profile
            self.current_snapshot = calc_current_snapshot(self.profile)
            self.current_projection = project_profile(self.profile)
            self.current_scenarios = scenario_results(self.profile)
            self.update_dashboard()
            self.update_scenarios()
        except Exception as e:
            if show_errors:
                messagebox.showerror("Calculation error", f"Could not calculate profile.\n\n{e}")

    def update_dashboard(self):
        s = self.current_snapshot
        p = self.current_projection
        if not s or not p:
            return
        fi_age = p["fi_age"]
        self.metric_cards["fi_age"].update_value("Not reached" if fi_age is None else f"Age {fi_age:.1f}", "Projected point where portfolio exceeds FI number")
        self.metric_cards["fi_number"].update_value(format_currency(float(s["fi_number_today"])), "Today, based on current lifestyle spending")
        self.metric_cards["investment"].update_value(format_currency(float(s["recommended_monthly_investment"])), "Estimated monthly capacity")
        self.metric_cards["fi_progress"].update_value(format_percent(float(s["fi_progress"])), "Current portfolio divided by FI number")
        self.metric_cards["savings_rate"].update_value(format_percent(float(s["savings_rate"])), "Includes cash savings and investing capacity")
        self.metric_cards["after_tax"].update_value(format_currency(float(s["after_tax_cash_income"])), "After taxes and pre-tax contributions")
        self.line_chart.set_data(p["rows"])

        insights = generate_insights(self.profile, s, p, self.current_scenarios)
        self._set_text(self.insights_text, "\n\n".join(f"• {x}" for x in insights))
        tax_lines = [
            f"Gross income: {format_currency(self.profile.gross_income)}",
            f"Federal income tax: {format_currency(float(s['federal_income_tax']))}",
            f"Payroll tax: {format_currency(float(s['payroll_tax']))}",
            f"State income tax: {format_currency(float(s['state_income_tax']))}",
            f"Local income tax: {format_currency(float(s['local_income_tax']))}",
            f"Total estimated tax: {format_currency(float(s['total_tax']))}",
            f"Effective tax rate: {format_percent(float(s['effective_tax_rate']))}",
            "",
            str(s["state_tax_label"]),
            str(s["local_tax_label"]),
        ]
        self._set_text(self.tax_text, "\n".join(tax_lines))

    def update_scenarios(self):
        for widget in self.scenario_table.winfo_children():
            widget.destroy()
        self.bar_chart.set_data(self.current_scenarios)
        headers = ["Scenario", "FI age", "Years to FI", "Final portfolio"]
        for col, h in enumerate(headers):
            ttk.Label(self.scenario_table, text=h, style="Card.TLabel", font=(FONT, 11, "bold")).grid(row=0, column=col, sticky="w", padx=8, pady=(0, 8))
            self.scenario_table.columnconfigure(col, weight=1)
        for r, item in enumerate(self.current_scenarios, start=1):
            fi_age = "Not reached" if item["fi_age"] is None else f"{float(item['fi_age']):.1f}"
            years = "—" if item["years_to_fi"] is None else f"{float(item['years_to_fi']):.1f}"
            final = format_currency(float(item["final_portfolio"]))
            values = [item["name"], fi_age, years, final]
            for c, value in enumerate(values):
                ttk.Label(self.scenario_table, text=value, style="Card.TLabel").grid(row=r, column=c, sticky="w", padx=8, pady=6)

    def _set_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def save_profile(self):
        try:
            self.recalculate(show_errors=False)
            APP_DIR.mkdir(parents=True, exist_ok=True)
            PROFILE_PATH.write_text(json.dumps(asdict(self.profile), indent=2), encoding="utf-8")
            messagebox.showinfo("Saved", f"Profile saved to {PROFILE_PATH}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def load_profile(self) -> Profile:
        try:
            if PROFILE_PATH.exists():
                data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
                valid = {f.name for f in fields(Profile)}
                clean = {k: v for k, v in data.items() if k in valid}
                return Profile(**clean)
        except Exception:
            pass
        return Profile()

    def load_sample(self):
        self.profile = Profile()
        for key, var in self.vars.items():
            val = getattr(self.profile, key)
            if key in {"debt_interest_rate", "expected_return", "expense_growth", "income_growth", "withdrawal_rate"}:
                val = val * 100
            var.set(str(val))
        self._refresh_city_values()
        self.recalculate()

    def reset_saved_profile(self):
        try:
            if PROFILE_PATH.exists():
                PROFILE_PATH.unlink()
            messagebox.showinfo("Reset", "Saved profile removed. Load sample to repopulate defaults.")
        except Exception as e:
            messagebox.showerror("Reset error", str(e))

    def export_projection_csv(self):
        self.recalculate(show_errors=False)
        if not self.current_projection:
            messagebox.showwarning("Nothing to export", "Run a projection first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="escape_velocity_projection.csv",
        )
        if not path:
            return
        try:
            rows = self.current_projection["rows"]
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            messagebox.showinfo("Exported", f"Projection exported to {path}")
        except Exception as e:
            messagebox.showerror("Export error", str(e))


def main():
    root = tk.Tk()
    try:
        if sys.platform == "darwin":
            root.tk.call("tk", "scaling", 1.25)
        else:
            root.tk.call("tk", "scaling", 1.15)
    except Exception:
        pass
    app = EscapeVelocityApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
