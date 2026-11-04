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

# CUDA
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'
prefs.get_devices()
for device in prefs.devices:
    device.use = True if device.type == 'CUDA' else False

# --- 3. OBJETOS ---
NOMBRE_HELI = 'ALH Dhruv Helicopter'
NOMBRE_CAMARA = 'Camera'

heli = bpy.data.objects.get(NOMBRE_HELI)
camara = bpy.data.objects.get(NOMBRE_CAMARA)
fog_obj = bpy.data.objects.get('Cube.009')

if not heli or not camara:
    print("ERROR: No se encontró el objeto o la cámara.")
    sys.exit(1)

# --- NIEBLA ---
mat = fog_obj.active_material
nodes = mat.node_tree.nodes

volume_node = None
for n in nodes:
    if n.type == 'VOLUME_SCATTER':
        volume_node = n
        break

if not volume_node:
    print("ERROR: No se encontró nodo Volume Scatter.")
    sys.exit(1)

ESCALA_ORIGINAL = heli.scale.copy()

# --- SALIDA ---
dir_actual = os.path.dirname(os.path.realpath(__file__))
ruta_salida = os.path.join(dir_actual, "dataset_lluvia_movido")
os.makedirs(ruta_salida, exist_ok=True)

# --- FUNCIÓN BBOX ---
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

    x_min, x_max = max(0.0, min(xs)), min(1.0, max(xs))
    y_min, y_max = max(0.0, min(ys)), min(1.0, max(ys))

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

# --- FUNCIÓN POSICIONAR HELI EN FRUSTUM ---
def colocar_heli_en_frustum(cam, obj):
    scene = bpy.context.scene
    
    # coordenadas en pantalla (NDC)
    x = random.uniform(0.3, 0.7)
    y = random.uniform(0.55, 0.9)  # mitad superior
    
    # distancia aleatoria
    distancia = random.uniform(80, 250)
    
    frame = cam.data.view_frame(scene=scene)

    punto = (
        frame[0] * (1 - x) * (1 - y) +
        frame[1] * x * (1 - y) +
        frame[2] * x * y +
        frame[3] * (1 - x) * y
    )
    
    direccion = punto.normalized()
    world_pos = cam.matrix_world @ (direccion * distancia)
    
    obj.location = world_pos

# --- BUCLE ---
print(f"Iniciando generación de imágenes: {inicio} a {fin}")

for i in range(inicio, fin):

    # NIEBLA
    fog_density = random.uniform(0.0005, 0.001)
    volume_node.inputs["Density"].default_value = fog_density

    # ESCALA
    factor_escala = random.uniform(0.6, 1.1)
    heli.scale = ESCALA_ORIGINAL * factor_escala

    # POSICIÓN
    colocar_heli_en_frustum(camara, heli)

# ROTACIÓN NATURAL (NO MIRAR DIRECTO A CÁMARA)
    heli.rotation_euler = (
        random.uniform(math.radians(-8), math.radians(8)),   # inclinación ligera
        random.uniform(math.radians(-8), math.radians(8)),   # inclinación ligera
        random.uniform(0, 2 * math.pi)                      # giro libre
    )

    # RENDER
    nombre_archivo = f"heli_{i:04d}.png"
    scene.render.filepath = os.path.join(ruta_salida, nombre_archivo)
    
    print(f"[{i+1}/{fin}] Renderizando {nombre_archivo}...")
    bpy.ops.render.render(write_still=True)

    # BBOX
    bbox = get_bbox_precision(heli, camara)
    area = round(bbox[2] * bbox[3], 2)
    dist_real = (camara.location - heli.location).length

    # JSON
    info_json = {
        "file_name": nombre_archivo,
        "image_id": i,
        "category_id": 1,
        "bbox": bbox,
        "area": area,
        "weather": "lluvia",
        "fog_density": round(fog_density, 4),
        "luminosity": 0.0,
        "distance": round(dist_real, 2)
    }
    
    nombre_json = f"heli_{i:04d}.json"
    with open(os.path.join(ruta_salida, nombre_json), 'w') as f:
        json.dump(info_json, f, indent=4)

# RESET
heli.scale = ESCALA_ORIGINAL

print(f"✅ Proceso completado en: {ruta_salida}")