import os
from fpdf import FPDF, HTMLMixin
from PIL import Image
from io import BytesIO
from django.conf import settings

class MyPDF_V(FPDF, HTMLMixin):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.WIDTH = 210
        self.HEIGHT = 297
        self.set_auto_page_break(auto=True, margin=15)
        self.current_y = 0      
    def add_page(self, plantilla_path=None):
        super().add_page()
        if plantilla_path is None:
            plantilla_path = os.path.join(settings.BASE_DIR, 'media', 'plantillas', 'default.png')
        self.image(plantilla_path, x=0, y=0, w=self.WIDTH, h=self.HEIGHT)
        self.current_y = 0     
    def set_custom_margins(self, left=10, top=10, right=10):
        self.set_left_margin(left)
        self.set_top_margin(top)
        self.set_right_margin(right)      
    def set_position_y(self, y):
        self.current_y = y

# === Función principal que genera el certificado ===

def generar_certificado(estudiante, certificado, ruta_foto, ruta_qr):# codigo_certificado):
    pdf = MyPDF_V()  
    plantilla_path = certificado.evento.plantilla.path if certificado.evento.plantilla else None
    pdf.add_page(plantilla_path=plantilla_path)
    # Fuentes personalizadas
    pdf.add_font('Lovelo', '', os.path.join(settings.BASE_DIR, 'media', 'fonts', 'FSLucasPro-XtraBd','FSLucasPro-XtraBd.ttf'), uni=True)
    pdf.add_font('OpenSansLight', '', os.path.join(settings.BASE_DIR, 'media', 'fonts', 'open-sans','OpenSans-Light.ttf'), uni=True)
    pdf.add_font('GreatVibes', '', os.path.join(settings.BASE_DIR, 'media', 'fonts','nuva', 'DancingScript-VariableFont_wght.ttf'), uni=True)
    pdf.add_font('Newsreader', '', os.path.join(settings.BASE_DIR, 'media', 'fonts','Newsreader', 'Newsreader.ttf'), uni=True)
    pdf.add_font('NewsreaderB', '', os.path.join(settings.BASE_DIR, 'media', 'fonts', 'Newsreader','Newsreader_60pt-Bold.ttf'), uni=True)
    pdf.add_font('New', '', os.path.join(settings.BASE_DIR, 'media', 'fonts', 'Newsreader','Newsreader-VariableFont_opsz,wght.ttf'), uni=True)

    def add_text_mc(font, size, text, H, x=None, y=None, border=None, p=None):
        pdf.set_font(font, size=size)
        if x is None:
            x = (pdf.WIDTH - pdf.get_string_width(text)) / 2
        if y is None:
            y = pdf.current_y
        pdf.set_xy(x, y)
        if border is None:
            border = 0
        if p is None:
            p = 'C'
        pdf.cell(w=pdf.get_string_width(text), h=H, txt=text, ln=True, align=p, border=border)
        pdf.current_y = y + H
    def multiblocktext(font, size, W, H, text, p=None, x=None, y=None, border=None):
        pdf.set_font(font, '', size)
        if p is None:
            p = 'C'
        if x is None:
            x = (pdf.WIDTH - W) / 2
        if y is None:
            y = pdf.current_y
        pdf.set_xy(x, y)
        if border is None:
            border = 0
        pdf.multi_cell(w=W, h=H, txt=text, ln=True, align=p, border=border)
        pdf.current_y += pdf.b_margin

    border = 0
    add_text_mc(font='Lovelo', size=22, H=8, y=44, border=border, text="UNIVERSIDAD TÉCNICA ESTATAL DE QUEVEDO")
    multiblocktext(font='Lovelo', size=14, W=140, H=5, border=border, p='C',
                   text='CENTRO DE CAPACITACIÓN, DESARROLLO Y TRANSFERENCIA\nDE CIENCIA, EDUCACIÓN Y TECNOLOGÍA\n"SCIEDTEC"')
    add_text_mc(font='OpenSansLight', size=13, H=8, border=border, text='Confieren el presente certificado a:')
    multiblocktext(font='GreatVibes', x=19, W=155, size=27, p='C', H=30, border=border, text=f'{estudiante.nombres.title()} {estudiante.apellidos.title()}')

    # Insertar imágenes
    img_foto = Image.open(ruta_foto)
    pdf.image(img_foto.filename, x=170, y=72, w=31.2, h=36)

    img_qr = Image.open(ruta_qr)
    pdf.image(img_qr.filename, x=73, y=273, w=23, h=23)

    add_text_mc(font='Newsreader', size=15, y=105, H=7, border=border, text='Por haber APROBADO el:')
    add_text_mc(font='NewsreaderB', size=20, H=15, border=border, text='DIPLOMADO EN DOCENCIA SUPERIOR')
    multiblocktext(font='New', size=14, W=190, H=5, border=border, p='C',
                   text='Con el Aval de la Universidad Técnica Estatal de Quevedo y dictado por el Centro De Capacitación Desarrollo y Transferencia de Ciencia, Educación y Tecnología.\n"SCIEDTEC"')

    add_text_mc(font='New', size=10, H=4, border=border, text='')
    fecha_inicio = certificado.evento.fecha_inicio.strftime('%d/%m/%Y')  # aquí podrías mejorar luego con `fecha_inicio` real
    fecha_fin = certificado.evento.fecha_fin.strftime('%d/%m/%Y')      # por ahora usamos la misma
    horas_academicas = certificado.evento.horas_academicas
    multiblocktext(font='New', size=12, W=190, H=4, border=border, p='C',
                   text=f'Duración: {horas_academicas} Horas Académicas\nRealizado del {fecha_inicio} al {fecha_fin}.')
    fecha ='21 de marzo de 2025'
    multiblocktext(font='New', size=10, W=190, H=4, border=border, p='R',
                   text=f'Quevedo,{fecha}\n{certificado.evento.aval}-SCI-{certificado.evento.codigo_evento}-{certificado.codigo_certificado}')
   
   
    # Firmas
    add_text_mc(font='Newsreader', size=9, y=210, H=5, border=border, p='C', text='Dr. Eduardo Díaz Ocampo, Ph.D.')
    multiblocktext(font='NewsreaderB', size=7, W=30, H=3, y=214, border=border, p='C', text='RECTOR\nUTEQ')
    add_text_mc(font='Newsreader', size=9, x=146, y=210, H=5, border=border, p='R', text='Mg. Esp. Andrea Escobar Quezada.')
    multiblocktext(font='NewsreaderB', size=7, W=30, H=3, x=154, y=214, border=border, p='C', text='GERENTE GENERAL\nSCIEDTEC')
    add_text_mc(font='Newsreader', size=9, x=24, y=210, H=5, border=border, p='L', text='Msc. Cesil Moreno Cedeño, Md.')
    multiblocktext(font='NewsreaderB', size=7, W=30, H=3, x=33, y=214, border=border, p='C', text='GERENTE GENERAL\nPRODEUTEQ')
    add_text_mc(font='Newsreader', size=9, y=247, H=5, border=border, p='C', text='Ing. Carmen Cerezo Bustamante.')
    multiblocktext(font='NewsreaderB', size=7, W=30, H=3, y=251, border=border, p='C', text='DIRECTORA\nCECAPRO')

    # Ruta de salida del PDF
    nombre_carpeta = certificado.evento.codigo_evento
    output_folder = os.path.join(settings.MEDIA_ROOT, 'certificados', nombre_carpeta)
    os.makedirs(output_folder, exist_ok=True)

    nombre_archivo = f"{certificado.evento.aval}-SCI-{certificado.evento.codigo_evento}-{certificado.codigo_certificado}.pdf"
    output_path = os.path.join(output_folder, nombre_archivo)
    pdf.output(output_path,'F')
    return output_path


# === Versión inline: genera PDF en memoria (bytes) sin guardar en disco ===
def generar_certificado_bytes(
    estudiante,
    certificado,
    plantilla_path=None,
    foto_bytes: bytes | None = None,
    qr_bytes: bytes | None = None,
):
    pdf = MyPDF_V()
    if plantilla_path is None:
        plantilla_path = certificado.evento.plantilla.path if getattr(certificado.evento, 'plantilla', None) else None
    pdf.add_page(plantilla_path=plantilla_path)

    # Fuentes personalizadas
    try:
        pdf.add_font('Lovelo', '', os.path.join(settings.BASE_DIR, 'media', 'fonts', 'FSLucasPro-XtraBd','FSLucasPro-XtraBd.ttf'), uni=True)
        pdf.add_font('OpenSansLight', '', os.path.join(settings.BASE_DIR, 'media', 'fonts', 'open-sans','OpenSans-Light.ttf'), uni=True)
        pdf.add_font('GreatVibes', '', os.path.join(settings.BASE_DIR, 'media', 'fonts','nuva', 'DancingScript-VariableFont_wght.ttf'), uni=True)
        pdf.add_font('Newsreader', '', os.path.join(settings.BASE_DIR, 'media', 'fonts','Newsreader', 'Newsreader.ttf'), uni=True)
        pdf.add_font('NewsreaderB', '', os.path.join(settings.BASE_DIR, 'media', 'fonts', 'Newsreader','Newsreader_60pt-Bold.ttf'), uni=True)
        pdf.add_font('New', '', os.path.join(settings.BASE_DIR, 'media', 'fonts', 'Newsreader','Newsreader-VariableFont_opsz,wght.ttf'), uni=True)
    except Exception:
        # En caso de falta de fuentes, usar las por defecto de fpdf
        pass

    def add_text_mc(font, size, text, H, x=None, y=None, border=None, p=None):
        try:
            pdf.set_font(font, size=size)
        except Exception:
            pdf.set_font('Helvetica', size=size)
        if x is None:
            x = (pdf.WIDTH - pdf.get_string_width(text)) / 2
        if y is None:
            y = pdf.current_y
        pdf.set_xy(x, y)
        if border is None:
            border = 0
        if p is None:
            p = 'C'
        pdf.cell(w=pdf.get_string_width(text), h=H, txt=text, ln=True, align=p, border=border)
        pdf.current_y = y + H

    def multiblocktext(font, size, W, H, text, p=None, x=None, y=None, border=None):
        try:
            pdf.set_font(font, '', size)
        except Exception:
            pdf.set_font('Helvetica', '', size)
        if p is None:
            p = 'C'
        if x is None:
            x = (pdf.WIDTH - W) / 2
        if y is None:
            y = pdf.current_y
        pdf.set_xy(x, y)
        if border is None:
            border = 0
        pdf.multi_cell(w=W, h=H, txt=text, ln=True, align=p, border=border)
        pdf.current_y += pdf.b_margin

    border = 0
    add_text_mc(font='Lovelo', size=22, H=8, y=44, border=border, text="UNIVERSIDAD TÉCNICA ESTATAL DE QUEVEDO")
    multiblocktext(font='Lovelo', size=14, W=140, H=5, border=border, p='C',
                   text='CENTRO DE CAPACITACIÓN, DESARROLLO Y TRANSFERENCIA\nDE CIENCIA, EDUCACIÓN Y TECNOLOGÍA\n"SCIEDTEC"')
    add_text_mc(font='OpenSansLight', size=13, H=8, border=border, text='Confieren el presente certificado a:')
    multiblocktext(font='GreatVibes', x=19, W=155, size=27, p='C', H=30, border=border, text=f'{estudiante.nombres.title()} {estudiante.apellidos.title()}')

    # Insertar imágenes si están disponibles
    # Inserción de imágenes usando archivos temporales para máxima compatibilidad
    import tempfile
    if foto_bytes:
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmpf:
                tmpf.write(foto_bytes)
                tmpf.flush()
                pdf.image(tmpf.name, x=170, y=72, w=31.2, h=36)
        except Exception:
            pass
    if qr_bytes:
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmpq:
                tmpq.write(qr_bytes)
                tmpq.flush()
                pdf.image(tmpq.name, x=73, y=273, w=23, h=23)
        except Exception:
            pass

    add_text_mc(font='Newsreader', size=15, y=105, H=7, border=border, text='Por haber APROBADO el:')
    add_text_mc(font='NewsreaderB', size=20, H=15, border=border, text='DIPLOMADO EN DOCENCIA SUPERIOR')
    multiblocktext(font='New', size=14, W=190, H=5, border=border, p='C',
                   text='Con el Aval de la Universidad Técnica Estatal de Quevedo y dictado por el Centro De Capacitación Desarrollo y Transferencia de Ciencia, Educación y Tecnología.\n"SCIEDTEC"')

    add_text_mc(font='New', size=10, H=4, border=border, text='')
    fecha_inicio = certificado.evento.fecha_inicio.strftime('%d/%m/%Y')
    fecha_fin = certificado.evento.fecha_fin.strftime('%d/%m/%Y')
    horas_academicas = certificado.evento.horas_academicas
    multiblocktext(font='New', size=12, W=190, H=4, border=border, p='C',
                   text=f'Duración: {horas_academicas} Horas Académicas\nRealizado del {fecha_inicio} al {fecha_fin}.')
    fecha_text = fecha_fin
    multiblocktext(font='New', size=10, W=190, H=4, border=border, p='R',
                   text=f'Quevedo,{fecha_text}\n{certificado.evento.aval}-SCI-{certificado.evento.codigo_evento}-{certificado.codigo_certificado}')

    # Firmas (texto)
    add_text_mc(font='Newsreader', size=9, y=210, H=5, border=border, p='C', text='Dr. Eduardo Díaz Ocampo, Ph.D.')
    multiblocktext(font='NewsreaderB', size=7, W=30, H=3, y=214, border=border, p='C', text='RECTOR\nUTEQ')
    add_text_mc(font='Newsreader', size=9, x=146, y=210, H=5, border=border, p='R', text='Mg. Esp. Andrea Escobar Quezada.')
    multiblocktext(font='NewsreaderB', size=7, W=30, H=3, x=154, y=214, border=border, p='C', text='GERENTE GENERAL\nSCIEDTEC')
    add_text_mc(font='Newsreader', size=9, x=24, y=210, H=5, border=border, p='L', text='Msc. Cesil Moreno Cedeño, Md.')
    multiblocktext(font='NewsreaderB', size=7, W=30, H=3, x=33, y=214, border=border, p='C', text='GERENTE GENERAL\nPRODEUTEQ')
    add_text_mc(font='Newsreader', size=9, y=247, H=5, border=border, p='C', text='Ing. Carmen Cerezo Bustamante.')
    multiblocktext(font='NewsreaderB', size=7, W=30, H=3, y=251, border=border, p='C', text='DIRECTORA\nCECAPRO')

    # Salida en memoria (fpdf2 retorna bytes/bytearray)
    data = pdf.output(dest='S')
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    # Compatibilidad si alguna versión retorna str
    return str(data).encode('latin-1')


def generar_constancia_bytes(estudiante, certificado, evento, qr_bytes: bytes | None = None) -> bytes:
    """Genera un PDF simple de constancia de verificación (sin firmas).
    Contiene datos mínimos y un QR de verificación.
    """
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Encabezado
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 10, 'Constancia de Verificacion de Certificado', ln=1, align='C')
    pdf.ln(5)

    pdf.set_font('Helvetica', '', 12)
    pdf.multi_cell(0, 7, txt=(
        'La presente constancia certifica que el siguiente documento ha sido emitido por el sistema oficial y '
        'es valido para verificacion en linea. Este documento NO sustituye al certificado fisico con firmas.'
    ))
    pdf.ln(5)

    # Datos
    def row(label, value):
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(50, 7, f'{label}:')
        pdf.set_font('Helvetica', '', 11)
        pdf.cell(0, 7, str(value), ln=1)

    row('Codigo', certificado.codigo_certificado)
    row('Estudiante', f'{estudiante.nombres} {estudiante.apellidos}')
    row('Cedula', estudiante.cedula)
    row('Evento', evento.nombre)
    row('Tipo', evento.tipo)
    row('Horas academicas', evento.horas_academicas)
    row('Fechas', f"{evento.fecha_inicio} a {evento.fecha_fin}")
    row('Emitido', str(certificado.fecha_emision))

    pdf.ln(8)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.multi_cell(0, 6, txt=(
        'Nota: Para validar escanee el codigo QR o ingrese al enlace proporcionado. '
        'La validez de la constancia esta sujeta a la no revocacion del certificado.'
    ))

    # QR grande
    if qr_bytes:
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmpq:
                tmpq.write(qr_bytes)
                tmpq.flush()
                pdf.image(tmpq.name, x=85, y=210, w=40, h=40)
        except Exception:
            pass

    data = pdf.output(dest='S')
    return bytes(data) if isinstance(data, (bytes, bytearray)) else str(data).encode('latin-1')
