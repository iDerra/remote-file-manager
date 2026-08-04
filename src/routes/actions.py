from flask import Blueprint, request, flash, redirect, url_for, current_app, jsonify
import os
from urllib.parse import unquote

# Importamos las funciones aisladas desde nuestro módulo de operaciones
from utils.file_ops import (
    process_multiple_deletions, 
    process_multiple_moves,
    process_create_folder, 
    process_delete_item, 
    process_move_item
)

actions_bp = Blueprint('actions', __name__)

@actions_bp.route('/create_folder/<path:parent_folder_segment>', methods=['POST'])
def create_folder(parent_folder_segment):
    parent_folder_segment = unquote(parent_folder_segment)
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    new_folder_name_form = request.form.get('new_folder_name')
    
    success, message = process_create_folder(FILE_SYSTEM_ROOT, parent_folder_segment, new_folder_name_form)
    
    flash(message, "success" if success else "danger")
    redirect_subpath = '' if parent_folder_segment == '__root__' else parent_folder_segment
    return redirect(url_for('browse.browse_directory', subpath=redirect_subpath))


@actions_bp.route('/delete_item/<path:item_to_delete_segment>', methods=['POST'])
def delete_item(item_to_delete_segment):
    item_to_delete_segment = unquote(item_to_delete_segment)
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    
    success, message = process_delete_item(FILE_SYSTEM_ROOT, item_to_delete_segment)
    
    flash(message, "success" if success else "danger")
    
    # Manejamos de forma segura el retorno a la carpeta padre
    if item_to_delete_segment == '__root__':
        parent_directory_segment = ''
    else:
        parent_directory_segment = os.path.dirname(item_to_delete_segment)
        
    return redirect(url_for('browse.browse_directory', subpath=parent_directory_segment))


@actions_bp.route('/move_item/<path:item_to_move_segment>', methods=['POST'])
def move_item(item_to_move_segment):
    item_to_move_segment = unquote(item_to_move_segment)
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    destination_relative_path_form = request.form.get('destination_path', '').strip()
    
    success, message = process_move_item(FILE_SYSTEM_ROOT, item_to_move_segment, destination_relative_path_form)
    
    flash(message, "success" if success else "danger")
    
    if item_to_move_segment == '__root__':
        current_item_parent_dir = ''
    else:
        current_item_parent_dir = os.path.dirname(item_to_move_segment)
        
    return redirect(url_for('browse.browse_directory', subpath=current_item_parent_dir))


@actions_bp.route('/delete_multiple_items', methods=['POST'])
def delete_multiple_items():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()
    
    if not data or 'items_to_delete' not in data:
        return jsonify({"overall_success": False, "message": "No items were specified for removal.", "details": []}), 400
        
    items_to_delete_segments_quoted = data['items_to_delete']
    
    if not isinstance(items_to_delete_segments_quoted, list):
        return jsonify({"overall_success": False, "message": "Invalid format.", "details": []}), 400
        
    items_unquoted = [unquote(item) for item in items_to_delete_segments_quoted]
    
    overall_success_flag, any_successful_deletions, results_details = process_multiple_deletions(FILE_SYSTEM_ROOT, items_unquoted)
    
    final_json_overall_success = overall_success_flag and any_successful_deletions
    successful_delete_count = sum(1 for detail in results_details if detail["success"])
    total_attempted_count = len(items_to_delete_segments_quoted)
    
    if successful_delete_count == total_attempted_count and total_attempted_count > 0:
        final_message = f"All {successful_delete_count} selected item(s) were successfully deleted."
        flash_category = "success"
    elif successful_delete_count > 0:
        final_message = f"{successful_delete_count} of {total_attempted_count} item(s) deleted successfully. Some failed."
        flash_category = "warning"
    elif total_attempted_count > 0:
        final_message = "None of the selected items could be deleted."
        flash_category = "danger"
    else:
        final_message = "No valid items were selected for deletion."
        flash_category = "info"
        
    flash(final_message, flash_category)
    
    return jsonify({
        "overall_success": final_json_overall_success,
        "message": final_message,
        "details": results_details
    }), 200


@actions_bp.route('/move_multiple_items', methods=['POST'])
def move_multiple_items():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()
    
    if not data:
        return jsonify({"overall_success": False, "message": "Invalid request data.", "details": []}), 400
        
    items_to_move_quoted = data.get('items_to_move')
    destination_relative_path_form = data.get('destination_path', '')
    
    if not items_to_move_quoted or not isinstance(items_to_move_quoted, list):
        return jsonify({"overall_success": False, "message": "No items specified.", "details": []}), 400
        
    normalized_destination_relative_path = destination_relative_path_form.strip().lstrip('/')
    
    items_unquoted = [unquote(item) for item in items_to_move_quoted]
    
    overall_success_flag, any_successful_moves, results_details = process_multiple_moves(
        FILE_SYSTEM_ROOT, items_unquoted, normalized_destination_relative_path
    )
    
    final_json_overall_success = overall_success_flag and any_successful_moves
    successful_move_count = sum(1 for detail in results_details if detail["success"])
    total_attempted_count = len(items_to_move_quoted)
    
    if successful_move_count == total_attempted_count and total_attempted_count > 0:
        final_message = f"All {successful_move_count} selected item(s) were successfully moved."
        flash_category = "success"
    elif successful_move_count > 0:
        final_message = f"{successful_move_count} of {total_attempted_count} item(s) moved successfully. Some failed."
        flash_category = "warning"
    elif total_attempted_count > 0 :
        final_message = "None of the selected items could be moved."
        flash_category = "danger"
    else:
        final_message = "No valid items were selected for move operation."
        flash_category = "info"
        
    flash(final_message, flash_category)
    
    return jsonify({
        "overall_success": final_json_overall_success,
        "message": final_message,
        "details": results_details
    }), 200