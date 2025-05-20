FROM python:3.11-alpine

WORKDIR /app

COPY api.py requirements.txt auxillary_functions.py classes_db.py routes.py /app/
COPY templates/ /app/templates/
COPY test/ /app/test/


RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "api.py"]
