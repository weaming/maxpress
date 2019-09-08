from mistletoe import HTMLRenderer
import emoji
import pangu


def emojize(text):
    return emoji.emojize(text, use_aliases=True)


class TextRenderer(HTMLRenderer):
    def render_raw_text(self, token):
        text = token.content
        parse = lambda x: pangu.spacing_text(emojize(x))
        if text.startswith("[ ]"):
            text = text[3:].strip()
            rv = '<input disabled="" type="checkbox"> %s\n' % parse(text)
        elif text.startswith("[x]"):
            text = text[3:].strip()
            rv = '<input checked="" disabled="" type="checkbox"> %s\n' % parse(text)
        else:
            rv = parse(text)
        return rv
