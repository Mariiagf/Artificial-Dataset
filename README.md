# Artificial Dataset: Synthetic Aircraft Images for Detect & Avoid (DAA)

Synthetic dataset of fixed-wing aircraft and helicopters, generated with **Blender** and automatically labelled in **COCO format**, to evaluate the **YOLOX** detection model used by [Gradiant](https://www.gradiant.org/) in its Detect and Avoid (DAA) system for drones flying BVLOS (Beyond Visual Line of Sight).

Project developed for the *Proxecto Integrador de Intelixencia Artificial* course (Grao en Intelixencia Artificial, Universidade de Santiago de Compostela, 2025/26), in collaboration with Gradiant.

## Motivation

Gradiant's DAA system struggles to detect fixed-wing aircraft (Cessna-type and ultralight), mainly because of a lack of training data. Capturing real air-to-air images is expensive (flights, fuel, pilots) and slow (weather, availability). This project replaces that process with a **3D synthetic data pipeline** that:

- Generates thousands of images with controlled variations (weather, distance, lighting, rotation, position).
- Labels every image automatically (bounding boxes projected from the 3D scene, so there is no manual labelling error).
- Allows the model to be evaluated by groups (scenario, weather, aircraft type) to find its strengths and weaknesses.

## Dataset overview

- **769 rendered images** in three scenarios: **sea**, **mountain** and **countryside**.
- **Aircraft:** a helicopter in the sea and mountain scenarios, and a Cessna 172 light aircraft in the countryside scenario.
- **Weather conditions:** clear, fog (variable density) and rain (Blender particle systems).
- **Randomised parameters:** aircraft position and rotation, camera distance and angle (from close range to a few pixels in size), scene luminosity, fog density, and off-centre aircraft placement.
- **Annotations:** COCO-style JSON including bounding box, area, aircraft model, weather, fog density, luminosity and camera-to-aircraft distance.

The images can be downloaded from the link in [`datasets_link.txt`](datasets_link.txt).

## Repository structure

```
Artificial-Dataset/
├── archives/                  # Blender scenes (stored with Git LFS)
│   ├── archivos_campo/        #   countryside scenario + label scrpits
│   ├── archivos_mar/          #   sea scenario
│   └── archivos_montana/      #   mountain scenario
├── docs/                      # Project deliverables (PDF)
├── results/                   # YOLOX validation results
├── commands.txt               # Commands used to run the generation on CESGA
├── datasets_link.txt          # Link to the generated datasets (Google Drive)
├── .gitattributes             # Git LFS configuration for .blend files
├── LICENSE
└── README.md
```

### Folders

| Folder | Content |
|--------|---------|
| `archives/` | Blender (`.blend`) scene files and the Python script for label generation. One folder per scenario: `archivos_campo` (countryside), `archivos_mar` (sea) and `archivos_montana` (mountain). |
| `docs/` | The three project deliverables: **AVP1** (project plan), **AVP2** (functional and technical requirements) and **AVP3** (results report and conclusions). |
| `results/` | Results of the YOLOX validation on the generated datasets. |


## How it works

```
Manual scenes in Blender
        ↓
Python script (bpy API): random aircraft / camera / weather / light
        ↓
Batch rendering on CESGA (Blender 5.0, background mode, GPU)
        ↓
3D → 2D projection → bounding box + metadata (JSON, COCO)
        ↓
Merge into a single COCO dataset (unir.py)
        ↓
Validation of the YOLOX model
```

## Usage

> Git LFS is required to download the `.blend` files: `git lfs install` before cloning.

### 1. Generate images and labels

Requirements: [Blender](https://www.blender.org/) 5.0 (the scenes contain the objects `Cessna 172 - Aircraft`, `Camera`, `Landscape` and `Cube` for fog, which the scripts look up by name).

```bash
# Interactive GPU session on CESGA (optional)
srun -p viz --gres=gpu:1 -c 32 --mem=32G -t 04:00:00 --pty bash

# Range of images to generate
INICIO=0
FIN=100

# Render and label
./blender-5.0.0-linux-x64/blender -b "scene.blend" -noaudio -P "generar_etiquetar.py" -- $INICIO $FIN
```

Output goes to `./dataset_bw/`, with one `lheli_XXXX.png` and one `lheli_XXXX.json` per image.

### 2. Build the COCO dataset

Place the per-scenario folders (images + annotation files) in `./prueba/` and run:

```bash
python unir.py
```

The merged dataset is written to `./helicoptero/datasets/COCO/` (`val2017/` and `annotations/instances_val2017.json`).

## Results

The datasets were validated with Gradiant's YOLOX model and compared with its validation on a real-image dataset (Airborne). Metrics are Precision (average over IoU 0.50:0.95) and Recall for all object sizes:

| Dataset | Images | Precision | Recall |
|---------|:------:|:---------:|:------:|
| Airborne (real) | – | 0.489 | 0.570 |
| Complete synthetic | 769 | 0.269 | 0.328 |
| Countryside / Cessna | 286 | 0.389 | 0.418 |
| Sea | 258 | 0.236 | 0.319 |
| Mountain | 225 | 0.108 | 0.143 |
| Fog | 273 | 0.308 | 0.364 |
| Rain | 193 | 0.150 | 0.186 |
| Clear | 303 | 0.335 | 0.392 |
| Helicopter | 483 | 0.173 | 0.237 |

Main conclusions:

- Detection improves with object size: small (distant) aircraft are the hardest case.
- **Mountain** scenes and **rain** are the most difficult conditions (camouflage against complex terrain, droplets occluding the contours).
- The synthetic dataset works well as a **diagnostic tool**: it reveals where the model fails (distance, weather, background), at a fraction of the cost of real flight campaigns.

See `docs/` (AVP3) for the full analysis, deviations from the plan and future work (video sequences, more weather conditions, night scenes, new object classes).


## Authors

- Alejandra Ares Rivas.
- María Gómez Fernández.
- Paula Esmorís Rodríguez.

Tutor at Gradiant: Daniel Jove Díaz.

## License

See the [LICENSE](LICENSE) file.
