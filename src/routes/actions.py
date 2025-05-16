from flask import Blueprint, request, flash, redirect, url_for, current_app, abort, jsonify
import os
import shutil
from werkzeug.utils import secure_filename
from utils.utilsHandler import is_safe_path
from urllib.parse import unquote

actions_bp = Blueprint('actions', __name__)

@actions_bp.route('/create_folder/<path:parent_folder_segment>', methods=['POST'])
def create_folder(parent_folder_segment):
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


@actions_bp.route('/move_item/<path:item_to_move_segment>', methods=['POST'])
def move_item(item_to_move_segment):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    current_item_parent_dir = os.path.dirname(item_to_move_segment)

    if item_to_move_segment == '__root__':
        flash("The root directory cannot be moved.", "danger")
        return redirect(url_for('browse.browse_directory'))

    destination_relative_path_form = request.form.get('destination_path', '').strip()

    if not is_safe_path(FILE_SYSTEM_ROOT, item_to_move_segment):
        flash("Error: The path of the item to move is invalid or not allowed.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))

    if not destination_relative_path_form:
        flash("A destination route to move was not specified.", "warning")
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
        flash(f"Error: The target directory '{normalized_destination_relative_path}' does not exist or is not a directory.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))
        
    final_destination_path_abs = os.path.join(destination_directory_abs, os.path.basename(source_path_abs))

    if os.path.exists(final_destination_path_abs):
        flash(f"Error: An item already exists under the name '{os.path.basename(source_path_abs)}' at the destination '{normalized_destination_relative_path}'.", "warning")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))
    
    if os.path.isdir(source_path_abs) and final_destination_path_abs.startswith(source_path_abs + os.sep):
        flash("Error: A folder cannot be moved within itself.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))

    try:
        shutil.move(source_path_abs, final_destination_path_abs)
        flash(f"Item '{os.path.basename(item_to_move_segment)}' moved to '{normalized_destination_relative_path}' successfully.", "success")
    except Exception as e:
        current_app.logger.error(f"Error moving '{source_path_abs}' to '{final_destination_path_abs}': {e}") 
        flash(f"Error when moving '{os.path.basename(item_to_move_segment)}': {str(e)}", "danger")

    return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))

@actions_bp.route('/delete_multiple_items', methods=['POST'])
def delete_multiple_items():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()

    if not data or 'items_to_delete' not in data:
        return jsonify({"success": False, "message": "No items were specified for removal.", "details": []}), 400

    items_to_delete_segments_quoted = data['items_to_delete']

    if not isinstance(items_to_delete_segments_quoted, list):
        return jsonify({"success": False, "message": "Invalid format for the elements to be deleted.", "details": []}), 400

    results_details = []
    overall_success = True
    any_successful_deletions = False

    for item_segment_quoted in items_to_delete_segments_quoted:
        item_segment_unquoted = unquote(item_segment_quoted)
        item_name_display = os.path.basename(item_segment_unquoted) if item_segment_unquoted else item_segment_unquoted


        if item_segment_unquoted == '__root__' or not item_segment_unquoted:
            results_details.append({"item_name": "Root", "item_path": item_segment_unquoted, "success": False, "message": "The root directory cannot be deleted."})
            overall_success = False
            continue

        if not is_safe_path(FILE_SYSTEM_ROOT, item_segment_unquoted):
            results_details.append({"item_name": item_name_display, "item_path": item_segment_unquoted, "success": False, "message": "Invalid or not allowed route."})
            overall_success = False
            continue

        item_path_abs = os.path.join(FILE_SYSTEM_ROOT, item_segment_unquoted)

        if not os.path.exists(item_path_abs):
            results_details.append({"item_name": item_name_display, "item_path": item_segment_unquoted, "success": False, "message": "Item not found (could have been deleted previously)." })
            overall_success = False 
            continue

        try:
            if os.path.isfile(item_path_abs):
                os.remove(item_path_abs)
                results_details.append({"item_name": item_name_display, "item_path": item_segment_unquoted, "success": True, "message": "File successfully deleted."})
                any_successful_deletions = True
            elif os.path.isdir(item_path_abs):
                shutil.rmtree(item_path_abs) 
                results_details.append({"item_name": item_name_display, "item_path": item_segment_unquoted, "success": True, "message": "Folder successfully deleted."})
                any_successful_deletions = True
            else:
                results_details.append({"item_name": item_name_display, "item_path": item_segment_unquoted, "success": False, "message": "The item is not a valid file or folder."})
                overall_success = False
        except Exception as e:
            current_app.logger.error(f"Error eliminando '{item_path_abs}': {e}")
            results_details.append({"item_name": item_name_display, "item_path": item_segment_unquoted, "success": False, "message": f"Error when deleting: {str(e)}"})
            overall_success = False
    
    final_message = "Multiple elimination operation completed."
    if any_successful_deletions and not overall_success:
        final_message = "Some elements were removed, but errors occurred with others."
    elif not any_successful_deletions and not overall_success:
         final_message = "None of the selected items could not be deleted due to errors or because they were not found."
    elif any_successful_deletions and overall_success:
         final_message = "All selected items were successfully removed."


    if any_successful_deletions:
        flash(final_message, "success" if overall_success else "warning")

    return jsonify({
        "overall_success": overall_success and any_successful_deletions, 
        "message": final_message,
        "details": results_details
    }), 200