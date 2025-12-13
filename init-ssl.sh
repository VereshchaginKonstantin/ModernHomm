#!/bin/bash
# Скрипт для получения SSL сертификата Let's Encrypt

DOMAIN="modernhomm.ru"
EMAIL="admin@modernhomm.ru"

# Создаём директории
mkdir -p certbot/conf certbot/www

# Останавливаем nginx если запущен
docker compose stop nginx 2>/dev/null

# Запускаем временный nginx для ACME challenge
docker run -d --name certbot_nginx -p 80:80 -v $(pwd)/certbot/www:/var/www/certbot nginx:alpine sh -c "mkdir -p /var/www/certbot/.well-known/acme-challenge && nginx -g 'daemon off;'"

sleep 3

# Получаем сертификат
docker run --rm -v $(pwd)/certbot/conf:/etc/letsencrypt -v $(pwd)/certbot/www:/var/www/certbot certbot/certbot certonly --webroot --webroot-path=/var/www/certbot --email $EMAIL --agree-tos --no-eff-email -d $DOMAIN -d www.$DOMAIN

# Останавливаем временный nginx
docker stop certbot_nginx && docker rm certbot_nginx

# Проверяем что сертификат создан
if [ -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo "SSL сертификат успешно получен!"
    echo "Теперь замените nginx/nginx.conf на nginx/nginx-ssl.conf"
    echo "И перезапустите: docker compose up -d nginx"
else
    echo "Ошибка получения сертификата"
    exit 1
fi
