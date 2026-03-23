# 邮件工作总结汇总系统 (CETWorkOverTime)

一个全配置化、具有安全前端与全自动功能特性的 Python Web 工具，用以协助从邮件（尤其针对企业邮箱）提取工作日志汇报内容，自动拼接去重，最终生成格式化的 Markdown 月度工作报告。

## ✨ 核心特性

- 🌐 **Web 集中管理**: 提供美观的专属仪表板，轻松查看当前获取邮件状态、报告生成状态与勤奋时间统计。
- 📥 **自动 IMAP 拉取**: 无需手动下载邮件。配置 IMAP，程序全自动从你指定的邮箱（如 QQ 企业邮箱）定时或一键抓取主题匹配的指定日期邮件。
- 📊 **智能解析整合**:
  - 自动识别.eml多格式编码。
  - 按日期和标识提取每日“工作内容”、“明后天计划”等数据。
  - 自动归并去重同日期的重复文件。
- 🔒 **两步验证 (2FA) 安全登录**: 基于 TOTP 实现访问隔离，保障你团队内部工作总结的隐私。
- 💾 **多路数据持久化 (MySQL & 本地)**: 将获取到的邮件记录结构化地存入 MySQL 并在本地生成独立的文件缓存，实现数据的高可用。
- 🐳 **开箱即用 (Docker)**: 完美支持 Docker Compose 一键部署，且提供内置 Python scheduler 任务调度，无需依赖复杂的系统级 Cron。
- 🕐 **时区自适应**: 完全支持修正 Docker 时区至 `Asia/Shanghai`，保证前端日历、自动任务和文件名称时钟同步。

## 🚀 快速开始

### 推荐: Docker Compose 部署

最简单也是官方推荐的方式是使用 `docker-compose`：

1. 克隆代码仓库。
2. 配置环境变量：将 `.env.example`（如下方示例）复制一份并重命名为 `.env`，按照你的实际情况修改。
3. 运行服务：
    ```bash
    docker-compose up -d
    ```
4. 初次访问与绑定身份验证：
    - 打开浏览器访问：`http://localhost:5000`
    - 系统会提示并展示 TOTP 绑定的二维码（或密钥）。使用如 Google Authenticator、Microsoft Authenticator 等应用扫码。
    - 输入动态 6 位验证码后即可进入系统。

### 本地原生部署

如果你不想使用 Docker，也可以本地运行：

1. **安装依赖**：
    ```bash
    pip install -r requirements.txt -i https://mirrors.huaweicloud.com/repository/pypi/simple
    ```
2. **准备运行环境**：
    - 准备一个可用的 MySQL 数据库实例，并按 `db.py` 中依赖的表结构准备数据表。
    - 在同级目录创建 `.env` 并填写对应配置项。
3. **运行 Web 服务**：
    ```bash
    # 结合 Flask 直接使用：
    python app.py
    ```

## ⚙️ 核心环境变量 (`.env` 配置说明)

运行前请务必配置相关环境变量。可以通过修改 `.env` 文件来实现，系统主要读取这些变量：

```env
# ======== 基础配置 ========
# 邮件保存目录
WORK_SUMMARY_DIR=工作总结
# 输出的 Markdown 报告存放目录
OUTPUT_DIR=output

# ======== IMAP 邮箱配置 ========
IMAP_SERVER=imap.exmail.qq.com
IMAP_PORT=993
IMAP_USE_SSL=true
# 你的邮箱地址
EMAIL_USERNAME=your.email@company.com
# 你的邮箱 IMAP 授权码 (非登录密码)
EMAIL_PASSWORD=your_imap_password
# 目标采集文件夹名
IMAP_MAILBOX=&XeVPXGXlX9c-
# 限定搜索标题包含的关键字
IMAP_SEARCH_SUBJECT=--工作日志

# ======== 安全设定 (2FA) ========
# TOTP 安全密钥 (请自行修改为长随机字符串，Base32格式，长度为16的倍数比较合适如：JBSWY3DPEHPK3PXP)
TOTP_SECRET=YOUR_32_CHAR_BASE32_SECRET

# ======== 数据库 (MySQL) 配置 ========
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password
DB_NAME=cetworkovertime
```

## 📁 主要目录与代码结构

```
CETWorkOverTime/
├── app.py                  # Flask Web 核心启动入口，提供路由与页面渲染
├── config.py               # 环境配置统筹模块 (结合.env与默认值)
├── db.py                   # 数据库连接池与基础操作抽象
├── email_fetcher.py        # 核心 IMAP 抓取逻辑，与邮箱通信的主力
├── email_parser.py         # .eml 文件文本及附件智能提取工具
├── email_processor.py      # 按规则归类、去重处理，分发生成报告的数据
├── email_repository.py     # 涉及 MySQL 存储具体业务表的增删改查实现
├── report_generator.py     # 整合数据最终构建美观的 Markdown/HTML 报告
├── requirements.txt        # python包依赖表
├── docker-compose.yml      # 容器化部署编排配置
├── templates/              # 前端网页 (包含登录及美观的仪表盘 dashboard.html 等)
└── static/                 # 样式资源文件 (style.css 等)
```

## 📦 产生的核心报告产物

生成出的核心 Markdown 将按**月度**组织到 `./output` 目录下（或你所指定的位置），如下：

- `YYYY年MM月工作总结.md`
  - 将当前月的按照日期排序依次罗列每日内容与规划。
  - 非常方便直接分享给领导或其他业务系统做归档沉淀。

## 🐛 常见问题参考

1. **为什么时区总是报错比服务器实际时间少或多8小时？**
   - 检查启动时的宿主机时区。如果是 Docker 启动，请确保 `docker-compose.yml` 中的环境变量包含 `TZ=Asia/Shanghai`。
2. **邮箱连不上？**
   - 确保你用的是邮箱设置提供的专属 **IMAP/SMTP客户端授权码**，而不是 Web 端系统登录密码！同时检查 `IMAP_SERVER` / `IMAP_PORT` 参数。
3. **内容抓取到，但是解析出空内容 (如“未解析出工作内容正文”)？**
   - 可以根据前端界面的日志，或者是服务器的 `app.log`。有可能是你的日报中没有命中内置的关键词 (如 `工作总结`、`今日工作`)。可在 `config.py` 的 `CONTENT_START_MARKERS` 自行补充匹配你的业务格式关键字。

## 🤝 参与贡献

欢迎通过 Issue 与 Pull Request 反馈您需要增强的解析逻辑或图表能力。

## 📄 开源许可证

MIT License
