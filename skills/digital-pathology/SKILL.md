---
name: digital-pathology
description: Generate correct code for whole-slide image (WSI) analysis using TIAToolbox and foundation models (H-optimus-0, UNI, Prov-GigaPath). Triggers on requests involving whole-slide images, WSI, digital pathology, histopathology, SVS/NDPI/pyramidal TIFF, tissue segmentation, patch extraction, stain normalization, H-optimus-0, TIAToolbox, CAMELYON16/17, SlideGraph, MIL aggregation, HoVer-Net, PanNuke, or SageMaker deployment of pathology models. Produces deterministic commands and Python snippets for slide-info inspection, tissue masking, tile extraction at specified mpp, foundation-model feature embedding, slide-level aggregation, and regulated cloud inference.
usage: Invoke when analyzing whole-slide images, extracting tiles, running foundation-model embeddings, or deploying pathology models on SageMaker.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {tiatoolbox: "1.5", openslide: "4.0"}
tags: [skill, category:pipeline, digital-pathology, tiatoolbox, h-optimus-0, whole-slide-image, hcls]
---

# Digital Pathology

## Overview

This skill teaches the agent to generate correct, runnable code for whole-slide image (WSI) pipelines. It covers TIAToolbox CLI and Python API, the H-optimus-0 foundation model, the standard tissue→tiles→features→aggregate→predict pattern, the CAMELYON datasets, and SageMaker deployment patterns for regulated workloads.

Default to TIAToolbox primitives (`WSIReader`, `PatchPredictor`, `DeepFeatureExtractor`) rather than reimplementing slide I/O. Default to H-optimus-0 at 0.5 mpp / 224×224 unless the task specifies otherwise.

## Usage

Invoke this skill when the user asks to:

- Inspect, tile, or stain-normalize a WSI (SVS, NDPI, MRXS, pyramidal TIFF).
- Extract features with a pathology foundation model.
- Build a slide-level classifier on CAMELYON or similar cohorts.
- Deploy a WSI model to AWS SageMaker.

Ask for clarification only if the resolution, model, or output artifact is ambiguous. Otherwise apply the defaults in the Resolution Rules section.


## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## Core Concepts

- **Pyramidal WSI**: multi-resolution image (levels). `baseline` = level 0 (native, finest). Addressing uses `resolution` + `units ∈ {mpp, power, level, baseline}`.
- **mpp**: microns per pixel. `0.5 mpp ≈ 20×`, `0.25 mpp ≈ 40×`. Downsample = `baseline_mpp / target_mpp`.
- **Tissue mask**: binary foreground mask computed at low resolution (e.g., Otsu at 1.25× or 4 mpp) to skip background tiles.
- **Patch / tile**: fixed-size crop (e.g., 224×224) read at a target mpp, used as model input.
- **Foundation model embedding**: per-tile feature vector from a pretrained ViT (H-optimus-0 → 1536-d).
- **Aggregation**: slide-level prediction from tile features (ABMIL, CLAM, TransMIL, SlideGraph).

## Quick Reference — Standard Pipeline

Copy-adapt this end-to-end pattern for any WSI classification task:

```python
import torch
from tiatoolbox.wsicore.wsireader import WSIReader
from tiatoolbox.models.architecture.vanilla import TimmBackbone
from tiatoolbox.models.engine.semantic_segmentor import IOSegmentorConfig
from tiatoolbox.models.engine.patch_predictor import IOPatchPredictorConfig
from tiatoolbox.models import DeepFeatureExtractor

SLIDE = "slide.svs"
OUT = "./out"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# 1. Inspect
reader = WSIReader.open(SLIDE)
info = reader.info.as_dict()
print(info["mpp"], info["level_dimensions"])

# 2. Tissue mask (Otsu at low res — do NOT pass as external mask)
mask_reader = reader.tissue_mask(method="otsu", resolution=4, units="mpp")

# 3. Tile + extract H-optimus-0 features @ 0.5 mpp, 224x224
ioconfig = IOPatchPredictorConfig(
    input_resolutions=[{"units": "mpp", "resolution": 0.5}],
    patch_input_shape=[224, 224],
    stride_shape=[224, 224],
)
extractor = DeepFeatureExtractor(
    model=TimmBackbone("H-optimus-0", pretrained=True),
    batch_size=16,
    num_loader_workers=4,
)
output = extractor.run(
    images=[SLIDE],
    masks=[mask_reader],
    patch_mode=False,
    ioconfig=ioconfig,
    save_dir=OUT,
    device=DEVICE,
)
# output[0] -> (positions.npy, features.npy)
```

Then aggregate (ABMIL / SlideGraph / mean-pool) on `features.npy` for a slide-level prediction.

## TIAToolbox CLI

All CLI commands accept `--img-input` (file or dir), `--output-path`, `--resolution`, `--units`, `--batch-size`, `--device cuda`.

```bash
# Slide metadata
tiatoolbox slide-info --img-input slide.svs --mode show

# Tissue mask (binary PNG)
tiatoolbox tissue-mask --img-input slide.svs --output-path ./mask --method otsu \
  --resolution 1.25 --units power

# Tile classification with built-in ResNet18 on Kather100k
tiatoolbox patch-predictor --img-input slide.svs \
  --pretrained-model resnet18-kather100k \
  --output-path ./pred --batch-size 32 --device cuda \
  --resolution 0.5 --units mpp

# Stain normalization (Reinhard / Macenko / Vahadane)
tiatoolbox stain-norm --img-input tiles/ --method reinhard --output-path ./norm
```

Use `--units baseline` when inputs are pre-extracted PNG tiles to avoid an "unknown scale" warning.

## TIAToolbox Python API

### WSIReader

```python
from tiatoolbox.wsicore.wsireader import WSIReader

reader = WSIReader.open("slide.svs")
reader.info.as_dict()                              # mpp, levels, vendor
reader.slide_dimensions(resolution=0.5, units="mpp")

tile = reader.read_rect(
    location=(10000, 10000),    # baseline coords
    size=(224, 224),
    resolution=0.5, units="mpp",
)
region = reader.read_bounds(
    bounds=(0, 0, 4096, 4096),
    resolution=2.0, units="mpp",
)
mask = reader.tissue_mask(method="otsu", resolution=4, units="mpp")
```

### PatchPredictor

```python
from tiatoolbox.models import PatchPredictor
from tiatoolbox.models.engine.patch_predictor import IOPatchPredictorConfig

ioconfig = IOPatchPredictorConfig(
    input_resolutions=[{"units": "mpp", "resolution": 0.5}],
    patch_input_shape=[224, 224],
    stride_shape=[224, 224],
)
predictor = PatchPredictor(pretrained_model="resnet18-kather100k", batch_size=32)
out = predictor.run(
    images=["slide.svs"], masks=[mask],
    patch_mode=False, ioconfig=ioconfig,
    save_dir="./pred", device="cuda",
)
```

### DeepFeatureExtractor + TimmBackbone

```python
from tiatoolbox.models import DeepFeatureExtractor
from tiatoolbox.models.architecture.vanilla import TimmBackbone

extractor = DeepFeatureExtractor(
    model=TimmBackbone("H-optimus-0", pretrained=True),
    batch_size=16, num_loader_workers=4,
)
```

### SlideGraph construction

```python
import numpy as np
from tiatoolbox.tools.graph import SlideGraphConstructor

positions = np.load("out/0.position.npy")   # (N, 4) x1,y1,x2,y2
features  = np.load("out/0.features.npy")   # (N, D)
graph = SlideGraphConstructor.build(
    positions=positions[:, :2], features=features,
)
# graph -> {"x": features, "edge_index": (2,E), "coords": (N,2)}
```

### Stain normalization

```python
from tiatoolbox.tools.stainnorm import get_normalizer

norm = get_normalizer("reinhard")   # or "macenko", "vahadane"
norm.fit(target_tile)               # RGB ndarray HxWx3
normed = norm.transform(source_tile)
```

## H-optimus-0 Foundation Model

1.1B-parameter ViT-G/14, input **224×224 RGB at 0.5 mpp**, output **1536-d** embedding. License is gated — accept terms on Hugging Face and run `huggingface-cli login`.

### Direct timm usage

```python
import timm, torch
from torchvision import transforms

model = timm.create_model(
    "hf-hub:bioptimus/H-optimus-0",
    pretrained=True,
    init_values=1e-5,
    dynamic_img_size=False,
).eval().to("cuda")

preprocess = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(
        mean=(0.707223, 0.578729, 0.703617),
        std=(0.211883, 0.230117, 0.177517),
    ),
])

with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
    feats = model(preprocess(tile).unsqueeze(0).to("cuda"))   # (1, 1536)
```

Use `batch_size=16` on a 24 GB GPU with fp16 autocast. Prefer `TimmBackbone("H-optimus-0", pretrained=True)` inside `DeepFeatureExtractor` — TIAToolbox applies the correct preprocessing automatically.

## Resolution Rules

| Model | mpp | Patch size |
| --- | --- | --- |
| H-optimus-0 / UNI / Prov-GigaPath | 0.5 | 224×224 |
| HoVer-Net (PanNuke) | 0.25 | 256×256 |
| SlideGraph CNN features | 0.25 | 512×512 |
| Tissue mask (Otsu) | 4 mpp or 1.25× | — |

Downsample factor = `baseline_mpp / target_mpp`. For a 0.25-mpp slide targeting 0.5 mpp, downsample by 2.

## CAMELYON Datasets

- **Format**: pyramidal `.tif`, OpenSlide-compatible, ~100 000 × 100 000 px at baseline.
- **Annotations**: ASAP XML, polygon coordinates in **baseline (level-0) pixels**.
- **CAMELYON16**: 270 training slides (`normal/` + `tumor/`) + 130 test slides, labels in `reference.csv`. Task: slide-level tumor classification + tumor segmentation.
- **CAMELYON17**: 1000 slides across 100 patients (5 slides each). Patient-level pN-stage in `stages.csv`. Official 5-fold split is **by patient** — never split by slide.

```python
import xml.etree.ElementTree as ET
tree = ET.parse("slide.xml")                 # ASAP format
for ann in tree.iter("Annotation"):
    pts = [(float(c.get("X")), float(c.get("Y")))
           for c in ann.iter("Coordinate")]   # baseline coords
```

## SageMaker Deployment

WSIs are gigapixel — **never send raw bytes through the invocation path**. Pass an **S3 URI** in the request and let the container read via `s3fs` / `boto3`.

- **Endpoint type**: **Async Inference** (long-running, per-request) or **Batch Transform** (cohort scoring).
- **Base container**: extend `763104351884.dkr.ecr.<region>.amazonaws.com/pytorch-inference:2.x-gpu-py310`.
- **Apt packages**: `openslide-tools libpixman-1-dev libvips`.
- **Pip**: `tiatoolbox timm huggingface_hub s3fs`.
- **Instance**: `ml.g5.2xlarge` minimum for H-optimus-0 fp16 (24 GB A10G). Use `ml.g5.12xlarge` for batches.
- **Async config**: `invocations_timeout=3600`, `max_concurrent_invocations_per_instance=2`.

```python
from sagemaker.async_inference import AsyncInferenceConfig
async_config = AsyncInferenceConfig(
    output_path="s3://bucket/async-out/",
    max_concurrent_invocations_per_instance=2,
)
predictor = model.deploy(
    instance_type="ml.g5.2xlarge", initial_instance_count=1,
    async_inference_config=async_config,
)
predictor.predict_async(input_path="s3://bucket/slides/slide.svs")
```

Dockerfile sketch:

```dockerfile
FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.3.0-gpu-py310
RUN apt-get update && apt-get install -y openslide-tools libpixman-1-dev libvips \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir tiatoolbox timm huggingface_hub s3fs
```

## Common Mistakes

- **Wrong:** Using an old pixman library (<0.40) with OpenSlide
  **Right:** `apt-get install libpixman-1-dev` and rebuild, or use libvips ≥ 8.12
  **Why:** Causes all-black tiles from `read_rect` due to a rendering bug

- **Wrong:** Requesting a resolution finer than the slide's native mpp
  **Right:** Use a coarser `resolution`, or check `reader.info.mpp` first
  **Why:** Triggers `UserWarning: Scale > 1` and produces upsampled (interpolated) data

- **Wrong:** Attempting to load H-optimus-0 without accepting the gated model terms
  **Right:** Accept terms on the Hugging Face model page, then run `huggingface-cli login`
  **Why:** Results in `OSError: 401` authentication failure

- **Wrong:** Using a batch size too large for GPU memory in DeepFeatureExtractor
  **Right:** Lower `batch_size` (16→8→4) and ensure fp16 autocast is enabled
  **Why:** Causes CUDA out-of-memory errors

- **Wrong:** Passing a non-pyramidal TIFF to OpenSlide
  **Right:** Convert first with `vips tiffsave in.tif out.tif --tile --pyramid --compression jpeg`
  **Why:** Raises `OpenSlideUnsupportedFormatError` because OpenSlide requires pyramidal format

- **Wrong:** Passing a numpy array as an external mask with shape not aligned to the WSI pyramid
  **Right:** Use `reader.tissue_mask(...)` directly and pass the returned reader object
  **Why:** Causes `DimensionMismatchError` due to resolution/shape mismatch

- **Wrong:** Processing PNG tiles without specifying resolution units
  **Right:** Pass `units="baseline"` and explicit `resolution=1.0`
  **Why:** Tiles lack mpp metadata, triggering an "unknown scale" warning

- **Wrong:** Splitting CAMELYON17 data by slide rather than by patient
  **Right:** Split by `patient_id` (5-fold) per the official protocol
  **Why:** Causes patient data leakage since each patient has 5 slides

- **Wrong:** Skipping H-optimus-0 normalization (mean/std) when extracting features
  **Right:** Use `TimmBackbone` (applies normalization automatically) or apply mean/std explicitly
  **Why:** Features look random and produce low AUC without proper input normalization

- **Wrong:** Using annotation coordinates at the wrong pyramid level
  **Right:** ASAP XML coordinates are always at **baseline** level — scale them when reading at lower resolution
  **Why:** Coordinates will be off by 2× or 4× if the level mismatch is not accounted for

## Minimal Dependency Set

```
tiatoolbox>=1.5
timm>=1.0
torch>=2.1
openslide-python
huggingface_hub
```

System: `openslide-tools`, `libpixman-1-dev`, `libvips` (for non-pyramidal TIFF conversion).

## References

- TIAToolbox: Pocock et al. Commun Med 2022, https://doi.org/10.1038/s43856-022-00186-5
- H-optimus-0: Bioptimus, https://huggingface.co/bioptimus/H-optimus-0
- CAMELYON16: Bejnordi et al. JAMA 2017, https://doi.org/10.1001/jama.2017.14585
- CAMELYON17: Bandi et al. IEEE TMI 2019, https://doi.org/10.1109/TMI.2018.2867350
