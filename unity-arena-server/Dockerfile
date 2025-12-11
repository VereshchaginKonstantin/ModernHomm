FROM nginx:alpine

# Копируем конфигурацию nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Создаём директорию для WebGL билда
RUN mkdir -p /usr/share/nginx/html/unityArena

# Копируем плейсхолдер страницу (будет заменена реальным билдом)
COPY placeholder.html /usr/share/nginx/html/unityArena/index.html

# Устанавливаем права на чтение для nginx
RUN chmod -R 755 /usr/share/nginx/html/unityArena

# Порт
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
