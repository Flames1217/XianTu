FROM node:22-alpine AS frontend

WORKDIR /build
COPY package*.json ./
RUN npm ci
COPY . .
ARG BACKEND_BASE_URL=""
ENV BACKEND_BASE_URL=${BACKEND_BASE_URL}
RUN npm run type-check && npm run build

FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash nginx tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

COPY server /app/server
COPY --from=frontend /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data /run/nginx

ENV PYTHONUNBUFFERED=1
ENV DDCT_DB_URL=sqlite:///data/xiantu.sqlite3

EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/local/bin/docker-entrypoint.sh"]
