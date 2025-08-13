class ImageGenerator:
    def __init__(self, ai_system, backend="comfyui"):
        self.ai = ai_system
        self.backend = backend
    
    def generate_image(self, prompt, size=(1024, 1024)):
        """Generate image from text prompt"""
        if self.backend == "comfyui":
            return self._generate_via_comfyui(prompt, size)
        else:
            return self._generate_via_sdapi(prompt, size)
    
    def _generate_via_comfyui(self, prompt, size):
        """Generate using ComfyUI API"""
        # Placeholder implementation - replace with actual ComfyUI integration
        workflow = self._create_comfyui_workflow(prompt, size)
        # api_url = "http://localhost:8188/prompt"
        # response = requests.post(api_url, json={"prompt": workflow})
        # return response.json().get("image_url")
        return f"https://dummyimage.com/{size[0]}x{size[1]}/000/fff&text={prompt[:20]}"
    
    def _create_comfyui_workflow(self, prompt, size):
        """Create ComfyUI workflow JSON"""
        return {
            "prompt": prompt,
            "width": size[0],
            "height": size[1],
            "steps": 30,
            "sampler": "k_euler",
            "cfg_scale": 7.5
        }
    
    def _generate_via_sdapi(self, prompt, size):
        """Generate using Stable Diffusion API"""
        # Placeholder implementation
        return f"https://dummyimage.com/{size[0]}x{size[1]}/000/fff&text={prompt[:20]}"