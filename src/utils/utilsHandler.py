import os
from urllib.parse import quote, unquote
from datetime import datetime

def get_item_details(fs_root_path, parent_relative_path, item_name):
    absolute_item_path = os.path.join(fs_root_path, parent_relative_path, item_name)
    item_relative_path_to_root = os.path.join(parent_relative_path, item_name).replace('\\', '/')
    id_path_quoted = quote(item_relative_path_to_root)
    
    details = {
        'name': item_name,
        'id_path': id_path_quoted,
        'relative_path_unquoted': item_relative_path_to_root, 
        'is_dir': False,
        'size': None,
        'modified': 'N/A'
    }

    try:
        if not os.path.exists(absolute_item_path): 
            print(f"WARN: get_item_details: Path does not exist '{absolute_item_path}'")
            return details

        stat_info = os.stat(absolute_item_path)
        details['is_dir'] = os.path.isdir(absolute_item_path)
        if not details['is_dir']:
            details['size'] = stat_info.st_size
        
        mod_time = datetime.fromtimestamp(stat_info.st_mtime)
        details['modified'] = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        
    except OSError as e:
        print(f"ERROR: OSError in get_item_details for '{absolute_item_path}': {e}")
        details['is_dir'] = os.path.isdir(absolute_item_path)

    return details

def is_safe_path(base_fs_root, requested_relative_path):
    base_path_abs = os.path.abspath(base_fs_root)
    full_requested_path_abs = os.path.abspath(os.path.join(base_path_abs, os.path.normpath(requested_relative_path)))
    
    if full_requested_path_abs == base_path_abs or \
       full_requested_path_abs.startswith(base_path_abs + os.sep):
        return True
    return False