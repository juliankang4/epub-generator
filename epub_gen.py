import os
import re
import sys
import uuid
from ebooklib import epub
from text_extractor import TextExtractor, ExtractionError

class EpubGenerator:
    # Pre-compile regex for performance
    # Supports various chapter patterns:
    # - # Chapter 1, ## 제목
    # - 제1화, 제 1 화, 제1장, 제 1 장
    # - 1화, 1장 (숫자로 시작)
    # - Chapter 1, CHAPTER 1
    # - Episode 1, EP.1, ep 1
    # - 프롤로그, 에필로그
    # - Part 1, PART 1
    CHAPTER_PATTERN = re.compile(
        r"^("
        r"(?:#+ .+)|"                                    # Markdown headers
        r"(?:제\s*\d+\s*[화장편부](?:\s*.+)?)|"           # 제1화, 제 1 장, 제1부
        r"(?:\d+\s*[화장편부](?:\s*.+)?)|"               # 1화, 1장
        r"(?:Chapter\s*\d+(?:\s*.+)?)|"                  # Chapter 1
        r"(?:Episode\s*\d+(?:\s*.+)?)|"                  # Episode 1
        r"(?:EP\.?\s*\d+(?:\s*.+)?)|"                    # EP.1, EP 1
        r"(?:Part\s*\d+(?:\s*.+)?)|"                     # Part 1
        r"(?:프롤로그|에필로그|서장|종장|막간)(?:\s*.+)?" # Korean chapter markers
        r")$",
        flags=re.MULTILINE | re.IGNORECASE
    )

    def __init__(self, title, author="Unknown"):
        self.book = epub.EpubBook()
        # UUID 사용으로 고유 식별자 보장
        self.book.set_identifier(f"urn:uuid:{uuid.uuid4()}")
        self.book.set_title(title)
        self.book.set_language("ko")
        self.book.add_author(author)

        self.chapters = []
        self.cover_image = None
        # 다양한 EPUB 리더 호환을 위한 폰트 폴백 체인
        self.style = """
            @namespace epub "http://www.idpf.org/2007/ops";
            body {
                font-family: "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", "맑은 고딕", sans-serif;
                line-height: 1.8;
                padding: 5% 10%;
                text-align: justify;
            }
            h1 { text-align: center; margin-bottom: 2em; border-bottom: 1px solid #ccc; padding-bottom: 0.5em; }
            p { margin: 0; text-indent: 1em; margin-bottom: 1em; }
            p.dialogue { text-indent: 0; font-style: normal; }
            .scene-break { text-align: center; margin: 2em 0; font-weight: bold; }
        """

    def extract_text(self, file_path):
        """Delegates to TextExtractor"""
        return TextExtractor.extract(file_path)

    def set_cover(self, image_path):
        """표지 이미지 설정"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"표지 이미지를 찾을 수 없습니다: {image_path}")

        ext = os.path.splitext(image_path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            raise ValueError("지원하는 이미지 형식: JPG, PNG, GIF")

        with open(image_path, 'rb') as f:
            image_data = f.read()

        self.book.set_cover(f"cover{ext}", image_data)
        self.cover_image = image_path

    def get_chapter_preview(self, raw_text, max_chapters=10):
        """챕터 미리보기 생성 (변환 전 확인용)"""
        raw_text = raw_text.replace("\r\n", "\n")
        parts = self.CHAPTER_PATTERN.split(raw_text)

        preview = []
        if len(parts) <= 1:
            # 챕터가 없으면 전체를 하나로
            word_count = len(raw_text.split())
            preview.append({
                'title': 'Chapter 1',
                'word_count': word_count,
                'preview': raw_text[:200] + '...' if len(raw_text) > 200 else raw_text
            })
        else:
            # 서문이 있으면 추가
            if parts[0].strip():
                content = parts[0].strip()
                preview.append({
                    'title': 'Introduction',
                    'word_count': len(content.split()),
                    'preview': content[:200] + '...' if len(content) > 200 else content
                })

            # 각 챕터 정보
            for i in range(1, len(parts), 2):
                if len(preview) >= max_chapters:
                    break
                title = parts[i].strip()
                content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                preview.append({
                    'title': title,
                    'word_count': len(content.split()),
                    'preview': content[:200] + '...' if len(content) > 200 else content
                })

        total_chapters = (len(parts) - 1) // 2 if len(parts) > 1 else 1
        if parts[0].strip() and len(parts) > 1:
            total_chapters += 1

        return {
            'total_chapters': total_chapters,
            'chapters': preview,
            'total_words': len(raw_text.split())
        }

    def process_text(self, raw_text):
        # Normalize line endings
        raw_text = raw_text.replace("\r\n", "\n")
        
        # Split into chapters using pre-compiled regex
        parts = self.CHAPTER_PATTERN.split(raw_text)
        
        if len(parts) <= 1:
            # No chapters found, treat as one
            self.add_chapter("Chapter 1", raw_text)
        else:
            # First part might be intro/metadata
            if parts[0].strip():
                self.add_chapter("Introduction", parts[0])
            
            # parts[0] is intro, [1] is chap1 title, [2] is chap1 content, [3] is chap2 title...
            for i in range(1, len(parts), 2):
                title = parts[i].strip()
                content = parts[i+1].strip() if i+1 < len(parts) else ""
                self.add_chapter(title, content)

    def format_content(self, text):
        lines = text.split("\n")
        formatted_html = ""
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Scene break detection
            if line_stripped in ["***", "---", "###", "==="]:
                formatted_html += '<p class="scene-break">***</p>'
            elif line_stripped.startswith('"') or line_stripped.startswith("'") or line_stripped.startswith('「') or line_stripped.startswith('『'):
                # Dialogue: no indent
                formatted_html += f'<p class="dialogue">{line_stripped}</p>'
            else:
                # Narrative: default indent
                formatted_html += f"<p>{line_stripped}</p>"
        
        return formatted_html

    def add_chapter(self, title, content):
        index = len(self.chapters) + 1
        file_name = f"chap_{index:03d}.xhtml"
        
        chapter = epub.EpubHtml(title=title, file_name=file_name, lang="ko")
        
        html_content = f"<h1>{title}</h1>"
        html_content += self.format_content(content)
        
        # Link CSS
        chapter.add_link(href="style/main.css", rel="stylesheet", type="text/css")
        
        chapter.content = f'<html><head><meta charset="UTF-8"/></head><body>{html_content}</body></html>'
        
        self.book.add_item(chapter)
        self.chapters.append(chapter)

    def generate(self, output_path):
        # Set TOC, Spine, etc.
        self.book.toc = tuple(self.chapters)
        
        # Add basic structure
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        
        # Define CSS file
        style_item = epub.EpubItem(uid="style_main", file_name="style/main.css", media_type="text/css", content=self.style)
        self.book.add_item(style_item)
        
        # Add default spine
        self.book.spine = ["nav"] + self.chapters
        
        # Write to file
        epub.write_epub(output_path, self.book, {})
        print(f"Successfully generated: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert Text to EPUB for Web Novels")
    parser.add_argument("--input", required=True, help="Path to input .txt file")
    parser.add_argument("--output", required=True, help="Path to output .epub file")
    parser.add_argument("--title", default="My Web Novel", help="Title of the book")
    parser.add_argument("--author", default="Writer", help="Author name")
    
    args = parser.parse_args()
    
    if os.path.exists(args.input):
        gen = EpubGenerator(args.title, args.author)
        try:
            raw_text = gen.extract_text(args.input)
        except Exception as e:
            print(f"Extraction failed: {str(e)}")
            sys.exit(1)
        
        if not raw_text.strip():
            print(f"Error: No text extracted from {args.input}")
            sys.exit(1)
            
        gen.process_text(raw_text)
        gen.generate(args.output)
    else:
        print(f"Error: File not found {args.input}")
