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

ruta_salida = "./dataset_niebla_bordes/" 
if not os.path.exists(ruta_salida): os.makedirs(ruta_salida)

heli = bpy.data.objects.get('ALH Dhruv Helicopter')
camara = bpy.data.objects.get('Cámara')
sol = bpy.data.objects.get('Sol')
referencia = bpy.data.objects.get('Base')
cubo_niebla = bpy.data.objects.get('CuboNiebla') 

# --- 3. LIMPIEZA DE CÁMARA ---
for c in camara.constraints:
    camara.constraints.remove(c)

camara.rotation_mode = 'XYZ'
camara.rotation_euler.y = 0 # Nivelar horizonte

bpy.context.scene.camera = camara
camara.data.clip_end = 5000

# --- FUNCIONES ---

def get_bbox(obj, cam):
    scene = bpy.context.scene
    render = scene.render
    width, height = render.resolution_x, render.resolution_y
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
            if co_ndc.z > 0: coords_2d.append((co_ndc.x, co_ndc.y))
        ob_eval.to_mesh_clear()

    if not coords_2d: return [0, 0, 0, 0]
    xs, ys = zip(*coords_2d)
    x_min, x_max = max(min(xs), 0.0), min(max(xs), 1.0)
    y_min, y_max = max(min(ys), 0.0), min(max(ys), 1.0)
    
    return [round(x_min * width, 2), round((1 - y_max) * height, 2), 
            round((x_max - x_min) * width, 2), round((y_max - y_min) * height, 2)]

def colocar_heli_en_frustum_bordes(cam, obj, ref):
    scene = bpy.context.scene
    # 1. Distancia Cámara -> Base (Montaña)
    distancia_a_base = (cam.location - ref.location).length
    
    # 2. Garantizar que esté delante (80% de la distancia a la montaña)
    distancia_final = distancia_a_base * random.uniform(2.5, 3.5)
    
    # 3. Lógica de bordes (Excluyendo el centro)
    x = random.choice([random.uniform(0.1, 0.3), random.uniform(0.7, 0.9)])
    y = random.choice([random.uniform(0.2, 0.4), random.uniform(0.6, 0.85)])
    
    # 4. Cálculo de Frustum
    frame = cam.data.view_frame(scene=scene)
    punto_frustum_local = (
        frame[0] * (1 - x) * (1 - y) +
        frame[1] * x * (1 - y) +
        frame[2] * x * y +
        frame[3] * (1 - x) * y
    )
    
    direccion = punto_frustum_local.normalized()
    obj.location = cam.matrix_world @ (direccion * distancia_final)

# --- 4. BUCLE DE GENERACIÓN ---
for i in range(inicio, fin):
    
    # A. Configuración de Niebla
    densidad_niebla = random.uniform(0.005, 0.05) 
    if cubo_niebla and cubo_niebla.active_material:
        nodes = cubo_niebla.active_material.node_tree.nodes
        node_vol = next((n for n in nodes if n.type == 'VOLUME_SCATTER'), None)
        if node_vol:
            node_vol.inputs[1].default_value = densidad_niebla 

    # B. Posicionamiento 
    colocar_heli_en_frustum_bordes(camara, heli, referencia)

    # C. Rotaciones
    heli.rotation_euler[0] = random.uniform(math.radians(-5), math.radians(5))
    heli.rotation_euler[1] = random.uniform(math.radians(-5), math.radians(5))
    heli.rotation_euler[2] = random.uniform(0, 2 * math.pi)

    # D. Luminosidad (Alta para niebla)
    luz = random.uniform(8.0, 15.0) 
    sol.data.energy = luz
    sol.rotation_euler[1] = random.uniform(0.35, 2.8)
    sol.rotation_euler[2] = random.uniform(0, 6.28)

    bpy.context.view_layer.update()

    # Render
    nombre = f"heli_niebla_{i:04d}"
    bpy.context.scene.render.filepath = os.path.join(ruta_salida, f"{nombre}.png")
    
    print(f"[{i+1}/{fin}] Renderizando {nombre} con niebla y encuadre en borde...")
    bpy.ops.render.render(write_still=True)

    # Etiqueta
    bbox = get_bbox(heli, camara)
    area = round(bbox[2] * bbox[3], 2)
    distancia_real = (heli.location - camara.location).length

    label = {
        "file_name": f"{nombre}.png",
        "image_id": i,
        "category_id": 1,
        "bbox": bbox,
        "area": area,
        "weather": "niebla",
        "fog_density": round(densidad_niebla, 4),
        "luminosity": round(luz, 2),
        "distance": round(distancia_real, 2)
    }

    if area > 0:
        with open(os.path.join(ruta_salida, f"{nombre}.json"), 'w') as f:
            json.dump(label, f, indent=4)

print(f"✅ Proceso completado. Imágenes de niebla con encuadre descentrado generadas.")