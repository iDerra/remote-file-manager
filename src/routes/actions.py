from flask import Blueprint, request, flash, redirect, url_for, current_app, abort
import os
import shutil
from werkzeug.utils import secure_filename
from utils.utilsHandler import is_safe_path

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