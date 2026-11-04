import bpy
import bpy_extras
import sys
import os
import random
import math
import json
from mathutils import Vector


# 1. CONFIGURACIÓN Y OBJETOS
NOMBRE_HELI = 'ALH Dhruv Helicopter'
NOMBRE_CAMARA = 'Camera'
NOMBRE_CUBO_NIEBLA = 'Cube.009'

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE' 

# --- VERIFICACIÓN OBJETOS ---
heli = bpy.data.objects.get(NOMBRE_HELI)
camara = bpy.data.objects.get(NOMBRE_CAMARA)
fog_obj = bpy.data.objects.get(NOMBRE_CUBO_NIEBLA)

if not heli or not camara:
    print(f"ERROR: No se encontró {NOMBRE_HELI} o {NOMBRE_CAMARA}")
    sys.exit(1)

# --- CONFIGURACIÓN MATERIAL NIEBLA ---
volume_node = None
if fog_obj and fog_obj.active_material and fog_obj.active_material.use_nodes:
    nodes = fog_obj.active_material.node_tree.nodes
    # Buscamos tanto Volume Scatter como Principled Volume por si acaso
    for n in nodes:
        if n.type in ['VOLUME_SCATTER', 'PRINCIPLED_VOLUME']:
            volume_node = n
            break

if not volume_node:
    print(f"AVISO: No se encontró nodo de volumen en {NOMBRE_CUBO_NIEBLA}. Se renderizará sin niebla variable.")

# --- ARGUMENTOS ---
try:
    args = sys.argv[sys.argv.index("--") + 1:]
    inicio = int(args[0])
    fin = int(args[1])
except:
    inicio, fin = 0, 20

ruta_salida = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dataset_niebla_movido")
os.makedirs(ruta_salida, exist_ok=True)

width = scene.render.resolution_x
height = scene.render.resolution_y
aspect = width / height

# FUNCIONES DE PRECISIÓN
def get_bbox_stats(obj, cam, scene, width, height):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    coords_2d = []
    
    for ob in [obj] + list(obj.children_recursive):
        if ob.type != 'MESH': continue
        mesh = ob.evaluated_get(depsgraph).to_mesh()
        for v in mesh.vertices:
            world_coord = ob.matrix_world @ v.co
            co_ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_coord)
            coords_2d.append(co_ndc)
        ob.evaluated_get(depsgraph).to_mesh_clear()

    if not coords_2d: return None, False

    xs = [c.x for c in coords_2d]
    ys = [c.y for c in coords_2d]
    zs = [c.z for c in coords_2d]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    z_min = min(zs)

    # Verificación estricta: dentro de cámara y en la mitad superior
    is_inside = (x_min > 0.02 and x_max < 0.98 and 
                 y_min > 0.50 and y_max < 0.98 and 
                 z_min > 0)

    px_bbox = [
        round(x_min * width, 2),
        round((1 - y_max) * height, 2),
        round((x_max - x_min) * width, 2),
        round((y_max - y_min) * height, 2)
    ]
    
    return px_bbox, is_inside

# LOOP CON REINTENTOS
for i in range(inicio, fin):
    
    intentos = 0
    fuera_de_rango = True
    final_bbox = []
    final_dist = 0

    # --- CAMBIAR NIEBLA ---
    fog_density = random.uniform(0.01, 0.055)
    if volume_node:
        volume_node.inputs["Density"].default_value = fog_density

    while fuera_de_rango and intentos < 50:
        intentos += 1
        
        distancia = random.uniform(300, 700)
        fov = camara.data.angle
        v_h = 2 * math.tan(fov / 2) * distancia
        v_w = v_h * aspect

        local_x = random.uniform(-v_w * 0.4, v_w * 0.4)
        local_y = random.uniform(v_h * 0.05, v_h * 0.4)
        
        heli.location = camara.matrix_world @ Vector((local_x, local_y, -distancia))
        heli.rotation_euler = (random.uniform(-0.2, 0.2), random.uniform(-0.3, 0.3), random.random() * 6.28)
        
        bpy.context.view_layer.update()
        bbox, inside = get_bbox_stats(heli, camara, scene, width, height)
        
        if inside:
            fuera_de_rango = False
            final_bbox = bbox
            final_dist = distancia

    if not fuera_de_rango:
        nombre_base = f"heli_{i:04d}"
        scene.render.filepath = os.path.join(ruta_salida, f"{nombre_base}.png")
        bpy.ops.render.render(write_still=True)

        label = {
            "file_name": f"{nombre_base}.png",
            "image_id": i,
            "category_id": 1,
            "model": "ALH Dhruv",
            "bbox": final_bbox,
            "area": round(final_bbox[2] * final_bbox[3], 2),
            "weather": "niebla" if fog_density > 0.01 else "despejado",
            "fog_density": round(fog_density, 4),
             "luminosity": 1.0,
            "distance": round(final_dist, 2)
        }
        
        with open(os.path.join(ruta_salida, f"{nombre_base}.json"), 'w') as f:
            json.dump(label, f, indent=4)
        print(f"{nombre_base} (Intento {intentos}) - Niebla: {fog_density:.3f}")
    else:
        print(f"Frame {i} fallido tras 50 intentos.")

print(f"Proceso finalizado. Archivos en: {ruta_salida}")