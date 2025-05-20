FROM python:3.11-alpine

WORKDIR /app

COPY api.py /app/
COPY requirements.txt /app/
#COPY .env app/
#COPY templates/ /app/templates/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "api.py"]
