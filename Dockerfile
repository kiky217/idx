FROM python:3.12-slim
WORKDIR /app

# Keeps python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py indodax_signal.py executor.py risk.py scalper.py pnl.py telegram.py ./

EXPOSE 5000

CMD ["gunicorn","-w","1","-b","0.0.0.0:8925","--timeout","30","app:app"]
