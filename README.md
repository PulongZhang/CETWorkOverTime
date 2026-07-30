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

1. 创建配置：

   ```bash
   cp .env.example .env
   ```

2. 修改 `.env` 中的 MySQL、IMAP、TOTP 和 Session 配置。

3. 构建并启动：

   ```bash
   docker compose up -d --build
   ```

4. 访问 `http://127.0.0.1:5000`。

默认仅绑定宿主机 `127.0.0.1`。通过 OpenResty/1Panel 发布时，将反向代理指向该地址，并保持 `/api/v1` 路径不变。启用 HTTPS 后设置：

```env
COOKIE_SECURE=true
```

应用使用单 Worker，因为内置调度器和任务状态保存在应用进程中。

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
