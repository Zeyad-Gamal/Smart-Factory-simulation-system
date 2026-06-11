# Build Stage
FROM node:22-alpine AS builder

WORKDIR /app

# انسخ كل مشروع الفرونت
COPY Full-SCADA-system/ ./

# تثبيت dependencies
RUN npm ci

# بناء المشروع بعد توفر كل الملفات (index.html + src)
RUN npm run build


# Runtime Stage
FROM nginx:alpine

# إعداد nginx
COPY docker/scada-frontend/nginx.conf /etc/nginx/conf.d/default.conf

# نسخ ملفات البناء النهائية
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]