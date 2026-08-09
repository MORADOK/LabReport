from dotenv import load_dotenv
import os

# โหลด .env
load_dotenv()

# ดึงค่า DATABASE_URL
url = os.getenv('DATABASE_URL')

print(f'DATABASE_URL exists: {url is not None}')
print(f'DATABASE_URL value: [{url}]')
if url:
    print(f'Length: {len(url)}')
    print(f'First 100 chars: {repr(url[:100])}')
    print(f'Starts with "DATABASE_URL=": {url.startswith("DATABASE_URL=")}')
