import os
import json
import shutil

CARPETA_RAIZ = "./prueba"
CARPETA_DESTINO = "./helicoptero/datasets/COCO"
NOMBRE_CARPETA_IMGS = "val2017"
NOMBRE_CARPETA_ANNS = "annotations"
NOMBRE_MASTER_JSON = "instances_val2017.json"


def unificar_coco_separado():
    ruta_imgs_dest = os.path.join(CARPETA_DESTINO, NOMBRE_CARPETA_IMGS)
    ruta_anns_dest = os.path.join(CARPETA_DESTINO, NOMBRE_CARPETA_ANNS)
    os.makedirs(ruta_imgs_dest, exist_ok=True)
    os.makedirs(ruta_anns_dest, exist_ok=True)
    lista_images = []
    lista_annotations = []
    lista_categories = [{"id": 1, "name": "plane"}]
    global_img_id = 0
    global_ann_id = 0
    escenarios = [
        d for d in os.listdir(CARPETA_RAIZ)
        if os.path.isdir(os.path.join(CARPETA_RAIZ, d))]

    print(f"Escenarios encontrados: {len(escenarios)}")

    for esc in escenarios:

        ruta_esc = os.path.join(CARPETA_RAIZ, esc)

        jsons = [f for f in os.listdir(ruta_esc) if f.endswith(".json")]

        print(f"\nProcesando {esc} ({len(jsons)} JSON)")
        for js in jsons:
            ruta_json = os.path.join(ruta_esc, js)
            with open(ruta_json, "r", encoding="utf-8") as f:
                coco = json.load(f)
            img_id_map = {}

            for img in coco.get("images", []):

                old_id = img["id"]
                file_name = img["file_name"]

                ruta_origen = os.path.join(ruta_esc, file_name)

                nuevo_nombre = f"{esc}_heli_{global_img_id:05d}.png"
                ruta_destino = os.path.join(ruta_imgs_dest, nuevo_nombre)

                if not os.path.isfile(ruta_origen):
                    print(f" Falta: {ruta_origen}")
                    continue

                shutil.copy2(ruta_origen, ruta_destino)

                lista_images.append({
                    "id": global_img_id,
                    "file_name": nuevo_nombre,
                    "width": img.get("width", 1920),
                    "height": img.get("height", 1080),})

                img_id_map[old_id] = global_img_id
                global_img_id += 1

            for ann in coco.get("annotations", []):

                if ann["image_id"] not in img_id_map:
                    continue

                lista_annotations.append({
                    "id": global_ann_id,
                    "image_id": img_id_map[ann["image_id"]],
                    "category_id": 1,
                    "model": ann.get("model", "ALH Dhruv"),
                    "bbox": ann["bbox"],
                    "area": ann.get("area", ann["bbox"][2] * ann["bbox"][3]),
                    "distance": ann.get("distance", 0.0),
                    "weather": ann.get("weather", "despejado"),
                    "fog_density": ann.get("fog_density", 0.0),
                    "luminosity": ann.get("luminosity", 0.0)})

                global_ann_id += 1

    final_json = {
        "images": lista_images,
        "annotations": lista_annotations,
        "categories": lista_categories}

    ruta_final = os.path.join(ruta_anns_dest, NOMBRE_MASTER_JSON)

    with open(ruta_final, "w", encoding="utf-8") as f:
        json.dump(final_json, f, indent=4)

    print("\nDataset unificado correctamente")
    print(f"=Á Imágenes: {ruta_imgs_dest}")
    print(f"=Ä JSON: {ruta_final}")


if __name__ == "__main__":
    unificar_coco_separado()
