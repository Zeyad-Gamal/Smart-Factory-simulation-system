# docker run -d --name scada-mysql -e MYSQL_ROOT_PASSWORD=Root@123 -e MYSQL_DATABASE=scada_db -p 3306:3306 mysql:8.0

FROM mysql:8.0

COPY /init/scada_system.sql /docker-entrypoint-initdb.d/


# COPY scada_system.sql /docker-entrypoint-initdb.d/scada_system.sql