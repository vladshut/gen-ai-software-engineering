"""Frozen contracts: currencies, fraud weights, FX rates, fee config.

Everything in this module is decided ONCE (see HW6 build plan -> "Frozen
contracts") and imported everywhere else so the rules live in a single place.
"""

from __future__ import annotations

from decimal import Decimal

# --- ISO-4217 accepted set (MVP) ---------------------------------------------
# Anything outside this set (e.g. "XYZ") is rejected by the validator.
ACCEPTED_CURRENCIES: frozenset[str] = frozenset(
    {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "PLN", "UAH"}
)

# --- Amount rule -------------------------------------------------------------
MAX_DECIMAL_PLACES = 2
# One toggle: when False, amount must be strictly > 0 (refunds via negative
# amounts are rejected). Flip to True to accept negative amounts.
ALLOW_NEGATIVE_FOR_REFUND = False

# --- Fraud scoring (additive) ------------------------------------------------
# Thresholds
HIGH_VALUE_THRESHOLD = Decimal("10000")
VERY_HIGH_VALUE_THRESHOLD = Decimal("50000")
STRUCTURING_LOW = Decimal("9800")
STRUCTURING_HIGH = Decimal("10000")  # exclusive upper bound
UNUSUAL_HOUR_START = 0  # inclusive, UTC
UNUSUAL_HOUR_END = 5  # exclusive, UTC  -> [00:00, 05:00)
DOMESTIC_COUNTRY = "US"
HIGH_RISK_TYPE = "wire_transfer"

# Points
POINTS_HIGH_VALUE = 40
POINTS_VERY_HIGH_VALUE = 20  # additional, on top of high value
POINTS_STRUCTURING = 50
POINTS_UNUSUAL_TIMING = 20
POINTS_CROSS_BORDER = 15
POINTS_HIGH_RISK_RAIL = 10

# Decision bands
FLAGGED_THRESHOLD = 50  # >= 50  -> flagged_review
REVIEW_THRESHOLD = 25  # 25..49 -> review ; < 25 -> approved

# --- Settlement: static FX rates to USD base ---------------------------------
# Documented, static rates (1 unit of currency -> this many USD). USD is 1:1.
FX_RATES_TO_USD: dict[str, Decimal] = {
    "USD": Decimal("1.00"),
    "EUR": Decimal("1.08"),
    "GBP": Decimal("1.27"),
    "JPY": Decimal("0.0067"),
    "CHF": Decimal("1.12"),
    "CAD": Decimal("0.74"),
    "AUD": Decimal("0.66"),
    "PLN": Decimal("0.25"),
    "UAH": Decimal("0.024"),
}

# Settlement fee: 0.1% of the USD-converted amount, min $0.01.
SETTLEMENT_FEE_RATE = Decimal("0.001")
MIN_SETTLEMENT_FEE = Decimal("0.01")

# --- Statuses ----------------------------------------------------------------
STATUS_APPROVED = "approved"
STATUS_REVIEW = "review"
STATUS_FLAGGED = "flagged_review"
STATUS_REJECTED = "rejected"
STATUS_SETTLED = "settled"
STATUS_HELD = "held"

# --- Compliance: sanctions + restricted jurisdictions -------------------------
SANCTIONED_ACCOUNTS: frozenset[str] = frozenset({"ACC-9999"})
RESTRICTED_COUNTRIES: frozenset[str] = frozenset({"KP", "IR", "SY"})

# --- Agent names (used in the message envelope) ------------------------------
AGENT_VALIDATOR = "transaction_validator"
AGENT_FRAUD = "fraud_detector"
AGENT_COMPLIANCE = "compliance_checker"
AGENT_SETTLEMENT = "settlement_processor"
AGENT_INTEGRATOR = "integrator"
