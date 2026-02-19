# De-Rukkies Collections

## Assistant API

Endpoint: `POST /api/assistant/chat/`

Request body:

```json
{
  "message": "find glow soap",
  "session_id": null,
  "context": null
}
```

Response body:

```json
{
  "reply": "Top matches for 'glow soap':\n- Glow Soap - $15.00 (In stock)",
  "suggestions": ["Show featured products", "Find skincare products", "Search by category"],
  "intent": "product_search",
  "session_id": "2ab9f0f655f24cc1a167887f5e437f26"
}
```

Example curl:

```bash
curl -X POST http://127.0.0.1:8000/api/assistant/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message":"track order ABC123DEF456","session_id":null,"context":null}'
```

Notes:
- Intent routing is deterministic (custom keyword/regex rules first).
- Shipping, returns, and payment replies use DB-backed `AssistantPolicy` records.
- Product search replies include top 5 matching products with price and stock status.
