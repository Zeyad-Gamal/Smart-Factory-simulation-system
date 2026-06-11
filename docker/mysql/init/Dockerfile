# docker run -d --name scada-mysql -e MYSQL_ROOT_PASSWORD=Root@123 -e MYSQL_DATABASE=scada_db -p 3306:3306 mysql:8.0

FROM mysql:8.0

COPY scada_system.sql /init/scada_system.sql