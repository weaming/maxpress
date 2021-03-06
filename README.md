# MaxPress：Markdown+Python实现微信公众号一键排版

[原始README](https://github.com/insula1701/maxpress/blob/master/README.md)

-------------

同时也可作为一个调优了的 Markdown 渲染工具使用。

## 基本功能

1. 批量转换MarkDown文档为适合粘贴微信编辑器的HTML文件。
2. 支持自定义：正文字号、文字颜色（正文颜色、主题色、引用色）、行间距、段间距、标题水平对齐方式、内容两侧留白比例、底部图片。
3. 转换完成的MarkDown文档可以自动移动存档。

## feature/cil 分支

* 在原始项目基础上添加命令行工具，添加更方便的全局配置`$HOME/.config/maxpress/`
* 转换单个文件后会自动在浏览器打开 HTML

## Markdown 渲染引擎

mistune 引擎退役，仅使用 mistletoe 引擎。

* Pygments 代码高亮
* mathjax 转换
* Emoji 转换 :wink:
* Pangu 转换

## 格式调整

在运行转换程序之前，修改`~/.config/maxpress/config.json`文件，可自定义常用格式变量。

包括：

| 变量名       | 默认值  | 说明                                                                                        |
| :-----       | :-----  | :----                                                                                       |
| main_size    | 16px    | 正文主字号                                                                                  |
| theme_color  | #349971 | 主题色，用于标题、强调元素等文字颜色                                                        |
| text_color   | #555    | 正文文字颜色                                                                                |
| quote_color  | #999    | 引用框和代码框内文字颜色                                                                    |
| line_height  | 2em     | 正文行高                                                                                    |
| para_spacing | 1.5em   | 正文段间距                                                                                  |
| align        | 多项    | 各部分的水平对齐方式，建议`left`或`center`（`h1`～`h6`代表标题1～标题6，`content`代表正文） |
| main_margin  | 3%      | 内容两侧留白比例                                                                            |
| banner_url   | ""      | 文章头部引导关注图片的url                                                                   |
| poster_url   | ""      | 底部二维码／海报图片的地址                                                                  |
| convert_list | true    | 将正文中的列表转换为普通段落，以修正微信不能正常显示列表序号样式的问题（仅用于微信）        |
| auto_archive | ""      | 是否自动存档（转换后将原始`.md`文件移动至`result／archive`目录下）                          |
| auto_rename  | false   | 冲突文件名的处理：`true`自动重命名；`false`覆盖先前的文件                                   |


**备注：**

- 如果对自定义的要求不高，建议更换一下`theme_color`，其余可以采用默认配置。

## 更多自定义

* 自定义 less 文件
  * `<libroot>/maxpress/less/styles.less`
  * `$HOME/.config/maxpress/styles.less`
  * `--styless`: 可传入多个，这时`config.json`中用于定义样式的参数将会失效，`custom.css`将在你的全部自定义样式表之后引入
* 如果你希望覆盖默认样式中的个别样式，可以自主编写`custom.css`，它将在`default.css`之后被引入。
  * `$HOME/.config/maxpress/custom.css`
* 自定义高亮 CSS
  * [`HIGHLIGHT_CSS_NAME`](https://bitbucket.org/birkenfeld/pygments-main/src/default/pygments/styles/)，默认 `autumn`
  * `HIGHLIGHT_CSS_URL` 将叠加在上面 `HIGHLIGHT_CSS_NAME`
* 自定义 icon
  * `ICON_URL`


## 开发环境

使用Python 3开发，CSS样式表使用LESS编译。
快速安装依赖：`pip install -r requirements.lock`

## 运行

* `maxpress --help`
* `python -m maxpress`

或者作为模块导入：

```python
import maxpress

maxpress.convert_all(archive=True, styles=None)
maxpress.convert_file(archive=True, styles=None)
```

## 关于微信公众号格式（仅供参考）

* 目前这版微信UI，貌似对所有列表序号都只能显示默认样式，即使把样式写进上级元素，粘贴进编辑器的时候也会被“洗掉”，目前尚未找到方法绕过此限制，因此添加`convert_list`选项作为临时解决方案，当此项为`true`时，正文中的所有列表（不包括代码块中的内容）会被转化为段首带序号的普通段落。注意，这种情况下，`styles.less`中专门为列表设置的样式将会失效。如果你有更好的办法，欢迎开issue告诉我。
* 带样式的列表粘贴到微信编辑器时，可能意外出现格式丢失的情况（貌似是微信的bug？） 目前通过在每个`li`元素内额外添加一个`span`元素包装样式，暂时可以解决。
* 要注意，如果自定义样式的话，为`li span`所设置的字号、颜色等不能与上级元素完全一致，否则在粘贴到微信编辑器时会被自动去掉。

## License

MIT
