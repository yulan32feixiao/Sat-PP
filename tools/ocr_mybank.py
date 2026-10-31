#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把两个素材文件夹的复盘截图批量 OCR 成文本。

要点：本机 Leptonica 读不了 macOS 截图 PNG（连临时目录都读不了），
必须用 stdin 管道喂给 tesseract；先经 PIL 转纯 RGB 再喂，去掉怪异色彩配置。
产出 work/ocr/<名字>.txt，供后续解析。
"""
import glob
import os
import subprocess
import sys

from PIL import Image

JOBS = [
    ("/Users/feixiao/Desktop/sat训练题库", "rw"),
    ("/Users/feixiao/Desktop/sat Math素材", "math"),
]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mybank_ocr")


def ocr_png(path):
    """PIL 转纯 RGB → PNG 字节 → tesseract stdin。"""
    im = Image.open(path).convert("RGB")
    import io
    buf = io.BytesIO()
    im.save(buf, "PNG")
    r = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "3"],
                       input=buf.getvalue(), capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for folder, tag in JOBS:
        fs = sorted(glob.glob(os.path.join(folder, "Screenshot*.png")))
        for i, f in enumerate(fs):
            name = "%s_%03d_%s" % (tag, i, os.path.basename(f)[11:25].replace(" ", ""))
            out_path = os.path.join(OUT, name + ".txt")
            if only and only not in os.path.basename(f):
                continue
            if os.path.exists(out_path) and os.path.getsize(out_path) > 50:
                continue
            text = ocr_png(f)
            with open(out_path, "w") as fh:
                fh.write(text)
            print("%s %s -> %d chars" % (tag, os.path.basename(f)[-24:], len(text)))
    print("done ->", OUT)


if __name__ == "__main__":
    main()
