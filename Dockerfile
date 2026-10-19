FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /sivad

COPY requirements.txt .
#Intalador de dependencias del proyecto

RUN pip install --no-cache-dir -r requirements.txt

#Copiar el codigo de la aplicacion
COPY app ./app

#Usuario sin privilegios de administrador
RUN useradd --create-home sivad
USER sivad

#Puerto donde se escucha la API
EXPOSE 8000

#El comando de arranque del servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

