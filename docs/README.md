# TextCleaner

西班牙语 OCR 文本清洗工具。

当前版本：v1.2.0

## 安装与使用

普通用户可从 GitHub Releases 下载 `TextCleaner-v1.2.0.zip`：

- macOS：首次运行 `1_首次安装_macOS.command`，之后把文件拖到 `TextCleaner.app`。
- Windows：首次运行 `1_首次安装_Windows.bat`，之后把文件拖到 `2_拖放清洗_Windows.bat`。

源码运行：

```bash
python3 -m pip install -r requirements.txt
python3 "textcleaner V1.2.py"
```

## 常用入口


- 双击 `拆分大PDF.command`：把超过 250 页的 PDF 按每卷 200 页拆分到桌面 `pdf_split/`
- 双击 `TextCleaner.app`：清洗拖入的 Markdown
- 运行 `textcleaner V1.2.py`：清洗 `output/mineru_raw/` 中的 Markdown

## 目录

- `data/`：停用短语和候选词
- `docs/`：项目文档与使用说明
- `tests/`：自动测试
- `output/`：TextCleaner 的输入、输出和日志

## 测试

```bash
python3 -m pytest
```

详细说明：

- `docs/README_Codex.md`
- `docs/PDF拆分使用说明.txt`
- `docs/拖放程序使用说明.txt`
