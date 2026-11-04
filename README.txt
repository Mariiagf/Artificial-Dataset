Para la generación y etiquetado de las imágenes en el CESGA se han utilizado los siguientes comandos:

srun -p viz --gres=gpu:1 -c 32 --mem=32G -t 04:00:00 --pty bash #para iniciar una sesión interactiva

#definimos el número de imágenes que se desean

INICIO=0
FIN= num_imagenes 

#para que se ejecute el archivo .py

./blender-5.0.0-linux-x64/blender -b "nombre_escenario" -noaudio -P "nombre_archivo_generacion_etiquetado.py" -- $INICIO $FIN 