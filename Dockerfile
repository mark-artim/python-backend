FROM python:3.11

WORKDIR /app/backend
COPY ./backend /app/backend
COPY requirements.txt /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8000

CMD ["python", "-u", "main.py"]
