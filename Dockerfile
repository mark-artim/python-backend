FROM python:3.11

# This sets your working directory inside the container to where main.py is copied
WORKDIR /app/backend

# Copy backend source into /app/backend
COPY ./backend /app/backend

# Copy the requirements file to the outer /app folder (not required to be in /backend)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE 8000

# 🚨 Use -u (unbuffered) and make sure it runs YOUR main.py
CMD ["python", "-u", "main.py"]
