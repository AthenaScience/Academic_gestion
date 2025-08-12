import os

# Crear un CSV de ejemplo en memoria
csv_ejemplo = """nombres,qr,ruta,Codigo
Jairo Eloy Velaña Navarrete,img/Qr/cons6523.png,img/Img/0941300071.png,6523
Sonia Alexandra Ochoa Icaza,img/Qr/cons6524.png,img/Img/0929632438.png,6524
Lady Lizbeth Pazos Alvarado,img/Qr/cons6525.png,img/Img/0922824917.png,6525
"""

csv_file_path = "importacion/data.csv"

with open(csv_file_path, "w", encoding="utf-8") as f:
    f.write(csv_ejemplo)

# Creamos rutas falsas para imágenes (no se subirán imágenes reales aquí, solo ilustración)
qr_files = ["cons6523.png", "cons6524.png", "cons6525.png"]
img_files = ["0941300071.png", "0929632438.png", "0922824917.png"]

qr_folder = "importacion/img/Qr"
img_folder = "importacion/img/Img"

os.makedirs(qr_folder, exist_ok=True)
os.makedirs(img_folder, exist_ok=True)

# Crear archivos vacíos como placeholders
for qr in qr_files:
    with open(os.path.join(qr_folder, qr), "wb") as f:
        f.write(b"FAKE QR IMAGE")

for img in img_files:
    with open(os.path.join(img_folder, img), "wb") as f:
        f.write(b"FAKE PHOTO")

# Ruta base para importar (esto es lo que usarás en el campo base_path)
carpeta_base = "importacion"

carpeta_base
