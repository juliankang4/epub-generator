import os
import re
from ebooklib import epub

# Additional imports for multiple formats
try:
    from pypdf import PdfReader
    import docx
    import gethwp
except ImportError:
    pass

class EpubGenerator:
    def __init__(self, title, author="Unknown"):
        self.book = epub.EpubBook()
        self.book.set_identifier("novel-id-123456")
        self.book.set_title(title)
        self.book.set_language("ko")
        self.book.add_author(author)
        
        self.chapters = []
        self.style = """
            @namespace epub "http://www.idpf.org/2007/ops";
            body { 
                font-family: "Noto Sans KR", serif; 
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
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        
        elif ext == ".pdf":
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
            
        elif ext == ".docx":
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
            
        elif ext == ".hwp":
            try:
                from hwp5.hwp5txt import TextTransform
                from hwp5.xmlmodel import Hwp5File
                from contextlib import closing
                import io
                
                text_transform = TextTransform()
                transform = text_transform.transform_hwp5_to_text
                # hwp5txt writes bytes to the output stream
                output = io.BytesIO()
                with closing(Hwp5File(file_path)) as hwp5file:
                    transform(hwp5file, output)
                return output.getvalue().decode("utf-8", errors="ignore")
            except Exception as e:
                return f"Error extracting HWP: {str(e)}"
                
        elif ext == ".hwpx":
            try:
                # First try pyhwp's hwp5txt logic (it might support HWPX if it's treated as Hwp5File)
                # But HWPX is typically just a zip of XMLs.
                import zipfile
                from xml.etree import ElementTree
                
                if not zipfile.is_zipfile(file_path):
                    return "Error: .hwpx file is not a valid zip archive."
                    
                with zipfile.ZipFile(file_path, 'r') as z:
                    content_files = [f for f in z.namelist() if f.startswith('Contents/section')]
                    full_text = []
                    for cf in sorted(content_files):
                        with z.open(cf) as f:
                            tree = ElementTree.parse(f)
                            # Extract text from p nodes which are typically for paragraphs
                            # In HWPX, text is often in <hp:t> or similar
                            for node in tree.iter():
                                if node.tag.endswith('}t') and node.text:
                                    full_text.append(node.text)
                                elif node.tag.endswith('}p'):
                                    full_text.append("\n") # Paragraph break
                    return "".join(full_text)
            except Exception as e:
                return f"Error extracting HWPX: {str(e)}"
                
        elif ext == ".doc":
            return "Legacy .doc format is not directly supported. Please save as .docx or .txt."
            
        return ""

    def process_text(self, raw_text):
        # Normalize line endings
        raw_text = raw_text.replace("\r\n", "\n")
        
        # Split into chapters
        # Look for "# [Chapter Name]" or "제 N 화 [제목]" or "Chapter N"
        # Using a non-capturing group for the prefix, but capturing the whole line
        chapter_pattern = r"^((?:#\s+|제\s*\d+\s*[화장]\s*|Chapter\s*\d+\s*).*$)"
        
        parts = re.split(chapter_pattern, raw_text, flags=re.MULTILINE)
        
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
        raw_text = gen.extract_text(args.input)
        
        if not raw_text.strip():
            print(f"Error: No text extracted from {args.input}")
            sys.exit(1)
            
        gen.process_text(raw_text)
        gen.generate(args.output)
    else:
        print(f"Error: File not found {args.input}")
