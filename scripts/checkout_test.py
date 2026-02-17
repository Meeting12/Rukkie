import requests, json

base = 'http://127.0.0.1:8000'
s = requests.Session()
print('GET products')
r = s.get(base + '/api/products/')
print(r.status_code, r.text[:500])
items = r.json().get('value') if isinstance(r.json(), dict) else r.json()
if not items:
    print('no products')
    raise SystemExit(1)
prod_id = items[0]['id']
print('Using product', prod_id)

print('POST add to cart')
r = s.post(base + '/api/cart/add/', json={'product_id': prod_id, 'quantity': 1})
print(r.status_code, r.text)

checkout_payload = {
    'shipping_method': None,
    'shipping_address': {
        'full_name': 'Test User',
        'line1': '123 Main St',
        'city': 'City',
        'postal_code': '12345',
        'country': 'Testland'
    },
    'billing_address': {
        'full_name': 'Test User',
        'line1': '123 Main St',
        'city': 'City',
        'postal_code': '12345',
        'country': 'Testland'
    }
}
print('POST checkout')
r = s.post(base + '/api/checkout/', json=checkout_payload)
print('status', r.status_code)
try:
    print('body', r.json())
except Exception:
    print('body text', r.text)
