docker run -d \
    --name my-mariadb \
    -e MYSQL_ROOT_PASSWORD=root_password \
    -e MYSQL_DATABASE=database \
    -e MYSQL_USER=username \
    -e MYSQL_PASSWORD=password \
    -p 3306:3306 \
    mariadb:latest