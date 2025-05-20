import os
from flask import Blueprint, render_template, url_for, abort, current_app, jsonify
from urllib.parse import unquote
from utils.utilsHandler import get_item_details, is_safe_path


def _generate_folder_list_for_select(root_folder_abs_path):
    folder_options = []

    for current_dir_abs, sub_dirs, _ in os.walk(root_folder_abs_path):
        sub_dirs.sort(key=lambda d: d.lower())

        for sub_dir_name in sub_dirs:
            sub_dir_full_abs_path = os.path.join(current_dir_abs, sub_dir_name)
            
            relative_path = os.path.relpath(sub_dir_full_abs_path, root_folder_abs_path).replace('\\', '/')
            if relative_path == '.':
                relative_path = ""

            depth = relative_path.count('/')
            indent_spaces = "\u00A0\u00A0\u00A0\u00A0" * depth
            
            display_name = f"{indent_spaces}{sub_dir_name}"
            
            folder_options.append({
                'path': relative_path,
                'display': display_name
            })
            
    folder_options.sort(key=lambda x: x['path'].lower())
    return folder_options


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

    items = []
    try:
        dir_items = []
        file_items = []
        for item_name_raw in os.listdir(current_path_abs):
            details = get_item_details(FILE_SYSTEM_ROOT, current_fs_path_for_os, item_name_raw)
            
            if details['is_dir']:
                details['url'] = url_for('browse.browse_directory', subpath=details['relative_path_unquoted'])
                details['download_url'] = url_for('files.download_folder_zip', folderpath=details['id_path'])
                dir_items.append(details)
            else:
                details['download_url'] = url_for('files.download_single_file', filepath=details['id_path'])
                file_items.append(details)
        
        dir_items.sort(key=lambda x: x['name'].lower())
        file_items.sort(key=lambda x: x['name'].lower())
        items = dir_items + file_items
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
                           items=items,
                           current_directory_display=display_current_folder_name,
                           current_path_display=display_current_logical_path,
                           current_path_for_forms=path_param_for_forms, 
                           parent_path_url=parent_path_url)


@browse_bp.route('/api/list-all-folders')
def api_list_all_folders():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    if not os.path.isdir(FILE_SYSTEM_ROOT):
        current_app.logger.error(f"FILE_SYSTEM_ROOT '{FILE_SYSTEM_ROOT}' is not a valid directory.")
        return jsonify({"error": "Server configuration error: Root directory not found."}), 500
        
    try:
        folder_list = _generate_folder_list_for_select(FILE_SYSTEM_ROOT)
        return jsonify(folder_list)
    except Exception as e:
        current_app.logger.error(f"Error generating folder list for move: {e}")
        return jsonify({"error": "Could not retrieve folder list."}), 500