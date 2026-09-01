from markdown_it import MarkdownIt

import nh3

_md = MarkdownIt("commonmark", {"html": False})

ALLOWED_TAGS = {
    "p",
    "a",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "code",
    "pre",
    "blockquote",
    "em",
    "strong",
    "hr",
    "br",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
}

ALLOWED_ATTRS = {"a": {"href", "title"}, "code": {"class"}}


def render_markdown(text: str) -> str:
    html = _md.render(text or "")
    return nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
