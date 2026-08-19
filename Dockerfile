FROM mambaorg/micromamba:latest

USER root

RUN micromamba create -y -n app -c conda-forge \
    python=3.11 \
    gdal=3.13.2 \
    numpy=1.26.4 \
    pip \
    && micromamba clean --all --yes

ENV PATH=/opt/conda/envs/app/bin:$PATH

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]