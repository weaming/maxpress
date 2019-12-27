import os
from mistletoe import Document

from mistletoe_contrib.text_renderer import TextRenderer
from mistletoe_contrib.mathjax import MathJaxRenderer
from mistletoe_contrib.pygments_renderer import PygmentsRenderer
from mistletoe_contrib.toc_renderer import TOCRenderer

HOSTNAME = os.getenv('HOSTNAME')


class MixRender(TOCRenderer, PygmentsRenderer, MathJaxRenderer, TextRenderer):
    def render_link(self, token):
        template = '<a href="{href}"{title}{target}>{inner}</a>'
        href = self.escape_url(token.target)
        if token.title:
            title = ' title="{}"'.format(self.escape_html(token.title))
        else:
            title = ''
        if HOSTNAME and HOSTNAME.lower() not in token.target:
            target = ' target="_blank"'
        else:
            target = ''
        inner = self.render_inner(token)
        return template.format(href=href, title=title, inner=inner, target=target)


def mistletoe_parse(text, toc=False):
    doc = Document(text)
    with MixRender() as renderer:
        rendered = renderer.render(doc)
        if toc:
            toc = renderer.render(renderer.toc)
            return f'<div id="toc">{toc}</div>' + rendered
        return rendered
