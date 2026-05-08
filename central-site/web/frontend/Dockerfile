# ---- Étape 1 : Installation des dépendances ----
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# ---- Étape 2 : Build de l'application ----
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG BACKEND_INTERNAL_URL=http://localhost:8000
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_APP_ENV="development"
ARG NEXT_PUBLIC_RECAPTCHA_SITE_KEY=""
ARG NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=""
ARG NEXT_PUBLIC_COGNITO_USER_POOL_ID=""
ARG NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=""
ARG NEXT_PUBLIC_AWS_REGION="eu-west-1"
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_APP_ENV=${NEXT_PUBLIC_APP_ENV}
ENV NEXT_PUBLIC_RECAPTCHA_SITE_KEY=${NEXT_PUBLIC_RECAPTCHA_SITE_KEY}
ENV NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY}
ENV NEXT_PUBLIC_COGNITO_USER_POOL_ID=${NEXT_PUBLIC_COGNITO_USER_POOL_ID}
ENV NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=${NEXT_PUBLIC_COGNITO_APP_CLIENT_ID}
ENV NEXT_PUBLIC_AWS_REGION=${NEXT_PUBLIC_AWS_REGION}
RUN npm run build

# ---- Étape 3 : Image de production ----
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copier uniquement les fichiers nécessaires à l'exécution
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
