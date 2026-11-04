import bpy
import bpy_extras
import random
import os
import math
import json
import sys
from mathutils import Vector

# --- 1. CONFIGURACIÓN DE GPU Y SALIDA ---
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.render.image_settings.color_mode = 'RGB'
bpy.context.scene.render.image_settings.color_depth = '8'

bpy.context.preferences.addons['cycles'].preferences.compute_device_type = 'CUDA'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.preferences.addons['cycles'].preferences.get_devices()
for device in bpy.context.preferences.addons['cycles'].preferences.devices:
    device.use = True

# --- 2. RANGOS Y OBJETOS ---
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [0, 10]
inicio, fin = int(args[0]), int(args[1])

# Cambiamos el nombre de la carpeta para diferenciar el dataset
ruta_salida = "./dataset_niebla/" 
if not os.path.exists(ruta_salida): os.makedirs(ruta_salida)

heli = bpy.data.objects.get('ALH Dhruv Helicopter')
camara = bpy.data.objects.get('Cámara')
sol = bpy.data.objects.get('Sol')
referencia = bpy.data.objects.get('Base')
# Añadimos el cubo de niebla
cubo_niebla = bpy.data.objects.get('CuboNiebla') 

bpy.context.scene.camera = camara
camara.data.clip_end = 5000

def get_bbox(obj, cam):
    scene = bpy.context.scene
    render = scene.render
    width = render.resolution_x
    height = render.resolution_y
    depsgraph = bpy.context.evaluated_depsgraph_get()
    coords_2d = []
    objects = [obj] + list(obj.children_recursive)

    for ob in objects:
        if ob.type != 'MESH': continue
        ob_eval = ob.evaluated_get(depsgraph)
        mesh = ob_eval.to_mesh()
        for v in mesh.vertices:
            world_coord = ob.matrix_world @ v.co
            co_ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_coord)
            if co_ndc.z < 0: continue
            coords_2d.append((co_ndc.x, co_ndc.y))
        ob_eval.to_mesh_clear()

    if not coords_2d: return [0, 0, 0, 0]
    xs, ys = zip(*coords_2d)
    x_min, x_max = max(min(xs), 0.0), min(max(xs), 1.0)
    y_min, y_max = max(min(ys), 0.0), min(max(ys), 1.0)
    
    left = x_min * width
    right = x_max * width
    top = (1 - y_max) * height
    bottom = (1 - y_min) * height
    return [round(left, 2), round(top, 2), round(right - left, 2), round(bottom - top, 2)]

# --- 4. BUCLE DE GENERACIÓN ---
for i in range(inicio, fin):
    
    # 1. Configuración de la Niebla (Lógica del vídeo)
    densidad_niebla = random.uniform(0.005, 0.055) # Densidad aleatoria
    if cubo_niebla and cubo_niebla.active_material:
        cubo_niebla.hide_render = False
        nodes = cubo_niebla.active_material.node_tree.nodes
        node_vol = next((n for n in nodes if n.type == 'VOLUME_SCATTER'), None)
        if node_vol:
            node_vol.inputs[1].default_value = densidad_niebla # Density
            node_vol.inputs[2].default_value = 0.7            # Anisotropy (para rayos de luz)

    # 2. Posicionamiento
    x_heli = random.uniform(-0.35, 0.70)
    z_heli = referencia.location.z + random.uniform(0.1, 0.6)
    ir_lejos = random.random() < 0.5 
    
    if ir_lejos:
        offset = random.uniform(2.5, 6.0) 
        y_heli = referencia.location.y + (offset if camara.location.y < referencia.location.y else -offset)
        tipo = "LEJOS"
    else:
        offset = random.uniform(0.1, 0.6)
        y_heli = referencia.location.y - (offset if camara.location.y < referencia.location.y else -offset)
        tipo = "CERCA"

    heli.location = (x_heli, y_heli, z_heli)
    heli.rotation_euler = (random.uniform(-0.17, 0.17), random.uniform(-0.26, 0.26), random.uniform(0, 6.28))

    # 3. Luminosidad (Aumentada para que se vea a través de la niebla)
    luz = random.uniform(10.0, 20.0) 
    sol.data.energy = luz
    sol.rotation_euler[1] = random.uniform(0.35, 2.8)
    sol.rotation_euler[2] = random.uniform(0, 6.28)

    bpy.context.view_layer.update()

    # Render
    nombre = f"heli_niebla_{i:04d}"
    bpy.context.scene.render.filepath = os.path.join(ruta_salida, f"{nombre}.png")
    bpy.ops.render.render(write_still=True)

    # Etiqueta
    bbox = get_bbox(heli, camara)
    label = {
        "file_name": f"{nombre}.png",
        "image_id": i,
        "category_id": 1,
        "bbox": bbox,
        "area": round(bbox[2] * bbox[3], 2),
        "weather": "niebla",
        "fog_density": round(densidad_niebla, 4),
        "luminosity": round(luz, 2),
        "distance": round((heli.location - camara.location).length, 2),
    }

    with open(os.path.join(ruta_salida, f"{nombre}.json"), 'w') as f:
        json.dump(label, f, indent=4)
    
    print(f"Imagen {nombre} | Niebla: {label['fog_density']} | Distancia: {label['distance']}")