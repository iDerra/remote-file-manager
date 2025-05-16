import os
from flask import Blueprint, render_template, url_for, abort, current_app
from urllib.parse import unquote
from utils.utilsHandler import get_item_details, is_safe_path

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