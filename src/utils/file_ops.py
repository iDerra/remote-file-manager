import subprocess
import json
import os
import shutil
import zipfile
from utils.utilsHandler import is_safe_path
from werkzeug.utils import secure_filename

def get_video_subtitles(abs_path):
    """
    Usa ffprobe para leer las pistas de subtítulos incrustadas en un archivo de vídeo.
    """
    cmd = [
        'ffprobe', '-v', 'error', 
        '-select_streams', 's', 
        '-show_entries', 'stream=index:stream_tags=language,title', 
        '-of', 'json', abs_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    
    subs = []
    for stream in data.get('streams', []):
        tags = stream.get('tags', {})
        lang = tags.get('language', 'und')
        title = tags.get('title', f'Pista {stream.get("index")}')
        subs.append({
            'index': stream.get('index'),
            'language': lang,
            'label': f"{title} ({lang})"
        })
    return subs

def generate_vtt_stream(abs_path, stream_index):
    """
    Usa ffmpeg para extraer y convertir una pista de subtítulos a formato WebVTT en tiempo real.
    """
    cmd = [
        'ffmpeg', '-v', 'error', '-i', abs_path,
        '-map', f'0:{stream_index}',
        '-f', 'webvtt', '-'
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for chunk in iter(lambda: process.stdout.read(4096), b''):
        yield chunk

def process_multiple_deletions(file_system_root, items_unquoted):
    """
    Procesa una lista de rutas, validando su seguridad y eliminando los archivos o carpetas.
    Devuelve banderas de estado y los detalles de cada operación.
    """
    results_details = []
    overall_success_flag = True
    any_successful_deletions = False

    for item_segment_unquoted in items_unquoted:
        item_name_display = os.path.basename(item_segment_unquoted) if item_segment_unquoted else item_segment_unquoted
        current_item_detail = {
            "item_name": item_name_display,
            "item_path": item_segment_unquoted,
            "success": False,
            "message": ""
        }

        if item_segment_unquoted == '__root__' or not item_segment_unquoted:
            current_item_detail["message"] = "The root directory cannot be deleted."
            results_details.append(current_item_detail)
            overall_success_flag = False
            continue

        if not is_safe_path(file_system_root, item_segment_unquoted):
            current_item_detail["message"] = "Invalid or not allowed route."
            results_details.append(current_item_detail)
            overall_success_flag = False
            continue

        item_path_abs = os.path.join(file_system_root, item_segment_unquoted)
        if not os.path.exists(item_path_abs):
            current_item_detail["message"] = "Item not found (could have been deleted previously)."
            results_details.append(current_item_detail)
            continue

        try:
            if os.path.isfile(item_path_abs):
                os.remove(item_path_abs)
                current_item_detail["message"] = "File successfully deleted."
                current_item_detail["success"] = True
                any_successful_deletions = True
            elif os.path.isdir(item_path_abs):
                shutil.rmtree(item_path_abs)
                current_item_detail["message"] = "Folder successfully deleted."
                current_item_detail["success"] = True
                any_successful_deletions = True
            else:
                current_item_detail["message"] = "The item is not a valid file or folder."
                overall_success_flag = False
            results_details.append(current_item_detail)
        except Exception as e:
            current_item_detail["message"] = f"Error when deleting: {str(e)}"
            overall_success_flag = False
            results_details.append(current_item_detail)

    return overall_success_flag, any_successful_deletions, results_details


def process_multiple_moves(file_system_root, items_unquoted, normalized_destination):
    """
    Procesa el movimiento masivo de archivos o carpetas, validando colisiones
    y previniendo bucles de directorios.
    """
    results_details = []
    overall_success_flag = True
    any_successful_moves = False
    
    destination_directory_abs = os.path.join(file_system_root, normalized_destination)

    for item_segment_unquoted in items_unquoted:
        item_name_display = os.path.basename(item_segment_unquoted) if item_segment_unquoted else "Invalid Item Path"
        current_item_detail = {
            "item_name": item_name_display,
            "item_path": item_segment_unquoted,
            "success": False,
            "message": ""
        }

        if not item_segment_unquoted or item_segment_unquoted == '__root__':
            current_item_detail["message"] = "The root directory or invalid item cannot be moved."
            results_details.append(current_item_detail)
            overall_success_flag = False
            continue

        if not is_safe_path(file_system_root, item_segment_unquoted):
            current_item_detail["message"] = "Invalid or not allowed source path."
            results_details.append(current_item_detail)
            overall_success_flag = False
            continue

        source_path_abs = os.path.join(file_system_root, item_segment_unquoted)
        final_destination_path_abs = os.path.join(destination_directory_abs, os.path.basename(source_path_abs))

        if not os.path.exists(source_path_abs):
            current_item_detail["message"] = "Source item does not exist (it may have been moved or deleted)."
            results_details.append(current_item_detail)
            continue
            
        if source_path_abs == final_destination_path_abs:
            current_item_detail["message"] = "Source and destination are the same. No action taken."
            current_item_detail["success"] = True
            results_details.append(current_item_detail)
            any_successful_moves = True
            continue

        if os.path.exists(final_destination_path_abs):
            current_item_detail["message"] = f"An item already exists at the destination with the name '{os.path.basename(source_path_abs)}'."
            results_details.append(current_item_detail)
            overall_success_flag = False
            continue
            
        if os.path.isdir(source_path_abs) and \
           (final_destination_path_abs == source_path_abs or \
            final_destination_path_abs.startswith(source_path_abs + os.sep)):
            current_item_detail["message"] = "A folder cannot be moved into itself or one of its subdirectories."
            results_details.append(current_item_detail)
            overall_success_flag = False
            continue

        try:
            shutil.move(source_path_abs, final_destination_path_abs)
            current_item_detail["message"] = f"Successfully moved to '{normalized_destination or 'Root'}'."
            current_item_detail["success"] = True
            any_successful_moves = True
        except Exception as e:
            current_item_detail["message"] = f"Error during move operation: {str(e)}"
            overall_success_flag = False
            
        results_details.append(current_item_detail)

    return overall_success_flag, any_successful_moves, results_details


def create_zip_from_items(file_system_root, items_unquoted, zip_output_path):
    """
    Empaqueta una lista de archivos/carpetas directamente en un archivo ZIP
    sin usar carpetas intermedias (staging), ahorrando RAM, CPU y E/S de disco.
    """
    overall_success = True
    message = "ZIP creado con éxito."
    
    try:
        # ZIP_STORED solo empaqueta sin intentar comprimir. Esencial para no quemar la CPU
        # de la Raspberry Pi con archivos de video que ya están comprimidos.
        with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_STORED) as zipf:
            for item_unquoted in items_unquoted:
                item_abs_path = os.path.join(file_system_root, item_unquoted)
                
                if not os.path.exists(item_abs_path):
                    continue
                    
                if os.path.isfile(item_abs_path):
                    # Si es un archivo suelto, se añade a la raíz del ZIP
                    arcname = os.path.basename(item_abs_path)
                    zipf.write(item_abs_path, arcname)
                    
                elif os.path.isdir(item_abs_path):
                    # Si es una carpeta, se recorre recursivamente y se añade
                    parent_dir_name = os.path.basename(item_abs_path)
                    for root, _, files in os.walk(item_abs_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Calcular la estructura de carpetas relativa dentro del ZIP
                            rel_path = os.path.relpath(file_path, item_abs_path)
                            arcname = os.path.join(parent_dir_name, rel_path)
                            zipf.write(file_path, arcname)
    except Exception as e:
        overall_success = False
        message = f"Error al crear el ZIP: {str(e)}"
        
    return overall_success, message


def process_create_folder(file_system_root, parent_folder_segment, new_folder_name_form):
    """Lógica aislada para crear una carpeta de forma segura."""
    actual_fs_relative_path = '' if parent_folder_segment == '__root__' else parent_folder_segment
    
    if not is_safe_path(file_system_root, actual_fs_relative_path):
        return False, "Error: La ruta base es inválida o no permitida."
    
    if not new_folder_name_form:
        return False, "No se especificó un nombre para la nueva carpeta."
    
    new_folder_name_secured = secure_filename(new_folder_name_form)
    if not new_folder_name_secured:
        return False, "El nombre de la carpeta contiene caracteres no válidos."
        
    new_folder_path_abs = os.path.join(file_system_root, actual_fs_relative_path, new_folder_name_secured)
    
    if os.path.exists(new_folder_path_abs):
        return False, f"La carpeta '{new_folder_name_secured}' ya existe."
        
    try:
        os.makedirs(new_folder_path_abs)
        return True, f"Carpeta '{new_folder_name_secured}' creada con éxito."
    except OSError as e:
        return False, f"Error al crear la carpeta '{new_folder_name_secured}': {str(e)}"


def process_delete_item(file_system_root, item_to_delete_segment):
    """Lógica aislada para eliminar un archivo o carpeta individual."""
    if item_to_delete_segment == '__root__':
        return False, "El directorio raíz no puede ser eliminado."
        
    if not is_safe_path(file_system_root, item_to_delete_segment):
        return False, "Error: La ruta del elemento a eliminar es inválida o no permitida."
        
    item_path_abs = os.path.join(file_system_root, item_to_delete_segment)
    item_name = os.path.basename(item_to_delete_segment)
    
    if not os.path.exists(item_path_abs):
        return False, f"Error: El elemento '{item_name}' no se encontró."
        
    try:
        if os.path.isfile(item_path_abs):
            os.remove(item_path_abs)
            return True, f"Archivo '{item_name}' eliminado con éxito."
        elif os.path.isdir(item_path_abs):
            shutil.rmtree(item_path_abs)
            return True, f"Carpeta '{item_name}' eliminada con éxito."
        else:
            return False, f"El elemento '{item_name}' no es un archivo ni carpeta válido."
    except Exception as e:
        return False, f"Error al eliminar '{item_name}': {str(e)}"


def process_move_item(file_system_root, item_to_move_segment, destination_relative_path_form):
    """Lógica aislada para mover un archivo o carpeta individual."""
    if item_to_move_segment == '__root__':
        return False, "El directorio raíz no puede ser movido."
        
    if not is_safe_path(file_system_root, item_to_move_segment):
        return False, "Error: La ruta de origen es inválida o no permitida."
        
    normalized_destination_relative_path = destination_relative_path_form.lstrip('/')
    if not is_safe_path(file_system_root, normalized_destination_relative_path):
        return False, "Error: La ruta de destino es inválida o no permitida."
        
    source_path_abs = os.path.join(file_system_root, item_to_move_segment)
    destination_directory_abs = os.path.join(file_system_root, normalized_destination_relative_path)
    
    if not os.path.exists(source_path_abs):
        return False, f"Error: El elemento de origen '{os.path.basename(item_to_move_segment)}' no existe."
        
    if not os.path.isdir(destination_directory_abs):
        return False, f"Error: El directorio de destino '{normalized_destination_relative_path or 'Raíz'}' no existe."
        
    final_destination_path_abs = os.path.join(destination_directory_abs, os.path.basename(source_path_abs))
    
    if os.path.exists(final_destination_path_abs):
        return False, f"Error: Ya existe un elemento llamado '{os.path.basename(source_path_abs)}' en el destino."
        
    if os.path.isdir(source_path_abs) and (final_destination_path_abs == source_path_abs or final_destination_path_abs.startswith(source_path_abs + os.sep)):
        return False, "Error: No puedes mover una carpeta dentro de sí misma o de sus subcarpetas."
        
    try:
        shutil.move(source_path_abs, final_destination_path_abs)
        return True, f"Elemento '{os.path.basename(item_to_move_segment)}' movido a '{normalized_destination_relative_path or 'Raíz'}' con éxito."
    except Exception as e:
        return False, f"Error al mover '{os.path.basename(item_to_move_segment)}': {str(e)}"