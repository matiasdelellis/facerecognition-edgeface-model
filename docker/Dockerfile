# Stage 1: download the weights and export EdgeFace to ONNX (needs torch, not shipped).
FROM python:3.12-slim-bookworm AS models

RUN apt-get update -yq \
    && apt-get install -yq --no-install-recommends ca-certificates git unzip wget \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 torchvision==0.20.1 \
    && pip install --no-cache-dir numpy==1.26.4 timm==1.0.11 onnx==1.17.0 onnxruntime==1.20.1

COPY docker/download.sh docker/export_edgeface.py /build/
RUN /build/download.sh /models \
    && git clone -q https://github.com/otroshi/edgeface /build/edgeface \
    && git -C /build/edgeface checkout -q ce86851cfc37979a9cd2558598d0e9bc592cbba3 \
    && python /build/export_edgeface.py /build/edgeface /models/edgeface_base.pt /models/edgeface_base.onnx \
    && rm /models/edgeface_base.pt

# Stage 2: the service, with onnxruntime and OpenCV only.
FROM python:3.12-slim-bookworm

RUN pip install --no-cache-dir flask==3.1.0 gunicorn==23.0.0 numpy==1.26.4 \
      opencv-python-headless==4.10.0.84 onnxruntime==1.20.1

COPY --from=models /models/ /app/models/
COPY app/ /app/app/

WORKDIR /app/

EXPOSE 5000

ARG GUNICORN_WORKERS="1" \
    PORT="5000"
ENV GUNICORN_WORKERS="${GUNICORN_WORKERS}"\
    PORT="${PORT}"\
    API_KEY=some-super-secret-api-key\
    DETECTOR=scrfd_500m\
    MODEL_THREADS=1

ENTRYPOINT ["gunicorn", "-c", "app/gunicorn.py", "app.server:app"]
