# Start with the official MLflow image
FROM ghcr.io/mlflow/mlflow:v2.10.2

# Install the PostgreSQL database adapter
RUN pip install psycopg2-binary