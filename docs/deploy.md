# 云服务器部署指南

> 把「多 Agent 金融风控审查系统」部署到云服务器（公网可访问）。以 Ubuntu 22.04 为例。

## 一、准备云服务器

1. 购买云服务器（阿里云 ECS / 腾讯云 CVM / 华为云 ECS）
   - **系统**：Ubuntu 22.04 LTS
   - **配置**：2 核 2G 起步（够用，跑 LLM 调用不吃本地算力）
   - **带宽**：按量即可

2. **配置安全组**（控制台里设置，开放入方向端口）：
   | 端口 | 用途 |
   |---|---|
   | 22 | SSH 登录 |
   | 8000 | 应用（FastAPI 服务） |

## 二、SSH 登录

```bash
ssh root@<你的服务器公网IP>
```

## 三、安装依赖

```bash
# 1. 更新系统
apt update && apt upgrade -y

# 2. Python 3.11 + venv
apt install -y python3 python3-pip python3-venv

# 3. MySQL 8
apt install -y mysql-server
systemctl enable --now mysql

# 4. 中文字体（PDF 导出需要，没有会乱码）
apt install -y fonts-wqy-microhei

# 5. Node.js 18+（构建前端用）
apt install -y nodejs npm
# 若版本过低，用 nvm 装新版：
# curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
# nvm install 20
```

## 四、获取代码

```bash
git clone https://github.com/1user363/fin-risk-control.git
cd fin-risk-control
```

## 五、配置后端

```bash
cd backend

# 1. 建 venv + 装依赖
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
vim .env   # 填 LLM_API_KEY、EMBEDDING_API_KEY、MYSQL_PASSWORD

# 3. 初始化 MySQL
mysql -u root -p < app/db/schema.sql
```

`.env` 关键项（Linux 路径无需改，代码自动适配）：
```
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-chat
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_API_KEY=sk-xxx
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
MYSQL_HOST=127.0.0.1
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DB=risk_control
```

## 六、构建前端

```bash
cd ../frontend
npm install
npm run build   # 产出 dist/
```

## 七、启动后端

后端会自动检测到 `frontend/dist/` 并托管静态文件（单服务部署）。

**方式一：nohup（快速验证）**
```bash
cd ../backend
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

**方式二：systemd（推荐，开机自启 + 自动重启）**

创建 `/etc/systemd/system/fin-risk-control.service`：
```ini
[Unit]
Description=Fin Risk Control System
After=network.target mysql.service

[Service]
WorkingDirectory=/root/fin-risk-control/backend
ExecStart=/root/fin-risk-control/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now fin-risk-control
systemctl status fin-risk-control   # 查看状态
```

## 八、访问

浏览器打开：
```
http://<你的服务器公网IP>:8000
```

即可使用完整系统（上传 → 审查 → 复核 → 统计 → 导出 PDF）。

## 九、常见问题

| 问题 | 解决 |
|---|---|
| 访问不了 8000 | 检查安全组是否开放 8000 端口 |
| PDF 中文乱码 | `apt install fonts-wqy-microhei` 装中文字体 |
| 依赖装失败 | 用国内镜像：`pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple` |
| npm 装不动 | `npm config set registry https://registry.npmmirror.com` |
| 进程挂了 | `systemctl restart fin-risk-control`，看 `journalctl -u fin-risk-control` 日志 |

## 十、进阶（可选）

- **域名 + HTTPS**：买域名解析到服务器 IP，用 Nginx 反代 + Let's Encrypt 免费证书
- **MySQL 安全**：`mysql_secure_installation`，改 root 密码，应用专用账号
- **监控**：`journalctl -u fin-risk-control -f` 看日志
