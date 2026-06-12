FROM nginx:1.27-alpine

RUN apk add --no-cache openssl

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY nginx-bootstrap.sh /docker-entrypoint.d/99-bootstrap-cert.sh
RUN chmod +x /docker-entrypoint.d/99-bootstrap-cert.sh
