from flask import (Blueprint, send_from_directory, abort, current_app, send_file, 
                   after_this_request, request, flash, redirect, url_for, jsonify, Response)
import os
import shutil
import tempfile
import uuid
from werkzeug.utils import secure_filename
from utils.utilsHandler import is_safe_path
from utils.file_ops import get_video_subtitles, generate_vtt_stream
from urllib.parse import unquote

files_bp = Blueprint('files', __name__)

TEMP_ZIP_FOLDER_NAME = '.tmp_zips'

def get_temp_zip_dir_abs():
    file_system_root = current_app.config['FILE_SYSTEM_ROOT']
    temp_zip_dir = os.path.join(file_system_root, TEMP_ZIP_FOLDER_NAME)
    os.makedirs(temp_zip_dir, exist_ok=True)
    return temp_zip_dir

@files_bp.route('/download_file/<path:filepath>')
def download_single_file(filepath):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    filepath = unquote(filepath)
    
    if not is_safe_path(FILE_SYSTEM_ROOT, filepath):
        current_app.logger.warning(f"Unsecured download attempt (file): {filepath} path {FILE_SYSTEM_ROOT}")
        abort(404, "File not found or not allowed.")
        
    absolute_file_path = os.path.join(FILE_SYSTEM_ROOT, filepath)
    
    if not os.path.isfile(absolute_file_path):
        current_app.logger.warning(f"Download requested for a non-file: {absolute_file_path}")
        abort(404, "The requested resource is not a valid file or does not exist.")
        
    try:
        directory = os.path.dirname(absolute_file_path)
        filename = os.path.basename(absolute_file_path)
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        current_app.logger.error(f"File not found for send_from_directory: {absolute_file_path}")
        abort(404, "File not found.")
    except Exception as e:
        current_app.logger.error(f"Error downloading file {filepath}: {e}")
        abort(500, "Error processing download.")


@files_bp.route('/download_folder_zip/<path:folderpath>')
def download_folder_zip(folderpath):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    folderpath = unquote(folderpath)
    
    if not is_safe_path(FILE_SYSTEM_ROOT, folderpath):
        current_app.logger.warning(f"Unsecured download attempt (folder): {folderpath} path {FILE_SYSTEM_ROOT}")
        abort(404, "Folder not found or not allowed.")
            
    absolute_folder_path = os.path.join(FILE_SYSTEM_ROOT, folderpath)
    if not os.path.isdir(absolute_folder_path):
        current_app.logger.warning(f"ZIP download requested for a non-directory: {absolute_folder_path}")
        abort(404, "The requested resource is not a valid directory or does not exist.")
            
    # Determinar el nombre del archivo ZIP
    folder_name_for_zip_source = os.path.basename(folderpath) if folderpath else os.path.basename(FILE_SYSTEM_ROOT)
    zip_display_name_base = secure_filename(folder_name_for_zip_source)
    if not zip_display_name_base: 
        zip_display_name_base = "archive"
    final_zip_display_name = f"{zip_display_name_base}.zip"
    
    # Generar ruta de almacenamiento temporal segura (usando la HDD de 4TB)
    temp_zip_storage_abs = get_temp_zip_dir_abs()
    unique_zip_filename = f"{uuid.uuid4()}_{final_zip_display_name}"
    zip_filename_full_path = os.path.join(temp_zip_storage_abs, unique_zip_filename)
    
    # Importar nuestra función optimizada
    from utils.file_ops import create_zip_from_items
    
    # Preparamos la ruta como una lista de un solo elemento para reutilizar la función
    items_unquoted = [folderpath] if folderpath else ['']
    
    # Crear el ZIP directamente, sin copias intermedias y sin compresión excesiva
    success, message = create_zip_from_items(FILE_SYSTEM_ROOT, items_unquoted, zip_filename_full_path)
    
    if not success:
        current_app.logger.error(f"Error creating zip for folder {folderpath}: {message}")
        # Limpieza en caso de error
        if os.path.exists(zip_filename_full_path):
            try:
                os.remove(zip_filename_full_path)
            except Exception as cleanup_error:
                current_app.logger.error(f"Error deleting temporary file {zip_filename_full_path} after failure: {cleanup_error}")
        abort(500, "Error creating the folder ZIP file.")

    # Programar la limpieza del archivo ZIP después de que el usuario lo descargue
    @after_this_request 
    def cleanup_single_folder_zip(response_from_send_file):
        try:
            if os.path.exists(zip_filename_full_path):
                os.remove(zip_filename_full_path)
                current_app.logger.info(f"Temporary zip cleaned: {zip_filename_full_path}")
        except Exception as error:
            current_app.logger.error(f"Error deleting temporary zip {zip_filename_full_path}: {error}")
        return response_from_send_file
            
    return send_file(zip_filename_full_path, download_name=final_zip_display_name, as_attachment=True)


@files_bp.route('/upload/<path:destination_folder_segment>', methods=['POST'])
def upload_files(destination_folder_segment):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    
    destination_folder_segment = unquote(destination_folder_segment)
    base_target_relative_path = '' if destination_folder_segment == '__root__' else destination_folder_segment

    if not is_safe_path(FILE_SYSTEM_ROOT, base_target_relative_path):
        return jsonify({"success": False, "message": "Error: Base destination invalid."}), 403

    if 'files_to_upload' not in request.files:
        return jsonify({"success": False, "message": "No file part in request."}), 400

    file_storage = request.files.get('files_to_upload')
    if not file_storage or not file_storage.filename:
        return jsonify({"success": False, "message": "No file selected."}), 400

    # Extraemos información de los chunks (si viene)
    chunk_index = request.form.get('chunk_index', type=int)
    total_chunks = request.form.get('total_chunks', type=int)
    is_chunked = chunk_index is not None and total_chunks is not None
            
    item_relative_path_in_upload = request.form.get('relative_path', file_storage.filename)
    sanitized_item_path_parts = []
    for part in item_relative_path_in_upload.replace('\\', '/').split('/'):
        secured_part = secure_filename(part)
        if secured_part:
            sanitized_item_path_parts.append(secured_part)
    
    if not sanitized_item_path_parts:
        return jsonify({"success": False, "message": "Invalid filename."}), 400
    
    filename_secured = sanitized_item_path_parts[-1]
    sub_directories_in_upload = sanitized_item_path_parts[:-1]

    final_item_relative_dir = base_target_relative_path
    if sub_directories_in_upload:
        final_item_relative_dir = os.path.join(base_target_relative_path, *sub_directories_in_upload)

    if not is_safe_path(FILE_SYSTEM_ROOT, final_item_relative_dir):
        return jsonify({"success": False, "message": "Calculated path invalid."}), 403

    target_item_directory_abs = os.path.join(FILE_SYSTEM_ROOT, final_item_relative_dir)

    try:
        os.makedirs(target_item_directory_abs, exist_ok=True)
    except OSError as e:
        return jsonify({"success": False, "message": f"Error creating dir: {e}"}), 500

    destination_file_path_abs = os.path.join(target_item_directory_abs, filename_secured)
    
    # Comprobación de existencia (Solo si es un archivo normal o el primer chunk)
    if os.path.exists(destination_file_path_abs) and (not is_chunked or chunk_index == 0):
        return jsonify({"success": False, "message": "File already exists. Skipped."}), 409 

    try:
        if is_chunked:
            # Modo Chunk: Abrimos en modo "append binary" ('ab') para añadir al final
            with open(destination_file_path_abs, 'ab') as f:
                f.write(file_storage.read())
            
            # Si era el último chunk, mandamos éxito total
            if chunk_index == total_chunks - 1:
                return jsonify({"success": True, "message": "File uploaded successfully."}), 200
            else:
                # Si faltan chunks, avisamos de que este trozo se subió bien
                return jsonify({"success": True, "message": "Chunk uploaded."}), 206
        else:
            # Modo Normal (archivos pequeños sin chunks)
            file_storage.save(destination_file_path_abs)
            return jsonify({"success": True, "message": "File uploaded successfully."}), 200
            
    except Exception as e:
        current_app.logger.error(f"Upload error: {e}")
        return jsonify({"success": False, "message": "Error saving file."}), 500
        

@files_bp.route('/api/prepare_multiple_files_zip', methods=['POST'])
def prepare_multiple_files_zip():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "Invalid request."}), 400
        
    item_paths_quoted = data.get('items_to_download')
    user_zip_name_suggestion = data.get('zip_name', 'archive.zip')
    
    if not item_paths_quoted or not isinstance(item_paths_quoted, list):
        return jsonify({"success": False, "message": "No items specified for download."}), 400
        
    if not user_zip_name_suggestion.endswith('.zip'):
        user_zip_name_suggestion += '.zip'
        
    zip_display_name = secure_filename(user_zip_name_suggestion) or "downloaded_files.zip"
    
    temp_zip_storage_abs = get_temp_zip_dir_abs()
    unique_zip_filename_on_server = f"{uuid.uuid4()}_{zip_display_name}"
    final_zip_path_on_server_abs = os.path.join(temp_zip_storage_abs, unique_zip_filename_on_server)
    
    # Decodificar y validar rutas
    items_unquoted = []
    for item_q in item_paths_quoted:
        item_unq = unquote(item_q)
        if is_safe_path(FILE_SYSTEM_ROOT, item_unq):
            items_unquoted.append(item_unq)
            
    if not items_unquoted:
        return jsonify({"success": False, "message": "No valid files or folders were found."}), 400

    # Llamada limpia y segura a nuestra nueva función
    from utils.file_ops import create_zip_from_items
    success, message = create_zip_from_items(FILE_SYSTEM_ROOT, items_unquoted, final_zip_path_on_server_abs)
    
    if not success:
        current_app.logger.error(message)
        return jsonify({"success": False, "message": "Server error while creating the ZIP file."}), 500
        
    download_url_for_client = url_for('files.download_prepared_zip_route',
                                       zip_file_on_server=unique_zip_filename_on_server,
                                       _external=False)
                                       
    flash(f"ZIP file '{zip_display_name}' is ready. Your download will start automatically.", "success")
    
    return jsonify({
        "success": True,
        "download_url": download_url_for_client,
        "zip_display_name": zip_display_name
    }), 200
            

@files_bp.route('/download_prepared_zip/<path:zip_file_on_server>')
def download_prepared_zip_route(zip_file_on_server):
    temp_zip_dir_abs = get_temp_zip_dir_abs()
    safe_zip_filename = secure_filename(os.path.basename(zip_file_on_server))
    file_path_abs = os.path.join(temp_zip_dir_abs, safe_zip_filename)

    if not os.path.exists(file_path_abs) or not os.path.isfile(file_path_abs):
        current_app.logger.error(f"Prepared ZIP not found for download: {file_path_abs}")
        flash("The requested ZIP file was not found or has expired. Please try preparing it again.", "warning")
        return redirect(url_for('browse.browse_directory')) 
    
    try:
        return send_from_directory(temp_zip_dir_abs, safe_zip_filename, as_attachment=True)
    except Exception as e:
        current_app.logger.error(f"Error sending prepared ZIP {safe_zip_filename}: {e}")
        flash("An error occurred while trying to send the ZIP file.", "danger")
        return redirect(url_for('browse.browse_directory'))


@files_bp.after_request
def cleanup_prepared_zip(response):
    if request.endpoint == 'files.download_prepared_zip_route':
        if 200 <= response.status_code < 300:
            if 'zip_file_on_server' in request.view_args:
                zip_file_to_delete_basename = secure_filename(os.path.basename(request.view_args['zip_file_on_server']))
                temp_zip_dir = get_temp_zip_dir_abs()
                file_path_to_delete_abs = os.path.join(temp_zip_dir, zip_file_to_delete_basename)
                
                if os.path.exists(file_path_to_delete_abs):
                    try:
                        os.remove(file_path_to_delete_abs)
                        current_app.logger.info(f"Temporary ZIP deleted: {file_path_to_delete_abs}")
                    except Exception as e:
                        current_app.logger.error(f"Error deleting temporary ZIP {file_path_to_delete_abs}: {e}")
                else:
                    current_app.logger.warning(f"Temporary ZIP for cleanup not found (already deleted or moved?): {file_path_to_delete_abs}")
            else:
                current_app.logger.warning("Cleanup function called for download_prepared_zip_route but 'zip_file_on_server' not in view_args.")
    return response

@files_bp.route('/stream_file/<path:filepath>')
def stream_file(filepath):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    filepath = unquote(filepath)
    
    if not is_safe_path(FILE_SYSTEM_ROOT, filepath):
        abort(404, "File not found or not allowed.")
        
    absolute_file_path = os.path.join(FILE_SYSTEM_ROOT, filepath)
    
    if not os.path.isfile(absolute_file_path):
        abort(404, "The requested resource is not a valid file.")
        
    directory = os.path.dirname(absolute_file_path)
    filename = os.path.basename(absolute_file_path)
    
    return send_from_directory(directory, filename, as_attachment=False)

@files_bp.route('/api/video_subtitles/<path:filepath>')
def video_subtitles_info(filepath):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    filepath = unquote(filepath)
    abs_path = os.path.join(FILE_SYSTEM_ROOT, filepath)
    
    if not os.path.isfile(abs_path):
        return jsonify({"success": False, "subtitles": []})
        
    try:
        subs = get_video_subtitles(abs_path)
        return jsonify({"success": True, "subtitles": subs})
    except Exception as e:
        current_app.logger.error(f"Error reading subtitles with ffprobe: {e}")
        return jsonify({"success": False, "subtitles": []})

@files_bp.route('/stream_subtitle/<path:filepath>/<int:stream_index>')
def stream_subtitle(filepath, stream_index):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    filepath = unquote(filepath)
    abs_path = os.path.join(FILE_SYSTEM_ROOT, filepath)
    
    if not os.path.isfile(abs_path):
        abort(404)
        
    return Response(generate_vtt_stream(abs_path, stream_index), mimetype='text/vtt')