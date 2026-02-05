# AI 面试应用 - 后端 Dockerfile（开发模式，支持热重载）
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（包括 CA 证书用于 SSL 连接）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# SSL 证书路径
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# 暴露端口
EXPOSE 8000

# 启动命令（热重载模式）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
