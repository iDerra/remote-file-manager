import os
from urllib.parse import quote
from datetime import datetime


def get_folder_size(folder_path_abs):
    """
    Calculates the total size of a folder by summing the sizes of all files
    within it and its subdirectories.

    :param folder_path_abs: Absolute path to the folder.
    :type folder_path_abs: str
    :returns: Total size of the folder in bytes. Returns 0 if path is not accessible.
    :rtype: int
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path_abs):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except OSError as e:
                        print(f"Warning: Could not get size of file '{fp}': {e}")
    except OSError as e:
        print(f"Warning: Could not walk directory '{folder_path_abs}': {e}")
    return total_size


def get_item_details(fs_root_path, parent_relative_path, item_name):
    """
    Gathers details for a given file or folder item, including its name,
    paths (ID, relative), type (file/directory), size, and modification date.
    For directories, the size is set to None to avoid performance bottlenecks (Lazy Loading).

    :param fs_root_path: The absolute path to the root of the managed file system.
    :type fs_root_path: str
    :param parent_relative_path: The relative path of the item's parent directory
                                 from the fs_root_path.
    :type parent_relative_path: str
    :param item_name: The name of the file or folder.
    :type item_name: str
    :returns: A dictionary containing details of the item:
              - 'name' (str): The item's name.
              - 'id_path' (str): URL-quoted relative path from fs_root_path, used as an ID.
              - 'relative_path_unquoted' (str): Unquoted relative path from fs_root_path.
              - 'is_dir' (bool): True if the item is a directory, False otherwise.
              - 'size' (Optional[int]): Size in bytes. None for directories.
              - 'modified' (str): Last modification date formatted as 'YYYY-MM-DD HH:MM:SS',
                                  or 'N/A' if not determinable.
    :rtype: dict
    """
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

        if details['is_dir']:
            details['size'] = None 
        else:
            details['size'] = stat_info.st_size 

        mod_time = datetime.fromtimestamp(stat_info.st_mtime)
        details['modified'] = mod_time.strftime('%Y-%m-%d %H:%M:%S')

    except OSError as e:
        print(f"ERROR: OSError in get_item_details for '{absolute_item_path}': {e}")
        if os.path.exists(absolute_item_path):
            details['is_dir'] = os.path.isdir(absolute_item_path)
            if details['is_dir'] and details['size'] is None:
                details['size'] = None

    return details

def is_safe_path(base_fs_root, requested_relative_path):
    """
    Checks if the resolved absolute path of a requested relative path
    is genuinely within the defined base file system root.
    This is a security measure to prevent directory traversal attacks (e.g., using '../').

    :param base_fs_root: The absolute path to the root directory that is being managed.
    :type base_fs_root: str
    :param requested_relative_path: The relative path (potentially with '..')
                                    that the user is trying to access.
    :type requested_relative_path: str
    :returns: True if the path is safe and within the base_fs_root, False otherwise.
    :rtype: bool
    """
    base_path_abs = os.path.abspath(base_fs_root)
    full_requested_path_abs = os.path.abspath(os.path.join(base_path_abs, os.path.normpath(requested_relative_path)))
    
    if full_requested_path_abs == base_path_abs or \
       full_requested_path_abs.startswith(base_path_abs + os.sep):
        return True
    return False