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

# Activar Motion Blur para que la lluvia se vea 
bpy.context.scene.render.use_motion_blur = True
bpy.context.scene.render.motion_blur_shutter = 0.7

# --- 2. RANGOS ---
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [0, 10]
inicio, fin = int(args[0]), int(args[1])

ruta_salida = "./dataset_lluvia_cerca/"
if not os.path.exists(ruta_salida): os.makedirs(ruta_salida)

heli = bpy.data.objects.get('ALH Dhruv Helicopter')
camara = bpy.data.objects.get('Cámara')
sol = bpy.data.objects.get('Sol')
referencia = bpy.data.objects.get('Base')
emisor = bpy.data.objects.get('EmisorLluvia') # Objeto de las partículas

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

    return [
        round(x_min * width, 2),
        round((1 - y_max) * height, 2),
        round((x_max - x_min) * width, 2),
        round((y_max - y_min) * height, 2)
    ]

# --- 4. BUCLE DE GENERACIÓN ---
for i in range(inicio, fin):
    
    # A. Momento de captura (Usamos 1 porque el inicio está en -100)
    bpy.context.scene.frame_set(1)

    # B. Configuración de Lluvia (70k a 95k gotas)
    if emisor and emisor.particle_systems:
        psys = emisor.particle_systems[0]
        psys.settings.count = random.randint(70000, 95000)
        psys.seed = random.randint(0, 9999)
        # Ocultar el plano emisor para que no salga el cuadrado gris arriba
        try:
            psys.settings.use_render_emitter = False
        except:
            emisor.show_instancer_for_render = False

    # C. Posicionamiento
    x_heli = random.uniform(-0.35, 0.70)
    z_heli = referencia.location.z + random.uniform(0.1, 0.6)
    
    # Forzamos solo el modo CERCA
    offset = random.uniform(0.1, 0.6)
    if camara.location.y < referencia.location.y:
        y_heli = referencia.location.y - offset
    else:
        y_heli = referencia.location.y + offset
    tipo = "CERCA"

    heli.location = (x_heli, y_heli, z_heli)
    heli.rotation_euler = (random.uniform(-0.17, 0.17), random.uniform(-0.26, 0.26), random.uniform(0, 6.28))

    # --- D. ILUMINACIÓN CLARA (Día nublado potente) ---
    # Luz solar moderada para dar volumen
    luz_sol = random.uniform(2.0, 3.5)
    sol.data.energy = luz_sol
    sol.rotation_euler[1] = random.uniform(0.35, 2.8)
    
    # Luz del Mundo (Ambiental) alta
    if bpy.context.scene.world.node_tree:
        bg = next((n for n in bpy.context.scene.world.node_tree.nodes if n.type == 'BACKGROUND'), None)
        if bg:
            bg.inputs[0].default_value = (0.7, 0.75, 0.8, 1.0) # Tono nublado claro
            bg.inputs[1].default_value = 1.3 # Intensidad para iluminar sombras

    bpy.context.view_layer.update()

    # E. Render
    nombre = f"heli_lluvia_{i:04d}"
    bpy.context.scene.render.filepath = os.path.join(ruta_salida, f"{nombre}.png")
    bpy.ops.render.render(write_still=True)

    # F. Etiqueta 
    bbox = get_bbox(heli, camara)
    label = {
        "file_name": f"{nombre}.png",
        "image_id": i,
        "category_id": 1,
        "bbox": bbox,
        "area": round(bbox[2] * bbox[3], 2),
        "weather": "lluvia",
        "fog_density":0,
        "luminosity": round(luz_sol, 2),
        "distance": round((heli.location - camara.location).length, 2),
    }

    with open(os.path.join(ruta_salida, f"{nombre}.json"), 'w') as f:
        json.dump(label, f, indent=4)
    
    print(f"Imagen {nombre} | Modo: {tipo} | Distancia: {label['distance']} | Área: {label['area']}px")