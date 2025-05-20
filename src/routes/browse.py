import os
from flask import Blueprint, render_template, url_for, abort, current_app, jsonify
from utils.utilsHandler import get_item_details, is_safe_path


def _build_folder_tree_recursive(current_path_abs, root_path_abs, current_depth=0):
    """
    Recursively builds a hierarchical tree structure of folders starting from
    a given current path.

    Each node in the tree represents a folder and contains its name,
    relative path from the `root_path_abs`, depth in the tree, and a list
    of its children (subfolders), which are also nodes.

    :param current_path_abs: The absolute path of the directory currently being processed.
    :type current_path_abs: str
    :param root_path_abs: The absolute path of the root directory of the entire scan.
                         Used to calculate relative paths.
    :type root_path_abs: str
    :param current_depth: The depth of the `current_path_abs` node in the tree,
                          used for representation or client-side logic.
    :type current_depth: int
    :returns: A list of folder nodes. Each node is a dictionary with 'name',
              'path', 'depth', and 'children' keys.
    :rtype: list[dict]
    """
    
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
    """
    Handles browsing of directories within the configured FILE_SYSTEM_ROOT.

    It displays the contents (files and folders) of the specified `subpath`.
    If `subpath` is empty, it displays the contents of the FILE_SYSTEM_ROOT.
    The function performs security checks to ensure the requested path is safe
    and actually exists. It gathers details for each item (like name, type, URLs
    for download/navigation) and passes them to the 'index.html' template.

    Multiple routes map to this function to allow flexible URL access.

    :param subpath: The relative path from the FILE_SYSTEM_ROOT to the directory
                    to be browsed. Defaults to an empty string, which means
                    the root directory.
    :type subpath: str
    :returns: A rendered HTML page ('index.html') displaying the directory contents,
              or an HTTP error (404 or 500) if the path is invalid, not found,
              or an error occurs.
    :rtype: str | werkzeug.wrappers.response.Response
    """

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


@browse_bp.route('/api/list-all-folders-tree')
def api_list_all_folders_tree():
    """
    API endpoint to retrieve a hierarchical tree structure of all discoverable
    folders (subdirectories) within the configured FILE_SYSTEM_ROOT.

    This is useful for UI elements that need to display a folder tree, such as
    a navigation pane or a more complex folder selection dialog.
    It uses the `_build_folder_tree_recursive` helper function.

    :returns: A Flask JSON response containing a list of root-level folder nodes.
              Each node has 'name', 'path', 'depth', and 'children' (recursively).
              Returns a JSON error object and HTTP 500 status on failure.
    :rtype: tuple[werkzeug.wrappers.response.Response, int]
    """
    
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