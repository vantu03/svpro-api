import fitz
from typing import List, Dict

class PDFExtractor:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.doc = fitz.open(file_path)
        self.chunks: List[Dict] = []

    def extract(self, zoom: int = 2):
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]

            # Lấy text
            text = page.get_text("text")

            # Lấy ảnh nhúng trong trang
            images = []
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                pix = fitz.Pixmap(self.doc, xref)
                if pix.n > 4:  # chuyển về RGB nếu CMYK/alpha
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img_bytes = pix.tobytes("png")
                images.append({
                    "index": img_index,
                    "xref": xref,
                    "bytes": img_bytes,
                })

            # Render nguyên trang thành ảnh
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            page_image = pix.tobytes("png")

            # Lưu vào chunks
            self.chunks.append({
                "page": page_num + 1,
                "text": text,
                "images": images,
                "page_image": page_image
            })
        return self.chunks

    def close(self):
        self.doc.close()
