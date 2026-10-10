FROM nginx:1.27-alpine

# Copy built production assets
COPY dist /usr/share/nginx/html

# Copy nginx config that proxies /api to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
