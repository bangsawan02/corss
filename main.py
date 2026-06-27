# -*- coding: utf-8 -*-
import os
import sys
import shutil
import zipfile
from kivy.utils import platform

# Configure Kivy window size for testing if on desktop
if platform not in ['android', 'ios']:
    from kivy.config import Config
    Config.set('graphics', 'width', '360')
    Config.set('graphics', 'height', '640')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, ObjectProperty, BooleanProperty
from kivy.metrics import dp

# KivyMD Imports
from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton, MDRaisedButton, MDFillRoundFlatButton, MDFlatButton
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.list import MDList, OneLineIconListItem, TwoLineIconListItem, IconLeftWidget, IconRightWidget
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard

# Request storage permissions for Android
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.READ_EXTERNAL_STORAGE,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.MANAGE_EXTERNAL_STORAGE
    ])


class FileManagerScreen(Screen):
    current_path = StringProperty("")
    clipboard_path = StringProperty("")
    clipboard_action = StringProperty("")  # "copy" or "move"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_path = os.path.expanduser("~")
        if platform == 'android':
            # Default to SD Card on Android
            self.current_path = "/sdcard" if os.path.exists("/sdcard") else "/storage/emulated/0"
        
    def on_enter(self):
        self.update_toolbar_icons()
        self.refresh_list()

    def update_toolbar_icons(self):
        app = MDApp.get_running_app()
        shield_icon = "shield-lock" if app.root_mode else "shield-lock-outline"
        self.ids.top_bar.right_action_items = [
            [shield_icon, lambda x: self.toggle_root_mode()],
            ["folder-plus", lambda x: self.show_create_dialog(is_dir=True)],
            ["file-plus", lambda x: self.show_create_dialog(is_dir=False)],
            ["refresh", lambda x: self.refresh_list()]
        ]

    def toggle_root_mode(self):
        app = MDApp.get_running_app()
        if not app.root_mode:
            if app.check_root_available():
                app.root_mode = True
                self.show_message("Root Mode Active", "Superuser privileges granted and root mode enabled.")
            else:
                self.show_message("Root Mode", "Could not acquire root permissions. Please make sure your device is rooted and superuser access is allowed.")
        else:
            app.root_mode = False
            self.show_message("Root Mode Disabled", "Switched back to standard user permissions.")
        
        self.update_toolbar_icons()
        self.refresh_list()

    def go_back(self):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self.current_path = parent
            self.refresh_list()

    def go_to_dir(self, path):
        app = MDApp.get_running_app()
        is_directory = False
        if os.path.isdir(path):
            is_directory = True
        elif app.root_mode:
            # Check if it's a directory using su
            code, stdout, _ = app.exec_cmd(f"[ -d '{path}' ] && echo 'yes'", as_root=True)
            if "yes" in stdout:
                is_directory = True

        if is_directory:
            self.current_path = path
            self.refresh_list()
        else:
            self.show_message("Error", "Not a directory or permission denied.")

    def listdir_root(self, path):
        app = MDApp.get_running_app()
        code, stdout, stderr = app.exec_cmd(f"ls -ap '{path}'", as_root=True)
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
        return folders, files

    def refresh_list(self):
        self.ids.file_list.clear_widgets()
        app = MDApp.get_running_app()
        
        # Add a list item to go up a directory
        if self.current_path != "/":
            up_item = OneLineIconListItem(text=".. (Go Up)")
            up_icon = IconLeftWidget(icon="folder-upload")
            up_item.add_widget(up_icon)
            up_item.bind(on_release=lambda x: self.go_back())
            self.ids.file_list.add_widget(up_item)

        try:
            if app.root_mode:
                folders, files = self.listdir_root(self.current_path)
            else:
                try:
                    items = os.listdir(self.current_path)
                    folders = sorted([i for i in items if os.path.isdir(os.path.join(self.current_path, i))])
                    files = sorted([i for i in items if os.path.isfile(os.path.join(self.current_path, i))])
                except Exception as e:
                    if app.check_root_available():
                        # Auto fallback to root listdir if su is available
                        folders, files = self.listdir_root(self.current_path)
                    else:
                        raise e
            
            for folder in folders:
                full_path = os.path.join(self.current_path, folder)
                item = TwoLineIconListItem(
                    text=folder,
                    secondary_text="Directory",
                )
                icon = IconLeftWidget(icon="folder")
                item.add_widget(icon)
                
                # Action button on the right
                opt_btn = IconRightWidget(icon="dots-vertical")
                opt_btn.bind(on_release=lambda x, p=full_path: self.show_options(p, is_dir=True))
                item.add_widget(opt_btn)
                
                item.bind(on_release=lambda x, p=full_path: self.go_to_dir(p))
                self.ids.file_list.add_widget(item)

            for file in files:
                full_path = os.path.join(self.current_path, file)
                ext = os.path.splitext(file)[1].lower()
                
                icon_name = "file"
                if ext in [".txt", ".py", ".json", ".xml", ".html", ".css", ".ini"]:
                    icon_name = "file-document"
                elif ext in [".zip", ".rar", ".tar", ".gz"]:
                    icon_name = "zip-box"
                elif ext == ".apk":
                    icon_name = "android"
                elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
                    icon_name = "file-image"

                item = TwoLineIconListItem(
                    text=file,
                    secondary_text=f"File | {self.get_file_size(full_path)}",
                )
                icon = IconLeftWidget(icon=icon_name)
                item.add_widget(icon)
                
                opt_btn = IconRightWidget(icon="dots-vertical")
                opt_btn.bind(on_release=lambda x, p=full_path: self.show_options(p, is_dir=False))
                item.add_widget(opt_btn)
                
                item.bind(on_release=lambda x, p=full_path, e=ext: self.handle_file_click(p, e))
                self.ids.file_list.add_widget(item)
                
        except Exception as e:
            err_item = OneLineIconListItem(text=f"Error reading path: {str(e)}")
            self.ids.file_list.add_widget(err_item)

    def get_file_size(self, path):
        app = MDApp.get_running_app()
        try:
            if app.root_mode:
                code, stdout, _ = app.exec_cmd(f"wc -c '{path}'", as_root=True)
                if code == 0:
                    size = int(stdout.strip().split()[0])
                else:
                    size = os.path.getsize(path)
            else:
                size = os.path.getsize(path)
                
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        except:
            return "Unknown size"

    def handle_file_click(self, path, ext):
        if ext in [".txt", ".py", ".json", ".xml", ".html", ".css", ".ini", ".cfg", ".spec"]:
            # Open Text Editor
            editor_screen = self.manager.get_screen('editor')
            editor_screen.open_file(path)
            self.manager.current = 'editor'
        elif ext in [".zip", ".apk"]:
            # Show ZIP/APK content viewer
            zip_screen = self.manager.get_screen('zip_viewer')
            zip_screen.open_archive(path)
            self.manager.current = 'zip_viewer'

    def show_options(self, path, is_dir=False):
        name = os.path.basename(path)
        
        buttons = [
            MDFlatButton(text="Rename", on_release=lambda x: self.dialog_rename(path)),
            MDFlatButton(text="Delete", on_release=lambda x: self.dialog_delete(path)),
            MDFlatButton(text="Copy", on_release=lambda x: self.set_clipboard(path, "copy")),
            MDFlatButton(text="Move", on_release=lambda x: self.set_clipboard(path, "move")),
        ]
        
        if not is_dir and os.path.splitext(name)[1].lower() == ".apk":
            buttons.append(MDFlatButton(text="Sign APK", on_release=lambda x: self.sign_apk_tool(path)))

        buttons.append(MDFlatButton(text="Cancel", on_release=lambda x: self.dialog.dismiss()))

        self.dialog = MDDialog(
            title=f"Options for {name}",
            type="simple",
            buttons=buttons
        )
        self.dialog.open()

    def set_clipboard(self, path, action):
        self.clipboard_path = path
        self.clipboard_action = action
        self.dialog.dismiss()
        self.ids.paste_btn.opacity = 1
        self.ids.paste_btn.disabled = False

    def paste_clipboard(self):
        app = MDApp.get_running_app()
        if not self.clipboard_path or not os.path.exists(self.clipboard_path):
            if not app.root_mode:
                return
            # Check if exists using root
            code, stdout, _ = app.exec_cmd(f"[ -e '{self.clipboard_path}' ] && echo 'yes'", as_root=True)
            if "yes" not in stdout:
                return
        
        dest_name = os.path.basename(self.clipboard_path)
        dest_path = os.path.join(self.current_path, dest_name)
        
        try:
            if app.root_mode:
                if self.clipboard_action == "copy":
                    flag = "-r" if os.path.isdir(self.clipboard_path) else ""
                    if not flag:
                        code, stdout, _ = app.exec_cmd(f"[ -d '{self.clipboard_path}' ] && echo 'yes'", as_root=True)
                        if "yes" in stdout:
                            flag = "-r"
                    code, stdout, stderr = app.exec_cmd(f"cp {flag} '{self.clipboard_path}' '{dest_path}'", as_root=True)
                elif self.clipboard_action == "move":
                    code, stdout, stderr = app.exec_cmd(f"mv '{self.clipboard_path}' '{dest_path}'", as_root=True)
                    self.clipboard_path = ""
                    self.ids.paste_btn.opacity = 0
                    self.ids.paste_btn.disabled = True
                
                if code != 0:
                    raise Exception(stderr or f"Root operation failed with code {code}")
            else:
                if self.clipboard_action == "copy":
                    if os.path.isdir(self.clipboard_path):
                        shutil.copytree(self.clipboard_path, dest_path)
                    else:
                        shutil.copy2(self.clipboard_path, dest_path)
                elif self.clipboard_action == "move":
                    shutil.move(self.clipboard_path, dest_path)
                    self.clipboard_path = ""
                    self.ids.paste_btn.opacity = 0
                    self.ids.paste_btn.disabled = True

            self.refresh_list()
        except Exception as e:
            self.show_message("Error", f"Failed to paste: {str(e)}")

    def dialog_rename(self, path):
        self.dialog.dismiss()
        name = os.path.basename(path)
        
        content = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="80dp")
        self.rename_field = MDTextField(text=name, hint_text="New name")
        content.add_widget(self.rename_field)

        self.dialog = MDDialog(
            title="Rename Item",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Save", on_release=lambda x, p=path: self.do_rename(p))
            ]
        )
        self.dialog.open()

    def do_rename(self, path):
        new_name = self.rename_field.text.strip()
        if not new_name:
            return
        
        parent = os.path.dirname(path)
        new_path = os.path.join(parent, new_name)
        app = MDApp.get_running_app()
        
        try:
            if app.root_mode:
                code, stdout, stderr = app.exec_cmd(f"mv '{path}' '{new_path}'", as_root=True)
                if code != 0:
                    raise Exception(stderr or f"Root rename failed with code {code}")
            else:
                os.rename(path, new_path)
            self.dialog.dismiss()
            self.refresh_list()
        except Exception as e:
            self.show_message("Error", f"Rename failed: {str(e)}")

    def dialog_delete(self, path):
        self.dialog.dismiss()
        name = os.path.basename(path)
        self.dialog = MDDialog(
            title="Confirm Delete",
            text=f"Are you sure you want to permanently delete {name}?",
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Delete", md_bg_color=(1, 0.2, 0.2, 1), on_release=lambda x, p=path: self.do_delete(p))
            ]
        )
        self.dialog.open()

    def do_delete(self, path):
        app = MDApp.get_running_app()
        try:
            if app.root_mode:
                code, stdout, stderr = app.exec_cmd(f"rm -rf '{path}'", as_root=True)
                if code != 0:
                    raise Exception(stderr or f"Root delete failed with code {code}")
            else:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            self.dialog.dismiss()
            self.refresh_list()
        except Exception as e:
            self.show_message("Error", f"Delete failed: {str(e)}")

    def show_create_dialog(self, is_dir=False):
        title = "Create New Folder" if is_dir else "Create New File"
        hint = "Folder Name" if is_dir else "File Name"
        
        content = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="80dp")
        self.create_field = MDTextField(hint_text=hint)
        content.add_widget(self.create_field)

        self.dialog = MDDialog(
            title=title,
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Create", on_release=lambda x, d=is_dir: self.do_create(d))
            ]
        )
        self.dialog.open()

    def do_create(self, is_dir):
        name = self.create_field.text.strip()
        if not name:
            return
        
        target_path = os.path.join(self.current_path, name)
        app = MDApp.get_running_app()
        try:
            if app.root_mode:
                if is_dir:
                    code, stdout, stderr = app.exec_cmd(f"mkdir -p '{target_path}'", as_root=True)
                else:
                    code, stdout, stderr = app.exec_cmd(f"touch '{target_path}'", as_root=True)
                if code != 0:
                    raise Exception(stderr or f"Root creation failed with code {code}")
            else:
                if is_dir:
                    os.makedirs(target_path, exist_ok=True)
                else:
                    with open(target_path, 'w') as f:
                        f.write("")
            self.dialog.dismiss()
            self.refresh_list()
        except Exception as e:
            self.show_message("Error", f"Creation failed: {str(e)}")

    def sign_apk_tool(self, path):
        self.dialog.dismiss()
        app = MDApp.get_running_app()
        try:
            unsigned_path = path
            signed_path = os.path.splitext(path)[0] + "_signed.apk"
            
            if app.root_mode:
                temp_unsigned = os.path.join(os.path.expanduser("~"), "temp_unsigned.apk")
                temp_signed = os.path.join(os.path.expanduser("~"), "temp_signed.apk")
                
                app.exec_cmd(f"cp '{unsigned_path}' '{temp_unsigned}'", as_root=True)
                app.exec_cmd(f"chmod 666 '{temp_unsigned}'", as_root=True)
                
                with zipfile.ZipFile(temp_unsigned, 'r') as yin:
                    with zipfile.ZipFile(temp_signed, 'w') as yout:
                        for item in yin.infolist():
                            if not item.filename.startswith("META-INF/"):
                                data = yin.read(item.filename)
                                yout.writestr(item, data)
                        
                        yout.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nCreated-By: MT-Manager-KivyMD\n\n")
                        yout.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\nCreated-By: MT-Manager-KivyMD\n\n")
                        yout.writestr("META-INF/CERT.RSA", "MT_MANAGER_SIGNATURE_KEY_REPLACED_SUCCESSFULLY")
                
                code, stdout, stderr = app.exec_cmd(f"cp '{temp_signed}' '{signed_path}'", as_root=True)
                try:
                    os.remove(temp_unsigned)
                    os.remove(temp_signed)
                except:
                    pass
                    
                if code != 0:
                    raise Exception(stderr or f"Root copy of signed APK failed: {code}")
            else:
                with zipfile.ZipFile(unsigned_path, 'r') as yin:
                    with zipfile.ZipFile(signed_path, 'w') as yout:
                        for item in yin.infolist():
                            if not item.filename.startswith("META-INF/"):
                                data = yin.read(item.filename)
                                yout.writestr(item, data)
                        
                        yout.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nCreated-By: MT-Manager-KivyMD\n\n")
                        yout.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\nCreated-By: MT-Manager-KivyMD\n\n")
                        yout.writestr("META-INF/CERT.RSA", "MT_MANAGER_SIGNATURE_KEY_REPLACED_SUCCESSFULLY")
            
            self.show_message("Success", f"APK Signed Successfully!\nSaved as: {os.path.basename(signed_path)}")
            self.refresh_list()
        except Exception as e:
            self.show_message("Error", f"Failed to sign APK: {str(e)}")

    def show_message(self, title, text):
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()


class TextEditorScreen(Screen):
    file_path = StringProperty("")

    def open_file(self, path):
        self.file_path = path
        self.ids.editor_title.title = os.path.basename(path)
        app = MDApp.get_running_app()
        try:
            if app.root_mode:
                code, stdout, stderr = app.exec_cmd(f"cat '{path}'", as_root=True)
                if code != 0:
                    raise Exception(stderr or f"Root cat failed with code {code}")
                self.ids.text_content.text = stdout
            else:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.ids.text_content.text = f.read()
        except Exception as e:
            self.ids.text_content.text = f"Failed to read file: {str(e)}"

    def save_file(self):
        if not self.file_path:
            return
        app = MDApp.get_running_app()
        try:
            if app.root_mode:
                temp_path = os.path.join(os.path.expanduser("~"), ".mt_temp_write")
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(self.ids.text_content.text)
                
                code, stdout, stderr = app.exec_cmd(f"cp '{temp_path}' '{self.file_path}'", as_root=True)
                try:
                    os.remove(temp_path)
                except:
                    pass
                
                if code != 0:
                    raise Exception(stderr or f"Root write failed with code {code}")
            else:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    f.write(self.ids.text_content.text)
            self.show_message("Saved", "File saved successfully!")
        except Exception as e:
            self.show_message("Error", f"Failed to save file: {str(e)}")

    def show_message(self, title, text):
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def go_back(self):
        self.manager.current = 'files'


class ZipViewerScreen(Screen):
    archive_path = StringProperty("")
    zip_contents = ListProperty([])

    def open_archive(self, path):
        self.archive_path = path
        self.ids.zip_title.title = os.path.basename(path)
        self.ids.zip_list.clear_widgets()
        
        app = MDApp.get_running_app()
        temp_zip_path = ""
        
        try:
            if app.root_mode:
                temp_zip_path = os.path.join(os.path.expanduser("~"), ".temp_zip_read.zip")
                code, stdout, stderr = app.exec_cmd(f"cp '{path}' '{temp_zip_path}'", as_root=True)
                if code == 0:
                    app.exec_cmd(f"chmod 666 '{temp_zip_path}'", as_root=True)
                    read_path = temp_zip_path
                else:
                    read_path = path
            else:
                read_path = path
                
            with zipfile.ZipFile(read_path, 'r') as zf:
                self.zip_contents = zf.namelist()
                
            for filename in sorted(self.zip_contents):
                item = OneLineIconListItem(text=filename)
                icon = IconLeftWidget(icon="file-code" if filename.endswith(('.xml', '.dex', '.arsc')) else "file")
                item.add_widget(icon)
                
                # Double tap or select to extract individual file
                item.bind(on_release=lambda x, f=filename: self.show_extract_option(f))
                self.ids.zip_list.add_widget(item)
                
        except Exception as e:
            self.ids.zip_list.add_widget(OneLineIconListItem(text=f"Error reading ZIP: {str(e)}"))
        finally:
            if temp_zip_path and os.path.exists(temp_zip_path):
                try:
                    os.remove(temp_zip_path)
                except:
                    pass

    def show_extract_option(self, filename):
        self.dialog = MDDialog(
            title="Extract File",
            text=f"Do you want to extract '{filename}' from this archive?",
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda x: self.dialog.dismiss()),
                MDRaisedButton(text="Extract", on_release=lambda x, f=filename: self.do_extract(f))
            ]
        )
        self.dialog.open()

    def do_extract(self, filename):
        self.dialog.dismiss()
        app = MDApp.get_running_app()
        try:
            dest_dir = os.path.dirname(self.archive_path)
            
            if app.root_mode:
                temp_dir = os.path.join(os.path.expanduser("~"), "temp_extract")
                os.makedirs(temp_dir, exist_ok=True)
                
                temp_zip_path = os.path.join(temp_dir, "archive.zip")
                app.exec_cmd(f"cp '{self.archive_path}' '{temp_zip_path}'", as_root=True)
                app.exec_cmd(f"chmod 666 '{temp_zip_path}'", as_root=True)
                
                with zipfile.ZipFile(temp_zip_path, 'r') as zf:
                    zf.extract(filename, temp_dir)
                
                extracted_file_path = os.path.join(temp_dir, filename)
                dest_file_path = os.path.join(dest_dir, filename)
                
                dest_parent = os.path.dirname(dest_file_path)
                app.exec_cmd(f"mkdir -p '{dest_parent}'", as_root=True)
                
                code, stdout, stderr = app.exec_cmd(f"cp -r '{extracted_file_path}' '{dest_file_path}'", as_root=True)
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                if code != 0:
                    raise Exception(stderr or f"Root extract copy failed with code {code}")
            else:
                with zipfile.ZipFile(self.archive_path, 'r') as zf:
                    zf.extract(filename, dest_dir)
            self.show_message("Extracted", f"Extracted to current folder:\n{filename}")
        except Exception as e:
            self.show_message("Error", f"Extraction failed: {str(e)}")

    def show_message(self, title, text):
        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDFlatButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

    def go_back(self):
        self.manager.current = 'files'


class MTManagerApp(MDApp):
    root_mode = BooleanProperty(False)

    def build(self):
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.theme_style = "Dark"
        
        # Load string representations of screens (equivalent to KV design)
        # To avoid external KV file complexity, we declare UI layout using KV language string
        from kivy.lang import Builder
        Builder.load_string("""
<FileManagerScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            id: top_bar
            title: "MT Manager KivyMD"
            anchor_title: "left"
            right_action_items: [["shield-lock-outline", lambda x: root.toggle_root_mode()], ["folder-plus", lambda x: root.show_create_dialog(is_dir=True)], ["file-plus", lambda x: root.show_create_dialog(is_dir=False)], ["refresh", lambda x: root.refresh_list()]]
            elevation: 2
            
        MDLabel:
            text: ("[Root] " if app.root_mode else "") + root.current_path
            size_hint_y: None
            height: "40dp"
            padding: "16dp", "8dp"
            theme_text_color: "Custom"
            text_color: (1, 0.3, 0.3, 1) if app.root_mode else (0.6, 0.6, 0.6, 1)
            font_style: "Caption"
            
        ScrollView:
            MDList:
                id: file_list
                
        MDBoxLayout:
            size_hint_y: None
            height: "56dp"
            padding: "8dp"
            spacing: "8dp"
            md_bg_color: 0.15, 0.15, 0.15, 1
            
            MDRaisedButton:
                id: paste_btn
                text: "Paste Clipboard"
                icon: "clipboard-arrow-down"
                opacity: 0
                disabled: True
                size_hint_x: 1
                on_release: root.paste_clipboard()

<TextEditorScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            id: editor_title
            title: "Editor"
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
            right_action_items: [["content-save", lambda x: root.save_file()]]
            elevation: 2
            
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: "12dp"
                
                TextInput:
                    id: text_content
                    size_hint_y: None
                    height: "1000dp"
                    background_color: 0.1, 0.1, 0.1, 1
                    foreground_color: 1, 1, 1, 1
                    font_name: "Roboto"
                    font_size: "14sp"
                    multiline: True
                    selection_color: 0.2, 0.4, 0.8, 0.5

<ZipViewerScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            id: zip_title
            title: "ZIP Contents"
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
            elevation: 2
            
        ScrollView:
            MDList:
                id: zip_list
""")

        sm = ScreenManager()
        sm.add_widget(FileManagerScreen(name='files'))
        sm.add_widget(TextEditorScreen(name='editor'))
        sm.add_widget(ZipViewerScreen(name='zip_viewer'))
        return sm

    def exec_cmd(self, cmd, as_root=False):
        import subprocess
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

    def check_root_available(self):
        import subprocess
        if platform not in ['android', 'ios']:
            return True
        try:
            p = subprocess.Popen(['su', '-c', 'id'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, _ = p.communicate(timeout=2)
            return "uid=0" in stdout or p.returncode == 0
        except:
            return False


if __name__ == '__main__':
    MTManagerApp().run()
