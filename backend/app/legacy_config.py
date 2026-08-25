import os

from app.core.config import get_settings

settings = get_settings()

BASE_DIR = settings.work_summary_dir.parent
WORK_SUMMARY_DIR = settings.work_summary_dir
OUTPUT_DIR = settings.output_dir
EMAIL_FILE_EXTENSION = os.getenv("EMAIL_FILE_EXTENSION", ".eml")
EMAIL_FILE_PATTERNS = [
    r"--工作日志\[(\d{4}-\d{1,2}-\d{1,2})\]--\[提交成功\]\.eml$",
    r"--工作日志\[(\d{4}-\d{1,2}-\d{1,2})\]--\[提交成功\]\(不够300字\)\.eml$",
    r"--工作日志\[(\d{4}-\d{1,2}-\d{1,2})\]--\[提交成功\]_迟发补登\.eml$",
    r"--工作日志\[(\d{4}-\d{1,2}-\d{1,2})\]--\[提交成功\]\(不够300字\)\(\d+\)\.eml$",
    r"--工作日志\[(\d{4}-\d{1,2}-\d{1,2})\]--\[提交成功\]\(\d+\)\.eml$",
    r"--工作日志\[(\d{4}-\d{1,2}-\d{1,2})\]--\[提交成功\]_迟发补登\(不够300字\)\.eml$",
    r"--工作日志\[(\d{4}-\d{1,2}-\d{1,2})\]--\[提交成功\]_迟发补登\(不够300字\)\(\d+\)\.eml$",
]
EXCLUDE_PATTERNS = [r"^回复_.*\.eml$"]
DEFAULT_ENCODING = os.getenv("DEFAULT_ENCODING", "gb2312")
FALLBACK_ENCODINGS = os.getenv("FALLBACK_ENCODINGS", "utf-8,gbk,gb18030").split(",")
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "markdown")
CACHE_FILENAME = os.getenv("CACHE_FILENAME", ".process_cache.json")
DATE_FORMAT = "%Y年%m月"
REPORT_FILENAME_FORMAT = "{year}年{month:02d}月工作总结.md"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
CONTENT_START_MARKERS = ["工作总结", "今日工作", "工作内容"]
CONTENT_END_MARKERS = [
    "[点击查看详细的工作计划请点击查看]",
    "工作计划",
    "明日计划",
]
IMAP_SERVER = settings.imap_server
IMAP_PORT = settings.imap_port
IMAP_USE_SSL = settings.imap_use_ssl
IMAP_USERNAME = settings.imap_username
IMAP_PASSWORD = settings.imap_password
IMAP_MAILBOX = settings.imap_mailbox
WORK_PLAN_MAILBOX = settings.work_plan_mailbox
IMAP_SEARCH_SUBJECT = settings.imap_search_subject
IMAP_SEARCH_DAYS = settings.imap_search_days
CLEANUP_EML_AFTER_SYNC = settings.cleanup_eml_after_sync

WORK_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
