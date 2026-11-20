FROM node:22-alpine AS deps
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci

FROM deps AS build
COPY web/ ./
ARG API_PROXY_URL=http://api:8000
ENV API_PROXY_URL=$API_PROXY_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app/web/.next/standalone ./
COPY --from=build /app/web/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
