# Remote File Manager

A web-based file manager built with Flask that allows users to browse, upload and download items, create folders, move items, and delete items within a specified root directory.

## Features

* **Browse Files and Folders:** Navigate through the directory structure.
* **File & Folder Operations:**
    * Create new folders.
    * Upload individual files.
    * Upload entire folders (preserving structure).
    * Download individual files.
    * Download entire folders as a ZIP archive.
    * Move selected files/folders to a different location within the managed directory.
    * Delete selected files/folders.
* **Bulk Actions:**
    * Select multiple items (files/folders).
    * Download selected items as a single ZIP archive with an auto-generated name.
    * Move selected items simultaneously to a chosen destination folder via a modal interface.
    * Delete selected items simultaneously.
* **User Interface:**
    * Modern, responsive design.
    * Visual progress bar for uploads.
    * Modal dialog for selecting destination folders when moving items.
    * Drag-and-drop support for uploading files and folders.
    * Flash messages for operation feedback (success, warning, error).
    * Favicon for browser tab/bookmarks.
* **Details Displayed:**
    * Item name
    * Item size (calculates total size for folders)
    * Last modified date

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/iDerra/remote-file-manager
    cd remote-file-manager
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    The project uses Flask and python-dotenv.
    ```bash
    pip3 install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    * Create a `.env` file in the root directory of the project.
    * Add the following variables:
        ```env
        FILE_SYSTEM_ROOT=/path/to/your/manageable/folder
        SECRET_KEY=your_very_secret_random_key_here
        # FLASK_DEBUG=True    (Optional, for development)
        ```
        * Replace `/path/to/your/manageable/folder` with the absolute path to the directory you want this application to manage. **Important:** This directory will be fully accessible (read, write, delete) through the web interface.
        * Replace `your_very_secret_random_key_here` with a strong, random secret key.

## Running the Application

1.  **Activate the virtual environment (if not already active):**
    ```bash
    source .venv/bin/activate
    ```

2.  **Navigate to the `root` directory and run:**
    ```bash
    python3 src/main.py
    ```
    The application will start, and it will print the URL where it's accessible (usually `http://127.0.0.1:6061/` or `http://localhost:6061/` by default, based on your `config.py`).

## Usage

* Open the provided URL in your web browser.
* **Navigation:** Click on folder names to enter them. Use the "back" button to go up.
* **Create Folder:** Type a name in the "Create New Folder" section and click "Create Folder".
* **Upload Files:** Click "Choose files..." in the "Upload Files" section, select one or more files, and click "Upload Files". Or, drag and drop files onto this area.
* **Upload Folder:** Click "Choose folder..." in the "Upload Folder" section, select a folder, and click "Upload Folder". Or, drag and drop a folder onto this area.
* **Item Actions (per row):**
    * **Download:** Click the download icon (or ZIP icon for folders).
    * **Delete:** Click the trash icon (a confirmation will be asked).
    * **Move:** Click the "Move" icon/button. A modal will appear allowing you to select the destination folder from a tree view.
* **Bulk Actions (after selecting items using checkboxes):**
    * **Select/Deselect All:** Use the checkbox in the table header.
    * **Download Selected as ZIP:** Generates a ZIP file of all selected items (preserving folder structure) with an auto-generated name.
    * **Move Selected:** Opens the move modal to select a common destination for all selected items.
    * **Delete Selected:** Deletes all selected items (a confirmation will be asked).

## Key Technologies

* **Backend:** Python, Flask
* **Frontend:** HTML, CSS, JavaScript (vanilla)
* **Icons:** Font Awesome

## To-Do / Potential Improvements

* User authentication and authorization.
* More robust error handling and logging for edge cases.
* Option to rename files/folders.
* Option to view/edit text files.
* Image previews.
* Search functionality.
* More advanced responsive design for very small screens (e.g., collapsing action forms).


## License

This project is licensed under the **MIT** license.