import sys
sys.path.insert(0, r'c:\Users\himan\Desktop\blog_generation_pipeline')

try:
    from blog_platform.config import Config
    from blog_platform.blog_generator import BlogGenerator
    print("✓ Imports successful")
    print(f"✓ Config loaded: API Key available: {bool(Config.MEGALLM_API_KEY)}")
    print(f"✓ Model: {Config.MODEL}")
    print(f"✓ Base URL: {Config.MEGALLM_BASE_URL}")
    
    # Try to create generator
    generator = BlogGenerator(
        Config.MEGALLM_API_KEY,
        Config.MEGALLM_BASE_URL,
        Config.MODEL,
        max_retries=3
    )
    print("✓ BlogGenerator created successfully")
    print("✓ Ready to generate blogs with retry logic")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
