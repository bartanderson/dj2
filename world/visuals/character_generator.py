"""
Offline character generator — run ONCE per archetype to build the character library.
Do NOT import during game startup; loads heavy ML models.

Pipeline per archetype:
  1. Generate reference image (SDXL, full prompt)
  2. Generate state variants (IP-Adapter identity transfer: wounded, friendly, etc.)
  3. Generate pose views (Zero123++ or ControlNet pose: front, 3/4, side)
  4. Remove backgrounds → cutout PNGs (rembg, CPU-friendly)
  5. Register everything in AssetCatalog

Usage:
    python -m world.visuals.character_generator
    python -m world.visuals.character_generator --id innkeeper_female_stout
    python -m world.visuals.character_generator --dry-run
    python -m world.visuals.character_generator --cutouts-only
"""

import argparse
import json
from pathlib import Path
from typing import Optional, List


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def reference_prompt(archetype) -> str:
    return (
        f"portrait of {archetype.base_prompt}, "
        f"facing forward, full upper body, plain dark background, "
        f"{archetype.style_suffix}"
    )


def variant_prompt(archetype, variant: str) -> str:
    mood_desc = {
        "neutral":    "neutral calm expression",
        "friendly":   "warm friendly smile, relaxed posture",
        "suspicious": "narrowed eyes, guarded expression, slight frown",
        "wounded":    "injured, blood stain, grimacing in pain, bandaged",
        "fearful":    "wide frightened eyes, backed away, trembling",
        "alert":      "tense, hand on weapon, scanning for danger",
        "attacking":  "aggressive stance, weapon raised, battle expression",
        "fleeing":    "turning to run, desperate expression",
        "raging":     "furious, berserk expression, veins visible",
        "chanting":   "eyes half-closed, lips moving, ritual focus",
        "surrendering": "hands raised, defeated expression",
        "prowling":   "low stance, muscles coiled, predatory focus",
        "crumbling":  "partially collapsed, bones falling apart",
        "standing":   "rigid upright stance, weapon at ready",
        "dead":       "collapsed on ground, motionless",
    }.get(variant, f"{variant} expression")

    return (
        f"portrait of {archetype.base_prompt}, "
        f"{mood_desc}, facing forward, full upper body, plain dark background, "
        f"{archetype.style_suffix}"
    )


POSE_PROMPTS = {
    "front":        "facing directly forward, symmetrical",
    "three_quarter": "turned slightly to the right, 3/4 view",
    "side":         "profile view, facing right",
}


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def _load_sdxl(device, dtype):
    from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
    import torch
    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=dtype,
        variant="fp16" if device == "cuda" else None,
    ).to(device)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config, use_karras_sigmas=True
    )
    if device == "cuda":
        pipe.enable_vae_slicing()
        pipe.enable_model_cpu_offload()
    return pipe


def _load_ip_adapter(pipe, device):
    """Add IP-Adapter to existing SDXL pipeline for identity transfer."""
    pipe.load_ip_adapter(
        "h94/IP-Adapter",
        subfolder="sdxl_models",
        weight_name="ip-adapter_sdxl.bin",
    )
    pipe.set_ip_adapter_scale(0.6)
    pipe = pipe.to(device)   # move IP-Adapter weights to GPU
    return pipe


def generate_reference(archetype, output_path: Path, pipe) -> bool:
    """Generate the identity anchor image for an archetype."""
    from PIL import Image
    import torch

    prompt = reference_prompt(archetype)
    print(f"  Generating reference: {archetype.id}")

    try:
        result = pipe(
            prompt=prompt,
            negative_prompt=archetype.negative_prompt,
            width=768,
            height=1024,
            num_inference_steps=30,
            guidance_scale=7.5,
            generator=torch.Generator().manual_seed(42),
        ).images[0]
        result.save(str(output_path))
        return True
    except Exception as e:
        print(f"    FAILED reference: {e}")
        return False


def generate_variants(archetype, reference_path: Path, output_dir: Path,
                      pipe) -> List[Path]:
    """Generate state variants using IP-Adapter identity transfer."""
    from PIL import Image
    import torch

    ref_image = Image.open(reference_path).convert("RGB")
    generated = []

    for variant in archetype.variants:
        out_path = output_dir / f"{archetype.id}_{variant}.png"
        if out_path.exists():
            print(f"  skip variant {variant} (exists)")
            generated.append(out_path)
            continue

        prompt = variant_prompt(archetype, variant)
        print(f"  variant: {variant}")

        try:
            result = pipe(
                prompt=prompt,
                negative_prompt=archetype.negative_prompt,
                ip_adapter_image=ref_image,
                width=768,
                height=1024,
                num_inference_steps=30,
                guidance_scale=6.0,
                generator=torch.Generator().manual_seed(hash(variant) % 10000),
            ).images[0]
            result.save(str(out_path))
            generated.append(out_path)
        except Exception as e:
            print(f"    FAILED variant {variant}: {e}")

    return generated


def generate_pose_views(archetype, reference_path: Path, output_dir: Path,
                        pipe) -> List[Path]:
    """
    Generate front / 3-quarter / side views.
    Uses img2img with pose prompt injection as a lightweight alternative to Zero123++.
    For better multi-view consistency, replace with Zero123++ pipeline when available.
    """
    from diffusers import AutoPipelineForImage2Image
    from PIL import Image
    import torch

    ref_image = Image.open(reference_path).convert("RGB")
    generated = []

    for pose_name, pose_desc in POSE_PROMPTS.items():
        if pose_name == "front":
            generated.append(reference_path)   # front IS the reference
            continue

        out_path = output_dir / f"{archetype.id}_pose_{pose_name}.png"
        if out_path.exists():
            print(f"  skip pose {pose_name} (exists)")
            generated.append(out_path)
            continue

        prompt = (
            f"portrait of {archetype.base_prompt}, "
            f"{pose_desc}, full upper body, plain dark background, "
            f"{archetype.style_suffix}"
        )
        print(f"  pose: {pose_name}")

        try:
            # img2img keeps identity better than text-only for poses
            img2img_pipe = AutoPipelineForImage2Image.from_pipe(pipe)
            result = img2img_pipe(
                prompt=prompt,
                negative_prompt=archetype.negative_prompt,
                image=ref_image,
                strength=0.55,
                num_inference_steps=30,
                guidance_scale=7.0,
                generator=torch.Generator().manual_seed(hash(pose_name) % 10000),
            ).images[0]
            result.save(str(out_path))
            generated.append(out_path)
        except Exception as e:
            print(f"    FAILED pose {pose_name}: {e}")

    return generated


def remove_backgrounds(image_paths: List[Path], output_dir: Path) -> List[Path]:
    """
    Remove backgrounds → transparent PNG cutouts.
    Uses rembg (CPU-friendly, ~100MB model, no GPU needed).
    Install: pip install rembg
    """
    try:
        from rembg import remove
        from PIL import Image
    except ImportError:
        print("  rembg not installed (pip install rembg) — skipping cutouts.")
        return []

    cutouts_dir = output_dir / "cutouts"
    cutouts_dir.mkdir(exist_ok=True)
    results = []

    for img_path in image_paths:
        out_path = cutouts_dir / (img_path.stem + "_cutout.png")
        if out_path.exists():
            print(f"  skip cutout {img_path.stem} (exists)")
            results.append(out_path)
            continue

        print(f"  cutout: {img_path.name}")
        try:
            with open(img_path, "rb") as f:
                data = f.read()
            result_data = remove(data)
            out_path.write_bytes(result_data)
            results.append(out_path)
        except Exception as e:
            print(f"    FAILED cutout {img_path.name}: {e}")

    return results


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_archetype(archetype, characters_dir: Path, catalog,
                      dry_run: bool = False, cutouts_only: bool = False) -> None:
    arch_dir = characters_dir / archetype.id
    arch_dir.mkdir(parents=True, exist_ok=True)

    ref_path = arch_dir / f"{archetype.id}_reference.png"

    print(f"\n=== {archetype.label} ({archetype.id}) ===")

    if dry_run:
        print(f"  Would generate: reference + {len(archetype.variants)} variants + {len(POSE_PROMPTS)} poses")
        print(f"  Would cut out all → transparent PNGs")
        print(f"  Would register {archetype.id} in catalog")
        return

    if not cutouts_only:
        # Load models
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype  = torch.float16 if device == "cuda" else torch.float32
            print(f"  Loading SDXL on {device}...")
            pipe = _load_sdxl(device, dtype)

            # Reference
            if not ref_path.exists():
                generate_reference(archetype, ref_path, pipe)
            else:
                print(f"  Reference exists, skipping generation.")

            # Pose views first — before IP-Adapter is loaded (plain img2img)
            pose_paths = generate_pose_views(archetype, ref_path, arch_dir, pipe)

            # IP-Adapter for identity-consistent state variants
            print("  Loading IP-Adapter...")
            pipe = _load_ip_adapter(pipe, device)
            variant_paths = generate_variants(archetype, ref_path, arch_dir, pipe)

            # Unload IP-Adapter so pipe is clean for next archetype
            if hasattr(pipe, "unload_ip_adapter"):
                pipe.unload_ip_adapter()

            all_generated = [ref_path] + variant_paths + pose_paths

        except ImportError:
            print("  torch/diffusers not available — skipping generation.")
            all_generated = list(arch_dir.glob("*.png"))
    else:
        all_generated = list(arch_dir.glob("*.png"))

    # Cutouts (CPU, always runs)
    cutout_paths = remove_backgrounds(all_generated, arch_dir)

    # Register in catalog
    if ref_path.exists():
        catalog.register_character(
            id=archetype.id,
            path=ref_path,
            char_type=archetype.char_type,
            tags=archetype.tags,
            anchor={"w": 180, "h": 360},   # default sprite size in compositor
        )

    for cutout_path in cutout_paths:
        variant_id = cutout_path.stem.replace("_cutout", "")
        catalog.register_character(
            id=variant_id,
            path=cutout_path,
            char_type=archetype.char_type,
            tags=archetype.tags + [_variant_tag(cutout_path.stem)],
            anchor={"w": 180, "h": 360},
        )

    print(f"  Done: {len(cutout_paths)} cutouts registered.")


def _variant_tag(stem: str) -> str:
    """Extract variant/pose label from filename stem."""
    parts = stem.split("_")
    return parts[-1] if parts else "unknown"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build character library")
    parser.add_argument("--id", help="Only process this archetype ID")
    parser.add_argument("--type", choices=["npc", "enemy", "creature", "player"],
                        help="Only process this char_type")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cutouts-only", action="store_true",
                        help="Skip generation, only run background removal on existing images")
    parser.add_argument("--assets-dir", default="assets/visuals")
    args = parser.parse_args()

    from world.visuals.catalog import AssetCatalog
    from world.visuals.archetypes import ALL_ARCHETYPES, ARCHETYPE_BY_ID

    assets_dir     = Path(args.assets_dir)
    characters_dir = assets_dir / "characters"
    db_path        = assets_dir / "visual_assets.db"

    catalog = AssetCatalog(db_path)

    if args.id:
        archetypes = [ARCHETYPE_BY_ID[args.id]] if args.id in ARCHETYPE_BY_ID else []
        if not archetypes:
            print(f"Unknown archetype: {args.id}")
            print(f"Available: {list(ARCHETYPE_BY_ID.keys())}")
            exit(1)
    elif args.type:
        archetypes = [a for a in ALL_ARCHETYPES if a.char_type == args.type]
    else:
        archetypes = ALL_ARCHETYPES

    print(f"Processing {len(archetypes)} archetypes...")
    for archetype in archetypes:
        process_archetype(
            archetype, characters_dir, catalog,
            dry_run=args.dry_run,
            cutouts_only=args.cutouts_only,
        )

    catalog.close()
    print("\nCharacter library build complete.")
