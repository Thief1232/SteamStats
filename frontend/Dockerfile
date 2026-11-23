FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Local development: Vite dev server, code is bind-mounted by docker-compose.override.yml.
FROM deps AS dev
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM deps AS build
# No build-time settings: the bundle calls the API on its own origin.
COPY . .
RUN npm run build

# Server: static files only, no Node at runtime.
FROM caddy:2.10-alpine AS prod
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
