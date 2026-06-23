"""
Offline variant generator — run this ONCE to build the image library.
Do NOT import this during game startup; it loads heavy ML models.

Usage:
    python -m world.visuals.variant_generator
    python -m world.visuals.variant_generator --base dore_forest_dark
    python -m world.visuals.variant_generator --dry-run

Strategy:
  For each registered base image, generate variants for the modifier matrix:
    seasons    x  weather  x  time_of_day  x  mood
  Uses img2img (high denoise) rather than pure inpainting so no mask is needed.
  Moebius can replace this pipeline when available locally.
"""

import argparse
import uuid
from pathlib import Path
from itertools import product
from typing import List, Optional

# Modifier matrix - keep small, inpaint covers the rest
SEASONS    = ["spring", "summer", "autumn", "winter"]
WEATHERS   = ["clear", "rain", "fog", "storm"]
TIMES      = ["day", "dusk", "night", "dawn"]
MOODS      = ["neutral", "tense", "eerie", "cozy"]

# Only generate these combinations offline; compositor handles minor tweaks at runtime
# Full matrix = 4*4*4*4 = 256 per base — too many. Generate a useful subset.
PRIORITY_COMBOS = [
    # (season,   weather, time,    mood)
    ("summer",  "clear", "day",   "neutral"),
    ("summer",  "clear", "night", "eerie"),
    ("summer",  "rain",  "day",   "tense"),
    ("autumn",  "fog",   "dusk",  "eerie"),
    ("winter",  "snow",  "day",   "desolate"),
    ("winter",  "storm", "night", "tense"),
    ("spring",  "clear", "dawn",  "cozy"),
    ("autumn",  "clear", "day",   "neutral"),
]


def build_prompt(base_prompt_hint: str, season: str, weather: str,
                 time_of_day: str, mood: str) -> str:
    """Construct a detailed inpainting/img2img prompt from modifiers."""
    time_desc = {
        "day":   "bright daylight",
        "dusk":  "golden hour dusk, long shadows",
        "night": "moonlit night, darkness, stars",
        "dawn":  "misty dawn, soft early light",
    }.get(time_of_day, "daylight")

    weather_desc = {
        "clear": "clear skies",
        "rain":  "heavy rain, wet ground, dark clouds",
        "fog":   "thick fog, mist, low visibility",
        "storm": "thunderstorm, lightning, ominous clouds",
        "snow":  "snowfall, blanketed in snow",
    }.get(weather, "clear")

    season_desc = {
        "spring": "spring, fresh green leaves, flowers blooming",
        "summer": "summer, lush green, warm",
        "autumn": "autumn, orange and red leaves, falling leaves",
        "winter": "winter, bare trees, frost, cold",
    }.get(season, "")

    mood_desc = {
        "neutral":  "serene, peaceful",
        "tense":    "ominous, foreboding, danger",
        "eerie":    "eerie, unsettling, supernatural atmosphere",
        "cozy":     "warm, inviting, safe",
        "desolate": "desolate, abandoned, bleak",
    }.get(mood, "")

    return (
        f"{base_prompt_hint}, {season_desc}, {time_desc}, {weather_desc}, "
        f"{mood_desc}, fantasy art, highly detailed, dramatic lighting, "
        f"Gustave Dore style engraving"
    )


def generate_variants(catalog, assets_dir: Path, base_ids: Optional[List[str]] = None,
                      dry_run: bool = False) -> None:
    """
    For each base image (or specified subset), generate priority variant combos.
    Requires diffusers + torch; skips gracefully if unavailable.
    """
    try:
        import torch
        from diffusers import AutoPipelineForImage2Image
        from PIL import Image
        HAS_DIFFUSERS = True
    except ImportError:
        print("diffusers/torch not available — running in dry-run mode.")
        HAS_DIFFUSERS = False
        dry_run = True

    variants_dir = assets_dir / "variants"
    variants_dir.mkdir(parents=True, exist_ok=True)

    bases = catalog.find_bases()
    if base_ids:
        bases = [b for b in bases if b["id"] in base_ids]

    if not bases:
        print("No base images registered. Run sources.register_sources() first.")
        return

    pipe = None
    if not dry_run and HAS_DIFFUSERS:
        print("Loading img2img pipeline (SDXL-Turbo)...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype  = torch.float16 if device == "cuda" else torch.float32
        pipe = AutoPipelineForImage2Image.from_pretrained(
            "stabilityai/sdxl-turbo",
            torch_dtype=dtype,
            variant="fp16" if device == "cuda" else None,
        ).to(device)
        if device == "cuda":
            pipe.enable_vae_slicing()

    for base in bases:
        base_id   = base["id"]
        hint      = base.get("prompt_hint", "fantasy landscape")
        base_path = Path(base["path"])

        print(f"\n--- {base_id} ---")

        for (season, weather, time_of_day, mood) in PRIORITY_COMBOS:
            variant_id   = f"{base_id}__{season}_{weather}_{time_of_day}_{mood}"
            variant_path = variants_dir / f"{variant_id}.jpg"

            # Skip if already generated (check file directly, not fuzzy catalog lookup)
            if variant_path.exists():
                print(f"  skip {variant_id} (exists)")
                # Re-register in case catalog was reset
                catalog.register_variant(id=variant_id, base_id=base_id, path=variant_path,
                                         season=season, weather=weather,
                                         time_of_day=time_of_day, mood=mood)
                continue

            prompt = build_prompt(hint, season, weather, time_of_day, mood)
            print(f"  {'[DRY]' if dry_run else 'gen'} {variant_id}")
            if dry_run:
                print(f"        prompt: {prompt[:80]}...")
                continue

            try:
                init_image = Image.open(base_path).convert("RGB").resize((768, 512))
                result = pipe(
                    prompt=prompt,
                    image=init_image,
                    num_inference_steps=4,      # SDXL-Turbo: 4 steps is enough
                    strength=0.6,               # 0.5-0.7: preserves composition, changes mood
                    guidance_scale=0.0,         # Turbo uses CFG=0
                ).images[0]
                result.save(str(variant_path))

                catalog.register_variant(
                    id=variant_id,
                    base_id=base_id,
                    path=variant_path,
                    season=season,
                    weather=weather,
                    time_of_day=time_of_day,
                    mood=mood,
                )
                print(f"    saved {variant_path.name}")

            except Exception as e:
                print(f"    FAILED: {e}")

    print("\nVariant generation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build visual variant library")
    parser.add_argument("--base", help="Only process this base_id")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be generated without running")
    parser.add_argument("--assets-dir", default="assets/visuals",
                        help="Root directory for assets (default: assets/visuals)")
    args = parser.parse_args()

    from world.visuals.catalog import AssetCatalog
    from world.visuals.sources import register_sources

    assets_dir = Path(args.assets_dir)
    db_path    = assets_dir / "visual_assets.db"
    bases_dir  = assets_dir / "bases"

    catalog = AssetCatalog(db_path)

    # Register sources if not already done
    if not catalog.find_bases():
        print("No bases found — downloading source images...")
        register_sources(catalog, bases_dir)

    base_ids = [args.base] if args.base else None
    generate_variants(catalog, assets_dir, base_ids=base_ids, dry_run=args.dry_run)

    catalog.close()
