# calculadora-api

API de una **calculadora de préstamos** con el **sistema francés** (cuota fija). Genera el cronograma de pagos a partir del monto, la tasa (TEA o TCEA), la frecuencia y el número de cuotas, y recalcula el cronograma cuando se hace una **amortización extraordinaria** (abono a capital).

Frontend: [calculadora-web](https://github.com/JustMaykol/calculadora-web) · 🌐 https://calculadora-web-orcin.vercel.app

## Stack

- Python 3.12 · FastAPI · Pydantic
- SQLAlchemy 2.0 (async) + asyncpg · Alembic
- PostgreSQL en [Neon](https://neon.tech)
- Despliegue en Render

## Modelo financiero

| Concepto | Fórmula |
|---|---|
| Tasa periódica | `i = (1 + TEA)^(1/m) − 1`, con `m` periodos por año |
| Cuota fija | `cuota = P · i / (1 − (1 + i)^−n)` |
| Plazo tras un abono | `n' = −ln(1 − saldo · i / cuota) / ln(1 + i)` |

- **Frecuencias**: mensual (12), quincenal (24), bimestral (6), trimestral (4), cuatrimestral (3), semestral (2) y anual (1).
- **Amortización extraordinaria**: la cuota se mantiene y el **plazo se reduce** (estrategia "reducir plazo").
- **Redondeo**: montos a 2 decimales; la última cuota absorbe la diferencia para que el saldo termine exactamente en cero.

### Ejemplo

Préstamo de **10 000** al **12 % TEA**, **12 cuotas mensuales**:

- Tasa mensual: 0.9489 %
- Cuota fija: **885.62**
- Interés total: 627.44

Con un abono extra de **3 000** después de la cuota 3, el plazo restante baja de 9 a **6 cuotas** y el interés restante de 365.36 a **140.82**.

La implementación está en [`app/amortization.py`](app/amortization.py).

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/loans` | Crea un préstamo y genera su cronograma |
| `GET` | `/loans` | Lista los préstamos |
| `GET` | `/loans/{id}` | Detalle con cronograma y amortizaciones |
| `PUT` | `/loans/{id}` | Edita las condiciones y regenera el cronograma (descarta las amortizaciones previas) |
| `DELETE` | `/loans/{id}` | Elimina un préstamo |
| `POST` | `/loans/{id}/amortizations` | Aplica un abono a capital después de una cuota y recalcula el resto |

Documentación interactiva en `/docs`.

## Configuración

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Cadena de conexión de Neon tal cual la entrega su panel. La app la adapta para asyncpg (`app/db_url.py`) y Alembic para psycopg2 |
| `CORS_ORIGINS` | Orígenes permitidos, separados por coma (por defecto `http://localhost:4321`) |

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # configura DATABASE_URL

alembic upgrade head
uvicorn app.main:app --reload   # http://localhost:8000
```

## Despliegue en Render

El repo incluye un Blueprint (`render.yaml`):

1. Crea el servicio en Render desde este repositorio.
2. Configura `DATABASE_URL` y `CORS_ORIGINS` (con la URL del frontend en Vercel).
3. El build ejecuta `alembic upgrade head` antes de levantar la API.

## Estructura

```
app/
├── main.py            # FastAPI + CORS
├── amortization.py    # motor financiero (sistema francés)
├── crud.py            # préstamos, cronogramas y amortizaciones
├── routers/loans.py   # endpoints
├── models.py          # Loan, Installment, Amortization
├── schemas.py
├── database.py        # engine async
└── db_url.py          # adapta la URL de Neon a cada driver
alembic/               # migraciones
```
