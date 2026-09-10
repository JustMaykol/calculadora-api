# Calculadora de Intereses — API (calculadora-api)

API en **FastAPI** + **SQLAlchemy (async)** sobre **Postgres (Neon)**. Calcula cronogramas de pago por el sistema francés (cuota fija) a partir de monto, TEA/TCEA, frecuencia y número de cuotas, y permite aplicar amortizaciones extraordinarias (abonos a capital) que reducen el plazo restante.

Repo hermano del frontend: [calculadora-web](https://github.com/JustMaykol/calculadora-web).

## Requisitos

- Python 3.12+
- Una base de datos Postgres (recomendado: [Neon](https://neon.tech), tiene plan gratuito)

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edita .env con tu DATABASE_URL de Neon

alembic upgrade head
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000`. Documentación interactiva en `http://localhost:8000/docs`.

## Modelo financiero

- **Tasa periódica**: la TEA/TCEA (anual efectiva) se convierte a tasa efectiva por periodo según la frecuencia: `i = (1 + TEA)^(1/m) - 1`, donde `m` es el número de periodos por año (12 mensual, 24 quincenal, 6 bimestral, 4 trimestral, 3 cuatrimestral, 2 semestral, 1 anual).
- **Cuota fija (sistema francés)**: `cuota = P * i / (1 - (1+i)^-n)`.
- **Amortización extraordinaria**: al abonar un extra a capital después de una cuota específica, la cuota fija **se mantiene igual** y el plazo restante se recalcula y se acorta (estrategia "reducir plazo"). La última cuota del nuevo cronograma absorbe cualquier diferencia de redondeo para que el saldo llegue exactamente a cero.

Ver `app/amortization.py` para la implementación.

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/loans` | Crea un préstamo y genera su cronograma completo |
| GET | `/loans` | Lista los préstamos guardados |
| GET | `/loans/{id}` | Detalle de un préstamo con su cronograma y amortizaciones |
| POST | `/loans/{id}/amortizations` | Aplica un abono extra a capital tras una cuota y recalcula el resto |
| DELETE | `/loans/{id}` | Elimina un préstamo |

## Despliegue en Render

Este repo incluye `render.yaml` (Blueprint). Al crear el servicio en Render:

1. Conecta el repositorio y selecciona la carpeta `backend/` como raíz del servicio.
2. Configura la variable de entorno `DATABASE_URL` con la cadena de conexión de Neon (usa el driver `postgresql+asyncpg://...`).
3. Configura `CORS_ORIGINS` con la URL de tu frontend en Vercel.
4. El build ejecuta `alembic upgrade head` automáticamente antes de levantar el servicio.
