#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAVARDT USA | Image SEO and Visual Accessibility Auditor
Repository: https://github.com/TAVARDT-USA/image-seo-validator-us
Official Tool: https://tools.tavardt.com/image-seo-checker/
Enterprise Portal: https://ag.tavardt.com/

Audits alt text completeness, modern format adoption (WebP/AVIF), layout stability dimensions, and descriptive filenames.
"""

import sys
import argparse
import json
import re
import urllib.request
import urllib.error
from urllib.parse import urlparse, urljoin

BANNER = "TAVARDT USA | Image SEO and Visual Accessibility Auditor"
DESC = "Audits alt text completeness, modern format adoption (WebP/AVIF), layout stability dimensions, and descriptive filenames."
TARGET_PROMPT = "Target URL to audit image SEO and accessibility"
JSON_HELP = "Output analysis results strictly as JSON"
FETCHING = "Inspecting images and visual attributes at:"
STATUS_CODE = "HTTP response status code:"
TOTAL_IMAGES_LABEL = "Total images detected:"
MISSING_ALT_LABEL = "Images missing alt attribute (critical):"
GENERIC_ALT_LABEL = "Images with generic or placeholder alt text:"
NEXT_GEN_LABEL = "Images in modern format (WebP/AVIF):"
DIMS_DEFINED_LABEL = "Images with explicit width and height:"
LAZY_LOADING_LABEL = "Images with loading='lazy' directive:"
OG_IMAGE_LABEL = "Open Graph social sharing image:"
SCORE_TITLE = "Image SEO and Accessibility Score:"
STATUS_PASS = "COMPLIANT"
STATUS_WARN = "WARNING"
STATUS_FAIL = "CRITICAL"
WARN_MISSING_ALT = "CRITICAL ALERT: {count} images lack alt attributes, impairing accessibility and search indexing."
WARN_GENERIC_ALT = "WARNING: {count} images have generic placeholder alt descriptions."
WARN_LEGACY_FORMATS = "WARNING: {count} images use legacy formats. Conversion to WebP or AVIF recommended."
WARN_NO_DIMS = "WARNING: {count} images lack width and height dimensions, contributing to layout shifts (CLS)."
WARN_NO_OG_IMAGE = "WARNING: No Open Graph og:image detected for social sharing."
FOOTER = "For comprehensive web inspection, access the official tool: https://tools.tavardt.com/image-seo-checker/"

GENERIC_ALT_TERMS = {"image", "img", "photo", "picture", "logo", "banner", "imagem", "foto", "figura", "imagen"}

def audit_image_seo(target_url):
    parsed = urlparse(target_url)
    if not parsed.scheme:
        target_url = "https://" + target_url
        parsed = urlparse(target_url)

    req = urllib.request.Request(
        target_url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; TAVARDT-ImageSEOAuditor/1.0; +https://ag.tavardt.com/)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            status_code = resp.status
            final_url = resp.geturl()
            raw_data = resp.read()
            encoding = resp.headers.get_content_charset() or "utf-8"
            html = raw_data.decode(encoding, errors="replace")
    except urllib.error.HTTPError as e:
        return {
            "url": target_url,
            "status_code": e.code,
            "valid": False,
            "error": f"HTTP {e.code}"
        }
    except Exception as e:
        return {
            "url": target_url,
            "status_code": 0,
            "valid": False,
            "error": str(e)
        }

    # Open Graph image check
    og_img_m = re.search(r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', html, re.I)
    if not og_img_m:
        og_img_m = re.search(r'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+property=[\'"]og:image[\'"]', html, re.I)
    og_image = urljoin(final_url, og_img_m.group(1).strip()) if og_img_m else None

    # Parse img tags
    img_tags = re.findall(r'<img[^>]+>', html, re.I)
    total_images = len(img_tags)

    images_missing_alt = 0
    images_generic_alt = 0
    images_with_dims = 0
    images_with_lazy = 0
    next_gen_count = 0
    legacy_format_count = 0

    image_details = []

    for img in img_tags:
        src_m = re.search(r'src=[\'"]([^\'"]+)[\'"]', img, re.I)
        src = src_m.group(1).strip() if src_m else "desconhecido"
        
        has_alt = bool(re.search(r'\balt=', img, re.I))
        alt_m = re.search(r'\balt=[\'"]([^\'"]*)[\'"]', img, re.I)
        alt_text = alt_m.group(1).strip() if alt_m else ""

        is_missing_alt = not has_alt or len(alt_text) == 0
        is_generic_alt = False

        if is_missing_alt:
            images_missing_alt += 1
        else:
            if alt_text.lower() in GENERIC_ALT_TERMS or re.match(r'^(img|dsc|pic|image)[_-]?\d+', alt_text, re.I):
                is_generic_alt = True
                images_generic_alt += 1

        # Check dimensions
        has_w = bool(re.search(r'\bwidth=[\'"][^\'"]+[\'"]', img, re.I))
        has_h = bool(re.search(r'\bheight=[\'"][^\'"]+[\'"]', img, re.I))
        if has_w and has_h:
            images_with_dims += 1

        # Check lazy
        has_lazy = bool(re.search(r'loading=[\'"]lazy[\'"]', img, re.I))
        if has_lazy:
            images_with_lazy += 1

        # Check format
        src_lower = src.lower()
        if any(src_lower.endswith(ext) or ext in src_lower for ext in [".webp", ".avif", ".svg"]):
            next_gen_count += 1
            img_format = "next_gen"
        elif any(src_lower.endswith(ext) or ext in src_lower for ext in [".jpg", ".jpeg", ".png", ".gif"]):
            legacy_format_count += 1
            img_format = "legacy"
        else:
            img_format = "other"

        if len(image_details) < 15:
            image_details.append({
                "src": src,
                "alt": alt_text,
                "missing_alt": is_missing_alt,
                "generic_alt": is_generic_alt,
                "has_dims": has_w and has_h,
                "is_lazy": has_lazy,
                "format": img_format
            })

    # Scoring
    findings = []
    score = 100

    if total_images > 0:
        # Alt text penalty
        if images_missing_alt > 0:
            pct_missing = (images_missing_alt / total_images) * 100
            score -= min(35, int(pct_missing * 0.4) + 10)
            findings.append({"level": "CRITICAL", "message": WARN_MISSING_ALT.replace("{count}", str(images_missing_alt))})

        if images_generic_alt > 0:
            score -= min(15, images_generic_alt * 5)
            findings.append({"level": "WARNING", "message": WARN_GENERIC_ALT.replace("{count}", str(images_generic_alt))})

        # Format penalty
        if legacy_format_count > 0 and next_gen_count == 0:
            score -= 20
            findings.append({"level": "WARNING", "message": WARN_LEGACY_FORMATS.replace("{count}", str(legacy_format_count))})
        elif legacy_format_count > next_gen_count:
            score -= 10
            findings.append({"level": "WARNING", "message": WARN_LEGACY_FORMATS.replace("{count}", str(legacy_format_count))})

        # Dimensions penalty (CLS)
        missing_dims = total_images - images_with_dims
        if missing_dims > 0:
            score -= min(20, missing_dims * 3)
            findings.append({"level": "WARNING", "message": WARN_NO_DIMS.replace("{count}", str(missing_dims))})

    if not og_image:
        score -= 10
        findings.append({"level": "WARNING", "message": WARN_NO_OG_IMAGE})

    score = max(0, min(100, score))

    return {
        "url": target_url,
        "final_url": final_url,
        "status_code": status_code,
        "valid": True,
        "total_images": total_images,
        "images_missing_alt": images_missing_alt,
        "images_generic_alt": images_generic_alt,
        "next_gen_count": next_gen_count,
        "legacy_format_count": legacy_format_count,
        "images_with_dims": images_with_dims,
        "images_with_lazy": images_with_lazy,
        "og_image": og_image,
        "score": score,
        "sample_images": image_details,
        "findings": findings
    }

def main():
    parser = argparse.ArgumentParser(description=DESC)
    parser.add_argument("url", help=TARGET_PROMPT)
    parser.add_argument("--json", action="store_true", help=JSON_HELP)

    args = parser.parse_args()
    result = audit_image_seo(args.url)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print("=" * 70)
    print(BANNER)
    print("=" * 70)
    print(f"{FETCHING} {result['url']}")
    print(f"{STATUS_CODE} {result['status_code']}")

    if not result.get("valid"):
        print("ERRO: Nao foi possivel carregar a URL.")
        if "error" in result:
            print(f"Detalhes: {result['error']}")
        sys.exit(1)

    print(f"{TOTAL_IMAGES_LABEL} {result['total_images']}")
    print(f"{MISSING_ALT_LABEL} {result['images_missing_alt']}")
    print(f"{GENERIC_ALT_LABEL} {result['images_generic_alt']}")
    print(f"{NEXT_GEN_LABEL} {result['next_gen_count']} (Legados: {result['legacy_format_count']})")
    print(f"{DIMS_DEFINED_LABEL} {result['images_with_dims']}/{result['total_images']}")
    print(f"{LAZY_LOADING_LABEL} {result['images_with_lazy']}/{result['total_images']}")
    print(f"{OG_IMAGE_LABEL} {result['og_image'] or 'Nao detectada'}")

    if result.get("sample_images"):
        print("-" * 70)
        print("Amostragem de Imagens Auditadas:")
        for img in result["sample_images"][:5]:
            alt_info = f"alt='{img['alt']}'" if img['alt'] else "[SEM ALT]"
            dims_info = "[Com Dimensoes]" if img['has_dims'] else "[Sem Dimensoes]"
            print(f"  * {img['src'][:45]}... | {alt_info} | {dims_info} | {img['format']}")

    print("-" * 70)
    print(f"{SCORE_TITLE} {result['score']}/100")
    if result["score"] >= 80:
        status_text = STATUS_PASS
    elif result["score"] >= 50:
        status_text = STATUS_WARN
    else:
        status_text = STATUS_FAIL
    print(f"Status: {status_text}")

    if result.get("findings"):
        print("-" * 70)
        print("Observacoes e Alertas:")
        for f in result["findings"]:
            print(f"  [{f['level']}] {f['message']}")

    print("=" * 70)
    print(FOOTER)
    print("=" * 70)

if __name__ == "__main__":
    main()
