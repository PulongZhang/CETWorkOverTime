# CETWorkOverTime

基于 **Vue 3 + TypeScript + FastAPI + SQLAlchemy 2 + MySQL** 的邮件工作总结管理系统。系统从 IMAP 抓取工作日志邮件，解析并写入现有 MySQL 年度分表，提供勤奋时间仪表板、月度明细和 Markdown 报告查看。

## 功能

- TOTP 动态验证码登录，使用 HttpOnly Cookie Session
- IMAP UID 增量抓取及 Message-ID 去重
- `.eml` 编码识别、正文清洗和同日邮件去重
- 兼容已有 `email_meta`、`email_2024`、`email_2025` 等年度分表
- 年度/月度勤奋时间统计和每日工作明细
- 数据库动态生成 Markdown/HTML 月度报告
- 单实例后台任务与定时抓取
- 周末、法定节假日、调休补班及个人请假的工作计划跳过规则
- Docker Compose 单容器部署

## 架构

```text
backend/                 FastAPI 后端
  app/api/v1/            /api/v1 接口
  app/core/              配置和 SQLAlchemy Engine
  app/repositories/      MySQL 年度分表数据访问
  app/services/          邮件抓取、解析、处理和报告服务
frontend/                Vue 3 单页应用
sql/init.sql             兼容数据库初始化脚本
```

数据库继续使用 MySQL。迁移不会合并或重建现有年度表；SQLAlchemy Core 直接访问 `email_YYYY` 表。

## Docker 部署

当前 Compose 配置使用 Docker Hub 上的 `pulongzhang/cetworkovertime:latest`，并连接 1Panel 创建的外部网络 `1panel-network`。MySQL 容器需要在该网络中提供 `mysql` 网络别名，数据库端口无需暴露到公网。

1. 确认外部网络存在：

   ```bash
   docker network inspect 1panel-network
   ```

2. 创建配置：

   ```bash
   cp .env.example .env
   ```

3. 修改 `.env` 中的 MySQL、IMAP、TOTP 和 Session 配置。使用 1Panel MySQL 时，数据库地址配置为：

   ```env
   DB_HOST=mysql
   DB_PORT=3306
   ```

   数据库账号、密码和库名按实际环境填写。启用 HTTPS 后设置：

   ```env
   COOKIE_SECURE=true
   ```

4. 拉取镜像并启动：

   ```bash
   docker compose pull
   docker compose up -d --force-recreate
   ```

5. 检查容器和数据库主机解析：

   ```bash
   docker compose ps
   docker exec cetworkovertime python -c "import socket; print(socket.gethostbyname('mysql'))"
   docker compose logs --tail=50 cetworkovertime
   ```

   容器健康检查访问 `GET /api/v1/health`。数据库连接正常时，日志中不应出现 `Name or service not known`。

6. 访问 `http://服务器地址:5000`。通过 OpenResty/1Panel 发布时，将反向代理指向宿主机的 `5000` 端口，并保持 `/api/v1` 路径不变。如果仅需本机反向代理访问，可将 Compose 端口映射改为 `127.0.0.1:5000:5000`。

应用使用单 Worker，因为内置调度器和任务状态保存在应用进程中。不要将 MySQL 的 `3306` 端口发布到公网；应用通过 `1panel-network` 直接访问 `mysql:3306`。

### 常见数据库连接问题

若日志提示无法解析主机 `mysql`，表示应用容器与 MySQL 容器不在同一个 Docker 网络。检查两个容器的网络配置：

```bash
docker inspect cetworkovertime --format '{{json .NetworkSettings.Networks}}'
docker inspect 1Panel-mysql-TDOY --format '{{json .NetworkSettings.Networks}}'
```

两者均应包含 `1panel-network`。若 1Panel 中的 MySQL 容器名称不同，请替换检查命令中的容器名称；`.env` 中仍使用该容器在网络内配置的别名。

## 本地开发

### 后端

```bash
uv sync --project backend
uv run --project backend uvicorn --app-dir backend app.main:app --reload
```

后端地址为 `http://127.0.0.1:8000`，健康检查：

```text
GET /api/v1/health
```

### 前端

```bash
pnpm --dir frontend install
pnpm --dir frontend dev
```

Vite 会将 `/api` 代理到本地 FastAPI。

## 工作日历

工作计划检查会自动跳过普通周末、法定节假日和个人请假，调休补班日仍正常检查。请假日期可在前端“请假”页面添加或移除，不使用数据库。

配置持久化在 `OUTPUT_DIR/work_calendar.json`。文件首次生成时使用内置的 2026 年国务院办公厅节假日安排；后续年度可直接更新其中的 `holidays` 和 `makeup_workdays` 数组，个人请假保存在 `leave_dates` 数组。Docker Compose 已持久化整个 `output` 目录。

```json
{
  "holidays": ["2026-10-01"],
  "makeup_workdays": ["2026-10-10"],
  "leave_dates": ["2026-09-07"]
}
```

## 验证

```bash
uv run --project backend ruff check backend/app backend/tests
uv run --project backend pytest backend/tests
pnpm --dir frontend build
docker compose config
```

## 数据库兼容说明

现有表结构保持不变：

```text
email_meta
email_2024
email_2025
email_2026
...
```

每个年度表继续以 `email_date` 唯一，同一天出现多封日志时，只在新记录勤奋时长更长时覆盖。应用会按需创建未来年份表，但不会删除或自动修改已有年度表。

## 安全说明

- 不要提交 `.env`。
- `TOTP_SECRET` 和 `SECRET_KEY` 必须替换默认占位值。
- 生产环境必须通过 HTTPS 访问并设置 `COOKIE_SECURE=true`。
- MySQL 不应直接暴露到公网。
