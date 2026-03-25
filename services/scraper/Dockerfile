FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY . .
EXPOSE 18797
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "18797"]