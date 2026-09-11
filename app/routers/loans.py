import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.database import get_db

router = APIRouter(prefix="/loans", tags=["loans"])


def _to_detail(loan: models.Loan) -> schemas.LoanDetail:
    total_interest, total_paid = crud.loan_totals(loan)
    return schemas.LoanDetail(
        **schemas.LoanSummary.model_validate(loan).model_dump(),
        installments=[schemas.InstallmentOut.model_validate(i) for i in loan.installments],
        amortizations=[schemas.AmortizationOut.model_validate(a) for a in loan.amortizations],
        total_interest=total_interest,
        total_paid=total_paid,
    )


async def _get_loan_or_404(loan_id: uuid.UUID, db: AsyncSession) -> models.Loan:
    loan = await crud.get_loan(db, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    return loan


@router.post("", response_model=schemas.LoanDetail, status_code=201)
async def create_loan(payload: schemas.LoanCreate, db: AsyncSession = Depends(get_db)):
    loan = await crud.create_loan(db, payload)
    return _to_detail(loan)


@router.get("", response_model=list[schemas.LoanSummary])
async def list_loans(db: AsyncSession = Depends(get_db)):
    loans = await crud.list_loans(db)
    return [schemas.LoanSummary.model_validate(loan) for loan in loans]


@router.get("/{loan_id}", response_model=schemas.LoanDetail)
async def get_loan(loan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    loan = await _get_loan_or_404(loan_id, db)
    return _to_detail(loan)


@router.put("/{loan_id}", response_model=schemas.LoanDetail)
async def update_loan(loan_id: uuid.UUID, payload: schemas.LoanUpdate, db: AsyncSession = Depends(get_db)):
    loan = await _get_loan_or_404(loan_id, db)
    loan = await crud.update_loan(db, loan, payload)
    return _to_detail(loan)


@router.delete("/{loan_id}", status_code=204)
async def delete_loan(loan_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    loan = await _get_loan_or_404(loan_id, db)
    await crud.delete_loan(db, loan)


@router.post("/{loan_id}/amortizations", response_model=schemas.LoanDetail)
async def amortize(loan_id: uuid.UUID, payload: schemas.AmortizationCreate, db: AsyncSession = Depends(get_db)):
    loan = await _get_loan_or_404(loan_id, db)
    try:
        loan = await crud.apply_amortization(db, loan, payload)
    except crud.AmortizationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_detail(loan)
