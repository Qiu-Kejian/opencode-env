"""pdf2md.py — PDF 解读工具（pdf-inspector 主引擎 + pymupdf 渲染 + rapidocr 兜底）

智能路由：
  text_based    → pdf-inspector 直接转 Markdown（毫秒级，不出网）
  scanned/image → pymupdf 渲染页面 + rapidocr 识别（无文本层 PDF 兜底）
  mixed         → 文本页走 Markdown，需要 OCR 的页单独识别

用法：
  py pdf2md.py 文档.pdf
  py pdf2md.py a.pdf b.pdf -o 输出.txt          # 批量
  py pdf2md.py 扫描件.pdf --detect-only         # 只分类不提取
  py pdf2md.py 扫描件.pdf --no-ocr              # 扫描版也不 OCR，只报告
  py pdf2md.py 文档.pdf --pages                 # Markdown 中插入 <!-- Page N --> 分页标记
  py pdf2md.py 文档.pdf --dpi 300 --verbose     # 调 OCR 分辨率 / 详细信息
"""

import argparse
import sys
import time


def load_classifier():
    import pdf_inspector  # 本地安装的 pdf-inspector（PyPI 预编译 wheel）
    return pdf_inspector


def load_ocr(dpi):
    """懒加载 OCR 链路：pymupdf 渲染 + rapidocr 识别"""
    import pymupdf
    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()
    return pymupdf, ocr


def ocr_pdf(pdf_path, pages, dpi, out):
    """对指定页码（1-indexed）做渲染 + OCR，逐页输出"""
    pymupdf, ocr = load_ocr(dpi)
    doc = pymupdf.open(pdf_path)
    for p in pages:
        if p < 1 or p > doc.page_count:
            continue
        page = doc[p - 1]
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        result, _ = ocr(img_bytes)
        out.write(f"--- 第 {p} 页（OCR） ---\n")
        if not result:
            out.write("(未识别到文字)\n")
        else:
            for line in result:
                out.write(line[1] + "\n")
        out.write("\n")
    doc.close()


def main():
    parser = argparse.ArgumentParser(description="PDF 解读：分类 + Markdown 提取 + 扫描版 OCR 兜底")
    parser.add_argument("pdfs", nargs="+", help="PDF 路径（支持多个）")
    parser.add_argument("-o", "--output", help="输出到文件（UTF-8），缺省输出到控制台")
    parser.add_argument("--detect-only", action="store_true", help="只分类不提取")
    parser.add_argument("--no-ocr", action="store_true", help="扫描版/图片版不自动 OCR，只报告")
    parser.add_argument("--pages", action="store_true", help="Markdown 中插入 <!-- Page N --> 分页标记")
    parser.add_argument("--dpi", type=int, default=200, help="OCR 渲染分辨率（默认 200）")
    parser.add_argument("--verbose", action="store_true", help="输出分类详情（置信度/耗时/需OCR页等）")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    pi = load_classifier()
    out = sys.stdout
    if args.output:
        out = open(args.output, "w", encoding="utf-8")

    for path in args.pdfs:
        if len(args.pdfs) > 1:
            out.write(f"===== {path} =====\n")
        t0 = time.time()
        r = pi.detect_pdf(path)
        elapsed_ms = int((time.time() - t0) * 1000)

        if args.verbose:
            out.write(
                f"[{r.pdf_type} | 置信度 {r.confidence:.3f} | {r.page_count} 页 | 分类耗时 {elapsed_ms}ms]\n"
            )
            if r.pages_needing_ocr:
                out.write(f"  需OCR页: {r.pages_needing_ocr}\n")
            if getattr(r, "pages_with_tables", None):
                out.write(f"  表格页: {r.pages_with_tables}\n")
            if getattr(r, "pages_with_columns", None):
                out.write(f"  多栏页: {r.pages_with_columns}\n")
            if getattr(r, "has_encoding_issues", False):
                out.write("  警告: 字体编码异常，建议 OCR\n")
            if getattr(r, "title", None):
                out.write(f"  标题: {r.title}\n")

        if args.detect_only:
            continue

        if r.pdf_type == "text_based":
            if args.pages:
                pages_res = pi.extract_pages_markdown(path)
                for p in pages_res.pages:
                    out.write(f"<!-- Page {p.page + 1} -->\n")
                    out.write(p.markdown)
                    out.write("\n\n")
            else:
                full = pi.process_pdf(path)
                md = full.markdown or ""
                out.write(md)
                if not md.endswith("\n"):
                    out.write("\n")
                out.write("\n")
        elif r.pdf_type == "mixed":
            pages_res = pi.extract_pages_markdown(path)
            need_ocr = [p.page + 1 for p in pages_res.pages if p.needs_ocr]
            for p in pages_res.pages:
                if p.needs_ocr:
                    if args.no_ocr:
                        out.write(f"--- 第 {p.page + 1} 页（需OCR，--no-ocr 跳过） ---\n\n")
                    else:
                        continue  # 交给下面统一 OCR
                else:
                    out.write(p.markdown)
                    out.write("\n\n")
            if need_ocr and not args.no_ocr:
                ocr_pdf(path, need_ocr, args.dpi, out)
        else:  # scanned / image_based
            if args.no_ocr:
                out.write(f"(扫描版 PDF，{r.page_count} 页无文本层，--no-ocr 跳过识别)\n")
            else:
                ocr_pdf(path, list(range(1, r.page_count + 1)), args.dpi, out)
        out.write("\n")

    if args.output:
        out.close()
        print(f"已写入 {args.output}")


if __name__ == "__main__":
    main()
