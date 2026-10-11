# Stage 1: Build production React application
FROM node:20-alpine AS builder
WORKDIR /app

# Copy dependency manifests and install dependencies
COPY package*.json ./
RUN npm ci

# Copy application source and build production bundle
COPY . .
RUN npm run build

# Stage 2: Serve compiled assets via Nginx with backend reverse proxy
FROM nginx:1.27-alpine

# Copy built production assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config that proxies /api requests to FastAPI backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
