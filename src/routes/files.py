from flask import (Blueprint, send_from_directory, abort, current_app, send_file, 
                   after_this_request, request, flash, redirect, url_for, jsonify)
import os
import shutil
import tempfile
import uuid
from werkzeug.utils import secure_filename
from utils.utilsHandler import is_safe_path
from urllib.parse import unquote


files_bp = Blueprint('files', __name__)

TEMP_ZIP_FOLDER_NAME = '.tmp_zips'

def get_temp_zip_dir_abs():
    """
    Gets the absolute path to the temporary ZIP storage directory and creates it if it doesn't exist.

    :returns: The absolute path to the temporary ZIP directory.
    :rtype: str
    """

    temp_zip_dir = os.path.join(current_app.static_folder, TEMP_ZIP_FOLDER_NAME)
    os.makedirs(temp_zip_dir, exist_ok=True)
    return temp_zip_dir


@files_bp.route('/download_file/<path:filepath>')
def download_single_file(filepath):
    """
    Handles the download of a single specified file.

    It first checks if the requested `filepath` is safe and within the configured
    FILE_SYSTEM_ROOT. If the path is valid and points to an existing file,
    it sends the file to the client as an attachment.

    :param filepath: The relative path from the FILE_SYSTEM_ROOT to the file
                     to be downloaded.
    :type filepath: str
    :returns: A Flask response object that sends the file to the client,
              or an HTTP error (404 or 500) if the file is not found,
              the path is unsafe, or an error occurs.
    :rtype: werkzeug.wrappers.response.Response
    """

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
    """
    Handles the download of a specified folder as a ZIP archive.

    The function first validates the safety of the `folderpath`. If valid and
    the path points to an existing directory, it creates a temporary ZIP archive
    of the folder's contents. This ZIP file is then sent to the client as an
    attachment. A cleanup function is registered using `@after_this_request`
    to delete the temporary directory used for ZIP creation after the response
    has been sent.

    :param folderpath: The relative path from the FILE_SYSTEM_ROOT to the folder
                       to be downloaded as a ZIP. Can be an empty string to
                       indicate the root directory itself.
    :type folderpath: str
    :returns: A Flask response object that sends the ZIP file to the client,
              or an HTTP error (404 or 500) if the folder is not found,
              the path is unsafe, or an error occurs during ZIP creation.
    :rtype: werkzeug.wrappers.response.Response
    """

    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']

    if not is_safe_path(FILE_SYSTEM_ROOT, folderpath):
        current_app.logger.warning(f"Unsecured download attempt (folder): {folderpath} path {FILE_SYSTEM_ROOT}")
        abort(404, "Folder not found or not allowed.")
        
    absolute_folder_path = os.path.join(FILE_SYSTEM_ROOT, folderpath)

    if not os.path.isdir(absolute_folder_path):
        current_app.logger.warning(f"ZIP download requested for a non-directory: {absolute_folder_path}")
        abort(404, "The requested resource is not a valid directory or does not exist.")
        
    temp_dir_for_zip_creation = None
    try:
        temp_dir_for_zip_creation = tempfile.mkdtemp()
        
        folder_name_for_zip_source = os.path.basename(folderpath) if folderpath else os.path.basename(FILE_SYSTEM_ROOT)
        zip_display_name_base = secure_filename(folder_name_for_zip_source)
        if not zip_display_name_base:
             zip_display_name_base = "archive"
        
        archive_basename_in_temp_dir = os.path.join(temp_dir_for_zip_creation, zip_display_name_base)
        
        if folderpath:
            root_dir_for_archive = os.path.dirname(absolute_folder_path)
            base_dir_for_archive = os.path.basename(absolute_folder_path)
        else:
            root_dir_for_archive = os.path.dirname(FILE_SYSTEM_ROOT) 
            base_dir_for_archive = os.path.basename(FILE_SYSTEM_ROOT)
            if not base_dir_for_archive:
                 base_dir_for_archive = "filesystem_root"

        zip_filename_full_path = shutil.make_archive(
            base_name=archive_basename_in_temp_dir,
            format='zip',
            root_dir=root_dir_for_archive,
            base_dir=base_dir_for_archive
        )

        final_zip_display_name = f"{zip_display_name_base}.zip"
        response = send_file(zip_filename_full_path, download_name=final_zip_display_name, as_attachment=True)

        @after_this_request 
        def cleanup_single_folder_zip(response_from_send_file):
            try:
                if temp_dir_for_zip_creation and os.path.exists(temp_dir_for_zip_creation):
                    shutil.rmtree(temp_dir_for_zip_creation)
                    current_app.logger.info(f"Temporary dir for single folder zip cleaned: {temp_dir_for_zip_creation}")
            except Exception as error:
                current_app.logger.error(f"Error deleting temporary dir for single folder zip {temp_dir_for_zip_creation}: {error}")
            return response_from_send_file
            
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error creating zip for folder {folderpath}: {e}")
        if temp_dir_for_zip_creation and os.path.exists(temp_dir_for_zip_creation):
            try:
                shutil.rmtree(temp_dir_for_zip_creation)
            except Exception as cleanup_error:
                current_app.logger.error(f"Error deleting temporary dir {temp_dir_for_zip_creation} after failure: {cleanup_error}")
        abort(500, "Error creating the folder ZIP file.")


@files_bp.route('/upload/<path:destination_folder_segment>', methods=['POST'])
def upload_files(destination_folder_segment):
    """
    Handles file uploads, including individual files and files within a folder structure.

    It receives the base destination folder segment from the URL. The actual files
    are sent as multipart/form-data. For folder uploads, the client (JavaScript)
    is expected to send the `relative_path` of each file within the uploaded folder
    structure in the form data.

    The function performs several checks:
    - Validates the safety of the base destination path.
    - Ensures files are part of the request.
    - Sanitizes the uploaded file/folder names and reconstructs the target path.
    - Validates the safety of the final calculated path for each item.
    - Creates necessary subdirectories on the server.
    - Checks for existing files to prevent overwriting (returns 409 Conflict).

    Returns a JSON response for each file indicating success or failure.

    :param destination_folder_segment: The relative path segment from the file system root
                                     to the base directory where files should be uploaded.
                                     '__root__' indicates the base file system root.
    :type destination_folder_segment: str
    :returns: A Flask JSON response detailing the outcome of the upload for the specific file.
              Possible statuses:
              - 200/201: Success
              - 400: Bad request (e.g., no file, invalid name)
              - 403: Forbidden (unsafe path)
              - 409: Conflict (file already exists)
              - 500: Server error
    :rtype: tuple[werkzeug.wrappers.response.Response, int]
    """

    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    
    base_target_relative_path = '' if destination_folder_segment == '__root__' else destination_folder_segment

    if not is_safe_path(FILE_SYSTEM_ROOT, base_target_relative_path):
        return jsonify({"success": False, "message": "Error: The base destination for upload is invalid or not allowed."}), 403

    if 'files_to_upload' not in request.files:
        return jsonify({"success": False, "message": "No file part in the request."}), 400

    file_storage = request.files.get('files_to_upload')
    if not file_storage or not file_storage.filename:
        return jsonify({"success": False, "message": "No file selected for upload."}), 400
            
    item_relative_path_in_upload = request.form.get('relative_path', file_storage.filename)
    sanitized_item_path_parts = []
    for part in item_relative_path_in_upload.replace('\\', '/').split('/'):
        secured_part = secure_filename(part)
        if secured_part:
            sanitized_item_path_parts.append(secured_part)
    
    if not sanitized_item_path_parts:
        return jsonify({"success": False, "filename": file_storage.filename, "message": "Invalid file or folder name after sanitization."}), 400
    
    filename_secured = sanitized_item_path_parts[-1]
    sub_directories_in_upload = sanitized_item_path_parts[:-1]

    final_item_relative_dir_on_server = base_target_relative_path
    if sub_directories_in_upload:
        final_item_relative_dir_on_server = os.path.join(base_target_relative_path, *sub_directories_in_upload)

    if not is_safe_path(FILE_SYSTEM_ROOT, final_item_relative_dir_on_server):
        return jsonify({"success": False, "filename": file_storage.filename, "message": f"Error: Calculated path '{final_item_relative_dir_on_server}' is invalid or not allowed."}), 403

    target_item_directory_abs = os.path.join(FILE_SYSTEM_ROOT, final_item_relative_dir_on_server)

    try:
        os.makedirs(target_item_directory_abs, exist_ok=True)
    except OSError as e:
        current_app.logger.error(f"Error creating directory '{target_item_directory_abs}': {e}")
        return jsonify({"success": False, "filename": filename_secured, "message": f"Error creating target directory on server: {e}"}), 500

    destination_file_path_abs = os.path.join(target_item_directory_abs, filename_secured)
    
    if os.path.exists(destination_file_path_abs):
        return jsonify({"success": False, "filename": item_relative_path_in_upload, "message": "File already exists at the destination. Skipped."}), 409 
    
    try:
        file_storage.save(destination_file_path_abs)
        return jsonify({"success": True, "filename": item_relative_path_in_upload, "message": "File uploaded successfully."}), 200
    except Exception as e:
        current_app.logger.error(f"Error saving file '{item_relative_path_in_upload}' to '{destination_file_path_abs}': {e}")
        return jsonify({"success": False, "filename": item_relative_path_in_upload, "message": f"Error saving the file on server."}), 500


@files_bp.route('/api/prepare_multiple_files_zip', methods=['POST'])
def prepare_multiple_files_zip():
    """
    API endpoint to prepare a ZIP archive containing multiple specified files and folders.

    Expects a JSON payload with:
    - `items_to_download` (list): A list of URL-encoded relative paths of items to include.
    - `zip_name` (str, optional): A suggested name for the output ZIP file.

    The process involves:
    1. Validating input and sanitizing the suggested ZIP name.
    2. Creating temporary staging and ZIP creation directories.
    3. For each specified item:
        - Decoding and validating its path.
        - Copying the item (file or folder tree) into the staging directory,
          maintaining its relative path structure.
    4. If any valid items were processed, creating a ZIP archive from the staging directory.
    5. Moving the created ZIP to a designated temporary ZIP storage area (within static folder).
    6. Returning a JSON response with a download URL for the prepared ZIP.

    Temporary directories are cleaned up in a finally block. The actual ZIP file in
    the static temporary storage is cleaned up by the `cleanup_prepared_zip`
    `after_request` handler when it's downloaded via `download_prepared_zip_route`.

    :returns: A Flask JSON response:
              - On success (200): `{"success": True, "download_url": "...", "zip_display_name": "..."}`
              - On failure (400 or 500): `{"success": False, "message": "Error details"}`
    :rtype: tuple[werkzeug.wrappers.response.Response, int]
    """

    FILE_SYSTEM_ROOT = current_app.config['FILE_SYSTEM_ROOT']
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Invalid request."}), 400

    item_paths_quoted = data.get('items_to_download')
    user_zip_name_suggestion = data.get('zip_name', 'archive.zip')

    if not item_paths_quoted or not isinstance(item_paths_quoted, list):
        return jsonify({"success": False, "message": "No items specified for download or invalid format."}), 400
    
    if not user_zip_name_suggestion.endswith('.zip'):
        user_zip_name_suggestion += '.zip'
    
    zip_display_name = secure_filename(user_zip_name_suggestion)
    if not zip_display_name:
        zip_display_name = "downloaded_files.zip"

    staging_dir_for_zip_contents = None
    zip_creation_temp_dir = None
    
    temp_zip_storage_abs = get_temp_zip_dir_abs()
    unique_zip_filename_on_server = f"{uuid.uuid4()}_{zip_display_name}"
    final_zip_path_on_server_abs = os.path.join(temp_zip_storage_abs, unique_zip_filename_on_server)

    try:
        staging_dir_for_zip_contents = tempfile.mkdtemp() 
        zip_creation_temp_dir = tempfile.mkdtemp()
        
        items_processed_count = 0
        for item_path_q in item_paths_quoted:
            item_path_unquoted = unquote(item_path_q)

            if not is_safe_path(FILE_SYSTEM_ROOT, item_path_unquoted):
                current_app.logger.warning(f"Multi-download prep: Unsafe path skipped: {item_path_unquoted}")
                continue
            
            absolute_item_path = os.path.join(FILE_SYSTEM_ROOT, item_path_unquoted)

            if not os.path.exists(absolute_item_path):
                current_app.logger.warning(f"Multi-download prep: Item '{item_path_unquoted}' not found, skipped.")
                continue

            destination_path_in_staging = os.path.join(staging_dir_for_zip_contents, item_path_unquoted)
            destination_parent_dir_in_staging = os.path.dirname(destination_path_in_staging)
            if destination_parent_dir_in_staging and not os.path.exists(destination_parent_dir_in_staging):
                os.makedirs(destination_parent_dir_in_staging, exist_ok=True)

            if os.path.isfile(absolute_item_path):
                shutil.copy2(absolute_item_path, destination_path_in_staging)
                items_processed_count += 1
            elif os.path.isdir(absolute_item_path):
                shutil.copytree(absolute_item_path, destination_path_in_staging, dirs_exist_ok=True)
                items_processed_count += 1
            else:
                current_app.logger.warning(f"Multi-download prep: Item '{item_path_unquoted}' is not a file or folder, skipped.")

        if items_processed_count == 0:
            flash("No valid files or folders were found to include in the ZIP.", "warning")
            return jsonify({"success": False, "message": "No valid files or folders were found to include in the ZIP."}), 400

        archive_base_name_in_temp = os.path.join(zip_creation_temp_dir, os.path.splitext(zip_display_name)[0])
        
        created_archive_path_abs = shutil.make_archive(
            base_name=archive_base_name_in_temp,
            format='zip',
            root_dir=staging_dir_for_zip_contents
        )
        
        shutil.move(created_archive_path_abs, final_zip_path_on_server_abs)

        download_url_for_client = url_for('files.download_prepared_zip_route', 
                                          zip_file_on_server=unique_zip_filename_on_server, 
                                          _external=False)

        flash(f"ZIP file '{zip_display_name}' is ready. Your download will start automatically.", "success")
        return jsonify({
            "success": True,
            "download_url": download_url_for_client,
            "zip_display_name": zip_display_name
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error creating multi-item ZIP for '{zip_display_name}': {e}")
        flash("Server error while creating the ZIP file. Please try again.", "danger")
        return jsonify({"success": False, "message": "Server error while creating the ZIP file."}), 500
    finally:
        if staging_dir_for_zip_contents and os.path.exists(staging_dir_for_zip_contents):
            shutil.rmtree(staging_dir_for_zip_contents)
        if zip_creation_temp_dir and os.path.exists(zip_creation_temp_dir):
            shutil.rmtree(zip_creation_temp_dir)
            

@files_bp.route('/download_prepared_zip/<path:zip_file_on_server>')
def download_prepared_zip_route(zip_file_on_server):
    """
    Serves a previously prepared ZIP file from the temporary ZIP storage.

    This route is typically called by the client after
    `/api/prepare_multiple_files_zip` returns a success response with a
    download URL pointing here. The `zip_file_on_server` is the unique,
    server-generated filename of the ZIP.

    The actual cleanup of the ZIP file from the server's temporary storage
    is handled by the `cleanup_prepared_zip` `after_request` handler.

    :param zip_file_on_server: The unique filename (basename) of the ZIP file
                               as it exists in the temporary ZIP storage directory.
    :type zip_file_on_server: str
    :returns: A Flask response object that sends the ZIP file to the client,
              or redirects to the browse view with an error/warning flash
              if the file is not found or an error occurs.
    :rtype: werkzeug.wrappers.response.Response
    """

    temp_zip_dir_abs = get_temp_zip_dir_abs()
    safe_zip_filename = secure_filename(os.path.basename(zip_file_on_server))
    file_path_abs = os.path.join(temp_zip_dir_abs, safe_zip_filename)

    if not os.path.exists(file_path_abs) or not os.path.isfile(file_path_abs):
        current_app.logger.error(f"Prepared ZIP not found for download: {file_path_abs}")
        flash("The requested ZIP file was not found or has expired. Please try preparing it again.", "warning")
        return redirect(url_for('browse.browse_directory')) 
    
    try:
        return send_from_directory(temp_zip_dir_abs, safe_zip_filename, as_attachment=True)
    except Exception as e:
        current_app.logger.error(f"Error sending prepared ZIP {safe_zip_filename}: {e}")
        flash("An error occurred while trying to send the ZIP file.", "danger")
        return redirect(url_for('browse.browse_directory'))


@files_bp.after_request
def cleanup_prepared_zip(response):
    """
    Cleans up (deletes) a temporary ZIP file after it has been successfully sent.

    This function is registered to run after every request within the `files_bp` blueprint.
    It specifically targets requests to the 'files.download_prepared_zip_route' endpoint.
    If the request was to download a prepared ZIP and the response status indicates
    a successful file transmission (e.g., 200 OK), it attempts to delete the
    corresponding ZIP file from the temporary storage.

    :param response: The response object that is about to be sent to the client.
    :type response: werkzeug.wrappers.response.Response
    :returns: The (potentially modified) response object.
    :rtype: werkzeug.wrappers.response.Response
    """

    if request.endpoint == 'files.download_prepared_zip_route':
        if 200 <= response.status_code < 300:
            if 'zip_file_on_server' in request.view_args:
                zip_file_to_delete_basename = secure_filename(os.path.basename(request.view_args['zip_file_on_server']))
                temp_zip_dir = get_temp_zip_dir_abs()
                file_path_to_delete_abs = os.path.join(temp_zip_dir, zip_file_to_delete_basename)
                
                if os.path.exists(file_path_to_delete_abs):
                    try:
                        os.remove(file_path_to_delete_abs)
                        current_app.logger.info(f"Temporary ZIP deleted: {file_path_to_delete_abs}")
                    except Exception as e:
                        current_app.logger.error(f"Error deleting temporary ZIP {file_path_to_delete_abs}: {e}")
                else:
                    current_app.logger.warning(f"Temporary ZIP for cleanup not found (already deleted or moved?): {file_path_to_delete_abs}")
            else:
                current_app.logger.warning("Cleanup function called for download_prepared_zip_route but 'zip_file_on_server' not in view_args.")
    return response