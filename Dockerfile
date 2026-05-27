FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY course_checker.py settings.py ./

CMD ["python", "-u", "course_checker.py"]
