"""Safe, readable formatting for external descriptions."""
import html
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment, NavigableString

ALLOWED = {'p', 'br', 'strong', 'em', 'b', 'i', 'ul', 'ol', 'li', 'h3', 'h4', 'blockquote', 'a'}
DROP = {'script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'img', 'svg'}


def paragraph_chunks(text, target=450):
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)
    groups, current = [], ''
    for sentence in sentences:
        if current and len(current) + len(sentence) > target:
            groups.append(current)
            current = ''
        current = (current + ' ' + sentence).strip()
    if current:
        groups.append(current)
    return groups


def sanitize_description(value):
    soup = BeautifulSoup(value or '', 'html.parser')
    for unsafe in soup.find_all(DROP):
        unsafe.decompose()
    if not soup.find(['p', 'ul', 'ol', 'h1', 'h2', 'h3', 'h4', 'blockquote']):
        text = soup.get_text(' ', strip=True)
        return ''.join(f'<p>{html.escape(part)}</p>' for part in paragraph_chunks(text))

    def render(node):
        if isinstance(node, Comment):
            return ''
        if isinstance(node, NavigableString):
            return html.escape(str(node))
        if node.name in DROP:
            return ''
        content = ''.join(render(child) for child in node.children)
        tag = 'h3' if node.name in ('h1', 'h2') else node.name
        if tag not in ALLOWED:
            return content
        if tag == 'br':
            return '<br>'
        if tag == 'a':
            href = urljoin('https://boardgamegeek.com/', node.get('href', ''))
            parsed = urlparse(href)
            if parsed.scheme not in ('https', 'http') or not parsed.hostname:
                return content
            return f'<a href="{html.escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">{content}</a>'
        if tag == 'p' and len(node.get_text()) > 650:
            text = node.get_text(' ', strip=True)
            return ''.join(f'<p>{html.escape(part)}</p>' for part in paragraph_chunks(text))
        return f'<{tag}>{content}</{tag}>'

    return ''.join(render(child) for child in soup.children)
