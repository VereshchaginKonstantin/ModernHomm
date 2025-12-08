# Настройка Nginx для ModernHomm

## Обзор

Nginx настроен как reverse proxy для админки ModernHomm. Он принимает HTTP запросы на порту 80 и проксирует их на Flask приложение (admin), работающее на порту 5000 внутри Docker сети.

## Архитектура

```
Клиент → nginx:80 (хост) → nginx контейнер → admin:5000 → Flask приложение
```

## Конфигурация

### Docker Compose

В `docker-compose.yml` настроены три основных сервиса:

1. **postgres** - База данных PostgreSQL
2. **admin** - Flask приложение (порт 5000 внутри сети)
3. **nginx** - Reverse proxy (порт 80 на хосте)

### Nginx конфигурация

Файл: `nginx/nginx.conf`

**Upstream:**
```nginx
upstream admin_backend {
    server admin:5000;
}
```

**Server blocks:**

1. **Для доменов modernhomm.ru и www.modernhomm.ru:**
   - Слушает на порту 80
   - Проксирует все запросы на `admin:5000`
   - Поддерживает WebSocket соединения

2. **Для IP адреса 130.49.176.128:**
   - Слушает на порту 80 (default_server)
   - Проксирует все запросы на `admin:5000`
   - Поддерживает WebSocket соединения

## Настройка DNS

Для работы с доменами необходимо настроить DNS записи:

```
modernhomm.ru       A    130.49.176.128
www.modernhomm.ru   A    130.49.176.128
```

## Запуск

### Первый запуск

```bash
# Остановить существующие контейнеры
docker compose down

# Собрать и запустить все контейнеры
docker compose up -d --build
```

### Проверка работоспособности

```bash
# Проверить статус контейнеров
docker compose ps

# Проверить логи nginx
docker compose logs nginx

# Проверить логи админки
docker compose logs admin

# Тест HTTP запроса
curl -I http://localhost/
```

Ожидаемый результат: HTTP 302 (редирект на страницу логина)

### Перезапуск nginx

```bash
# Только nginx
docker compose restart nginx

# Все сервисы
docker compose restart
```

## Доступ к админке

После запуска админка доступна по следующим адресам:

- http://modernhomm.ru (требуется настройка DNS)
- http://www.modernhomm.ru (требуется настройка DNS)
- http://130.49.176.128
- http://localhost (на сервере)

## SSL/TLS (HTTPS)

Для настройки HTTPS необходимо:

1. Получить SSL сертификаты (например, через Let's Encrypt)
2. Обновить `nginx/nginx.conf`:
   - Добавить `listen 443 ssl;`
   - Указать пути к сертификатам
   - Настроить редирект с HTTP на HTTPS

3. Обновить `docker-compose.yml`:
   - Добавить проброс порта `443:443`
   - Подключить сертификаты через volumes

Пример конфигурации для HTTPS будет добавлен позже.

## Отладка

### Проверка конфигурации nginx

```bash
# Внутри контейнера
docker compose exec nginx nginx -t

# Перезагрузка конфигурации без рестарта
docker compose exec nginx nginx -s reload
```

### Просмотр логов в реальном времени

```bash
# Все сервисы
docker compose logs -f

# Только nginx
docker compose logs -f nginx

# Только admin
docker compose logs -f admin
```

### Проверка сетевого соединения

```bash
# Проверка доступности admin из nginx контейнера
docker compose exec nginx wget -O- http://admin:5000/

# Проверка портов на хосте
netstat -tlnp | grep :80
```

## Безопасность

**Рекомендации:**

1. Использовать HTTPS в production
2. Настроить rate limiting в nginx
3. Добавить fail2ban для защиты от brute-force атак
4. Использовать production WSGI сервер (Gunicorn/uWSGI) вместо встроенного Flask сервера
5. Настроить firewall (UFW/iptables)

## Production рекомендации

Для production окружения рекомендуется:

1. **Заменить Flask dev server на Gunicorn:**
   ```bash
   # В Dockerfile.admin
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "admin_app:app"]
   ```

2. **Увеличить worker_connections в nginx:**
   ```nginx
   events {
       worker_connections 2048;
   }
   ```

3. **Добавить кеширование статики:**
   ```nginx
   location /static/ {
       expires 30d;
       add_header Cache-Control "public, immutable";
   }
   ```

4. **Настроить логирование:**
   ```nginx
   access_log /var/log/nginx/access.log combined;
   error_log /var/log/nginx/error.log warn;
   ```

## Troubleshooting

**Проблема:** nginx не может подключиться к admin

**Решение:**
```bash
# Проверить что контейнеры в одной сети
docker network inspect modernhomm_modernhomm_network

# Проверить что admin работает
docker compose exec admin wget -O- http://localhost:5000/
```

**Проблема:** Порт 80 уже занят

**Решение:**
```bash
# Найти процесс, занимающий порт
sudo lsof -i :80

# Остановить другой веб-сервер (например Apache)
sudo systemctl stop apache2
```

**Проблема:** 502 Bad Gateway

**Решение:**
- Проверить что admin контейнер запущен: `docker compose ps`
- Проверить логи admin: `docker compose logs admin`
- Проверить что admin слушает на 5000: `docker compose exec admin netstat -tlnp`
