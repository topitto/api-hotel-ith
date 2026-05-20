# Usar una imagen oficial de Python ligera
FROM python:3.11-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de dependencias y ejecutarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código (main.py y hotel_ith.db si existe)
COPY . .

# Exponer el puerto que usará Render
EXPOSE 8000

# Comando para ejecutar la API. Render inyecta la variable $PORT automáticamente.
CMD ["sh", "-c", "uvicorn Main:app --host 0.0.0.0 --port ${PORT:-8000}"]