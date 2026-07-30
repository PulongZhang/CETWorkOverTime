from datetime import date

import bleach
import markdown


def build_monthly_markdown(year: int, month: int, emails: list[dict]) -> str:
    lines = [f"# {year}年{month:02d}月工作总结", ""]
    if not emails:
        return "\n".join([*lines, "暂无数据。"])

    total_hours = sum(float(email.get("diligence_hours", 0) or 0) for email in emails)
    lines.extend(
        [
            "## 📊 统计信息",
            "",
            f"- **工作日数**: {len(emails)} 天",
            f"- **勤奋时间合计**: {total_hours:.2f} 小时",
            "",
            "## 📝 工作日志",
            "",
        ]
    )

    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    for email in emails:
        email_date = date.fromisoformat(str(email["email_date"]))
        lines.extend(
            [
                f"### {email_date:%Y年%m月%d日} ({weekdays[email_date.weekday()]})",
                "",
                f"**主题**: {email.get('subject', '')}",
            ]
        )
        hours = float(email.get("diligence_hours", 0) or 0)
        if hours:
            lines.append(
                f"**勤奋时间**: {email.get('diligence_start', '')} ~ "
                f"{email.get('diligence_end', '')}（{hours:.2f} 小时）"
            )
        lines.extend(["", "**工作内容**:", "", email.get("content", ""), ""])

    lines.extend(["---", "*此报告从数据库动态生成*"])
    return "\n".join(lines)


def render_markdown(content: str) -> str:
    rendered = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )
    return bleach.clean(
        rendered,
        tags={
            "h1", "h2", "h3", "h4", "p", "br", "hr", "strong", "em",
            "ul", "ol", "li", "blockquote", "pre", "code", "table",
            "thead", "tbody", "tr", "th", "td",
        },
        attributes={},
        strip=True,
    )
