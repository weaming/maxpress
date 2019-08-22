import mistune
from mistune_contrib.pangu import PanguRendererMixin
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import html


def startswith(x, lst):
    for y in lst:
        if x.startswith(y):
            return True
    return False


newline_types = ["paragraph", "newline", "heading", "open_html", "hrule", "table"]


class MDown(mistune.Markdown):
    def pop(self):
        if not hasattr(self, "list_depth"):
            self.list_depth = 0

        rv = super().pop()

        if self.token["type"] == "list_start":
            self.list_depth += 1
        elif self.token["type"] == "list_end":
            self.list_depth -= 1

        # print("-" * self.list_depth, self.list_depth, rv)
        return rv

    def output_list_item(self):
        body = self.renderer.placeholder()
        depth = self.list_depth
        while self.pop()["type"] != "list_item_end":
            if self.token["type"] == "text":
                body += self.tok_text()
            else:
                body += self.tok()
        rv = self.renderer.list_item(body, depth)
        return rv


class MRender(mistune.Renderer, PanguRendererMixin):
    def emojize(self, text):
        return text

    def text(self, text):
        if self.options.get("parse_block_html"):
            rv = text
        elif text.startswith("[ ]"):
            text = text[3:].strip()
            rv = '<input disabled="" type="checkbox"> %s\n' % mistune.escape(text)
        elif text.startswith("[x]"):
            text = text[3:].strip()
            rv = '<input checked="" disabled="" type="checkbox"> %s\n' % mistune.escape(
                text
            )
        else:
            rv = mistune.escape(text)
        return self.emojize(rv)

    def list_item(self, text, depth=None):
        if depth is not None:
            return '<li data-depth="%s">%s</li>\n' % (depth, text)
        return "<li>%s</li>\n" % text

    def block_code(self, code, lang):
        if not lang:
            return '\n<pre><code>%s</code></pre>\n' % mistune.escape(code)
        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = html.HtmlFormatter()
        return highlight(code, lexer, formatter)


markdown = MDown(renderer=MRender())
