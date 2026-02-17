import json
from pathlib import Path

p = Path('api_products.json')
if not p.exists():
    print('api_products.json not found')
    raise SystemExit(1)

# Read text and strip UTF-8 BOM if present
raw = p.read_bytes()
if raw.startswith(b'\xef\xbb\xbf'):
    text = raw.decode('utf-8-sig')
else:
    # try utf-8 then fallback to latin-1
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')

data = json.loads(text)
# data may be list or paginated
items = data if isinstance(data, list) else data.get('results', [])

def map_product(p):
    return {
        'id': str(p.get('id')),
        'name': p.get('name'),
        'slug': p.get('slug'),
        'description': p.get('description') or '',
        'price': float(p.get('price') or 0),
        'originalPrice': float(p.get('original_price') or p.get('originalPrice') or 0) if (p.get('original_price') or p.get('originalPrice')) else None,
        'images': [ (i.get('image') or i.get('url') or i) for i in (p.get('images') or []) ],
        'category': (p.get('categories')[0].get('name') if p.get('categories') else (p.get('category') or 'Uncategorized')),
        'rating': float(p.get('rating') or 0),
        'reviewCount': int(p.get('review_count') or p.get('reviewCount') or 0),
        'inStock': (int(p.get('stock') or 0) > 0) if 'stock' in p else (p.get('inStock', True)),
        'isDigital': bool(p.get('is_digital') or p.get('isDigital')),
        'features': p.get('features') or [],
        'benefits': p.get('benefits') or [],
    }

mapped = [map_product(x) for x in items]

if not mapped:
    print('No products found in API response')
else:
    print(json.dumps(mapped[0], indent=2, ensure_ascii=False))
