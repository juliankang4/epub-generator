import os
import sys
from text_extractor import TextExtractor
from epub_gen import EpubGenerator

def test_file(file_path):
    print(f"Testing {file_path}...")
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
        
    try:
        content = TextExtractor.extract(file_path)
        if content.startswith("Error"):
            print(f"Failed to extract: {content}")
            return False
        
        print(f"Success! Extracted {len(content)} characters.")
        print(f"Preview: {content[:100].replace(chr(10), ' ')}...")
        
        # Test full generation
        output_epub = file_path + ".epub"
        gen = EpubGenerator("Test Book", "Test Author")
        gen.process_text(content)
        gen.generate(output_epub)
        
        if os.path.exists(output_epub):
            print(f"EPUB generated successfully: {output_epub}")
            return True
        else:
            print("EPUB generation failed.")
            return False
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== EPUB Generator Verification ===")
    
    files_to_test = ["sample.txt", "test.hwp"]
    success_count = 0
    
    for f in files_to_test:
        print("-" * 40)
        full_path = os.path.abspath(f)
        if test_file(full_path):
            success_count += 1
            
    print("=" * 40)
    print(f"Tests Completed: {success_count}/{len(files_to_test)} passed.")
    
    if success_count == len(files_to_test):
        sys.exit(0)
    else:
        sys.exit(1)
