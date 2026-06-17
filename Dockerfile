# Custom Airflow image with the ETL's runtime dependencies baked in.
# Building deps into the image (instead of installing them at container start
# via _PIP_ADDITIONAL_REQUIREMENTS) makes startup fast and builds reproducible.
FROM apache/airflow:3.2.2

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
