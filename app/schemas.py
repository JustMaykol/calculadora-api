import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import Frequency, InstallmentStatus, RateType


class LoanCreate(BaseModel):
    name: str = Field(default="Préstamo", max_length=150)
    principal: Decimal = Field(gt=0, description="Monto del préstamo")
    annual_rate: Decimal = Field(gt=0, lt=10, description="TEA o TCEA como fracción, p. ej. 0.18 para 18%")
    rate_type: RateType = RateType.TEA
    frequency: Frequency = Frequency.MENSUAL
    num_installments: int = Field(gt=0, le=600, description="Número de cuotas")
    start_date: date | None = Field(default=None, description="Fecha del primer pago; hoy si se omite")


class InstallmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    due_date: date
    initial_balance: Decimal
    interest_amount: Decimal
    amortization_amount: Decimal
    payment_amount: Decimal
    final_balance: Decimal
    status: InstallmentStatus


class AmortizationCreate(BaseModel):
    installment_number: int = Field(gt=0, description="Cuota tras la cual se aplica el abono extra")
    amount: Decimal = Field(gt=0, description="Monto extra a capital")


class AmortizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    installment_number: int
    amount: Decimal
    applied_at: datetime


class LoanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    principal: Decimal
    annual_rate: Decimal
    rate_type: RateType
    frequency: Frequency
    num_installments: int
    start_date: date
    created_at: datetime


class LoanDetail(LoanSummary):
    installments: list[InstallmentOut]
    amortizations: list[AmortizationOut]
    total_interest: Decimal
    total_paid: Decimal
