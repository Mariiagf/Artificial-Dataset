import bpy
import bpy_extras
import sys
import os
import random
import math
import json
from mathutils import Vector

def get_aircraft_bbox_2d(obj, cam, depsgraph, scene, width, height):
    coords_2d = []
    objects = [obj] + list(obj.children_recursive)
    for ob in objects:
        if ob.type != 'MESH':
            continue
        ob_eval = ob.evaluated_get(depsgraph)
        mesh = ob_eval.to_mesh()
        for v in mesh.vertices:
            world_coord = ob.matrix_world @ v.co
            co_ndc = bpy_extras.object_utils.world_to_camera_view(scene, cam, world_coord)

            if co_ndc.z < 0:
                continue
            coords_2d.append((co_ndc.x, co_ndc.y))
        ob_eval.to_mesh_clear()
        
    if not coords_2d:
        return [0, 0, 0, 0]

    xs, ys = zip(*coords_2d)
    x_min = max(min(xs), 0.0)
    x_max = min(max(xs), 1.0)
    y_min = max(min(ys), 0.0)
    y_max = min(max(ys), 1.0)

    left = x_min * width
    right = x_max * width
    top = (1 - y_max) * height
    bottom = (1 - y_min) * height

    bw = right - left
    bh = bottom - top

    if bw <= 0 or bh <= 0:
        return [0, 0, 0, 0]

    return [round(left,2), round(top,2), round(bw,2), round(bh,2)]


bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.cycles.device = 'GPU'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'

for d in prefs.devices:
    d.use = True

scene = bpy.context.scene
scene.cycles.samples = 16
scene.render.resolution_percentage = 50
scene.render.use_motion_blur = True

args = sys.argv[sys.argv.index("--") + 1:]
inicio = int(args[0])
fin = int(args[1])

ruta_salida = "./dataset_bw/"
os.makedirs(ruta_salida, exist_ok=True)

heli = bpy.data.objects.get('Cessna 172 - Aircraft')
camara = bpy.data.objects.get('Camera')
landscape = bpy.data.objects.get("Landscape")
fog_obj = bpy.data.objects.get('Cube')

mat = fog_obj.active_material
nodes = mat.node_tree.nodes

volume_node = next(
    (n for n in nodes if n.type == 'PRINCIPLED_VOLUME'),
    None)

landscape_bbox = [
    landscape.matrix_world @ Vector(corner)
    for corner in landscape.bound_box
]

xs = [v.x for v in landscape_bbox]
ys = [v.y for v in landscape_bbox]

margin = 50
X_MIN, X_MAX = min(xs) + margin, max(xs) - margin
Y_MIN, Y_MAX = min(ys) + margin, max(ys) - margin


scene.camera = camara
camara.data.clip_end = 5000

depsgraph = bpy.context.evaluated_depsgraph_get()
scene_ref = bpy.context.scene

width = scene.render.resolution_x
height = scene.render.resolution_y


bpy.ops.ptcache.free_bake_all()
bpy.context.scene.frame_set(1)

for f in range(1, 70):
    bpy.context.scene.frame_set(f)


for i in range(inicio, fin):

    frame = random.randint(200, 400)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()

    # NIEBLA
    fog_density = random.uniform(0.0, 0.0008)
    if volume_node:
        volume_node.inputs["Density"].default_value = fog_density

    # POSICIÓN AVIÓN
    heli.location = (
        random.uniform(X_MIN, X_MAX),
        random.uniform(Y_MIN, Y_MAX),
        random.uniform(40, 80))

    heli.rotation_euler = (
        random.uniform(math.radians(-10), math.radians(10)),
        random.uniform(math.radians(-15), math.radians(15)),
        random.uniform(0, 2 * math.pi))

    #CÁMARA
    distancia_cam = random.uniform(120, 400)
    angulo_h = random.uniform(0, 2 * math.pi)
    angulo_v = random.uniform(math.radians(-10), math.radians(10))

    offset = Vector((
        distancia_cam * math.cos(angulo_h) * math.cos(angulo_v),
        distancia_cam * math.sin(angulo_h) * math.cos(angulo_v),
        distancia_cam * math.sin(angulo_v)))

    camara.location = heli.location + offset

    #DESPLAZAMIENTO
    target_offset = Vector((
        random.uniform(-40, 40),   # izquierda/derecha
        random.uniform(-20, 20),   # adelante/atrás
        random.uniform(-10, 10)))      # vertical

    target = heli.location + target_offset

    direccion = target - camara.location
    camara.rotation_euler = direccion.to_track_quat('-Z', 'Y').to_euler()

    nombre = f"lheli_{i:04d}"
    scene.render.filepath = os.path.join(ruta_salida, f"{nombre}.png")

    bpy.ops.render.render(write_still=True)

    # BBOX
    aircraft_bbox_2d = get_aircraft_bbox_2d(
        heli, camara, depsgraph, scene_ref, width, height
    )

    # filtro
    '''if aircraft_bbox_2d[2] < 20 or aircraft_bbox_2d[3] < 20:
        continue'''

    distancia = (heli.location - camara.location).length
    label = {
        "file_name": f"{nombre}.png",
        "image_id": i,
        "category_id": 1,
        "model": "Cessna 172",
        "bbox": aircraft_bbox_2d,
        "area": round(aircraft_bbox_2d[2] * aircraft_bbox_2d[3], 2),
        "weather": "niebla",
        "fog_density": fog_density,
        "luminosity": 2,
        "distance": round(distancia, 2)}

    with open(os.path.join(ruta_salida, f"{nombre}.json"), 'w') as f:
        json.dump(label, f, indent=4)
