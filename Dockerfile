# SentinelX container - used for the free Hugging Face Spaces demo, works on any Docker host
FROM python:3.11-slim

# OpenCV runtime libraries
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs containers as uid 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860
WORKDIR $HOME/app

# CPU-only torch keeps the image ~2 GB smaller than the default CUDA build
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 7860
# One process only: the detector owns the camera, so never run multiple workers
CMD ["sh", "-c", "waitress-serve --threads=16 --listen=0.0.0.0:${PORT} app:app"]
