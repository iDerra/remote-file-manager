import os
import math
import shutil
import subprocess
import re
from flask import Blueprint, render_template, url_for, abort, current_app, jsonify, request
from utils.utilsHandler import get_item_details, is_safe_path
from urllib.parse import unquote

def _build_folder_tree_recursive(current_path_abs, root_path_abs, current_depth=0):
    folder_tree_nodes = []
    try:
        items = sorted(
            (item for item in os.listdir(current_path_abs) if os.path.isdir(os.path.join(current_path_abs, item))),
            key=str.lower
        )
    except OSError:
        current_app.logger.warning(f"The route to build the tree could not be accessed: {current_path_abs}")
        return []

    for item_name in items:
        item_full_abs_path = os.path.join(current_path_abs, item_name)
        relative_path = os.path.relpath(item_full_abs_path, root_path_abs).replace('\\', '/')
        
        node = {
            'name': item_name,
            'path': relative_path,
            'depth': current_depth,
            'children': _build_folder_tree_recursive(item_full_abs_path, root_path_abs, current_depth + 1)
        }
        folder_tree_nodes.append(node)
    return folder_tree_nodes
    

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

@browse_bp.route('/api/list-all-folders-tree')
def api_list_all_folders_tree():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    if not os.path.isdir(FILE_SYSTEM_ROOT):
        current_app.logger.error(f"FILE_SYSTEM_ROOT '{FILE_SYSTEM_ROOT}' is not a valid directory.")
        return jsonify({"error": "Server configuration error: Root directory not found."}), 500

    try:
        folder_tree = _build_folder_tree_recursive(FILE_SYSTEM_ROOT, FILE_SYSTEM_ROOT)
        return jsonify(folder_tree)
    except Exception as e:
        current_app.logger.error(f"Error generating the folder tree to move: {e}")
        return jsonify({"error": "The list of folders could not be retrieved."}), 500

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
        total, used, free = shutil.disk_usage(FILE_SYSTEM_ROOT)
        percent = round((used / total) * 100, 1) if total > 0 else 0
        
        device_path = "Desconocido"
        fs_type = "Desconocido"
        raw_device = ""
        
        df_result = subprocess.run(['df', '-T', FILE_SYSTEM_ROOT], capture_output=True, text=True)
        if df_result.returncode == 0:
            lines = df_result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                device_path = parts[0]  
                fs_type = parts[1]      
                
                match = re.match(r'(/dev/sd[a-z]|/dev/nvme\d+n\d+|/dev/mmcblk\d+)', device_path)
                if match:
                    raw_device = match.group(1)

        power_status = "Desconocido"
        temperature = "N/A"
        health = "Desconocido"

        if raw_device:
            hdparm_res = subprocess.run(['sudo', 'hdparm', '-C', raw_device], capture_output=True, text=True)
            if hdparm_res.returncode == 0:
                stdout_lower = hdparm_res.stdout.lower()
                if "standby" in stdout_lower:
                    power_status = "Reposo (Standby)"
                elif "active" in stdout_lower or "idle" in stdout_lower:
                    power_status = "Activo (Girando)"

            smart_res = subprocess.run(['sudo', 'smartctl', '-a', raw_device], capture_output=True, text=True)
            if "SMART support is: Enabled" in smart_res.stdout or "SMART overall-health" in smart_res.stdout:
                if "PASSED" in smart_res.stdout or "OK" in smart_res.stdout:
                    health = "Correcto"
                elif "FAILED" in smart_res.stdout:
                    health = "Riesgo de fallo"
                
                for line in smart_res.stdout.split('\n'):
                    if "Temperature_Celsius" in line:
                        parts = line.split()
                        temperature = f"{parts[-1]} °C"
                        break
                    elif "Current Drive Temperature:" in line:
                        temperature = f"{line.split(':')[1].strip()} C"
                        break

        return jsonify({
            "success": True,
            "total": total,
            "used": used,
            "free": free,
            "percent": percent,
            "device": device_path,
            "fs_type": fs_type.upper(),
            "power_status": power_status,
            "health": health,
            "temperature": temperature
        })
    except Exception as e:
        current_app.logger.error(f"Error getting disk info: {e}")
        return jsonify({"success": False, "message": "Error al leer la información del hardware."}), 500