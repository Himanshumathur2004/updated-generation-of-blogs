import sys
import traceback
import os
import logging

# Set up logging to capture HTTP details
logging.basicConfig(level=logging.DEBUG)

# Add the current directory to the path
sys.path.insert(0, os.getcwd())

print('=== Blog Generator Test Script ===')
print(f'Working Directory: {os.getcwd()}')
print()

try:
    print('[1] Importing BlogGenerator...')
    from blog_platform.blog_generator import BlogGenerator
    print('    ? BlogGenerator imported successfully')
    print()
    
    print('[2] Creating BlogGenerator instance with hardcoded MegaLLM credentials...')
    generator = BlogGenerator(
        api_key='test_api_key_12345',
        base_url='http://localhost:5000',
        model='megalm-v1'
    )
    print('    ? BlogGenerator instance created')
    print(f'    - API Key: {generator.api_key}')
    print(f'    - Base URL: {generator.base_url}')
    print(f'    - Model: {generator.model}')
    print(f'    - Headers: {generator.headers}')
    print()
    
    print('[3] Attempting to generate blog with topic \"Cost Optimization\"...')
    print('    Preparing request...')
    
    result = generator.generate_blog(
        topic='Cost Optimization',
        topic_description='Strategies for reducing cloud infrastructure costs',
        keywords=['cloud', 'cost', 'optimization', 'AWS'],
        word_count_min=500,
        word_count_max=800
    )
    
    print('    ? Blog generation completed')
    print()
    
    print('[4] Detailed Response Information:')
    print('    ' + '='*50)
    if isinstance(result, dict):
        for key, value in result.items():
            val_str = str(value)
            if len(val_str) > 200:
                print(f'    {key}:')
                print(f'      {val_str[:200]}...')
            else:
                print(f'    {key}: {value}')
    elif result is None:
        print('    Response: None (Empty/Error response)')
    else:
        print(f'    Response Type: {type(result)}')
        print(f'    Response Body: {str(result)[:300]}')
    print('    ' + '='*50)
    
except Exception as e:
    print(f'? ERROR OCCURRED')
    print()
    print('[ERROR DETAILS]')
    print('='*60)
    print(f'Exception Type: {type(e).__name__}')
    print(f'Exception Message: {str(e)}')
    print()
    print('[FULL TRACEBACK]')
    traceback.print_exc()
    print('='*60)
