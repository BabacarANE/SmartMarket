FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn sqlalchemy pg8000 mlflow joblib scikit-learn lightgbm xgboost pandas numpy

COPY api/ ./api/
COPY ml/ ./ml/

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
