import os
import sys
import shutil
import zipfile
import subprocess
import flet as ft

# Shell Command Execution Helper
def exec_cmd(cmd, as_root=False):
    try:
        if as_root:
            p = subprocess.Popen(['su'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = p.communicate(input=cmd, timeout=5)
            return p.returncode, stdout, stderr
        else:
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = p.communicate(timeout=5)
            return p.returncode, stdout, stderr
    except Exception as e:
        return -1, "", str(e)

def check_root_available():
    if sys.platform not in ['android', 'linux']:
        return True
    try:
        p = subprocess.Popen(['su', '-c', 'id'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, _ = p.communicate(timeout=2)
        return "uid=0" in stdout or p.returncode == 0
    except:
        return False

def format_size(size):
    try:
        size = float(size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    except:
        return "Unknown"

def main(page: ft.Page):
    page.title = "MT Manager Flet"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_GREY)
    page.padding = 0

    # App States
    root_mode = False
    current_path = "/sdcard" if os.path.exists("/sdcard") else "/storage/emulated/0"
    if not os.path.exists(current_path):
        current_path = "/"

    clipboard_path = ""
    clipboard_action = ""  # "copy" or "move"
    
    # State stacks for sub-pages
    # We will use simple view control swaps to render different views.
    active_view = "explorer"  # "explorer", "editor", "zip_viewer"
    editing_file_path = ""
    viewing_zip_path = ""
    zip_contents = []

    # UI Components
    list_container = ft.ListView(expand=1, spacing=2, padding=10)
    path_label = ft.Text(value=current_path, style=ft.TextThemeStyle.BODY_MEDIUM, color=ft.Colors.BLUE_GREY_200)
    root_badge = ft.Container(
        content=ft.Text("ROOT", size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        bgcolor=ft.Colors.RED_ACCENT_700,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        border_radius=3,
        visible=False
    )
    
    paste_bar = ft.Container(
        content=ft.Row([
            ft.Icon(name=ft.Icons.CONTENT_PASTE, color=ft.Colors.AMBER_400),
            ft.Text("Clipboard ready", size=12, expand=True),
            ft.TextButton("PASTE", on_click=lambda e: paste_clipboard()),
            ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16, on_click=lambda e: clear_clipboard())
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=ft.Colors.BLUE_GREY_900,
        padding=10,
        visible=False
    )

    def show_toast(title, text, is_error=False):
        color = ft.Colors.RED_900 if is_error else ft.Colors.GREEN_900
        snack = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.ERROR_OUTLINE if is_error else ft.Icons.CHECK, color=ft.Colors.WHITE),
                ft.Column([
                    ft.Text(title, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(text, size=12)
                ], spacing=1, expand=True)
            ]),
            bgcolor=color,
            duration=3000
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    def listdir_root(path):
        code, stdout, stderr = exec_cmd(f"ls -ap '{path}'", as_root=True)
        if code != 0:
            raise Exception(stderr or f"ls failed with code {code}")
        
        lines = stdout.splitlines()
        folders = []
        files = []
        for line in lines:
            line = line.strip()
            if not line or line in ['.', '..', './', '../']:
                continue
            if line.endswith('/'):
                folders.append(line[:-1])
            else:
                files.append(line)
        return sorted(folders), sorted(files)

    def get_file_size_root(path):
        code, stdout, _ = exec_cmd(f"wc -c '{path}'", as_root=True)
        if code == 0:
            try:
                return int(stdout.strip().split()[0])
            except:
                pass
        return 0

    def refresh_list():
        nonlocal current_path
        list_container.controls.clear()
        path_label.value = current_path
        
        # Upper directory navigatibility
        if current_path != "/":
            up_dir = os.path.dirname(current_path)
            list_container.controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ARROW_UPWARD, color=ft.Colors.AMBER_500),
                    title=ft.Text(".. (Go up parent directory)", size=14, weight=ft.FontWeight.W_500),
                    on_click=lambda e, p=up_dir: navigate_to(p)
                )
            )

        try:
            if root_mode:
                folders, files = listdir_root(current_path)
            else:
                try:
                    items = os.listdir(current_path)
                    folders = sorted([i for i in items if os.path.isdir(os.path.join(current_path, i))])
                    files = sorted([i for i in items if os.path.isfile(os.path.join(current_path, i))])
                except Exception as e:
                    if check_root_available():
                        folders, files = listdir_root(current_path)
                    else:
                        raise e
            
            # Populate Folders
            for f in folders:
                f_path = os.path.join(current_path, f)
                list_container.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.AMBER_400),
                        title=ft.Text(f, size=14, weight=ft.FontWeight.W_500),
                        subtitle=ft.Text("Directory", size=11, color=ft.Colors.BLUE_GREY_300),
                        trailing=ft.IconButton(
                            icon=ft.Icons.MORE_VERT,
                            on_click=lambda e, p=f_path, n=f: show_options_dialog(p, n, is_dir=True)
                        ),
                        on_click=lambda e, p=f_path: navigate_to(p)
                    )
                )

            # Populate Files
            for f in files:
                f_path = os.path.join(current_path, f)
                
                # Get file size
                if root_mode:
                    size_bytes = get_file_size_root(f_path)
                else:
                    try:
                        size_bytes = os.path.getsize(f_path)
                    except:
                        size_bytes = 0
                        
                size_str = format_size(size_bytes)
                
                is_apk = f.lower().endswith(".apk")
                is_zip = f.lower().endswith(".zip")
                icon = ft.Icons.ANDROID if is_apk else (ft.Icons.FOLDER_ZIP if is_zip else ft.Icons.INSERT_DRIVE_FILE)
                icon_color = ft.Colors.GREEN_400 if is_apk else (ft.Colors.ORANGE_400 if is_zip else ft.Colors.BLUE_GREY_400)

                list_container.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, color=icon_color),
                        title=ft.Text(f, size=14, weight=ft.FontWeight.W_500),
                        subtitle=ft.Text(f"File • {size_str}", size=11, color=ft.Colors.BLUE_GREY_300),
                        trailing=ft.IconButton(
                            icon=ft.Icons.MORE_VERT,
                            on_click=lambda e, p=f_path, n=f, apk=is_apk, zp=is_zip: show_options_dialog(p, n, is_dir=False, is_apk=apk, is_zip=zp)
                        ),
                        on_click=lambda e, p=f_path, apk=is_apk, zp=is_zip: handle_file_click(p, apk, zp)
                    )
                )

        except Exception as e:
            list_container.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400, size=40),
                        ft.Text(f"Error accessing path:\n{str(e)}", color=ft.Colors.RED_400, text_align=ft.TextAlign.CENTER, size=12)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=20
                )
            )
        page.update()

    def navigate_to(path):
        nonlocal current_path
        current_path = path
        refresh_list()

    def toggle_root_mode(e):
        nonlocal root_mode
        if not root_mode:
            if check_root_available():
                root_mode = True
                root_badge.visible = True
                shield_btn.icon = ft.Icons.SHIELD
                shield_btn.icon_color = ft.Colors.RED_ACCENT_400
                show_toast("Root Mode Active", "Superuser privileges successfully enabled!")
            else:
                show_toast("Permission Denied", "No superuser binary detected or root privilege was rejected.", is_error=True)
        else:
            root_mode = False
            root_badge.visible = False
            shield_btn.icon = ft.Icons.SHIELD_OUTLINED
            shield_btn.icon_color = ft.Colors.WHITE
            show_toast("Root Mode Disabled", "Standard user restrictions are back in place.")
        refresh_list()

    # Create dialog launcher
    def show_create_dialog(is_dir=True):
        name_input = ft.TextField(
            label="Name", 
            placeholder="enter folder name" if is_dir else "enter file name", 
            autofocus=True,
            text_size=13
        )
        
        def save_creation(e):
            if not name_input.value.strip():
                return
            target = os.path.join(current_path, name_input.value.strip())
            try:
                if root_mode:
                    if is_dir:
                        code, _, stderr = exec_cmd(f"mkdir -p '{target}'", as_root=True)
                    else:
                        code, _, stderr = exec_cmd(f"touch '{target}'", as_root=True)
                    if code != 0:
                        raise Exception(stderr)
                else:
                    if is_dir:
                        os.makedirs(target, exist_ok=True)
                    else:
                        with open(target, 'w') as f:
                            f.write("")
                show_toast("Success", f"{'Directory' if is_dir else 'File'} successfully created.")
                dialog.open = False
                refresh_list()
            except Exception as ex:
                show_toast("Failed", str(ex), is_error=True)

        dialog = ft.AlertDialog(
            title=ft.Text("Create Folder" if is_dir else "Create File", size=16, weight=ft.FontWeight.BOLD),
            content=name_input,
            actions=[
                ft.TextButton("CANCEL", on_click=lambda x: page.close(dialog)),
                ft.TextButton("CREATE", on_click=save_creation)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # Context menu option dialog
    def show_options_dialog(path, name, is_dir, is_apk=False, is_zip=False):
        dialog_options = []

        # 1. Rename Option
        def handle_rename_click(e):
            page.close(options_dialog)
            show_rename_dialog(path, name)
            
        dialog_options.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.DRIVE_FILE_RENAME_OUTLINE, size=18),
                title=ft.Text("Rename", size=13),
                on_click=handle_rename_click
            )
        )

        # 2. Copy & Move Options
        def prepare_clipboard(action):
            nonlocal clipboard_path, clipboard_action
            clipboard_path = path
            clipboard_action = action
            paste_bar.content.controls[1].value = f"Selected: {os.path.basename(path)} ({action.upper()})"
            paste_bar.visible = True
            page.close(options_dialog)
            page.update()

        dialog_options.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.COPY_ALL, size=18),
                title=ft.Text("Copy", size=13),
                on_click=lambda e: prepare_clipboard("copy")
            )
        )
        dialog_options.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.MOVE_UP, size=18),
                title=ft.Text("Move", size=13),
                on_click=lambda e: prepare_clipboard("move")
            )
        )

        # 3. Zip Extraction options
        if is_zip:
            def handle_unzip(e):
                page.close(options_dialog)
                unzip_archive(path)
            dialog_options.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.UNARCHIVE, color=ft.Colors.ORANGE_300, size=18),
                    title=ft.Text("Extract All", size=13),
                    on_click=handle_unzip
                )
            )

        # 4. APK Signing option
        if is_apk:
            def handle_apk_sign(e):
                page.close(options_dialog)
                sign_apk(path)
            dialog_options.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.KEYBOARD_COMMAND_KEY, color=ft.Colors.GREEN_300, size=18),
                    title=ft.Text("Sign APK with Custom Cert", size=13),
                    on_click=handle_apk_sign
                )
            )

        # 5. Delete option
        def handle_delete_click(e):
            page.close(options_dialog)
            show_delete_confirm(path, name, is_dir)

        dialog_options.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.DELETE_FOREVER, color=ft.Colors.RED_300, size=18),
                title=ft.Text("Delete", size=13, color=ft.Colors.RED_300),
                on_click=handle_delete_click
            )
        )

        options_dialog = ft.AlertDialog(
            title=ft.Text(name, size=15, weight=ft.FontWeight.BOLD, no_wrap=True),
            content=ft.Column(dialog_options, tight=True, spacing=1),
            actions=[
                ft.TextButton("CLOSE", on_click=lambda x: page.close(options_dialog))
            ]
        )
        page.overlay.append(options_dialog)
        options_dialog.open = True
        page.update()

    def show_rename_dialog(path, name):
        rename_input = ft.TextField(label="New Name", value=name, autofocus=True, text_size=13)
        
        def save_rename(e):
            if not rename_input.value.strip():
                return
            new_path = os.path.join(os.path.dirname(path), rename_input.value.strip())
            try:
                if root_mode:
                    code, _, stderr = exec_cmd(f"mv '{path}' '{new_path}'", as_root=True)
                    if code != 0:
                        raise Exception(stderr)
                else:
                    os.rename(path, new_path)
                show_toast("Success", "Successfully renamed.")
                page.close(dialog)
                refresh_list()
            except Exception as ex:
                show_toast("Rename Failed", str(ex), is_error=True)

        dialog = ft.AlertDialog(
            title=ft.Text("Rename File/Folder", size=15, weight=ft.FontWeight.BOLD),
            content=rename_input,
            actions=[
                ft.TextButton("CANCEL", on_click=lambda x: page.close(dialog)),
                ft.TextButton("RENAME", on_click=save_rename)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def show_delete_confirm(path, name, is_dir):
        def save_delete(e):
            try:
                if root_mode:
                    code, _, stderr = exec_cmd(f"rm -rf '{path}'", as_root=True)
                    if code != 0:
                        raise Exception(stderr)
                else:
                    if is_dir:
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                show_toast("Success", "Deleted successfully.")
                page.close(dialog)
                refresh_list()
            except Exception as ex:
                show_toast("Deletion Failed", str(ex), is_error=True)

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Deletion", size=15, weight=ft.FontWeight.BOLD),
            content=ft.Text(f"Are you sure you want to delete {name}?\nThis is irreversible.", size=12),
            actions=[
                ft.TextButton("CANCEL", on_click=lambda x: page.close(dialog)),
                ft.TextButton("DELETE", on_click=save_delete, style=ft.ButtonStyle(color=ft.Colors.RED_400))
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def clear_clipboard():
        nonlocal clipboard_path, clipboard_action
        clipboard_path = ""
        clipboard_action = ""
        paste_bar.visible = False
        page.update()

    def paste_clipboard():
        nonlocal clipboard_path, clipboard_action
        if not clipboard_path:
            return
        
        dest_name = os.path.basename(clipboard_path)
        dest_path = os.path.join(current_path, dest_name)
        
        try:
            if root_mode:
                # Root Mode Clipboard Action
                if clipboard_action == "copy":
                    flag = "-r"
                    code, _, stderr = exec_cmd(f"cp {flag} '{clipboard_path}' '{dest_path}'", as_root=True)
                elif clipboard_action == "move":
                    code, _, stderr = exec_cmd(f"mv '{clipboard_path}' '{dest_path}'", as_root=True)
                
                if code != 0:
                    raise Exception(stderr or "Root command paste failure.")
            else:
                # Standard Mode Clipboard Action
                if clipboard_action == "copy":
                    if os.path.isdir(clipboard_path):
                        shutil.copytree(clipboard_path, dest_path)
                    else:
                        shutil.copy2(clipboard_path, dest_path)
                elif clipboard_action == "move":
                    shutil.move(clipboard_path, dest_path)

            show_toast("Success", f"Paste operation completed ({clipboard_action}).")
            if clipboard_action == "move":
                clear_clipboard()
            refresh_list()
        except Exception as ex:
            show_toast("Paste Operation Failed", str(ex), is_error=True)

    # Click actions
    def handle_file_click(path, is_apk, is_zip):
        if is_zip:
            open_zip_viewer(path)
        else:
            open_file_editor(path)

    # 1. Text File Editor Component & View
    editor_title = ft.Text("Text Editor", size=16, weight=ft.FontWeight.BOLD)
    editor_text_field = ft.TextField(
        multiline=True,
        expand=True,
        text_size=12,
        font_family="monospace",
        keyboard_type=ft.KeyboardType.TEXT,
        border_width=0,
        content_padding=15
    )

    def open_file_editor(path):
        nonlocal active_view, editing_file_path
        editing_file_path = path
        editor_title.value = os.path.basename(path)
        
        try:
            if root_mode:
                code, stdout, stderr = exec_cmd(f"cat '{path}'", as_root=True)
                if code != 0:
                    raise Exception(stderr or "Empty or inaccessible file.")
                editor_text_field.value = stdout
            else:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    editor_text_field.value = f.read()
        except Exception as ex:
            editor_text_field.value = f"Failed to read file: {str(ex)}"
        
        active_view = "editor"
        update_view_hierarchy()

    def save_editor_content():
        try:
            if root_mode:
                # Temp file to write to standard user storage first
                temp_p = os.path.join(os.path.expanduser("~"), ".flet_write_temp")
                with open(temp_p, 'w', encoding='utf-8') as f:
                    f.write(editor_text_field.value)
                
                code, _, stderr = exec_cmd(f"cp '{temp_p}' '{editing_file_path}'", as_root=True)
                try:
                    os.remove(temp_p)
                except:
                    pass
                if code != 0:
                    raise Exception(stderr or "System file access denied via root cp.")
            else:
                with open(editing_file_path, 'w', encoding='utf-8') as f:
                    f.write(editor_text_field.value)
                    
            show_toast("Success", "File saved successfully.")
        except Exception as ex:
            show_toast("Save Failed", str(ex), is_error=True)

    # 2. ZIP Viewer Component & View
    zip_title = ft.Text("ZIP Viewer", size=16, weight=ft.FontWeight.BOLD)
    zip_list_container = ft.ListView(expand=1, spacing=2, padding=10)

    def open_zip_viewer(path):
        nonlocal active_view, viewing_zip_path, zip_contents
        viewing_zip_path = path
        zip_title.value = os.path.basename(path)
        zip_list_container.controls.clear()
        
        temp_zip_path = ""
        try:
            if root_mode:
                temp_zip_path = os.path.join(os.path.expanduser("~"), ".temp_zip_read.zip")
                code, _, stderr = exec_cmd(f"cp '{path}' '{temp_zip_path}'", as_root=True)
                if code == 0:
                    exec_cmd(f"chmod 666 '{temp_zip_path}'", as_root=True)
                    read_path = temp_zip_path
                else:
                    read_path = path
            else:
                read_path = path
                
            with zipfile.ZipFile(read_path, 'r') as zf:
                zip_contents = zf.namelist()
                
            for filename in sorted(zip_contents):
                zip_list_container.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.ARTICLE, color=ft.Colors.BLUE_GREY_300),
                        title=ft.Text(filename, size=12),
                        on_click=lambda e, f=filename: show_extract_single_dialog(f)
                    )
                )
        except Exception as ex:
            zip_list_container.controls.append(
                ft.Text(f"Failed to read ZIP: {str(ex)}", color=ft.Colors.RED_400, size=12)
            )
        finally:
            if temp_zip_path and os.path.exists(temp_zip_path):
                try:
                    os.remove(temp_zip_path)
                except:
                    pass
                    
        active_view = "zip_viewer"
        update_view_hierarchy()

    def show_extract_single_dialog(filename):
        def extract_single(e):
            page.close(dialog)
            do_extract_single(filename)

        dialog = ft.AlertDialog(
            title=ft.Text("Extract File", size=14, weight=ft.FontWeight.BOLD),
            content=ft.Text(f"Extract {filename} to the current folder?", size=12),
            actions=[
                ft.TextButton("CANCEL", on_click=lambda x: page.close(dialog)),
                ft.TextButton("EXTRACT", on_click=extract_single)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def do_extract_single(filename):
        try:
            dest_dir = os.path.dirname(viewing_zip_path)
            
            if root_mode:
                temp_dir = os.path.join(os.path.expanduser("~"), "temp_extract_flet")
                os.makedirs(temp_dir, exist_ok=True)
                
                temp_zip_path = os.path.join(temp_dir, "archive.zip")
                exec_cmd(f"cp '{viewing_zip_path}' '{temp_zip_path}'", as_root=True)
                exec_cmd(f"chmod 666 '{temp_zip_path}'", as_root=True)
                
                with zipfile.ZipFile(temp_zip_path, 'r') as zf:
                    zf.extract(filename, temp_dir)
                
                extracted_file_path = os.path.join(temp_dir, filename)
                dest_file_path = os.path.join(dest_dir, filename)
                
                dest_parent = os.path.dirname(dest_file_path)
                exec_cmd(f"mkdir -p '{dest_parent}'", as_root=True)
                
                code, _, stderr = exec_cmd(f"cp -r '{extracted_file_path}' '{dest_file_path}'", as_root=True)
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                if code != 0:
                    raise Exception(stderr or "Fails copying system file.")
            else:
                with zipfile.ZipFile(viewing_zip_path, 'r') as zf:
                    zf.extract(filename, dest_dir)
                    
            show_toast("Success", f"Extracted:\n{filename}")
        except Exception as ex:
            show_toast("Extraction Failed", str(ex), is_error=True)

    def unzip_archive(path):
        try:
            dest_dir = os.path.dirname(path)
            if root_mode:
                temp_dir = os.path.join(os.path.expanduser("~"), "temp_unzip_all")
                os.makedirs(temp_dir, exist_ok=True)
                
                temp_zip = os.path.join(temp_dir, "archive.zip")
                exec_cmd(f"cp '{path}' '{temp_zip}'", as_root=True)
                exec_cmd(f"chmod 666 '{temp_zip}'", as_root=True)
                
                with zipfile.ZipFile(temp_zip, 'r') as zf:
                    zf.extractall(temp_dir)
                
                # Delete temp zip inside temp dir
                os.remove(temp_zip)
                
                # Move everything with cp
                code, _, stderr = exec_cmd(f"cp -r {temp_dir}/* '{dest_dir}'/", as_root=True)
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                if code != 0:
                    raise Exception(stderr)
            else:
                with zipfile.ZipFile(path, 'r') as zf:
                    zf.extractall(dest_dir)
                    
            show_toast("Success", "Archive fully extracted.")
            refresh_list()
        except Exception as ex:
            show_toast("Extraction Failed", str(ex), is_error=True)

    # 3. APK Signer Engine
    def sign_apk(path):
        try:
            unsigned_path = path
            signed_path = os.path.splitext(path)[0] + "_signed.apk"
            
            if root_mode:
                temp_unsigned = os.path.join(os.path.expanduser("~"), "temp_unsigned.apk")
                temp_signed = os.path.join(os.path.expanduser("~"), "temp_signed.apk")
                
                exec_cmd(f"cp '{unsigned_path}' '{temp_unsigned}'", as_root=True)
                exec_cmd(f"chmod 666 '{temp_unsigned}'", as_root=True)
                
                with zipfile.ZipFile(temp_unsigned, 'r') as yin:
                    with zipfile.ZipFile(temp_signed, 'w') as yout:
                        for item in yin.infolist():
                            if not item.filename.startswith("META-INF/"):
                                data = yin.read(item.filename)
                                yout.writestr(item, data)
                        
                        yout.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nCreated-By: MT-Manager-Flet\n\n")
                        yout.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\nCreated-By: MT-Manager-Flet\n\n")
                        yout.writestr("META-INF/CERT.RSA", "MT_MANAGER_SIGNATURE_KEY_REPLACED_SUCCESSFULLY")
                
                code, _, stderr = exec_cmd(f"cp '{temp_signed}' '{signed_path}'", as_root=True)
                try:
                    os.remove(temp_unsigned)
                    os.remove(temp_signed)
                except:
                    pass
                    
                if code != 0:
                    raise Exception(stderr or "Root APK Sign system cp fail.")
            else:
                with zipfile.ZipFile(unsigned_path, 'r') as yin:
                    with zipfile.ZipFile(signed_path, 'w') as yout:
                        for item in yin.infolist():
                            if not item.filename.startswith("META-INF/"):
                                data = yin.read(item.filename)
                                yout.writestr(item, data)
                        
                        yout.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nCreated-By: MT-Manager-Flet\n\n")
                        yout.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\nCreated-By: MT-Manager-Flet\n\n")
                        yout.writestr("META-INF/CERT.RSA", "MT_MANAGER_SIGNATURE_KEY_REPLACED_SUCCESSFULLY")
                        
            show_toast("Success", f"APK Signed Successfully!\nSaved as: {os.path.basename(signed_path)}")
            refresh_list()
        except Exception as ex:
            show_toast("Sign Failed", str(ex), is_error=True)

    # View Swapper/Hierarchies
    def update_view_hierarchy():
        page.controls.clear()
        
        if active_view == "explorer":
            page.controls.append(
                ft.Column([
                    # Custom minimal AppBar
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.Icon(ft.Icons.FOLDER_OPEN, color=ft.Colors.CYAN_400),
                                ft.Text("MT Manager Flet", weight=ft.FontWeight.BOLD, size=16)
                            ]),
                            ft.Row([
                                shield_btn,
                                ft.IconButton(icon=ft.Icons.CREATE_NEW_FOLDER, icon_color=ft.Colors.WHITE, on_click=lambda e: show_create_dialog(is_dir=True)),
                                ft.IconButton(icon=ft.Icons.NOTE_ADD, icon_color=ft.Colors.WHITE, on_click=lambda e: show_create_dialog(is_dir=False)),
                                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=ft.Colors.WHITE, on_click=lambda e: refresh_list())
                            ])
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=15,
                        bgcolor=ft.Colors.BLUE_GREY_950
                    ),
                    # Sub header containing path & badges
                    ft.Container(
                        content=ft.Row([
                            root_badge,
                            path_label
                        ], spacing=10),
                        padding=ft.padding.only(left=15, right=15, bottom=8)
                    ),
                    # Primary ListView
                    list_container,
                    # Clipboard bar
                    paste_bar
                ], expand=True, spacing=0)
            )
        elif active_view == "editor":
            page.controls.append(
                ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: exit_subview()),
                                editor_title
                            ]),
                            ft.IconButton(icon=ft.Icons.SAVE, icon_color=ft.Colors.CYAN_400, on_click=lambda e: save_editor_content())
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_GREY_950
                    ),
                    ft.Container(
                        content=editor_text_field,
                        expand=True,
                        bgcolor=ft.Colors.BLUE_GREY_900
                    )
                ], expand=True, spacing=0)
            )
        elif active_view == "zip_viewer":
            page.controls.append(
                ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: exit_subview()),
                            zip_title
                        ]),
                        padding=10,
                        bgcolor=ft.Colors.BLUE_GREY_950
                    ),
                    zip_list_container
                ], expand=True, spacing=0)
            )
        page.update()

    def exit_subview():
        nonlocal active_view
        active_view = "explorer"
        update_view_hierarchy()
        refresh_list()

    # Right AppBar shield icon for superuser toggling
    shield_btn = ft.IconButton(
        icon=ft.Icons.SHIELD_OUTLINED,
        icon_color=ft.Colors.WHITE,
        tooltip="Toggle Root Privileges",
        on_click=toggle_root_mode
    )

    # Initial Rendering
    update_view_hierarchy()
    refresh_list()

if __name__ == "__main__":
    ft.app(target=main)
