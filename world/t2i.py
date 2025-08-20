import os
import torch
import warnings
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from diffusers.utils import logging as diffusers_logging
import uuid
from typing import Dict, List, Tuple
import time
import traceback
import math
import numpy as np
from PIL import Image
import json

# Disable Triton to avoid installation issues
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(False)
torch.backends.cuda.enable_math_sdp(True)

class TextToImage:
    def __init__(self, model_path: Path):
        """
        Initialize the text-to-image generator.
        
        Args:
            model_path: Path to the Stable Diffusion model file (.safetensors)
        """
        # Suppress noisy warnings
        warnings.filterwarnings("ignore")
        diffusers_logging.set_verbosity_error()
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        
        # Set cache directory
        self.cache_dir = Path.home() / ".hf_cache"
        os.environ["HF_HOME"] = str(self.cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Validate model path
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
            
        # Load pipeline
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.model_path = model_path
        self.pipeline = self._load_pipeline()

    def _load_pipeline(self):
        """Load the Stable Diffusion pipeline with optimizations"""
        print(f"Loading model: {self.model_path.name}")
        print(f"Device: {self.device} | Precision: {self.torch_dtype}")
        
        pipe = StableDiffusionPipeline.from_single_file(
            pretrained_model_link_or_path=str(self.model_path),
            torch_dtype=self.torch_dtype,
            safety_checker=None,
            requires_safety_checker=False,
            load_safety_checker=False,
            cache_dir=str(self.cache_dir))
        
        # Configure scheduler for better quality
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config, 
            use_karras_sigmas=True
        )
        pipe = pipe.to(self.device)
        
        # Apply optimizations
        if self.device == "cuda":
            if hasattr(pipe, "enable_xformers_memory_efficient_attention"):
                pipe.enable_xformers_memory_efficient_attention()
            if hasattr(pipe, "enable_model_cpu_offload"):
                pipe.enable_model_cpu_offload()
        else:
            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
        
        return pipe

    def _validate_dimensions(self, width: int, height: int) -> Tuple[int, int]:
        """
        Ensure dimensions are valid for Stable Diffusion.
        
        Args:
            width: Requested image width
            height: Requested image height
            
        Returns:
            Validated (width, height) tuple
        """
        # Must be divisible by 8
        width = math.ceil(width / 8) * 8
        height = math.ceil(height / 8) * 8
        
        # Enforce minimum size for quality
        width = max(width, 384)  # 384px minimum for reasonable quality
        height = max(height, 384)
        
        return width, height

    def _is_valid_image(self, image_path: Path) -> bool:
        """
        Validate that the generated image is not empty/black.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if valid, False if empty/black
        """
        try:
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                img_array = np.mean(img_array, axis=2)
            
            # Check if image has sufficient variance
            if img_array.std() < 10:  # Very low variance
                return False
                
            # Check if image is mostly black
            if np.mean(img_array) < 15:  # Very dark image
                return False
                
            return True
        except Exception as e:
            print(f"Image validation error: {str(e)}")
            return False

    def generate_batch(
        self,
        generation_requests: List[Dict],
        output_dir: Path,
        default_width: int = 768,
        default_height: int = 768
    ) -> Tuple[Dict, List[Dict]]:
        """
        Batch generate images with detailed error tracking.
        
        Args:
            generation_requests: List of image generation requests
            output_dir: Directory to save generated images
            default_width: Default image width
            default_height: Default image height
            
        Returns:
            Tuple of (successful_generations, failed_generations)
        """
        successful = {}
        failed = []
        
        # Ensure output directory exists
        output_dir.mkdir(exist_ok=True, parents=True)
        
        for request in generation_requests:
            request_id = request.get("request_id", str(uuid.uuid4()))
            prompt = request["prompt"]
            negative = request.get("negative_prompt", "blurry, deformed, ugly, text, signature, watermark")
            seed = request.get("seed", 42)
            width = request.get("width", default_width)
            height = request.get("height", default_height)
            
            # Validate prompt
            if not prompt or len(prompt.strip()) < 10:
                error_info = {
                    "request_id": request_id,
                    "prompt": prompt,
                    "exception": "Prompt must be at least 10 characters",
                    "traceback": ""
                }
                failed.append(error_info)
                print(f"✗ Invalid prompt for {request_id}: '{prompt}'")
                continue
                
            # Validate and adjust dimensions
            try:
                width, height = self._validate_dimensions(width, height)
            except Exception as e:
                error_info = {
                    "request_id": request_id,
                    "prompt": prompt,
                    "exception": str(e),
                    "traceback": traceback.format_exc()
                }
                failed.append(error_info)
                print(f"✗ Dimension error for {request_id}: {e}")
                continue
                
            output_path = output_dir / f"{request_id}.jpg"
            
            try:
                print(f"Generating: '{prompt}' ({width}x{height})")
                start_time = time.time()
                
                # Create generator with seed
                generator = torch.Generator(device=self.device)
                if seed is not None:
                    generator = generator.manual_seed(seed)
                
                # Generate image
                result = self.pipeline(
                    prompt=prompt,
                    negative_prompt=negative,
                    width=width,
                    height=height,
                    num_inference_steps=30,
                    guidance_scale=7.5,
                    generator=generator
                )
                
                # Save the image
                result.images[0].save(output_path)
                gen_time = time.time() - start_time
                
                # Validate the generated image
                if not self._is_valid_image(output_path):
                    raise RuntimeError("Generated image is invalid (all black or low variance)")
                
                print(f"✓ Generated {request_id} in {gen_time:.1f}s: {output_path}")
                successful[request_id] = {
                    "path": output_path,
                    "prompt": prompt,
                    "time": gen_time,
                    "dimensions": (width, height)
                }
                
            except Exception as e:
                # Clean up invalid image file
                if output_path.exists():
                    try:
                        output_path.unlink()
                    except OSError:
                        pass
                
                error_info = {
                    "request_id": request_id,
                    "prompt": prompt,
                    "exception": str(e),
                    "traceback": traceback.format_exc(),
                    "dimensions": (width, height)
                }
                print(f"✗ Failed to generate {request_id}: {e}")
                failed.append(error_info)
        
        return successful, failed

    def retry_failed_generations(
        self, 
        failed_requests: List[Dict],
        output_dir: Path
    ) -> Tuple[Dict, List[Dict]]:
        """
        Retry a batch of failed generation requests.
        
        Args:
            failed_requests: List of failed requests (from previous batch)
            output_dir: Directory to save generated images
            
        Returns:
            Tuple of (successful_retries, failed_retries)
        """
        # Prepare requests for retry
        retry_requests = []
        for failure in failed_requests:
            request = {
                "request_id": failure["request_id"],
                "prompt": failure["prompt"],
                "seed": failure.get("seed", 42),
                "width": failure.get("width", 768),
                "height": failure.get("height", 768)
            }
            retry_requests.append(request)
        
        return self.generate_batch(retry_requests, output_dir)


if __name__ == "__main__":
    # ===== CONFIGURATION =====
    MODEL_NAME = "realisticVisionV60B1_v51VAE.safetensors"
    MODEL_DIR = Path.home() / ".sdkit" / "models" / "stable-diffusion"
    OUTPUT_DIR = Path.cwd() / "generated_images"
    TEST_PROMPTS = [
        "A majestic fantasy castle on a floating island at sunset",
        "Ancient forest with glowing mushrooms and mystical creatures",
        "Underground dwarven city with glowing crystal structures"
    ]
    
    # ===== SETUP =====
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    
    # Initialize generator
    model_path = MODEL_DIR / MODEL_NAME
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        exit(1)
    
    print(f"Initializing text-to-image generator with {MODEL_NAME}...")
    t2i = TextToImage(model_path)
    
    # ===== PREPARE REQUESTS =====
    requests = []
    for i, prompt in enumerate(TEST_PROMPTS):
        requests.append({
            "request_id": f"test-{i+1}",
            "prompt": prompt,
            "seed": 42 + i,
            "width": 768,
            "height": 768
        })
    
    # Add special test cases
    requests.extend([
        # Valid small image
        {
            "request_id": "small-valid",
            "prompt": "Mountain fortress at dawn, detailed fantasy landscape",
            "width": 384,
            "height": 384
        },
        # Invalid dimensions (will be corrected)
        {
            "request_id": "adjusted-dims",
            "prompt": "Desert oasis with palm trees and clear water",
            "width": 777,  # Not divisible by 8
            "height": 777
        },
        # Too small dimensions (will be corrected)
        {
            "request_id": "min-size",
            "prompt": "Snowy mountain peak with aurora borealis",
            "width": 100,  # Below minimum
            "height": 100
        },
        # Invalid prompt (too short)
        {
            "request_id": "invalid-prompt",
            "prompt": "test",  # Too short
            "width": 768,
            "height": 768
        }
    ])
    
    # ===== GENERATE BATCH =====
    print(f"\nGenerating {len(requests)} test images...")
    start_time = time.time()
    successes, failures = t2i.generate_batch(requests, OUTPUT_DIR)
    gen_time = time.time() - start_time
    
    # ===== RESULTS =====
    print(f"\nBatch generation completed in {gen_time:.1f} seconds")
    print(f"Successful: {len(successes)}")
    for req_id, details in successes.items():
        w, h = details['dimensions']
        print(f"  {req_id}: {w}x{h} - {details['path']}")
    
    print(f"\nFailed: {len(failures)}")
    for failure in failures:
        print(f"  {failure['request_id']}: {failure['exception']}")
    
    # Save failure details for retry
    if failures:
        failure_file = OUTPUT_DIR / "failed_generations.json"
        with failure_file.open("w") as f:
            json.dump(failures, f, indent=2)
        print(f"\nSaved failure details to: {failure_file}")
        
        # Retry failed generations
        print("\nRetrying failed generations...")
        retry_successes, retry_failures = t2i.retry_failed_generations(failures, OUTPUT_DIR)
        
        print(f"Retry successful: {len(retry_successes)}")
        print(f"Retry failed: {len(retry_failures)}")
    
    print("\n✨ Test complete! ✨")