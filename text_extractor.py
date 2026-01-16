import os
import io
import zipfile
from xml.etree import ElementTree

# Optional dependencies
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

class TextExtractor:
    @staticmethod
    def extract(file_path):
        """
        Extracts text from the given file based on its extension.
        Supports: .txt, .pdf, .docx, .hwp, .hwpx
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".txt":
            return TextExtractor._extract_txt(file_path)
        elif ext == ".pdf":
            return TextExtractor._extract_pdf(file_path)
        elif ext == ".docx":
            return TextExtractor._extract_docx(file_path)
        elif ext == ".hwp":
            return TextExtractor._extract_hwp(file_path)
        elif ext == ".hwpx":
            return TextExtractor._extract_hwpx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _extract_txt(file_path):
        # Try common encodings
        encodings = ["utf-8", "cp949", "euc-kr", "latin-1"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        # Fallback
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _extract_pdf(file_path):
        if not PdfReader:
            return "Error: pypdf library is missing. Install it with `pip install pypdf`."
        
        try:
            reader = PdfReader(file_path)
            text = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text.append(extracted)
            return "\n".join(text)
        except Exception as e:
            return f"Error extracting PDF: {str(e)}"

    @staticmethod
    def _extract_docx(file_path):
        if not docx:
            return "Error: python-docx library is missing. Install it with `pip install python-docx`."
        
        try:
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            return f"Error extracting DOCX: {str(e)}"

    @staticmethod
    def _extract_hwp(file_path):
        try:
            from hwp5.hwp5txt import TextTransform
            from hwp5.xmlmodel import Hwp5File
            from contextlib import closing
            
            # Capture output in memory instead of stdout
            output = io.BytesIO()
            
            # hwp5txt transform setup
            text_transform = TextTransform()
            transform = text_transform.transform_hwp5_to_text
            
            with closing(Hwp5File(file_path)) as hwp5file:
                transform(hwp5file, output)
            
            return output.getvalue().decode("utf-8", errors="ignore")
        except ImportError:
             return "Error: hwp5 (pyhwp) library is missing. Install it with `pip install pyhwp`."
        except Exception as e:
            return f"Error extracting HWP: {str(e)}"

    @staticmethod
    def _extract_hwpx(file_path):
        try:
            if not zipfile.is_zipfile(file_path):
                return "Error: .hwpx file is not a valid zip archive."
                
            with zipfile.ZipFile(file_path, 'r') as z:
                # Find section files
                content_files = [f for f in z.namelist() if f.startswith('Contents/section')]
                full_text = []
                
                # Sort to ensure correct order
                for cf in sorted(content_files):
                    with z.open(cf) as f:
                        tree = ElementTree.parse(f)
                        root = tree.getroot()
                        
                        # XML namespaces are annoying in ElementTree, ignore them by local-name checks or just wildcards if simple
                        # Typically HWPX text is in <hp:t> inside <hp:p>
                        # We will iterate all elements and look for 't' (text) tags
                        
                        for node in root.iter():
                            tag = node.tag.split('}')[-1] # strip namespace
                            if tag == 't' and node.text:
                                full_text.append(node.text)
                            elif tag == 'p':
                                full_text.append("\n")
                                
                return "".join(full_text)
        except Exception as e:
            return f"Error extracting HWPX: {str(e)}"
