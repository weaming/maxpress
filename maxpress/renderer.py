import mistune
from mistune_contrib.pangu import PanguRendererMixin


def startswith(x, lst):
    for y in lst:
        if x.startswith(y):
            return True
    return False


class Break(Exception):
    pass


class MDown(mistune.Markdown):
    def pop(self):
        if not hasattr(self, "list_depth"):
            self.list_depth = 0

        rv = super().pop()

        if self.token["type"] == "list_start":
            self.list_depth += 1
        elif self.token["type"] == "list_end":
            self.list_depth -= 1

        return rv

    def output_list(self):
        ordered = self.token["ordered"]
        body = self.renderer.placeholder()
        while True:
            token = self.pop()
            if not token or token["type"] == "list_end":
                break
            body += self.tok()
        return self.renderer.list(body, ordered)

    def output_list_item(self):
        body = self.renderer.placeholder()
        depth = self.list_depth
        assert depth >= 0
        while True:
            token = self.pop()
            if depth - 1 == self.list_depth:
                break
            elif token["type"] == "list_item_end":
                break
            else:
                if self.token["type"] == "text":
                    body += self.tok_text()
                else:
                    body += self.tok()

        return self.renderer.list_item(body)


class MRender(mistune.Renderer, PanguRendererMixin):
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
        return rv


markdown = MDown(renderer=MRender())
