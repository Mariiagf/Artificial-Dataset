import bpy
import bpy_extras
import random
import os
import math
import json
import sys
from mathutils import Vector

# 1. CAPTURA DE ARGUMENTOS
try:
    args = sys.argv[sys.argv.index("--") + 1:]
    inicio = int(args[0])
    fin = inicio + 60
except (IndexError, ValueError):
    inicio = 0
    fin = 60

# 2. CONFIGURACIÓN DE RENDER 
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.render.use_persistent_data = False

prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'
prefs.get_devices()
for device in prefs.devices:
    device.use = True if device.type == 'CUDA' else False

# 3. OBJETOS 
heli = bpy.data.objects.get('ALH Dhruv Helicopter')
camara = bpy.data.objects.get('Camera')
fog_obj = bpy.data.objects.get('Cube.009')

if not heli or not camara or not fog_obj:
    print("ERROR: Falta heli, cámara o cubo de niebla.")
    sys.exit(1)

ESCALA_ORIGINAL = heli.scale.copy()

# MATERIAL NIEBLA 
mat = fog_obj.active_material
if not mat or not mat.use_nodes:
    print("ERROR: El cubo no tiene material con nodos.")
    sys.exit(1)

nodes = mat.node_tree.nodes

volume_node = None
for n in nodes:
    if n.type == 'VOLUME_SCATTER':
        volume_node = n
        break

if not volume_node:
    print("ERROR: No se encontró nodo Volume Scatter.")
    sys.exit(1)

# TRACK TO 
if not camara.constraints.get("LookAtHeli"):
    const = camara.constraints.new(type='TRACK_TO')
    const.target = heli
    const.track_axis = 'TRACK_NEGATIVE_Z'
    const.up_axis = 'UP_Y'

# BASE 
dx = camara.location.x - heli.location.x
dy = camara.location.y - heli.location.y
RADIO_BASE = math.sqrt(dx**2 + dy**2)
ALTURA_BASE = camara.location.z

# SALIDA
dir_actual = os.path.dirname(os.path.realpath(__file__))
ruta_salida = os.path.join(dir_actual, "dataset_niebla")
os.makedirs(ruta_salida, exist_ok=True)

# BBOX 
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

# GENERACIÓN 
print(f"Iniciando generación con niebla: {inicio} a {fin}")

for i in range(inicio, fin):

    # NIEBLA
    fog_density = random.uniform(0.01, 0.055)
    volume_node.inputs["Density"].default_value = fog_density

    # MOVIMIENTO 
    variacion_distancia = random.uniform(1.0, 2.5)
    radio_actual = RADIO_BASE * variacion_distancia
    
    factor_escala = random.uniform(0.6, 1.1)
    heli.scale = ESCALA_ORIGINAL * factor_escala
    heli.rotation_euler[2] = random.uniform(0, 2 * math.pi)
    
    angulo_cam = random.uniform(0, 2 * math.pi)
    camara.location.x = heli.location.x + radio_actual * math.cos(angulo_cam)
    camara.location.y = heli.location.y + radio_actual * math.sin(angulo_cam)
    camara.location.z = ALTURA_BASE + random.uniform(-5.0, 10.0)

    bpy.context.view_layer.update()
    
    # RENDER
    nombre_archivo = f"heli_{i:04d}.png"
    scene.render.filepath = os.path.join(ruta_salida, nombre_archivo)
    
    print(f"[{i+1}/{fin}] {nombre_archivo} | fog={fog_density:.3f}")
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
        "weather": "niebla",
        "fog_density": round(fog_density, 4),
        "luminosity": 0.0,
        "distance": round(dist_real, 2)
    }
    
    nombre_json = f"heli_{i:04d}.json"
    with open(os.path.join(ruta_salida, nombre_json), 'w') as f:
        json.dump(info_json, f, indent=4)

heli.scale = ESCALA_ORIGINAL

print(f"Dataset con niebla generado en: {ruta_salida}")