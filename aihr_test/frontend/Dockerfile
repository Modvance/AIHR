# AI 面试应用 - 前端 Dockerfile（开发模式，支持热重载）
FROM node:20-alpine

WORKDIR /app

# 复制依赖文件
COPY package.json .

# 安装依赖
RUN npm install

# 暴露端口
EXPOSE 5173

# 启动命令（开发模式，支持 HMR）
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
