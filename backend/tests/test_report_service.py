from app.services.report_service import render_markdown


def test_render_markdown_removes_unsafe_html() -> None:
    rendered = render_markdown("# 标题\n<script>alert('xss')</script><strong>内容</strong>")

    assert "<script" not in rendered
    assert "<strong>内容</strong>" in rendered
