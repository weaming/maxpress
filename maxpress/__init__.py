#!/usr/bin/env python3
import sys
import argparse
import os, re, json, shutil
from os.path import join as join_path

from six import StringIO
from mistune import Markdown
import premailer, lesscpy


ROOT = os.getenv("ROOT") or os.path.dirname(os.path.abspath(__file__))
config_path = os.path.expandvars("$HOME/.config/maxpress/config.json")
default_config = {
    "main_size": "16px",
    "main_margin": "3%",
    "line_height": "1.8em",
    "para_spacing": "1.5em",
    "text_color": "#555",
    "theme_color": "#349971",
    "quote_color": "#999",
    "align": {
        "h1": "left",
        "h2": "left",
        "h3": "center",
        "h4": "center",
        "h5": "center",
        "h6": "center",
        "content": "left",
    },
    "banner_url": "",
    "poster_url": "",
    "convert_list": True,
    "ul_style": "○",
    "auto_archive": False,
    "auto_rename": False,
}


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


def get_styles_less():
    cfg_style = os.path.expanduser("$HOME/.config/maxpress/styles.less")
    if os.path.isfile(cfg_style):
        return cfg_style
    embedded = join_path(ROOT, "less", "styles.less")
    return embedded


def get_custom_css_path():
    css = os.path.expanduser("$HOME/.config/maxpress/custom.css")
    if os.path.isfile(css):
        return css
    return join_path(ROOT, "css", "custom.css")


def get_compiled_css_path():
    return join_path(ROOT, "css", "default.css")


def get_default_less_path():
    return join_path(ROOT, "less", "default.less")


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
        "ul_style",
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


# 将待解析的md文档转换为适合微信编辑器的html
def md2html(
    text,
    title="",
    styles=None,
    poster="",
    banner="",
    convert_list=True,
    ul_style="\u25CB",
):
    md = Markdown()

    # 将markdown列表转化为带序号的普通段落（纯为适应微信中列表序号样式自动丢失的古怪现象）
    if convert_list:
        blocks = text.split("\n```")
        for i in range(0, len(blocks)):
            if i % 2 == 0:
                blocks[i] = re.sub(r"(\n\d+)(\.\s.*?)", r"\n\1\\\2", blocks[i])
                blocks[i] = re.sub(
                    r"\n[\-\+\*](\s.*?)", u"\n\n{} \1".format(ul_style), blocks[i]
                )
            else:
                continue  # 跳过代码块内部内容
        text = "\n```".join(blocks)

    inner_html = md(text)
    result = premailer.transform(pack_html(inner_html, title, styles, poster, banner))
    return result


def pack_html(html, title="", styles=None, poster="", banner=""):
    if not styles:
        styles = [get_compiled_css_path()]
    styles.append(get_custom_css_path())
    style_tags = [
        '<link rel="stylesheet" type="text/css" href="{}">'.format(sheet)
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

    head = """<!DOCTYPE html><html lang="zh-cn">
          <head>
          <meta charset="UTF-8">
          <title>{title}</title>
          {styles}
          </head>
          <body>
          <div class="wrapper">
          {banner}\n""".format(
        styles="\n".join(style_tags), banner=banner_tag, title=title
    )

    foot = """{}\n</div>\n</body>\n</html>""".format(poster_tag)

    result = fix_tbl(fix_img(fix_li(head + html + foot)))
    return result


def fix_li(html):  # 修正粘贴到微信编辑器时列表格式丢失的问题
    result = re.sub(r"<li>([\s\S]*?)</li>", r"<li><span>\1</span></li>", html)
    return result


def fix_img(html):  # 修正HTML图片大小自适应问题
    result = re.sub(
        r"(<p>)*?<img([\s\S]*?)>(</p>)*?",
        r'<section class="img-wrapper"><img\2></section>',
        html,
    )
    return result


def fix_tbl(html):  # 修正HTML表格左右留白问题
    result = re.sub(
        r"<table>([\s\S]*?)</table>",
        r'<section class="tbl-wrapper"><table>\1</table></section>',
        html,
    )
    return result


# 装饰器：提供报错功能
def report_error(func):
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            log("错误: {}".format(e))
            input("提示：运行前请将所有要转换的Markdown文档放入temp目录中\n" "请按回车键退出程序：")

    return wrapper


# 用于处理嵌套目录
def recursive_listdir(dir):
    for root, _, files in os.walk(dir):
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


# 转换temp下的所有md文档
# @report_error
def convert_all(
    src=join_path(ROOT, "temp"),
    dst=join_path(ROOT, "result", "html"),
    archive=None,
    styles=None,
):  # 通过styles参数传入css文件名列表时，默认样式将失效
    config, styles = load_config_and_css(styles)
    if archive is None:
        archive = config["auto_archive"]

    for file, filepath in recursive_listdir(src):
        if file.endswith(".md"):
            convert_file(file, filepath, dst, config, styles, archive=archive)
        else:
            if archive:
                # 非.md文件统一移到src一级目录下等待手动删除，以防意外丢失
                if re.split(r"[/\\]", filepath)[-2] != re.split(r"[/\\]", src)[-1]:
                    shutil.move(filepath, autoname(join_path(src, file)))
            else:
                continue

    if archive:
        # 删除src中剩余的空目录
        for path in os.listdir(src):
            try:
                shutil.rmtree(join_path(src, path))
            except:
                pass

    log("\n[+] 请进入result／html查看所有生成的HTML文档")
    log("[+] 请进入result／archive查看所有存档的MarkDown文档")


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
        ul_style=config["ul_style"],
    )


def convert_file(file, filepath, dst, config, styles, archive=False, title=""):
    log("[+] 正在转换{}...".format(file), end=" ")
    with open(filepath, encoding="utf-8") as md_file:
        text = md_file.read()
    result = convert_markdown(text, title or file[-3], config, styles)

    htmlpath = join_path(dst, file[:-3] + ".html")
    if config["auto_rename"]:
        htmlpath = autoname(htmlpath)
    prepare_dir(htmlpath)
    with open(htmlpath, "w", encoding="utf-8") as html_file:
        html_file.write(result)
    log("转换成功[{}]".format(htmlpath.split("/")[-1]))

    if archive:
        log("[+] 正在存档{}...".format(file), end=" ")
        arch_dir = join_path(ROOT, "result", "archive")
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
        "--src", default=join_path(ROOT, "temp"), help="source directory or file"
    )
    parser.add_argument(
        "--dst", default=join_path(ROOT, "result", "html"), help="destination directory"
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
