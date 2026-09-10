import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models, schemas
from app.amortization import add_period, apply_extraordinary_amortization, generate_schedule


class AmortizationError(ValueError):
    """Raised when an extraordinary amortization request is not applicable."""


def _loan_query():
    # populate_existing forces relationships to be reloaded from the DB even
    # when the Loan is already in the session's identity map — required
    # after apply_amortization's bulk delete/insert of installments, which
    # bypasses the ORM's normal collection-tracking.
    return (
        select(models.Loan)
        .options(selectinload(models.Loan.installments), selectinload(models.Loan.amortizations))
        .execution_options(populate_existing=True)
    )


async def create_loan(db: AsyncSession, payload: schemas.LoanCreate) -> models.Loan:
    start = payload.start_date or date.today()
    rows = generate_schedule(
        principal=payload.principal,
        annual_rate=payload.annual_rate,
        frequency=payload.frequency,
        num_installments=payload.num_installments,
        start_date=start,
    )

    loan = models.Loan(
        name=payload.name,
        principal=payload.principal,
        annual_rate=payload.annual_rate,
        rate_type=payload.rate_type,
        frequency=payload.frequency,
        num_installments=payload.num_installments,
        start_date=start,
        installments=[
            models.Installment(
                number=row.number,
                due_date=row.due_date,
                initial_balance=row.initial_balance,
                interest_amount=row.interest_amount,
                amortization_amount=row.amortization_amount,
                payment_amount=row.payment_amount,
                final_balance=row.final_balance,
            )
            for row in rows
        ],
    )
    db.add(loan)
    await db.commit()
    return await get_loan(db, loan.id)


async def list_loans(db: AsyncSession) -> list[models.Loan]:
    result = await db.execute(select(models.Loan).order_by(models.Loan.created_at.desc()))
    return list(result.scalars().all())


async def get_loan(db: AsyncSession, loan_id: uuid.UUID) -> models.Loan | None:
    result = await db.execute(_loan_query().where(models.Loan.id == loan_id))
    return result.scalars().first()


async def delete_loan(db: AsyncSession, loan: models.Loan) -> None:
    await db.delete(loan)
    await db.commit()


def loan_totals(loan: models.Loan) -> tuple[Decimal, Decimal]:
    total_interest = sum((Decimal(i.interest_amount) for i in loan.installments), Decimal("0"))
    total_paid = sum((Decimal(i.payment_amount) for i in loan.installments), Decimal("0"))
    return total_interest, total_paid


async def apply_amortization(
    db: AsyncSession, loan: models.Loan, payload: schemas.AmortizationCreate
) -> models.Loan:
    target = next((i for i in loan.installments if i.number == payload.installment_number), None)
    if target is None:
        raise AmortizationError(f"La cuota {payload.installment_number} no existe en este préstamo.")
    if Decimal(target.final_balance) <= 0:
        raise AmortizationError("Esa cuota ya cancela el préstamo; no queda saldo para amortizar.")
    if payload.amount >= Decimal(target.final_balance):
        raise AmortizationError(
            "El monto a amortizar debe ser menor al saldo pendiente después de esa cuota."
        )

    next_due = add_period(target.due_date, loan.frequency, 1)
    new_rows = apply_extraordinary_amortization(
        balance_before_extra=Decimal(target.final_balance),
        extra_amount=payload.amount,
        annual_rate=Decimal(loan.annual_rate),
        frequency=loan.frequency,
        original_payment=Decimal(target.payment_amount),
        start_date_next=next_due,
        first_number=target.number + 1,
    )

    await db.execute(
        delete(models.Installment).where(
            models.Installment.loan_id == loan.id, models.Installment.number > target.number
        )
    )
    for row in new_rows:
        db.add(
            models.Installment(
                loan_id=loan.id,
                number=row.number,
                due_date=row.due_date,
                initial_balance=row.initial_balance,
                interest_amount=row.interest_amount,
                amortization_amount=row.amortization_amount,
                payment_amount=row.payment_amount,
                final_balance=row.final_balance,
            )
        )
    loan.num_installments = target.number + len(new_rows)
    db.add(models.Amortization(loan_id=loan.id, installment_number=target.number, amount=payload.amount))

    await db.commit()
    return await get_loan(db, loan.id)
