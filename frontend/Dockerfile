# ─── Build Stage ─────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# ─── Runtime Stage ───────────────────────────────────────────
FROM node:22-alpine

ENV NODE_ENV=production
WORKDIR /app

# Copia apenas o build e as deps de produção
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./
RUN npm install --omit=dev 2>/dev/null; exit 0

# Porta padrão do adapter-node
EXPOSE 3000

# Variáveis configuráveis em runtime
ENV HOST=0.0.0.0
ENV PORT=3000
ENV ORIGIN=http://localhost:3000

CMD ["node", "build"]
