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
    fin = inicio + 60 
except (IndexError, ValueError):
    inicio = 0
    fin = 60

# --- 2. CONFIGURACIÓN DE RENDER ---
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.render.use_persistent_data = False

# Configuración CUDA
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'
prefs.get_devices()
for device in prefs.devices:
    device.use = True if device.type == 'CUDA' else False



# --- 3. IDENTIFICACIÓN DE OBJETOS ---
NOMBRE_HELI = 'ALH Dhruv Helicopter'
NOMBRE_CAMARA = 'Camera'

heli = bpy.data.objects.get(NOMBRE_HELI)
camara = bpy.data.objects.get(NOMBRE_CAMARA)
fog_obj = bpy.data.objects.get('Cube.009')

# --- MATERIAL NIEBLA ---
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

if not heli or not camara:
    print("ERROR: No se encontró el objeto o la cámara.")
    sys.exit(1)

ESCALA_ORIGINAL = heli.scale.copy()

if not camara.constraints.get("LookAtHeli"):
    const = camara.constraints.new(type='TRACK_TO')
    const.target = heli
    const.track_axis = 'TRACK_NEGATIVE_Z'
    const.up_axis = 'UP_Y'

# Parámetros de órbita base
dx = camara.location.x - heli.location.x
dy = camara.location.y - heli.location.y
RADIO_BASE = math.sqrt(dx**2 + dy**2)
ALTURA_BASE = camara.location.z

dir_actual = os.path.dirname(os.path.realpath(__file__))
ruta_salida = os.path.join(dir_actual, "dataset_lluvia")
if not os.path.exists(ruta_salida):
    os.makedirs(ruta_salida)

# --- FUNCIÓN DE PRECISIÓN  ---
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
            # Coordenada local a global
            world_coord = part.matrix_world @ v.co
            # Proyectar a cámara (0.0 a 1.0)
            co_ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_coord)

            if co_ndc.z > 0:
                coords_2d.append((co_ndc.x, co_ndc.y))
        
        part_eval.to_mesh_clear()

    if not coords_2d:
        return [0, 0, 0, 0]

    xs, ys = zip(*coords_2d)

    x_min, x_max = max(0.0, min(xs)), min(1.0, max(xs))
    y_min, y_max = max(0.0, min(ys)), min(1.0, max(ys))

    # Convertir a píxeles
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

# --- 4. BUCLE DE GENERACIÓN ---
print(f"Iniciando generación de 60 imágenes: {inicio} a {fin}")

for i in range(inicio, fin):

      # --- NIEBLA (CLAVE) ---
    fog_density = random.uniform(0.0005, 0.001)
    volume_node.inputs["Density"].default_value = fog_density

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
    
    # Renderizado
    nombre_archivo = f"heli_{i:04d}.png"
    scene.render.filepath = os.path.join(ruta_salida, nombre_archivo)
    
    print(f"[{i+1}/{fin}] Renderizando {nombre_archivo}... Escala: {factor_escala:.2f}")
    bpy.ops.render.render(write_still=True)
    
    # Cálculo de BBox con la función de precisión
    bbox = get_bbox_precision(heli, camara)
    area = round(bbox[2] * bbox[3], 2)
    dist_real = (camara.location - heli.location).length
    
    
    # Datos JSON
    info_json = {
        "file_name": nombre_archivo,
        "image_id": i,
        "category_id": 1,
        "bbox": bbox,
        "area": area,
        "weather": "lluvia",
        "fog_density": round(fog_density, 4),
        "luminosity": 1.0,
        "distance": round(dist_real, 2)
    }
    
    nombre_json = f"heli_{i:04d}.json"
    with open(os.path.join(ruta_salida, nombre_json), 'w') as f:
        json.dump(info_json, f, indent=4)

# Resetear escala
heli.scale = ESCALA_ORIGINAL
print(f"Archivos en: {ruta_salida}")