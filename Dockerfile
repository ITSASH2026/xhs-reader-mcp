# Build public upstream from a pinned commit; no local deployment files are copied.
FROM python:3.12-bookworm AS builder
ARG XHS_COMMIT=2ab2620b0dd35b04530e70f1e9c7ab3f78c5d6c5
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /upstream
RUN git init && git remote add origin https://github.com/JoeanAmier/XHS-Downloader.git \
    && git fetch --depth 1 origin "$XHS_COMMIT" && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "$XHS_COMMIT"
COPY requirements-addon.txt /build/requirements-addon.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt -r /build/requirements-addon.txt

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --from=builder /upstream/source /app/source
COPY --from=builder /upstream/locale /app/locale
COPY --from=builder /upstream/static /app/static
COPY --from=builder /upstream/main.py /app/main.py
COPY --from=builder /upstream/LICENSE /app/LICENSE.upstream
COPY LICENSE NOTICE.md /app/
COPY app/*.py /app/
RUN python /app/patch_upstream.py && python /app/fetch_model.py \
    && groupadd -g 1000 reader && useradd -u 1000 -g 1000 -M reader \
    && mkdir -p /app/Volume && chown -R 1000:1000 /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/app/Volume \
    HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1
USER 1000:1000
EXPOSE 5556
CMD ["python", "ephemeral.py"]
