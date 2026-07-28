from flask import Blueprint, request, flash, redirect, url_for, current_app, abort, jsonify
import os
import shutil
from werkzeug.utils import secure_filename
from utils.utilsHandler import is_safe_path
from urllib.parse import unquote

actions_bp = Blueprint('actions', __name__)

@actions_bp.route('/create_folder/<path:parent_folder_segment>', methods=['POST'])
def create_folder(parent_folder_segment):
    """
    Handles the creation of a new folder within a specified parent directory.

    It receives the parent folder path segment from the URL and the new folder name
    from the form data. It performs several checks:
    - Validates the safety of the parent folder path.
    - Ensures a folder name is provided.
    - Secures the folder name against malicious characters.
    - Checks if a folder with the same name already exists.
    If all checks pass, it creates the new folder. Otherwise, it flashes
    an appropriate error or warning message.

    The route expects a POST request. After the operation, it redirects the user
    back to the browse view of the parent directory.

    :param parent_folder_segment: The relative path segment from the file system root
                                  to the parent directory where the new folder
                                  should be created. '__root__' indicates the base
                                  file system root.
    :type parent_folder_segment: str
    :returns: A Flask redirect response to the browse view of the parent directory.
    :rtype: werkzeug.wrappers.response.Response
    """

    parent_folder_segment = unquote(parent_folder_segment)

    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    actual_fs_relative_path = '' if parent_folder_segment == '__root__' else parent_folder_segment
    redirect_subpath_on_return = '' if parent_folder_segment == '__root__' else parent_folder_segment

    if not is_safe_path(FILE_SYSTEM_ROOT, actual_fs_relative_path):
        flash("Error: The base path to create the folder is invalid or not allowed.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=redirect_subpath_on_return))

    new_folder_name_form = request.form.get('new_folder_name')
    if not new_folder_name_form:
        flash("No name was specified for the new folder.", "warning")
        return redirect(url_for('browse.browse_directory', subpath=redirect_subpath_on_return))

    new_folder_name_secured = secure_filename(new_folder_name_form)
    if not new_folder_name_secured:
        flash("The folder name provided is not valid (may contain invalid characters).", "danger")
        return redirect(url_for('browse.browse_directory', subpath=redirect_subpath_on_return))

    new_folder_path_abs = os.path.join(FILE_SYSTEM_ROOT, actual_fs_relative_path, new_folder_name_secured)
    if os.path.exists(new_folder_path_abs):
        flash(f"The folder '{new_folder_name_secured}' already exists at this location.", "warning")
    else:
        try:
            os.makedirs(new_folder_path_abs)
            flash(f"Folder '{new_folder_name_secured}' successfully created.", "success")
        except OSError as e:
            current_app.logger.error(f"Error creating the folder {new_folder_path_abs}: {e}")
            flash(f"Error creating the folder '{new_folder_name_secured}'.", "danger")
            
    return redirect(url_for('browse.browse_directory', subpath=redirect_subpath_on_return))


@actions_bp.route('/delete_item/<path:item_to_delete_segment>', methods=['POST'])
def delete_item(item_to_delete_segment):
    """
    Handles the deletion of a single file or folder.

    It receives the path segment of the item to be deleted from the URL.
    It performs several checks:
    - Prevents deletion of the root directory.
    - Validates the safety of the item's path.
    - Ensures the item exists before attempting deletion.
    If the item is a file, it's removed using `os.remove`. If it's a directory,
    it's removed using `shutil.rmtree`. Appropriate flash messages are displayed
    based on the outcome.

    The route expects a POST request. After the operation, it redirects the user
    back to the browse view of the parent directory of the deleted item.

    :param item_to_delete_segment: The relative path segment from the file system root
                                   to the item (file or folder) to be deleted.
    :type item_to_delete_segment: str
    :returns: A Flask redirect response to the browse view of the parent directory.
    :rtype: werkzeug.wrappers.response.Response
    """

    item_to_delete_segment = unquote(item_to_delete_segment)

    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    parent_directory_segment = os.path.dirname(item_to_delete_segment)

    if item_to_delete_segment == '__root__':
        flash("The root directory cannot be deleted.", "danger")
        return redirect(url_for('browse.browse_directory'))

    if not is_safe_path(FILE_SYSTEM_ROOT, item_to_delete_segment):
        flash("Error: The path of the item to be deleted is invalid or not allowed.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=parent_directory_segment))

    item_path_abs = os.path.join(FILE_SYSTEM_ROOT, item_to_delete_segment)
    item_name = os.path.basename(item_to_delete_segment)

    if not os.path.exists(item_path_abs):
        flash(f"Error: The item '{item_name}' was not found to remove.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=parent_directory_segment))

    try:
        if os.path.isfile(item_path_abs):
            os.remove(item_path_abs)
            flash(f"File '{item_name}' successfully removed.", "success")
        elif os.path.isdir(item_path_abs):
            shutil.rmtree(item_path_abs)
            flash(f"Folder '{item_name}' successfully removed.", "success")
        else:
            flash(f"The item '{item_name}' is neither a valid file nor a valid folder.", "warning")
    except Exception as e:
        current_app.logger.error(f"Error deleting '{item_path_abs}': {e}")
        flash(f"Error when deleting '{item_name}': {str(e)}", "danger")

    return redirect(url_for('browse.browse_directory', subpath=parent_directory_segment))


@actions_bp.route('/delete_multiple_items', methods=['POST'])
def delete_multiple_items():
    """
    Handles the deletion of multiple files and/or folders.

    This endpoint expects a JSON payload containing a list of item path segments
    to be deleted. For each item, it performs similar checks as the single
    delete_item function:
    - Prevents deletion of the root directory or invalid paths.
    - Validates the safety of each item's path.
    - Checks if the item exists.
    It attempts to delete each valid item and collects results for each operation.
    
    After processing all items, it flashes a summary message (success, warning,
    or danger) based on the outcomes of the deletions. It returns a JSON response
    detailing the success or failure for each item, along with an overall success
    status and the summary message.

    The route expects a POST request with a JSON body like:
    `{"items_to_delete": ["path/to/item1", "path/to/item2"]}`

    :returns: A Flask JSON response containing:
              - `overall_success` (bool): True if all specified items were successfully
                deleted or if no valid items were specified, False if any deletion failed.
              - `message` (str): A summary message suitable for flashing to the user.
              - `details` (list): A list of dictionaries, each detailing the outcome
                for an individual item (item_name, item_path, success, message).
              And an HTTP status code (200 for success/partial success, 400 for bad request).
    :rtype: tuple[werkzeug.wrappers.response.Response, int]
    """

    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()

    if not data or 'items_to_delete' not in data:
        return jsonify({"overall_success": False, "message": "No items were specified for removal.", "details": []}), 400

    items_to_delete_segments_quoted = data['items_to_delete']

    if not isinstance(items_to_delete_segments_quoted, list):
        return jsonify({"overall_success": False, "message": "Invalid format for the elements to be deleted.", "details": []}), 400

    results_details = []
    overall_success_flag = True
    any_successful_deletions = False

    for item_segment_quoted in items_to_delete_segments_quoted:
        item_segment_unquoted = unquote(item_segment_quoted)
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

        if not is_safe_path(FILE_SYSTEM_ROOT, item_segment_unquoted):
            current_item_detail["message"] = "Invalid or not allowed route."
            results_details.append(current_item_detail)
            overall_success_flag = False
            continue

        item_path_abs = os.path.join(FILE_SYSTEM_ROOT, item_segment_unquoted)

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
            current_app.logger.error(f"Error deleting '{item_path_abs}': {e}")
            current_item_detail["message"] = f"Error when deleting: {str(e)}"
            overall_success_flag = False
            results_details.append(current_item_detail)

    final_json_overall_success = overall_success_flag and any_successful_deletions
    successful_delete_count = sum(1 for detail in results_details if detail["success"])
    total_attempted_count = len(items_to_delete_segments_quoted)

    if successful_delete_count == total_attempted_count and total_attempted_count > 0:
        final_message = f"All {successful_delete_count} selected item(s) were successfully deleted."
        flash_category = "success"
        final_json_overall_success = True
    elif successful_delete_count > 0:
        final_message = f"{successful_delete_count} of {total_attempted_count} item(s) deleted successfully. Some items may have failed."
        flash_category = "warning"
        final_json_overall_success = False
    elif total_attempted_count > 0:
        final_message = "None of the selected items could be deleted due to errors or issues."
        flash_category = "danger"
        final_json_overall_success = False
    else:
        final_message = "No valid items were selected for deletion."
        flash_category = "info"
        final_json_overall_success = True

    if total_attempted_count > 0 or flash_category == "info":
        flash(final_message, flash_category)

    return jsonify({
        "overall_success": final_json_overall_success,
        "message": final_message,
        "details": results_details
    }), 200

@actions_bp.route('/move_item/<path:item_to_move_segment>', methods=['POST'])
def move_item(item_to_move_segment):
    """
    Handles moving a single file or folder to a new destination.

    It receives the path segment of the item to be moved from the URL and
    the destination path from the form data ('destination_path').
    Key checks performed:
    - Prevents moving the root directory.
    - Validates the safety of both source and destination paths.
    - Ensures the source item exists.
    - Ensures the destination is an existing directory.
    - Prevents an item from being moved into itself or one of its subdirectories.
    - Checks if an item with the same name already exists at the destination.
    If all checks pass, `shutil.move` is used to perform the move operation.
    Appropriate flash messages are displayed based on the outcome.

    The route expects a POST request. After the operation, it redirects the user
    back to the browse view of the original parent directory of the moved item.

    :param item_to_move_segment: The relative path segment from the file system root
                                 to the item (file or folder) to be moved.
    :type item_to_move_segment: str
    :returns: A Flask redirect response to the browse view of the original parent directory.
    :rtype: werkzeug.wrappers.response.Response
    """

    item_to_move_segment = unquote(item_to_move_segment)

    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    current_item_parent_dir = os.path.dirname(item_to_move_segment)

    if item_to_move_segment == '__root__':
        flash("The root directory cannot be moved.", "danger")
        return redirect(url_for('browse.browse_directory'))

    destination_relative_path_form = request.form.get('destination_path', '').strip()

    if not is_safe_path(FILE_SYSTEM_ROOT, item_to_move_segment):
        flash("Error: The path of the item to move is invalid or not allowed.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))

    normalized_destination_relative_path = destination_relative_path_form.lstrip('/')

    if not is_safe_path(FILE_SYSTEM_ROOT, normalized_destination_relative_path):
        flash("Error: The destination path to move is invalid or not allowed.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))

    source_path_abs = os.path.join(FILE_SYSTEM_ROOT, item_to_move_segment)
    destination_directory_abs = os.path.join(FILE_SYSTEM_ROOT, normalized_destination_relative_path)
    
    if not os.path.exists(source_path_abs):
        flash(f"Error: The source item '{os.path.basename(item_to_move_segment)}' does not exist.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))

    if not os.path.isdir(destination_directory_abs):
        flash(f"Error: The target directory '{normalized_destination_relative_path or 'Root'}' does not exist or is not a directory.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))
        
    final_destination_path_abs = os.path.join(destination_directory_abs, os.path.basename(source_path_abs))

    if os.path.exists(final_destination_path_abs):
        flash(f"Error: An item already exists under the name '{os.path.basename(source_path_abs)}' at the destination '{normalized_destination_relative_path or 'Root'}'.", "warning")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))
    
    if os.path.isdir(source_path_abs) and \
       (final_destination_path_abs == source_path_abs or \
        final_destination_path_abs.startswith(source_path_abs + os.sep)):
        flash("Error: A folder cannot be moved into itself or one ofits subdirectories.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))

    try:
        shutil.move(source_path_abs, final_destination_path_abs)
        flash(f"Item '{os.path.basename(item_to_move_segment)}' moved to '{normalized_destination_relative_path or 'Root'}' successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error moving '{source_path_abs}' to '{final_destination_path_abs}': {e}") 
        flash(f"Error when moving '{os.path.basename(item_to_move_segment)}': {str(e)}", "danger")

    return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))


@actions_bp.route('/move_multiple_items', methods=['POST'])
def move_multiple_items():
    """
    Handles the movement of multiple files and/or folders to a new destination.

    This endpoint expects a JSON payload containing a list of item path segments
    to be moved (`items_to_move`) and the destination path (`destination_path`).
    For each item, it performs checks similar to `move_item`:
    - Prevents moving the root directory or invalid paths.
    - Validates the safety of source and destination paths.
    - Ensures the source item exists.
    - Checks for name collisions at the destination.
    - Prevents moving a directory into itself or its subdirectories.
    The destination directory itself is also validated for existence and safety.

    After processing all items, it flashes a summary message (success, warning,
    or danger) based on the outcomes of the move operations. It returns a JSON
    response detailing the success or failure for each item, an overall success
    status, and the summary message.

    The route expects a POST request with a JSON body like:
    `{"items_to_move": ["path/to/item1", "path/to/item2"], "destination_path": "path/to/destination"}`

    :returns: A Flask JSON response containing:
              - `overall_success` (bool): True if all specified items were successfully
                moved, False if any move operation failed or if the destination was invalid.
              - `message` (str): A summary message suitable for flashing to the user.
              - `details` (list): A list of dictionaries, each detailing the outcome
                for an individual item's move attempt.
              And an HTTP status code (200 for success/partial success, 400 for bad request).
    :rtype: tuple[werkzeug.wrappers.response.Response, int]
    """

    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()

    if not data:
        return jsonify({"overall_success": False, "message": "Invalid request data.", "details": []}), 400

    items_to_move_quoted = data.get('items_to_move')
    destination_relative_path_form = data.get('destination_path', '') 

    if not items_to_move_quoted or not isinstance(items_to_move_quoted, list):
        return jsonify({"overall_success": False, "message": "No items specified for move or invalid format.", "details": []}), 400

    normalized_destination_relative_path = destination_relative_path_form.strip().lstrip('/')
    
    if not is_safe_path(FILE_SYSTEM_ROOT, normalized_destination_relative_path):
        flash("Error: The destination path is invalid or not allowed.", "danger")
        return jsonify({"overall_success": False, "message": "Error: The destination path is invalid or not allowed.", "details": []}), 400 # Or 403

    destination_directory_abs = os.path.join(FILE_SYSTEM_ROOT, normalized_destination_relative_path)

    if not os.path.exists(destination_directory_abs) or not os.path.isdir(destination_directory_abs):
        flash(f"Error: The target directory '{normalized_destination_relative_path or 'Root'}' does not exist or is not a directory.", "danger")
        return jsonify({"overall_success": False, "message": f"Error: The target directory '{normalized_destination_relative_path or 'Root'}' does not exist or is not a directory.", "details": []}), 400

    results_details = []
    overall_success_flag = True
    any_successful_moves = False

    for item_segment_quoted in items_to_move_quoted:
        item_segment_unquoted = unquote(item_segment_quoted)
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

        if not is_safe_path(FILE_SYSTEM_ROOT, item_segment_unquoted):
            current_item_detail["message"] = "Invalid or not allowed source path."
            results_details.append(current_item_detail)
            overall_success_flag = False
            continue

        source_path_abs = os.path.join(FILE_SYSTEM_ROOT, item_segment_unquoted)
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
            current_item_detail["message"] = f"Successfully moved to '{normalized_destination_relative_path or 'Root'}'."
            current_item_detail["success"] = True
            any_successful_moves = True
        except Exception as e:
            current_app.logger.error(f"Error moving '{source_path_abs}' to '{final_destination_path_abs}': {e}")
            current_item_detail["message"] = f"Error during move operation: {str(e)}"
            overall_success_flag = False
        
        results_details.append(current_item_detail)

    final_json_overall_success = overall_success_flag and any_successful_moves
    successful_move_count = sum(1 for detail in results_details if detail["success"])
    total_attempted_count = len(items_to_move_quoted)


    if successful_move_count == total_attempted_count and total_attempted_count > 0:
        final_message = f"All {successful_move_count} selected item(s) were successfully moved."
        flash_category = "success"
        final_json_overall_success = True
    elif successful_move_count > 0:
        final_message = f"{successful_move_count} of {total_attempted_count} item(s) moved successfully. Some items may have failed."
        flash_category = "warning"
        final_json_overall_success = False
    elif total_attempted_count > 0 :
        final_message = "None of the selected items could be moved due to errors or issues."
        flash_category = "danger"
        final_json_overall_success = False
    else:
        final_message = "No valid items were selected for move operation."
        flash_category = "info"
        final_json_overall_success = True

    if total_attempted_count > 0 or flash_category == "info":
        flash(final_message, flash_category)

    return jsonify({
        "overall_success": final_json_overall_success,
        "message": final_message,
        "details": results_details
    }), 200