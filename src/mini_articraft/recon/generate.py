"""Generate a whole-object mesh from a text prompt (or a real image): text -> sharp
image -> SAM 3D Objects (whole object). Consolidated into mini-articraft so the
whole pipeline (image -> mesh -> cull -> rig -> USD) lives in one place.

Requires FAL_KEY (image + SAM3D via fal) in .env.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

# sharpest text->image options on fal, best first
IMAGE_MODELS = {
    "flux-ultra": ("fal-ai/flux-pro/v1.1-ultra", {"aspect_ratio": "1:1"}),
    "recraft": ("fal-ai/recraft-v3", {"image_size": "square_hd"}),
    "flux-dev": ("fal-ai/flux/dev", {"image_size": "square_hd", "num_inference_steps": 40}),
}
SAM3D = "fal-ai/sam-3/3d-objects"


def _glbs(obj, acc=None):
    acc = [] if acc is None else acc
    if isinstance(obj, dict):
        for v in obj.values():
            _glbs(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _glbs(v, acc)
    elif isinstance(obj, str) and obj.startswith("http") and obj.split("?")[0].endswith(".glb"):
        acc.append(obj)
    return acc


def text_to_image(prompt: str, out_path: str, *, model: str = "flux-ultra") -> str:
    import fal_client
    endpoint, extra = IMAGE_MODELS[model]
    res = fal_client.run(endpoint, arguments={"prompt": prompt, **extra})
    url = res["images"][0]["url"]
    urllib.request.urlretrieve(url, out_path)
    return url


def image_to_mesh(image_url: str, sam_prompt: str, out_path: str) -> str:
    """SAM 3D Objects: whole object from a text/box prompt -> glb mesh file."""
    import fal_client
    res = fal_client.run(SAM3D, arguments={"image_url": image_url, "prompt": sam_prompt})
    glbs = _glbs(res)
    if not glbs:
        raise RuntimeError(f"SAM3D returned no mesh: {list(res)}")
    urllib.request.urlretrieve(glbs[0], out_path)
    return out_path


def real_image_to_mesh(image_url: str, sam_prompt: str, name: str, out_dir: str = "data/meshes") -> dict:
    """Real photo (any host) -> mesh: download with a browser UA (avoids 403),
    re-upload to fal, then SAM 3D with a prompt (segments the object from the scene)."""
    import urllib.request
    import fal_client
    d = Path(out_dir); d.mkdir(parents=True, exist_ok=True)
    img = str(d / f"{name}.jpg")
    req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0 (recon)"})
    Path(img).write_bytes(urllib.request.urlopen(req, timeout=30).read())
    fal_url = fal_client.upload_file(img)
    mesh = image_to_mesh(fal_url, sam_prompt, str(d / f"{name}.glb"))
    return {"image": img, "mesh": mesh}


def generate(name: str, image_prompt: str, *, sam_prompt: str | None = None,
             image_model: str = "flux-ultra", out_dir: str = "data/meshes") -> dict:
    """text -> sharp image -> whole-object mesh. Returns {image, mesh}."""
    d = Path(out_dir); d.mkdir(parents=True, exist_ok=True)
    img_path = str(d / f"{name}.png")
    url = text_to_image(image_prompt, img_path, model=image_model)
    mesh_path = image_to_mesh(url, sam_prompt or image_prompt.split(",")[0], str(d / f"{name}.glb"))
    return {"image": img_path, "mesh": mesh_path, "image_url": url}


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv(str(Path(__file__).resolve().parents[3] / ".env"))
    name = sys.argv[1] if len(sys.argv) > 1 else "laptop"
    prompt = sys.argv[2] if len(sys.argv) > 2 else (
        "a sleek modern open laptop, crisp sharp studio product photograph, high "
        "detail, clean edges, plain white seamless background, centered")
    model = sys.argv[3] if len(sys.argv) > 3 else "flux-ultra"
    print(f"generating '{name}' via {model} ...")
    r = generate(name, prompt, image_model=model)
    print(r)
