#!/bin/bash
echo "Iniciando build da aplicação Java..."
cd backend
mvn clean package -DskipTests
echo "Build concluído!"
