FROM nginx:alpine

# Копируем конфигурацию nginx
COPY unity-arena-server/nginx.conf /etc/nginx/nginx.conf

# Создаём директорию для WebGL билда
RUN mkdir -p /usr/share/nginx/html/unityArena

# Копируем Unity WebGL билд
COPY unity-arena/arena/ /usr/share/nginx/html/unityArena/

# Устанавливаем права на чтение для nginx
RUN chmod -R 755 /usr/share/nginx/html/unityArena

# Порт
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
