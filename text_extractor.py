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


class ExtractionError(Exception):
    """텍스트 추출 중 발생한 오류"""
    pass


class MissingLibraryError(ExtractionError):
    """필요한 라이브러리가 설치되지 않음"""
    pass


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
            raise MissingLibraryError("pypdf 라이브러리가 필요합니다. `pip install pypdf`로 설치하세요.")

        try:
            reader = PdfReader(file_path)
            text = []
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text.append(extracted)
            result = "\n".join(text)
            if not result.strip():
                raise ExtractionError("PDF에서 텍스트를 추출할 수 없습니다. 이미지 기반 PDF일 수 있습니다.")
            return result
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"PDF 추출 오류: {str(e)}")

    @staticmethod
    def _extract_docx(file_path):
        if not docx:
            raise MissingLibraryError("python-docx 라이브러리가 필요합니다. `pip install python-docx`로 설치하세요.")

        try:
            doc = docx.Document(file_path)
            result = "\n".join([para.text for para in doc.paragraphs])
            if not result.strip():
                raise ExtractionError("DOCX 파일이 비어있습니다.")
            return result
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"DOCX 추출 오류: {str(e)}")

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

            result = output.getvalue().decode("utf-8", errors="ignore")
            if not result.strip():
                raise ExtractionError("HWP 파일에서 텍스트를 추출할 수 없습니다. 파일이 손상되었거나 지원하지 않는 형식입니다.")
            return result
        except ImportError:
            raise MissingLibraryError("pyhwp 라이브러리가 필요합니다. `pip install pyhwp`로 설치하세요.")
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"HWP 추출 오류: {str(e)}")

    @staticmethod
    def _extract_hwpx(file_path):
        try:
            if not zipfile.is_zipfile(file_path):
                raise ExtractionError("HWPX 파일이 유효한 ZIP 형식이 아닙니다.")

            with zipfile.ZipFile(file_path, 'r') as z:
                # Find section files
                content_files = [f for f in z.namelist() if f.startswith('Contents/section')]
                if not content_files:
                    raise ExtractionError("HWPX 파일에서 콘텐츠를 찾을 수 없습니다.")

                full_text = []

                # Sort to ensure correct order
                for cf in sorted(content_files):
                    with z.open(cf) as f:
                        tree = ElementTree.parse(f)
                        root = tree.getroot()

                        for node in root.iter():
                            tag = node.tag.split('}')[-1]  # strip namespace
                            if tag == 't' and node.text:
                                full_text.append(node.text)
                            elif tag == 'p':
                                full_text.append("\n")

                result = "".join(full_text)
                if not result.strip():
                    raise ExtractionError("HWPX 파일이 비어있습니다.")
                return result
        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(f"HWPX 추출 오류: {str(e)}")
