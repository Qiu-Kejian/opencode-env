import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="OCR 图片文字提取（rapidocr-onnxruntime）")
    parser.add_argument("images", nargs="+", help="图片路径（支持多个）")
    parser.add_argument("-o", "--output", help="输出到文件（UTF-8），缺省输出到控制台")
    parser.add_argument("--verbose", action="store_true", help="同时输出每行坐标")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")

    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()
    out = sys.stdout
    if args.output:
        out = open(args.output, "w", encoding="utf-8")

    for path in args.images:
        result, _ = ocr(path)
        if len(args.images) > 1:
            out.write(f"===== {path} =====\n")
        if not result:
            out.write("(未识别到文字)\n")
            continue
        for line in result:
            if args.verbose:
                box, text, score = line
                try:
                    out.write(f"{text}  [{float(score):.2f}]\n")
                except (TypeError, ValueError):
                    out.write(f"{text}  [{score}]\n")
            else:
                out.write(line[1] + "\n")
        out.write("\n")

    if args.output:
        out.close()
        print(f"已写入 {args.output}")

if __name__ == "__main__":
    main()
