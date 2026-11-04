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

# --- 2. RANGOS ---
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [0, 10]
inicio, fin = int(args[0]), int(args[1])

ruta_salida = "./dataset_despejado/"
if not os.path.exists(ruta_salida): os.makedirs(ruta_salida)

heli = bpy.data.objects.get('ALH Dhruv Helicopter')
camara = bpy.data.objects.get('Cámara')
sol = bpy.data.objects.get('Sol')
referencia = bpy.data.objects.get('Base')

bpy.context.scene.camera = camara
camara.data.clip_end = 5000

def get_bbox(obj, cam):
    scene = bpy.context.scene
    render = scene.render
    width = render.resolution_x
    height = render.resolution_y

    # Obtener el grafo de dependencias para posiciones reales
    depsgraph = bpy.context.evaluated_depsgraph_get()
    coords_2d = []

    # Recorrer el objeto 
    objects = [obj] + list(obj.children_recursive)

    for ob in objects:
        if ob.type != 'MESH':
            continue

        # Evaluar la malla con modificadores aplicados
        ob_eval = ob.evaluated_get(depsgraph)
        mesh = ob_eval.to_mesh()

        for v in mesh.vertices:
            # Convertir cada vértice a coordenadas de mundo y luego a cámara
            world_coord = ob.matrix_world @ v.co
            co_ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_coord)

            # Si el vértice está detrás de la cámara, lo ignoramos
            if co_ndc.z < 0:
                continue

            coords_2d.append((co_ndc.x, co_ndc.y))

        ob_eval.to_mesh_clear()

    if not coords_2d:
        return [0, 0, 0, 0]

    xs, ys = zip(*coords_2d)

    # Ajustar al borde de la imagen
    x_min = max(min(xs), 0.0)
    x_max = min(max(xs), 1.0)
    y_min = max(min(ys), 0.0)
    y_max = min(max(ys), 1.0)

    # Convertir a píxeles
    left = x_min * width
    right = x_max * width
    top = (1 - y_max) * height
    bottom = (1 - y_min) * height

    bbox_width = right - left
    bbox_height = bottom - top

    if bbox_width <= 0 or bbox_height <= 0:
        return [0, 0, 0, 0]

    return [
        round(left, 2),
        round(top, 2),
        round(bbox_width, 2),
        round(bbox_height, 2)
    ]

# --- 4. BUCLE DE GENERACIÓN ---
for i in range(inicio, fin):
    
    # 1. Lateral (X)
    x_heli = random.uniform(-0.35, 0.70)
    
    # 2. Altura (Z): Lo subimos un poco más para que en la distancia no lo tape la montaña
    z_heli = referencia.location.z + random.uniform(0.1, 0.6)

    # --- 3. LÓGICA DE DISTANCIA (PROBABILIDAD 50/50) ---
    ir_lejos = random.random() < 0.5 
    
    if ir_lejos:
        # RANGO GRANDE: Se va al fondo del cielo (Detrás de la montaña)
        offset = random.uniform(2.5, 6.0) 
        if camara.location.y < referencia.location.y:
            y_heli = referencia.location.y + offset
        else:
            y_heli = referencia.location.y - offset
        tipo = "LEJOS"
    else:
        # RANGO PEQUEÑO: Se queda cerca (Delante de la montaña)
        offset = random.uniform(0.1, 0.6)
        if camara.location.y < referencia.location.y:
            y_heli = referencia.location.y - offset
        else:
            y_heli = referencia.location.y + offset
        tipo = "CERCA"

    heli.location = (x_heli, y_heli, z_heli)

    # Rotaciones
    heli.rotation_euler = (random.uniform(-0.17, 0.17), random.uniform(-0.26, 0.26), random.uniform(0, 6.28))

    # --- LUMINOSIDAD VARIABLE ---
    luz = random.uniform(2.0, 5.0) # Rango suave para que no queme la imagen
    sol.data.energy = luz
    sol.rotation_euler[1] = random.uniform(0.35, 2.8)
    sol.rotation_euler[2] = random.uniform(0, 6.28)

    bpy.context.view_layer.update()

    # Render
    nombre = f"heli_{i:04d}"
    bpy.context.scene.render.filepath = os.path.join(ruta_salida, f"{nombre}.png")
    bpy.ops.render.render(write_still=True)

    # Etiqueta Completa
    bbox = get_bbox(heli, camara)
    label = {
        "file_name": f"{nombre}.png",
        "image_id": i,
        "category_id": 1,
        "bbox": bbox,
        "area": round(bbox[2] * bbox[3], 2),
        "weather": "despejado",
        "fog_density": 0,
        "luminosity": round(luz, 2),
        "distance": round((heli.location - camara.location).length, 2),
    }

    with open(os.path.join(ruta_salida, f"{nombre}.json"), 'w') as f:
        json.dump(label, f, indent=4)
    
    print(f"Imagen {nombre} | Modo: {tipo} | Distancia: {label['distance']}")