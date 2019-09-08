from mistletoe import Document

from mistletoe_contrib.text_renderer import TextRenderer
from mistletoe_contrib.mathjax import MathJaxRenderer
from mistletoe_contrib.pygments_renderer import PygmentsRenderer
from mistletoe_contrib.toc_renderer import TOCRenderer


class MixRender(TOCRenderer, PygmentsRenderer, MathJaxRenderer, TextRenderer):
    pass


def mistletoe_parse(text, toc=False):
    doc = Document(text)
    with MixRender() as renderer:
        rendered = renderer.render(doc)
        if toc:
            toc = renderer.render(renderer.toc)
            return f'<div id="toc">{toc}</div>' + rendered
        return rendered
