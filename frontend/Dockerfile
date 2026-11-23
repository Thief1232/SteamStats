FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Local development: Vite dev server, code is bind-mounted by docker-compose.override.yml.
FROM deps AS dev
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM deps AS build
# Baked into the bundle at build time; empty means "use local fixtures".
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY . .
RUN npm run build

# Server: static files only, no Node at runtime.
FROM caddy:2.10-alpine AS prod
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
