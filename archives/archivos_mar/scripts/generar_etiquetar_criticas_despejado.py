import bpy
import bpy_extras
import random
import os
import math
import json
import sys
from mathutils import Vector

# --- 1. CAPTURA DE ARGUMENTOS ---
try:
    args = sys.argv[sys.argv.index("--") + 1:]
    inicio = int(args[0])
    fin = inicio + 20   
except (IndexError, ValueError):
    inicio = 0
    fin = 20

# --- 2. CONFIGURACIÓN DE RENDER ---
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.render.use_persistent_data = False

prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'
prefs.get_devices()
for device in prefs.devices:
    device.use = True if device.type == 'CUDA' else False

# --- 3. OBJETOS ---
heli = bpy.data.objects.get('ALH Dhruv Helicopter')
camara = bpy.data.objects.get('Camera')

if not heli or not camara:
    print("ERROR: Falta heli o cámara")
    sys.exit(1)

ESCALA_ORIGINAL = heli.scale.copy()

# Constraint 
if not camara.constraints.get("LookAtHeli"):
    const = camara.constraints.new(type='TRACK_TO')
    const.target = heli
    const.track_axis = 'TRACK_NEGATIVE_Z'
    const.up_axis = 'UP_Y'

# Base
dx = camara.location.x - heli.location.x
dy = camara.location.y - heli.location.y
RADIO_BASE = math.sqrt(dx**2 + dy**2)
ALTURA_BASE = camara.location.z

# Salida
dir_actual = os.path.dirname(os.path.realpath(__file__))
ruta_salida = os.path.join(dir_actual, "dataset_criticas_despejado")
os.makedirs(ruta_salida, exist_ok=True)

# --- BBOX ---
def get_bbox_precision(obj, cam):
    width = scene.render.resolution_x
    height = scene.render.resolution_y
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    coords_2d = []
    all_parts = [obj] + list(obj.children_recursive)

    for part in all_parts:
        if part.type != 'MESH':
            continue
        
        part_eval = part.evaluated_get(depsgraph)
        mesh = part_eval.to_mesh()

        for v in mesh.vertices:
            world_coord = part.matrix_world @ v.co
            co_ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_coord)

            if co_ndc.z > 0:
                coords_2d.append((co_ndc.x, co_ndc.y))
        
        part_eval.to_mesh_clear()

    if not coords_2d:
        return [0, 0, 0, 0]

    xs, ys = zip(*coords_2d)

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    px_left = x_min * width
    px_top = (1 - y_max) * height
    px_width = (x_max - x_min) * width
    px_height = (y_max - y_min) * height

    return [
        round(px_left, 2),
        round(px_top, 2),
        round(px_width, 2),
        round(px_height, 2)
    ]

# --- GENERACIÓN ---
print(f"Generando 20 imágenes ({inicio}-{fin})")
for i in range(inicio, fin):

    variacion_distancia = random.uniform(4.0, 10.0)

    angulo = random.uniform(0, 2 * math.pi)

    heli.location.x = camara.location.x + RADIO_BASE * variacion_distancia * math.cos(angulo)
    heli.location.y = camara.location.y + RADIO_BASE * variacion_distancia * math.sin(angulo)
    heli.location.z = camara.location.z + random.uniform(-30.0, 30.0)

    factor_escala = random.uniform(0.3, 0.8)
    heli.scale = ESCALA_ORIGINAL * factor_escala

    heli.rotation_euler[2] = random.uniform(0, 2 * math.pi)

    offset_strength = random.uniform(0.0, 1.2)

    camara.location.x += random.uniform(-offset_strength, offset_strength)
    camara.location.y += random.uniform(-offset_strength, offset_strength)

    bpy.context.view_layer.update()

    # --- RENDER ---
    nombre_img = f"heli_{i:04d}.png"
    scene.render.filepath = os.path.join(ruta_salida, nombre_img)

    bpy.ops.render.render(write_still=True)

    # --- BBOX ---
    bbox = get_bbox_precision(heli, camara)
    area = round(bbox[2] * bbox[3], 2)

    weather = "despejado"
    fog_density = 0.0
    luminosity = 1.0
    dist_real = (camara.location - heli.location).length

    info = {
        "file_name": nombre_img,
        "image_id": i,
        "category_id": 1,
        "bbox": bbox,
        "area": area,
        "weather": weather,
        "fog_density": fog_density,
        "luminosity": luminosity,
        "distance": round(dist_real, 2)
    }

    with open(os.path.join(ruta_salida, f"heli_{i:04d}.json"), 'w') as f:
        json.dump(info, f, indent=4)

heli.scale = ESCALA_ORIGINAL

print("Dataset listo")