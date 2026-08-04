import os
import math
from flask import Blueprint, render_template, url_for, abort, current_app, jsonify, request
from utils.utilsHandler import get_item_details, is_safe_path
from urllib.parse import unquote
from utils.hardware import get_system_disk_info, safely_unmount_disk

browse_bp = Blueprint('browse', __name__)

@browse_bp.route('/')
@browse_bp.route('/browse/')
@browse_bp.route('/browse/<path:subpath>')
def browse_directory(subpath=''):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    
    current_fs_path_for_os = subpath
    path_param_for_forms = current_fs_path_for_os if current_fs_path_for_os else '__root__'
    display_current_logical_path = current_fs_path_for_os if current_fs_path_for_os else 'Root'
    display_current_folder_name = os.path.basename(current_fs_path_for_os) if current_fs_path_for_os else os.path.basename(FILE_SYSTEM_ROOT)
    
    if not is_safe_path(FILE_SYSTEM_ROOT, current_fs_path_for_os):
        current_app.logger.warning(f"Unsecured access attempt (browse): {current_fs_path_for_os} path {FILE_SYSTEM_ROOT}")
        abort(404, "Path not found or not allowed.")

    current_path_abs = os.path.join(FILE_SYSTEM_ROOT, current_fs_path_for_os)

    if not os.path.exists(current_path_abs) or not os.path.isdir(current_path_abs):
        current_app.logger.error(f"Directory not found or not a directory (browse): {current_path_abs}")
        abort(404, "Directory not found.")

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    items_to_display = []
    try:
        all_item_names = os.listdir(current_path_abs)
        
        dir_names = []
        file_names = []
        for name in all_item_names:
            if os.path.isdir(os.path.join(current_path_abs, name)):
                dir_names.append(name)
            else:
                file_names.append(name)
                
        dir_names.sort(key=str.lower)
        file_names.sort(key=str.lower)
        all_sorted_names = dir_names + file_names
        
        total_items = len(all_sorted_names)
        total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1
        
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
            
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        names_for_this_page = all_sorted_names[start_idx:end_idx]
        
        for item_name in names_for_this_page:
            details = get_item_details(FILE_SYSTEM_ROOT, current_fs_path_for_os, item_name)
            if details['is_dir']:
                details['url'] = url_for('browse.browse_directory', subpath=details['relative_path_unquoted'])
                details['download_url'] = url_for('files.download_folder_zip', folderpath=details['id_path'])
            else:
                details['download_url'] = url_for('files.download_single_file', filepath=details['id_path'])
                
                if details.get('is_video'):
                    details['stream_url'] = url_for('files.stream_file', filepath=details['id_path'])
                
            items_to_display.append(details)

    except OSError as e:
        current_app.logger.error(f"Error listing directory {current_path_abs}: {e}")
        abort(500, "Error reading the directory.")

    parent_path_url = None
    if current_fs_path_for_os:
        parent_logical_subpath = os.path.dirname(current_fs_path_for_os)
        if parent_logical_subpath == "" and current_fs_path_for_os != "":
            parent_path_url = url_for('browse.browse_directory')
        elif parent_logical_subpath:
            parent_path_url = url_for('browse.browse_directory', subpath=parent_logical_subpath)
        else:
            parent_path_url = url_for('browse.browse_directory')

    return render_template('index.html',
                           items=items_to_display,
                           current_directory_display=display_current_folder_name,
                           current_path_display=display_current_logical_path,
                           current_path_for_forms=path_param_for_forms, 
                           raw_subpath=current_fs_path_for_os,
                           parent_path_url=parent_path_url,
                           page=page,
                           total_pages=total_pages,
                           total_items=total_items)

@browse_bp.route('/api/item-info', methods=['POST'])
def api_item_info():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()
    
    if not data or 'path' not in data:
        return jsonify({"success": False, "message": "Datos inválidos."}), 400
        
    item_path_segment = unquote(data['path'])
    
    if not is_safe_path(FILE_SYSTEM_ROOT, item_path_segment):
        return jsonify({"success": False, "message": "Ruta no permitida."}), 403
        
    abs_path = os.path.join(FILE_SYSTEM_ROOT, item_path_segment)
    
    if not os.path.exists(abs_path):
        return jsonify({"success": False, "message": "La ruta no existe."}), 404
        
    try:
        if os.path.isdir(abs_path):
            total_size = 0
            file_count = 0
            for dirpath, _, filenames in os.walk(abs_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
                        file_count += 1
            return jsonify({"success": True, "size": total_size, "file_count": file_count, "is_dir": True})
        else:
            return jsonify({"success": True, "size": os.path.getsize(abs_path), "file_count": 1, "is_dir": False})
    except Exception as e:
        current_app.logger.error(f"Error calculando tamaño: {e}")
        return jsonify({"success": False, "message": "Error leyendo el disco duro."}), 500


@browse_bp.route('/api/disk-info', methods=['GET'])
def api_disk_info():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    try:
        data = get_system_disk_info(FILE_SYSTEM_ROOT)
        return jsonify(data)
    except Exception as e:
        current_app.logger.error(f"Error getting disk info: {e}")
        return jsonify({"success": False, "message": "Error al leer la información del hardware."}), 500

@browse_bp.route('/api/unmount-disk', methods=['POST'])
def api_unmount_disk():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    try:
        success, message = safely_unmount_disk(FILE_SYSTEM_ROOT)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error del sistema: {str(e)}"})


@browse_bp.route('/api/folders-lazy', methods=['POST'])
def api_folders_lazy():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json() or {}
    
    current_rel_path = data.get('path', '')
    if current_rel_path == '__root__':
        current_rel_path = ''
        
    if not is_safe_path(FILE_SYSTEM_ROOT, current_rel_path):
        return jsonify({"error": "Ruta no permitida."}), 403
        
    current_abs_path = os.path.join(FILE_SYSTEM_ROOT, current_rel_path)
    
    if not os.path.exists(current_abs_path) or not os.path.isdir(current_abs_path):
        return jsonify({"error": "El directorio no existe."}), 404
        
    parent_rel_path = None
    if current_rel_path:
        parent_rel_path = os.path.dirname(current_rel_path)
        
    folders = []
    try:
        # Obtener solo las carpetas de este nivel
        for item in sorted(os.listdir(current_abs_path), key=str.lower):
            item_abs = os.path.join(current_abs_path, item)
            if os.path.isdir(item_abs):
                folders.append({
                    "name": item,
                    "path": os.path.relpath(item_abs, FILE_SYSTEM_ROOT).replace('\\', '/')
                })
    except OSError as e:
        return jsonify({"error": str(e)}), 500
        
    return jsonify({
        "current_path": current_rel_path,
        "parent_path": parent_rel_path,
        "folders": folders
    })