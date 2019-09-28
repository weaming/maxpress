#!/usr/bin/env python3
import sys
import argparse
import os, re, json, shutil
from concurrent.futures import ProcessPoolExecutor
from os.path import join as join_path

import premailer
import requests
from six import StringIO
import lesscpy
from maxpress.renderer import mistletoe_parse

LIB_ROOT = os.getenv("LIB_ROOT") or os.path.dirname(os.path.abspath(__file__))
# md 根目录
ROOT = os.getenv("ROOT")
config_path = os.path.expandvars("$HOME/.config/maxpress/config.json")
_ = """
自定义基本参数：
  main_size: 正文主字号
  main_margin: 内容两侧留白比例
  line_height: 正文行高
  para_spacing: 正文段间距
  title_align: 标题水平对齐方式，建议left或center（仅支持h3-h6，h1、h2固定使用左对齐）
  text_color: 正文文字颜色
  theme_color: 主题色，用于标题、强调元素等文字颜色
  quote_color: 引用框和代码框内文字颜色
  banner_url: 文章头部引导关注图片的url，如"http://placeholder.qiniudn.com/900x100"
  poster_url: 文章底部图片的url，通常是二维码或宣传海报，如"http://placeholder.qiniudn.com/900x600"
  auto_archive: 是否自动存档（转换后将原始`.md`文件移动至`result／archive`目录下）
  auto_rename: 如何处理冲突的文件名，true - 自动重命名；false - 覆盖先前的文件
  border_color: 边框颜色
"""
# https://www.color-hex.com/color-palette/83148
default_config = {
    "main_size": "16px",
    "main_margin": "3%",
    "line_height": "1.8em",
    "para_spacing": "1.5em",
    "list_padding_left": "1.5em",
    "text_color": "#555",
    "theme_color": "#f06",
    "quote_color": "#999",
    "border_color": "#ccc",
    "align": {
        "h1": "left",
        "h2": "left",
        "h3": "left",
        "h4": "left",
        "h5": "left",
        "h6": "left",
        "content": "left",
    },
    "banner_url": "",
    "poster_url": "",
    "convert_list": True,
    "auto_archive": False,
    "auto_rename": False,
}
export = {"mistletoe": mistletoe_parse}


def prepare_dir(path):
    path = os.path.abspath(path)
    if not path.endswith("/"):
        path = os.path.dirname(path) or "."

    if not os.path.isdir(path):
        os.makedirs(path)


if not os.path.isfile(config_path):
    prepare_dir(config_path)
    with open(config_path, "w") as f:
        f.write(json.dumps(default_config, ensure_ascii=False, indent=2))


def log(*args, **kw):
    print(*args, file=sys.stderr, **kw)


highlight_css = os.getenv("HIGHLIGHT_CSS_URL")


def get_styles_less():
    cfg_style = os.path.expandvars("$HOME/.config/maxpress/styles.less")
    if os.path.isfile(cfg_style):
        return cfg_style
    embedded = join_path(LIB_ROOT, "less", "styles.less")
    return embedded


def get_default_less_path():
    return join_path(LIB_ROOT, "less", "default.less")


def get_custom_css_path():
    css = os.path.expandvars("$HOME/.config/maxpress/custom.css")
    if os.path.isfile(css):
        return css


def get_compiled_css_path():
    return join_path(LIB_ROOT, "css", "default.css")


# 处理配置文件
def import_config(file=config_path):
    with open(file, encoding="utf-8") as json_file:
        text = json_file.read()
        json_text = re.search(r"\{[\s\S]*\}", text).group()  # 去除json文件中的注释
    config = json.loads(json_text)

    non_style_keys = [
        "poster_url",
        "banner_url",
        "convert_list",
        "auto_archive",
        "auto_rename",
    ]

    # 读取配置文件中的变量，最多支持两级嵌套
    cfg_lines = []
    for key, value in config.items():
        if key not in non_style_keys:
            if not isinstance(value, dict):
                cfg_lines.append("@{}: {};\n".format(key, value))
            else:
                for inner_key, inner_value in value.items():
                    cfg_lines.append(
                        "@{}: {};\n".format(inner_key + "_" + key, inner_value)
                    )

    variables = "\n".join(cfg_lines) + "\n\n"

    with open(get_styles_less(), encoding="utf-8") as styles_file:
        styles = styles_file.read()
    with open(get_default_less_path(), "w", encoding="utf-8") as default_less:
        default_less.write(variables + styles)
    return config


# 解析less文件，生成默认样式表
def compile_styles(file=get_default_less_path()):
    with open(file, encoding="utf-8") as raw_file:
        raw_text = raw_file.read()

    css = lesscpy.compile(StringIO(raw_text))
    css_path = get_compiled_css_path()
    prepare_dir(css_path)
    with open(css_path, "w", encoding="utf-8") as css_file:
        css_file.write(css)


def embed_css(html):
    import bs4

    soup = bs4.BeautifulSoup(html, features='lxml')
    stylesheets = soup.findAll("link", {"rel": "stylesheet"})
    for s in stylesheets:
        href = s["href"]
        t = soup.new_tag("style")
        if href:
            if os.path.isfile(href):
                css = open(href).read()
            else:
                css = requests.get(href).text
            c = bs4.element.NavigableString(css)
            t.insert(0, c)
            t["type"] = "text/css"
            s.replaceWith(t)
    return str(soup)


# 将待解析的md文档转换为适合微信编辑器的html
def md2html(text, title="", styles=None, poster="", banner="", convert_list=True):
    # 将markdown列表转化为带序号的普通段落（纯为适应微信中列表序号样式自动丢失的古怪现象）
    if convert_list:
        blocks = text.split("\n```")
        for i in range(0, len(blocks)):
            if i % 2 == 0:
                blocks[i] = re.sub(r"(\n\d+)(\.\s.*?)", r"\n\1\\\2", blocks[i])
            else:
                continue  # 跳过代码块内部内容
        text = "\n```".join(blocks)

    MD_PARSER = "mistletoe"
    MD = export[MD_PARSER]
    inner_html = MD(text)
    if os.getenv("DEBUG"):
        with open("1.html", "w") as f:
            f.write(inner_html)
    packed = pack_html(inner_html, title, styles, poster, banner)
    if os.getenv("DEBUG"):
        with open("2.html", "w") as f:
            f.write(packed)
    # return packed
    result = premailer.transform(packed)
    # result = embed_css(packed)
    if os.getenv("DEBUG"):
        with open("3.html", "w") as f:
            f.write(result)
    return result


def pack_html(html, title="", styles=None, poster="", banner=""):
    if not styles:
        styles = [get_compiled_css_path()]
    if highlight_css:
        styles.append(highlight_css)
    custom_css = get_custom_css_path()
    if custom_css:
        styles.append(custom_css)
    # log('styles', styles, end='  ')

    style_tags = [
        '<link rel="stylesheet" type="text/css" href="{}"/>'.format(sheet)
        for sheet in styles
    ]

    if poster.strip():
        poster_tag = '\n<br>\n<img src="{}" alt="poster"／>'.format(poster)
    else:
        poster_tag = ""

    if banner.strip():
        banner_tag = '<img src="{}" alt="banner"／>'.format(banner)
    else:
        banner_tag = ""

    icon = os.getenv("ICON_URL")
    if icon:
        icon_tag = f'<link rel="shortcut icon" href="{icon}">'
    else:
        icon_tag = ''
    head = """<!DOCTYPE html><html lang="zh-cn">
          <head>
          <meta charset="UTF-8">
          <title>{title}</title>
          {icon_tag}
          {styles}
          </head>
          <body>
          <div class="wrapper">
          {banner}\n""".format(
        styles="\n".join(style_tags), banner=banner_tag, title=title, icon_tag=icon_tag
    )

    foot = """{}\n</div>\n</body>\n</html>""".format(poster_tag)
    html = head + html + foot

    result = fix_tbl(fix_img(fix_li(html)))
    return result


def fix_li(html):
    """
    修正粘贴到微信编辑器时列表格式丢失的问题
    """
    result = re.sub(
        r"<li>(.*?)</li>", r"<li><span>\1</span></li>", html, flags=re.MULTILINE
    )
    return result


def fix_img(html):
    """
    修正HTML图片大小自适应问题
    """
    result = re.sub(
        r"(<p>)*?<img([\s\S]*?)>(</p>)*?",
        r'<section class="img-wrapper"><img\2></section>',
        html,
    )
    return result


def fix_tbl(html):
    """
    修正HTML表格左右留白问题
    """
    result = re.sub(
        r"<table>([\s\S]*?)</table>",
        r'<section class="tbl-wrapper"><table>\1</table></section>',
        html,
    )
    return result


# 装饰器：提供报错功能
# 用于处理嵌套目录
def recursive_listdir(dir):
    for root, _, files in os.walk(dir, followlinks=True):
        for file in files:
            yield (file, join_path(root, file))


# 用于处理冲突的文件名
def autoname(defaultpath):
    try:
        ext = re.search(r"\.\w+?$", defaultpath).group()
    except AttributeError:
        ext = None
    count = 0
    while count < 10000:
        suffix = "(%d)" % count if count > 0 else ""
        if ext:
            newpath = defaultpath[: 0 - len(ext)] + suffix + ext
        else:
            newpath = defaultpath + suffix
        if not os.path.exists(newpath):
            return newpath
        else:
            count += 1
            continue


def map_do(fn, iterable, n=20):
    with ProcessPoolExecutor(n) as executor:
        results = executor.map(fn, iterable)
        return results


def _map_fn_wrapper(p):
    convert_file(*p["args"], **p["kwargs"])


def convert_all(src=join_path(LIB_ROOT, "temp"), dst=None, archive=None, styles=None):
    """
    转换 src 下的所有md文档
    通过styles参数传入css文件名列表时，默认样式将失效
    """
    dst = dst or join_path(src, "../result/html")

    config, styles = load_config_and_css(styles)
    if archive is None:
        archive = config["auto_archive"]

    ps = []
    for file, filepath in recursive_listdir(src):
        if file.endswith(".md"):
            # convert_file(file, filepath, dst, config, styles, archive=archive)
            # renderer is not threadsafe
            param = dict(
                args=(file, filepath, dst, config, styles),
                kwargs=dict(archive=archive, title=file[:-3]),
            )
            ps.append(param)
        else:
            if archive:
                # 非.md文件统一移到src一级目录下等待手动删除，以防意外丢失
                if re.split(r"[/\\]", filepath)[-2] != re.split(r"[/\\]", src)[-1]:
                    shutil.move(filepath, autoname(join_path(src, file)))
            else:
                continue

    map_do(_map_fn_wrapper, ps)

    if archive:
        # 删除src中剩余的空目录
        for path in os.listdir(src):
            try:
                shutil.rmtree(join_path(src, path))
            except Exception:
                pass

    log(f"\n[+] 请进入{dst}查看所有生成的HTML文档")
    log(f"[+] 请进入{dst}查看所有存档的MarkDown文档")


def load_config_and_css(styles):
    log("[+] 正在导入配置文件...", end=" ")
    config = import_config()
    log("导入成功")

    if not styles:
        log("[+] 正在编译CSS样式表...", end=" ")
        compile_styles()
        log("编译成功")
    elif isinstance(styles, str):
        styles = [styles]
    return config, styles


def convert_markdown(text, title, config, styles):
    return md2html(
        text,
        title=title,
        styles=styles,
        poster=config["poster_url"],
        banner=config["banner_url"],
        convert_list=config["convert_list"],
    )


def convert_file(file, filepath, dst, config, styles, archive=False, title=""):
    log("[+] 正在转换{}...".format(file), end=" ")
    middle_path = os.path.dirname(os.path.relpath(filepath, ROOT)) if ROOT else None

    with open(filepath, encoding="utf-8") as md_file:
        text = md_file.read()
    result = convert_markdown(text, title or file[-3], config, styles)

    if middle_path:
        htmlpath = join_path(dst, middle_path, file[:-3] + ".html")
    else:
        htmlpath = join_path(dst, file[:-3] + ".html")
    if config["auto_rename"]:
        htmlpath = autoname(htmlpath)
    prepare_dir(htmlpath)
    with open(htmlpath, "w", encoding="utf-8") as html_file:
        html_file.write(result)
    log("转换成功[{}]".format(htmlpath.split("/")[-1]))

    if archive:
        log("[+] 正在存档{}...".format(file), end=" ")
        arch_dir = join_path(LIB_ROOT, "result", "archive")
        if not os.path.exists(arch_dir):
            os.mkdir(arch_dir)
        archpath = join_path(arch_dir, file)
        if config["auto_rename"]:
            archpath = autoname(archpath)
        prepare_dir(archpath)
        shutil.move(filepath, archpath)
        log("存档成功[{}]".format(archpath.split("/")[-1]))
        return archpath
    return htmlpath


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="convert all *.md under source directory",
    )
    parser.add_argument(
        "--archive", action="store_true", help="archive markdown after convert"
    )
    parser.add_argument("--stdout", action="store_true", help="print stdout")
    parser.add_argument(
        "--src", default=join_path(LIB_ROOT, "temp"), help="source directory or file"
    )
    parser.add_argument(
        "--dst",
        default=join_path(LIB_ROOT, "result", "html"),
        help="destination directory",
    )
    parser.add_argument("--styles", nargs="*", help="css file path")
    args = parser.parse_args()

    if args.all:
        convert_all(src=args.src, dst=args.dst, archive=args.archive)
    else:
        config, styles = load_config_and_css(args.styles)
        archive = config["auto_archive"]

        filepath = args.src
        file = os.path.basename(filepath)
        if os.path.isfile(filepath) and file.endswith(".md"):
            htmlpath = convert_file(
                file, filepath, args.dst, config, styles, archive=archive
            )
            if not args.stdout:
                print(htmlpath)
                os.system("open {}".format(htmlpath))
            else:
                with open(htmlpath) as f:
                    print(f.read())
            return
        log("--src should be a *.md file")


if __name__ == "__main__":
    # ./maxpress.py --src temp/example.md 2>/dev/null | xargs open
    # then copy & paste
    main()
