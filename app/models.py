import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RateType(str, enum.Enum):
    TEA = "TEA"
    TCEA = "TCEA"


class Frequency(str, enum.Enum):
    MENSUAL = "MENSUAL"
    QUINCENAL = "QUINCENAL"
    BIMESTRAL = "BIMESTRAL"
    TRIMESTRAL = "TRIMESTRAL"
    CUATRIMESTRAL = "CUATRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    ANUAL = "ANUAL"


# Number of payment periods per year for each frequency, used to convert the
# annual effective rate (TEA/TCEA) entered by the user into a periodic rate.
PERIODS_PER_YEAR: dict[Frequency, int] = {
    Frequency.MENSUAL: 12,
    Frequency.QUINCENAL: 24,
    Frequency.BIMESTRAL: 6,
    Frequency.TRIMESTRAL: 4,
    Frequency.CUATRIMESTRAL: 3,
    Frequency.SEMESTRAL: 2,
    Frequency.ANUAL: 1,
}


class InstallmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), default="Préstamo")
    principal: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    annual_rate: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    rate_type: Mapped[RateType] = mapped_column(Enum(RateType, name="rate_type"), nullable=False)
    frequency: Mapped[Frequency] = mapped_column(Enum(Frequency, name="frequency"), nullable=False)
    num_installments: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    installments: Mapped[list["Installment"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="Installment.number"
    )
    amortizations: Mapped[list["Amortization"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="Amortization.applied_at"
    )


class Installment(Base):
    __tablename__ = "installments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    interest_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    amortization_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    payment_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    final_balance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[InstallmentStatus] = mapped_column(
        Enum(InstallmentStatus, name="installment_status"), default=InstallmentStatus.PENDING
    )

    loan: Mapped["Loan"] = relationship(back_populates="installments")


class Amortization(Base):
    """An extraordinary extra payment to principal applied after a given installment."""

    __tablename__ = "amortizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    loan: Mapped["Loan"] = relationship(back_populates="amortizations")
