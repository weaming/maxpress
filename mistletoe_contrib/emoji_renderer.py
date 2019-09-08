from mistletoe import HTMLRenderer
import emoji
import pangu


def emojize(text):
    return emoji.emojize(text, use_aliases=True)


class EmojiRenderer(HTMLRenderer):
    def render_raw_text(self, token):
        return pangu.spacing_text(emojize(token.content))
