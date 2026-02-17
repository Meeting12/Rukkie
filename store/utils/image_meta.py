import os
import re
from collections import Counter

from PIL import Image


LOW_DETAIL_NOTE = "Image quality limits detailed analysis."


CATEGORY_KEYWORDS = {
    "Home Decor": {
        "decor", "lamp", "vase", "sofa", "chair", "table", "mirror", "plant", "bonsai",
        "garden", "planter", "shelf", "rug", "cushion", "lighting", "wall", "indoor",
    },
    "Fashion": {
        "shirt", "dress", "jacket", "coat", "jeans", "shoe", "sneaker", "bag", "watch",
        "hat", "hoodie", "tshirt", "trouser", "shorts", "sandal", "wallet",
    },
    "Beauty": {
        "serum", "cream", "lotion", "mask", "oil", "perfume", "fragrance", "cosmetic",
        "makeup", "skincare", "cleanser", "toner",
    },
    "Electronics": {
        "phone", "laptop", "headphone", "earbud", "speaker", "charger", "camera", "tablet",
        "monitor", "keyboard", "mouse", "smartwatch",
    },
    "Kitchen": {
        "mug", "bottle", "pan", "pot", "knife", "blender", "kettle", "plate", "bowl",
        "utensil", "cookware", "cup", "cutlery",
    },
    "Fitness": {
        "yoga", "dumbbell", "barbell", "mat", "band", "bike", "helmet", "sport", "fitness",
        "training", "workout",
    },
    "Office": {
        "desk", "notebook", "planner", "pen", "organizer", "stationery", "office", "file",
        "chair", "stand",
    },
}


PRICE_HINTS = {
    "Home Decor": "$39-$249",
    "Fashion": "$29-$199",
    "Beauty": "$15-$89",
    "Electronics": "$49-$499",
    "Kitchen": "$19-$149",
    "Fitness": "$24-$199",
    "Office": "$15-$159",
    "General": "$25-$199",
}


def _clean_title_from_filename(filename: str) -> str:
    name = os.path.splitext(os.path.basename(filename or ""))[0]
    name = re.sub(r"^(img|dsc|pxl|mvimg)[\W_0-9]*", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    if not re.search(r"[A-Za-z]", name):
        return ""
    return name.title()[:70]


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


def _safe_keywords(text: str, limit: int = 8) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", text or "") if len(w) > 2]
    deduped = list(dict.fromkeys(words))
    return deduped[:limit]


def _guess_category(tokens: set[str]) -> str:
    best_category = "General"
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = len(tokens.intersection(keywords))
        if score > best_score:
            best_category = category
            best_score = score
    return best_category


def _infer_material(tokens: set[str]) -> str:
    material_map = {
        "leather": "Leather",
        "wood": "Wood",
        "metal": "Metal",
        "steel": "Stainless Steel",
        "cotton": "Cotton",
        "linen": "Linen",
        "wool": "Wool",
        "ceramic": "Ceramic",
        "glass": "Glass",
        "plastic": "Plastic",
        "bamboo": "Bamboo",
    }
    for keyword, material in material_map.items():
        if keyword in tokens:
            return material
    return ""


def _infer_style(tokens: set[str]) -> str:
    style_map = {
        "modern": "Modern",
        "minimal": "Minimalist",
        "minimalist": "Minimalist",
        "vintage": "Vintage",
        "classic": "Classic",
        "luxury": "Premium",
        "premium": "Premium",
        "sport": "Sport",
        "casual": "Casual",
    }
    for keyword, style in style_map.items():
        if keyword in tokens:
            return style
    return "Contemporary"


def _most_common_color_rgb(img: Image.Image) -> tuple[int, int, int] | None:
    small = img.convert("RGB").copy()
    small.thumbnail((72, 72))
    pixels = list(small.getdata())
    if not pixels:
        return None
    return Counter(pixels).most_common(1)[0][0]


def _rgb_to_hex(rgb: tuple[int, int, int] | None) -> str:
    if not rgb:
        return ""
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _rgb_to_color_name(rgb: tuple[int, int, int] | None) -> str:
    if not rgb:
        return ""
    r, g, b = rgb
    avg = (r + g + b) / 3
    if max(r, g, b) - min(r, g, b) < 18:
        if avg < 40:
            return "Black"
        if avg > 220:
            return "White"
        return "Gray"
    if r > 180 and g > 150 and b < 120:
        return "Gold"
    if r > 150 and g > 90 and b < 80:
        return "Brown"
    if r > 130 and b > 120 and g < 110:
        return "Purple"
    if g > r and g > b:
        return "Green"
    if b > r and b > g:
        return "Blue"
    if r > g and r > b:
        return "Red"
    return "Neutral"


def _fallback_title(category: str, color_name: str) -> str:
    if category == "General":
        return "Premium Product"
    if color_name:
        return f"{color_name} {category} Product"
    return f"Premium {category} Product"


def _build_copy(title: str, category: str, color_name: str, low_detail: bool) -> tuple[str, str, list[str], list[str]]:
    color_phrase = f" in a {color_name.lower()} tone" if color_name else ""
    short_description = (
        f"{title}{color_phrase} delivers a polished, premium look with practical everyday appeal. "
        "Designed to be visually strong online and easy to style in real spaces."
    )

    if category == "Home Decor":
        description = (
            f"{title} is a decorative piece created to elevate interiors with calm, intentional styling. "
            "Its visible form, finish, and composition support a clean, curated atmosphere in homes, offices, or hospitality spaces.\n\n"
            "Use it to add depth, texture, and character without overwhelming the room. "
            "It is well-suited for minimalist, contemporary, and premium lifestyle setups."
        )
        features = [
            "Statement-ready aesthetic that upgrades modern interior styling",
            "Balanced visual profile that blends with neutral or layered palettes",
            "Premium presentation quality suitable for storefront and catalog display",
            "Flexible placement across living rooms, entryways, lounges, and office spaces",
            "Designed to create a refined focal point while maintaining a clean environment",
        ]
        benefits = [
            "Makes spaces feel more curated and high-end",
            "Adds visual interest without heavy redesign",
            "Supports cohesive styling across different room themes",
        ]
    elif category == "Fashion":
        description = (
            f"{title} combines style-forward design with everyday wearability. "
            "The visible silhouette and finish suggest a product built for confident daily use while keeping a premium fashion identity.\n\n"
            "It pairs easily with casual and elevated outfits, making it a reliable choice for wardrobe rotation."
        )
        features = [
            "Modern silhouette that upgrades everyday outfits",
            "Versatile styling potential for day-to-night wear",
            "Clean visual lines that support a premium wardrobe feel",
            "Designed for repeat use across multiple outfit combinations",
            "Storefront-ready presentation that photographs well for e-commerce",
        ]
        benefits = [
            "Makes outfit planning faster with flexible styling",
            "Helps create a polished look with minimal effort",
            "Improves perceived wardrobe quality through consistent aesthetics",
        ]
    elif category == "Beauty":
        description = (
            f"{title} is positioned as a premium beauty essential with a clean, trust-focused presentation. "
            "Its visible packaging style supports a modern self-care routine and shelf appeal.\n\n"
            "It fits well in curated skincare or grooming collections where consistency and visual quality matter."
        )
        features = [
            "Clean premium presentation that builds product trust",
            "Shelf-friendly design suited for personal or professional setups",
            "Aesthetic packaging that supports modern self-care branding",
            "Strong visual identity for online merchandising and ads",
            "Pairs naturally with existing skincare and beauty assortments",
        ]
        benefits = [
            "Creates a more premium routine experience",
            "Improves visual consistency across beauty collections",
            "Supports stronger first impressions in product listings",
        ]
    elif category == "Electronics":
        description = (
            f"{title} presents a contemporary tech-forward look focused on daily convenience and visual clarity. "
            "Its form factor appears optimized for modern setups where design and functionality need to work together.\n\n"
            "It fits naturally into home, office, and mobile environments that value clean technology aesthetics."
        )
        features = [
            "Modern product styling suited for current tech environments",
            "Compact, display-friendly appearance for desks and workstations",
            "Premium visual finish that strengthens product credibility",
            "Merchandising-ready presentation for high-conversion listing pages",
            "Designed to complement other contemporary digital accessories",
        ]
        benefits = [
            "Improves desk and setup aesthetics",
            "Supports a cleaner and more organized device ecosystem",
            "Enhances buyer confidence through polished visual presentation",
        ]
    else:
        description = (
            f"{title} offers a premium visual profile built for practical daily use and elevated presentation. "
            "The visible form and finish are suitable for shoppers seeking both style and utility.\n\n"
            "It is positioned as a versatile product option for modern lifestyles and clean merchandising."
        )
        features = [
            "Premium visual appeal designed for modern shoppers",
            "Balanced style-to-function profile for everyday use",
            "Flexible integration across home, office, or personal routines",
            "Strong presentation quality for product pages and campaigns",
            "Refined look that supports an upscale brand perception",
        ]
        benefits = [
            "Improves perceived value at first glance",
            "Supports easier styling and integration into daily life",
            "Drives stronger visual consistency across catalog listings",
        ]

    if low_detail:
        description = f"{description}\n\n{LOW_DETAIL_NOTE}"
        features[-1] = "Image quality limits precise material and dimensional validation"

    return short_description, description, features[:5], benefits[:3]


def generate_product_json_from_image(image_field) -> dict:
    """
    Generate conservative, product-focused metadata from image + filename context.
    The output avoids unverified brand/spec claims and is suitable for direct admin review.
    """
    fallback = {
        "title": "",
        "title_source": "none",
        "slug": "",
        "short_description": "",
        "description": LOW_DETAIL_NOTE,
        "features": [],
        "benefits": [],
        "specifications": {"material": "", "color": "", "style": "", "category": "", "dimensions": ""},
        "suggested_tags": [],
        "seo_keywords": [],
        "meta_description": "",
        "suggested_price_range": "",
        "confidence": 0.35,
    }

    try:
        filename = getattr(image_field, "name", "")
        image = Image.open(image_field).convert("RGB")
        width, height = image.size
    except Exception:
        return fallback

    raw_title = _clean_title_from_filename(filename)
    title_tokens = set(_safe_keywords(raw_title, limit=20))
    category = _guess_category(title_tokens)
    material = _infer_material(title_tokens)
    style = _infer_style(title_tokens)

    rgb = _most_common_color_rgb(image)
    color_hex = _rgb_to_hex(rgb)
    color_name = _rgb_to_color_name(rgb)
    low_detail = width < 500 or height < 500

    if raw_title:
        title = raw_title
        title_source = "filename"
        confidence = 0.93 if not low_detail else 0.88
    else:
        title = _fallback_title(category, color_name)
        title_source = "fallback"
        confidence = 0.87 if not low_detail else 0.86

    slug = _slugify(title)
    short_description, description, features, benefits = _build_copy(title, category, color_name, low_detail)

    keyword_base = _safe_keywords(title, limit=8)
    if category != "General":
        keyword_base.append(category.lower().replace(" ", "-"))
    if color_name:
        keyword_base.append(color_name.lower())
    seo_keywords = list(dict.fromkeys(keyword_base))[:12]
    suggested_tags = list(dict.fromkeys(keyword_base))[:8]

    meta_description = (
        f"{title}: premium {category.lower()} item with clean design, everyday usability, and catalog-ready presentation."
    )[:155]

    return {
        "title": title,
        "title_source": title_source,
        "slug": slug,
        "short_description": short_description,
        "description": description,
        "features": features,
        "benefits": benefits,
        "specifications": {
            "material": material,
            "color": color_name or color_hex or "",
            "style": style,
            "category": category,
            "dimensions": "",
        },
        "suggested_tags": suggested_tags,
        "seo_keywords": seo_keywords,
        "meta_description": meta_description,
        "suggested_price_range": PRICE_HINTS.get(category, PRICE_HINTS["General"]),
        "confidence": confidence,
    }
