from flask import (Blueprint, send_from_directory, abort, current_app, send_file, 
                   after_this_request, request, flash, redirect, url_for)
import os
import shutil
import tempfile
from werkzeug.utils import secure_filename
from utils.utilsHandler import is_safe_path

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
    redirect_subpath_on_return = actual_fs_relative_path

    if not is_safe_path(FILE_SYSTEM_ROOT, actual_fs_relative_path):
        flash("Error: The destination route to upload is invalid or not allowed.", "danger")
        return redirect(url_for('browse.browse_directory')) 

    target_upload_path_abs = os.path.join(FILE_SYSTEM_ROOT, actual_fs_relative_path)
    if not os.path.isdir(target_upload_path_abs):
        flash(f"Error: The target directory for uploading '{actual_fs_relative_path if actual_fs_relative_path else 'Root'}' does not exist.", "danger")
        return redirect(url_for('browse.browse_directory', subpath=redirect_subpath_on_return))

    if 'files_to_upload' not in request.files:
        flash('No files were selected for upload.', 'warning')
        return redirect(url_for('browse.browse_directory', subpath=redirect_subpath_on_return))

    files = request.files.getlist('files_to_upload')
    if not files or all(not f.filename for f in files):
        flash('No valid file was selected for upload.', 'warning')
        return redirect(url_for('browse.browse_directory', subpath=redirect_subpath_on_return))

    files_uploaded_count = 0
    for file_storage in files:
        if not file_storage or not file_storage.filename:
            continue
            
        filename = secure_filename(file_storage.filename)
        if not filename:
            flash(f"The original filename '{file_storage.filename}' is invalid and was omitted.", "warning")
            continue

        destination_file_path = os.path.join(target_upload_path_abs, filename)
        
        if os.path.exists(destination_file_path):
            flash(f"The file '{filename}' already exists in the destination. It was not uploaded.", "warning")
            continue
        try:
            file_storage.save(destination_file_path)
            files_uploaded_count += 1
        except Exception as e:
            current_app.logger.error(f"Error saving file '{filename}': {e}")
            flash(f"Error saving the file '{filename}'.", "danger")
    
    if files_uploaded_count > 0:
        flash(f"{files_uploaded_count} file(s) uploaded successfully.", "success")
    elif not files:
        flash('No files were selected for upload.', 'warning')
        
    return redirect(url_for('browse.browse_directory', subpath=redirect_subpath_on_return))