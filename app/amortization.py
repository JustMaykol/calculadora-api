"""Financial engine: French (fixed-payment) amortization system.

The user enters an annual effective rate (TEA or TCEA) and a payment
frequency. Both rate types are treated as an annual effective rate for the
purpose of period-rate conversion and schedule generation; TCEA additionally
implies all costs are already folded into the rate, which is a labeling
concern handled at the API layer, not a different formula here.
"""

import calendar
import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from app.models import PERIODS_PER_YEAR, Frequency

CENTS = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def periodic_rate(annual_rate: Decimal, frequency: Frequency) -> Decimal:
    """Convert an annual effective rate into an effective periodic rate."""
    m = PERIODS_PER_YEAR[frequency]
    base = Decimal(1) + annual_rate
    periodic = base ** (Decimal(1) / Decimal(m)) - Decimal(1)
    return periodic


def fixed_payment(principal: Decimal, rate: Decimal, num_periods: int) -> Decimal:
    """Cuota fija del sistema francés: P * i / (1 - (1+i)^-n)."""
    if rate == 0:
        return principal / Decimal(num_periods)
    factor = Decimal(1) - (Decimal(1) + rate) ** Decimal(-num_periods)
    return principal * rate / factor


def add_period(d: date, frequency: Frequency, count: int = 1) -> date:
    if frequency == Frequency.QUINCENAL:
        return d + timedelta(days=15 * count)
    months_map = {
        Frequency.MENSUAL: 1,
        Frequency.BIMESTRAL: 2,
        Frequency.TRIMESTRAL: 3,
        Frequency.CUATRIMESTRAL: 4,
        Frequency.SEMESTRAL: 6,
        Frequency.ANUAL: 12,
    }
    months = months_map[frequency] * count
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@dataclass
class InstallmentRow:
    number: int
    due_date: date
    initial_balance: Decimal
    interest_amount: Decimal
    amortization_amount: Decimal
    payment_amount: Decimal
    final_balance: Decimal


def _build_rows(
    balance: Decimal,
    rate: Decimal,
    payment: Decimal,
    num_installments: int,
    start_date: date,
    frequency: Frequency,
    first_number: int,
) -> list[InstallmentRow]:
    """Amortize `balance` over `num_installments` periods at a fixed `payment`.

    The last installment absorbs any rounding remainder so the final balance
    always reaches exactly zero.
    """
    rows: list[InstallmentRow] = []
    remaining = balance
    for i in range(num_installments):
        number = first_number + i
        due = add_period(start_date, frequency, number - first_number + 1)
        interest = _round(remaining * rate)
        is_last = i == num_installments - 1
        if is_last:
            capital = remaining
            cuota = _round(interest + capital)
        else:
            capital = _round(payment - interest)
            cuota = payment
        final_balance = _round(remaining - capital)
        rows.append(
            InstallmentRow(
                number=number,
                due_date=due,
                initial_balance=_round(remaining),
                interest_amount=interest,
                amortization_amount=capital,
                payment_amount=cuota,
                final_balance=final_balance if not is_last else Decimal("0.00"),
            )
        )
        remaining = final_balance
    return rows


def generate_schedule(
    principal: Decimal,
    annual_rate: Decimal,
    frequency: Frequency,
    num_installments: int,
    start_date: date,
) -> list[InstallmentRow]:
    """Generate a full French-system schedule for a brand-new loan."""
    rate = periodic_rate(annual_rate, frequency)
    payment = _round(fixed_payment(principal, rate, num_installments))
    return _build_rows(principal, rate, payment, num_installments, start_date, frequency, first_number=1)


def apply_extraordinary_amortization(
    balance_before_extra: Decimal,
    extra_amount: Decimal,
    annual_rate: Decimal,
    frequency: Frequency,
    original_payment: Decimal,
    start_date_next: date,
    first_number: int,
) -> list[InstallmentRow]:
    """Apply an extra payment to principal and rebuild the remaining schedule.

    Strategy: "reducir plazo" — the fixed payment amount stays the same as
    before the amortization, but fewer installments are needed to cancel the
    reduced balance. The number of remaining periods is derived analytically
    and then the schedule is rebuilt period by period (the last one absorbs
    any rounding remainder).
    """
    rate = periodic_rate(annual_rate, frequency)
    new_balance = balance_before_extra - extra_amount
    if new_balance <= 0:
        return []

    if rate == 0:
        remaining_periods = int((new_balance / original_payment).to_integral_value(rounding=ROUND_CEILING))
    else:
        # n' = -ln(1 - balance*i/payment) / ln(1+i)
        ratio = float(new_balance * rate / original_payment)
        if ratio >= 1:
            # The fixed payment can no longer cover interest on its own;
            # fall back to a single balloon installment.
            remaining_periods = 1
        else:
            n_float = -math.log(1 - ratio) / math.log(float(1 + rate))
            remaining_periods = max(1, math.ceil(round(n_float, 6)))

    return _build_rows(
        new_balance,
        rate,
        original_payment,
        remaining_periods,
        start_date_next,
        frequency,
        first_number=first_number,
    )
