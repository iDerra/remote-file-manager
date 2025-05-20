from flask import (Blueprint, send_from_directory, abort, current_app, send_file, 
                   after_this_request, request, flash, redirect, url_for, jsonify)
import os
import shutil
import tempfile
from werkzeug.utils import secure_filename
from utils.utilsHandler import is_safe_path
from urllib.parse import unquote

files_bp = Blueprint('files', __name__)

@files_bp.route('/download_file/<path:filepath>')
def download_single_file(filepath):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    
    if not is_safe_path(FILE_SYSTEM_ROOT, filepath):
        current_app.logger.warning(f"Unsecured download attempt (file): {filepath} path {FILE_SYSTEM_ROOT}")
        abort(404, "File not found or not allowed.")
        
    absolute_file_path = os.path.join(FILE_SYSTEM_ROOT, filepath)
    
    if not os.path.isfile(absolute_file_path):
        current_app.logger.warning(f"Download requested for a non-file: {absolute_file_path}")
        abort(404, "The requested resource is not a valid file or does not exist.")
        
    try:
        directory = os.path.dirname(absolute_file_path)
        filename = os.path.basename(absolute_file_path)
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        current_app.logger.error(f"File not found for send_from_directory: {absolute_file_path}")
        abort(404, "File not found.")
    except Exception as e:
        current_app.logger.error(f"Error downloading file {filepath}: {e}")
        abort(500, "Error processing download.")


@files_bp.route('/download_folder_zip/<path:folderpath>')
def download_folder_zip(folderpath):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']

    if not is_safe_path(FILE_SYSTEM_ROOT, folderpath):
        current_app.logger.warning(f"Unsecured download attempt (folder): {folderpath} path {FILE_SYSTEM_ROOT}")
        abort(404, "Folder not found or not allowed.")
        
    absolute_folder_path = os.path.join(FILE_SYSTEM_ROOT, folderpath)

    if not os.path.isdir(absolute_folder_path):
        current_app.logger.warning(f"ZIP download requested for a non-directory: {absolute_folder_path}")
        abort(404, "The requested resource is not a valid directory or does not exist.")
        
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        folder_name_for_zip_source = folderpath if folderpath else os.path.basename(FILE_SYSTEM_ROOT)
        folder_name_for_zip = secure_filename(os.path.basename(folder_name_for_zip_source))
        if not folder_name_for_zip:
             folder_name_for_zip = "archive"

        archive_basename = os.path.join(temp_dir, folder_name_for_zip)
        
        if folderpath:
            root_dir_for_archive = os.path.dirname(absolute_folder_path)
            base_dir_for_archive = os.path.basename(absolute_folder_path)
        else:
            root_dir_for_archive = os.path.dirname(FILE_SYSTEM_ROOT) 
            base_dir_for_archive = os.path.basename(FILE_SYSTEM_ROOT)

        zip_filename_full_path = shutil.make_archive(
            base_name=archive_basename,
            format='zip',
            root_dir=root_dir_for_archive,
            base_dir=base_dir_for_archive
        )

        zip_display_name = f"{folder_name_for_zip}.zip"
        
        @after_this_request
        def cleanup(response):
            try:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as error:
                current_app.logger.error(f"Error deleting temporary dir {temp_dir}: {error}")
            return response
            
        return send_file(zip_filename_full_path, download_name=zip_display_name, as_attachment=True)
        
    except Exception as e:
        current_app.logger.error(f"Error creating zip for folder {folderpath}: {e}")
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                current_app.logger.error(f"Error deleting temporary dir {temp_dir} after failure: {cleanup_error}")
        abort(500, "Error creating the folder file.")


@files_bp.route('/upload/<path:destination_folder_segment>', methods=['POST'])
def upload_files(destination_folder_segment):
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    
    actual_fs_relative_path = '' if destination_folder_segment == '__root__' else destination_folder_segment
    if not is_safe_path(FILE_SYSTEM_ROOT, actual_fs_relative_path):
        return jsonify({"success": False, "message": "Error: The destination route for the upload is invalid or not allowed."}), 400

    target_upload_path_abs = os.path.join(FILE_SYSTEM_ROOT, actual_fs_relative_path)
    if not os.path.isdir(target_upload_path_abs):
        return jsonify({"success": False, "message": f"Error: The target directory for the upload '{actual_fs_relative_path if actual_fs_relative_path else 'Root'}' does not exist."}), 400

    if 'files_to_upload' not in request.files:
        return jsonify({"success": False, "message": "No files were selected for upload."}), 400

    file_storage = request.files.get('files_to_upload') 

    if not file_storage or not file_storage.filename:
        return jsonify({"success": False, "message": "A valid file was not selected for upload."}), 400
            
    filename_original = file_storage.filename
    filename_secured = secure_filename(file_storage.filename)

    if not filename_secured:
        return jsonify({"success": False, "filename": filename_original, "message": f"The original filename '{filename_original}' is invalid and was omitted."}), 400

    destination_file_path = os.path.join(target_upload_path_abs, filename_secured)
    
    if os.path.exists(destination_file_path):
        return jsonify({"success": False, "filename": filename_secured, "message": f"The file '{filename_secured}' already exists in the destination. It was not uploaded."}), 409 
    
    try:
        file_storage.save(destination_file_path)
        return jsonify({"success": True, "filename": filename_secured, "message": "File uploaded successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Error saving file '{filename_secured}': {e}")
        return jsonify({"success": False, "filename": filename_secured, "message": f"Error saving the file '{filename_secured}'."}), 500


@files_bp.route('/download_multiple_files_zip', methods=['POST'])
def download_multiple_files_zip():
    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Invalid request."}), 400

    item_paths_quoted = data.get('items_to_download')
    user_zip_name = data.get('zip_name', 'archive.zip') 

    if not item_paths_quoted or not isinstance(item_paths_quoted, list):
        return jsonify({"success": False, "message": "No items specified for download or invalid format."}), 400
    
    if not user_zip_name.endswith('.zip'):
        user_zip_name += '.zip'
    
    zip_name_secured = secure_filename(user_zip_name)
    if not zip_name_secured:
        zip_name_secured = "downloaded_items.zip"

    staging_dir = None
    zip_creation_temp_dir = None

    try:
        staging_dir = tempfile.mkdtemp()
        zip_creation_temp_dir = tempfile.mkdtemp()
        
        items_processed_count = 0
        for item_path_q in item_paths_quoted:
            item_path_unquoted = unquote(item_path_q)

            if not is_safe_path(FILE_SYSTEM_ROOT, item_path_unquoted):
                current_app.logger.warning(f"Multi-download: Unsafe path skipped: {item_path_unquoted}")
                continue
            
            absolute_item_path = os.path.join(FILE_SYSTEM_ROOT, item_path_unquoted)

            if not os.path.exists(absolute_item_path):
                current_app.logger.warning(f"Multi-download: Item '{item_path_unquoted}' not found, skipped.")
                continue

            destination_path_in_staging = os.path.join(staging_dir, item_path_unquoted)
            destination_parent_dir_in_staging = os.path.dirname(destination_path_in_staging)
            if destination_parent_dir_in_staging and not os.path.exists(destination_parent_dir_in_staging):
                os.makedirs(destination_parent_dir_in_staging, exist_ok=True)

            if os.path.isfile(absolute_item_path):
                shutil.copy2(absolute_item_path, destination_path_in_staging)
                items_processed_count += 1
            elif os.path.isdir(absolute_item_path):
                shutil.copytree(absolute_item_path, destination_path_in_staging)
                items_processed_count += 1
            else:
                current_app.logger.warning(f"Multi-download: Item '{item_path_unquoted}' is not a recognized file or folder, skipped.")

        if items_processed_count == 0:
            if staging_dir and os.path.exists(staging_dir): shutil.rmtree(staging_dir)
            if zip_creation_temp_dir and os.path.exists(zip_creation_temp_dir): shutil.rmtree(zip_creation_temp_dir)
            return jsonify({"success": False, "message": "No valid files or folders were found to include in the ZIP."}), 400

        zip_file_base_name = os.path.join(zip_creation_temp_dir, os.path.splitext(zip_name_secured)[0])

        archive_path = shutil.make_archive(
            base_name=zip_file_base_name,
            format='zip',
            root_dir=staging_dir
        )

        @after_this_request
        def cleanup(response):
            nonlocal staging_dir, zip_creation_temp_dir
            try:
                if staging_dir and os.path.exists(staging_dir):
                    shutil.rmtree(staging_dir)
            except Exception as e:
                current_app.logger.error(f"Error cleaning up staging directory for multi-download: {e}")
            try:
                if zip_creation_temp_dir and os.path.exists(zip_creation_temp_dir):
                    shutil.rmtree(zip_creation_temp_dir)
            except Exception as e:
                current_app.logger.error(f"Error cleaning up ZIP creation directory for multi-download: {e}")
            return response
            
        return send_file(archive_path, download_name=zip_name_secured, as_attachment=True)

    except Exception as e:
        current_app.logger.error(f"Error creating multi-item ZIP '{zip_name_secured}': {e}")
        if staging_dir and os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        if zip_creation_temp_dir and os.path.exists(zip_creation_temp_dir):
            shutil.rmtree(zip_creation_temp_dir)
        return jsonify({"success": False, "message": "Server error while creating the ZIP file."}), 500