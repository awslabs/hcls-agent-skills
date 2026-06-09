import io
import json
import os
import torch
import timm
from PIL import Image
from torchvision import transforms


def model_fn(model_dir):
    """Load H-optimus-0 once at container startup."""
    # Login to HuggingFace for gated model access
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        from huggingface_hub import login
        login(token=hf_token)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = timm.create_model(
        "hf-hub:bioptimus/H-optimus-0",
        pretrained=True,
        init_values=1e-5,
        dynamic_img_size=False,
    )
    model.to(device)
    model.eval()
    print(f"H-optimus-0 loaded on {device}")
    return {"model": model, "device": device}


def input_fn(request_body, content_type):
    """Accept raw image bytes (PNG or JPEG)."""
    if content_type in ("image/png", "image/jpeg", "image/jpg", "application/x-image"):
        return Image.open(io.BytesIO(request_body)).convert("RGB")
    raise ValueError(f"Unsupported content type: {content_type}")


def predict_fn(image, model_dict):
    """Run inference on a single 224x224 patch, return 1536-dim features."""
    model = model_dict["model"]
    device = model_dict["device"]

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.707223, 0.578729, 0.703617),
            std=(0.211883, 0.230117, 0.177517),
        ),
    ])

    tensor = transform(image).unsqueeze(0).to(device)
    with torch.inference_mode(), torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device.type == "cuda"):
        features = model(tensor)

    return features.cpu().numpy().tolist()


def output_fn(prediction, accept):
    """Return features as JSON."""
    return json.dumps(prediction), "application/json"
