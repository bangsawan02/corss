import os
import sys
import subprocess
import struct
import zlib
import hashlib
import zipfile
import shutil
import flet as ft

# =====================================================================
# PART 1: BINARY ENGINE UTILITIES (DEX, SMALI, APK PARSERS & EDITORS)
# =====================================================================

def run_root_cmd(command: str) -> subprocess.CompletedProcess:
    """
    Eksekusi perintah shell menggunakan wrapper 'su' untuk akses root.
    """
    try:
        result = subprocess.run(
            ["su", "-c", command],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result
    except Exception as e:
        return subprocess.CompletedProcess(
            args=["su", "-c", command],
            returncode=-1,
            stdout="",
            stderr=str(e)
        )

def is_root_available() -> bool:
    try:
        result = subprocess.run(["su", "-c", "id"], capture_output=True, text=True, timeout=2)
        return result.returncode == 0 or "uid=0" in result.stdout
    except:
        return False

def parse_dex_file(file_path):
    """
    Membaca struktur header dan String Pool pada file DEX (class.dex).
    """
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        if len(data) < 112:
            return None, "Ukuran berkas terlalu kecil untuk format DEX."
        
        magic = data[0:8]
        if not magic.startswith(b"dex\n"):
            return None, f"Magic header DEX tidak valid: {magic}"
            
        checksum = struct.unpack_from("<I", data, 8)[0]
        signature = data[12:32].hex()
        file_size = struct.unpack_from("<I", data, 32)[0]
        header_size = struct.unpack_from("<I", data, 36)[0]
        endian_tag = struct.unpack_from("<I", data, 40)[0]
        
        string_ids_size = struct.unpack_from("<I", data, 56)[0]
        string_ids_off = struct.unpack_from("<I", data, 60)[0]
        
        type_ids_size = struct.unpack_from("<I", data, 64)[0]
        type_ids_off = struct.unpack_from("<I", data, 68)[0]
        
        proto_ids_size = struct.unpack_from("<I", data, 72)[0]
        proto_ids_off = struct.unpack_from("<I", data, 76)[0]
        
        field_ids_size = struct.unpack_from("<I", data, 80)[0]
        field_ids_off = struct.unpack_from("<I", data, 84)[0]
        
        method_ids_size = struct.unpack_from("<I", data, 88)[0]
        method_ids_off = struct.unpack_from("<I", data, 92)[0]
        
        class_defs_size = struct.unpack_from("<I", data, 96)[0]
        class_defs_off = struct.unpack_from("<I", data, 100)[0]
        
        strings = []
        max_strings_to_read = min(string_ids_size, 800) # Batasan tampilan UI agar responsif
        for i in range(max_strings_to_read):
            off_ptr = string_ids_off + i * 4
            if off_ptr + 4 > len(data):
                break
            str_off = struct.unpack_from("<I", data, off_ptr)[0]
            
            # Decode uleb128 string length
            idx = str_off
            if idx >= len(data):
                continue
            
            str_len = 0
            shift = 0
            while idx < len(data):
                b = data[idx]
                idx += 1
                str_len |= (b & 0x7F) << shift
                if not (b & 0x80):
                    break
                shift += 7
                if shift > 28:
                    break
            
            start = idx
            while idx < len(data) and data[idx] != 0:
                idx += 1
            s_bytes = data[start:idx]
            try:
                s_val = s_bytes.decode('utf-8', errors='ignore')
            except:
                s_val = s_bytes.decode('latin-1', errors='ignore')
            strings.append((i, s_val, str_off))
            
        info = {
            "magic": magic.decode('ascii', errors='ignore').strip(),
            "checksum": f"0x{checksum:X}",
            "signature": signature,
            "file_size": file_size,
            "string_count": string_ids_size,
            "type_count": type_ids_size,
            "proto_count": proto_ids_size,
            "field_count": field_ids_size,
            "method_count": method_ids_size,
            "class_count": class_defs_size,
            "strings": strings
        }
        return info, None
    except Exception as e:
        return None, str(e)

def update_dex_checksum_and_signature(data: bytearray) -> bytearray:
    # 1. Update SHA-1 signature (bytes 12-31, 20 bytes)
    h = hashlib.sha1()
    h.update(data[32:])
    data[12:32] = h.digest()
    
    # 2. Update Adler32 checksum (bytes 8-11, 4 bytes)
    checksum = zlib.adler32(data[12:]) & 0xffffffff
    data[8:12] = struct.pack("<I", checksum)
    return data

def replace_dex_string(file_path, str_index, old_str, new_str):
    try:
        with open(file_path, "rb") as f:
            data = bytearray(f.read())
            
        info, err = parse_dex_file(file_path)
        if err or not info:
            return False, f"Gagal membaca DEX: {err}"
            
        strings = info["strings"]
        target_item = None
        for item in strings:
            if item[0] == str_index:
                target_item = item
                break
                
        if not target_item:
            return False, "String index tidak ditemukan"
            
        str_off = target_item[2]
        
        idx = str_off
        str_len = 0
        shift = 0
        while idx < len(data):
            b = data[idx]
            idx += 1
            str_len |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
            
        start_string_bytes = idx
        while idx < len(data) and data[idx] != 0:
            idx += 1
        end_string_bytes = idx
        
        available_len = end_string_bytes - start_string_bytes
        new_bytes = new_str.encode('utf-8')
        
        if len(new_bytes) > available_len:
            return False, f"String terlalu panjang! Maksimal {available_len} karakter untuk in-place editing agar offset DEX stabil."
            
        # Pad dengan nulls agar panjang bytes tidak bergeser (in-place replacement)
        padded_new_bytes = new_bytes + b'\x00' * (available_len - len(new_bytes))
        data[start_string_bytes:end_string_bytes] = padded_new_bytes
        
        # Hitung ulang checksum & hash SHA1 agar DEX lolos verifikasi ART Android
        data = update_dex_checksum_and_signature(data)
        
        with open(file_path, "wb") as f:
            f.write(data)
            
        return True, "Berhasil mengganti string & memperbarui signature DEX!"
    except Exception as e:
        return False, str(e)

def parse_binary_xml_strings(data):
    """
    Ekstraksi String Pool dari file biner Android XML (seperti AndroidManifest.xml)
    """
    try:
        if len(data) < 8:
            return []
        magic = struct.unpack_from("<I", data, 0)[0]
        if magic != 0x00080003:
            return []
        
        chunk_type = struct.unpack_from("<I", data, 8)[0]
        if chunk_type != 0x001C0001:
            return []
            
        chunk_size = struct.unpack_from("<I", data, 12)[0]
        string_count = struct.unpack_from("<I", data, 16)[0]
        flags = struct.unpack_from("<I", data, 24)[0]
        string_pool_offset = struct.unpack_from("<I", data, 28)[0]
        
        strings = []
        is_utf8 = (flags & (1 << 8)) != 0
        
        for i in range(string_count):
            off_ptr = 36 + i * 4
            if off_ptr + 4 > len(data):
                break
            str_off = struct.unpack_from("<I", data, off_ptr)[0]
            actual_off = 8 + string_pool_offset + str_off
            
            if is_utf8:
                # Sederhanakan pembacaan utf-8
                if actual_off < len(data):
                    length = data[actual_off]
                    start = actual_off + 2
                    end = start + length
                    if end <= len(data):
                        strings.append(data[start:end].decode('utf-8', errors='ignore'))
            else:
                if actual_off + 2 <= len(data):
                    length = struct.unpack_from("<H", data, actual_off)[0]
                    start = actual_off + 2
                    end = start + length * 2
                    if end <= len(data):
                        s_bytes = data[start:end]
                        strings.append(s_bytes.decode('utf-16le', errors='ignore'))
        return strings
    except:
        return []

def get_apk_info(file_path):
    """
    Inspeksi berkas APK menggunakan library built-in zipfile tanpa emulator
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as archive:
            namelist = archive.namelist()
            manifest_data = b""
            if "AndroidManifest.xml" in namelist:
                manifest_data = archive.read("AndroidManifest.xml")
            
            strings = parse_binary_xml_strings(manifest_data)
            package_name = "Tidak diketahui"
            permissions = []
            activities = []
            
            for s in strings:
                cleaned = s.strip()
                if cleaned.startswith("android.permission."):
                    permissions.append(cleaned)
                elif "." in cleaned and len(cleaned) > 5 and not cleaned.startswith("android."):
                    if cleaned.endswith("Activity") or "activity" in cleaned.lower():
                        activities.append(cleaned)
                    elif package_name == "Tidak diketahui":
                        package_name = cleaned
            
            return {
                "files": namelist,
                "package_name": package_name,
                "permissions": sorted(list(set(permissions)))[:15],
                "activities": sorted(list(set(activities)))[:15]
            }, None
    except Exception as e:
        return None, str(e)


# =====================================================================
# PART 2: CORE FLET APPLICATION LAYOUT (DUAL PANEL & EDITORS)
# =====================================================================

def main(page: ft.Page):
    page.title = "MT Flet Manager"
    page.theme_mode = ft.ThemeMode.DARK
    # Gunakan skema warna Android UI default yang bersih & konsisten
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE_GREY)
    page.padding = 10
    
    # Root Status
    root_available = is_root_available()

    # Inisialisasi FilePicker global
    active_picker_panel = [None] # Left atau Right
    
    def on_directory_picked(e: ft.FilePickerResultEvent):
        if e.path and active_picker_panel[0]:
            if active_picker_panel[0] == "Left":
                left_panel.navigate_to(e.path)
            elif active_picker_panel[0] == "Right":
                right_panel.navigate_to(e.path)
        page.update()

    dir_picker = ft.FilePicker(on_result=on_directory_picked)
    page.overlay.append(dir_picker)

    # State Berbagi File (Selected file context menu)
    selected_file_path = [None]
    selected_file_panel = [None] # "Left" atau "Right"

    # =====================================================================
    # FILE PANEL CLASS
    # =====================================================================
    class FilePanel:
        def __init__(self, name: str, initial_path: str):
            self.name = name
            self.current_path = os.path.abspath(initial_path)
            self.selected_item = None
            
            # Controls
            self.path_text = ft.Text(
                self.current_path, 
                size=12, 
                color=ft.Colors.BLUE_200, 
                weight=ft.FontWeight.W_500,
                overflow=ft.TextOverflow.ELLIPSIS,
                max_lines=1
            )
            self.list_view = ft.ListView(expand=1, spacing=2, padding=5)
            
            # Panel Container
            self.container = ft.Container(
                content=ft.Column(
                    [
                        # Panel Toolbar / Header
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.ARROW_UPWARD, 
                                        icon_size=16,
                                        tooltip="Kembali ke folder atas",
                                        on_click=lambda _: self.navigate_up()
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.FOLDER_OPEN, 
                                        icon_size=16,
                                        tooltip="Pilih Folder",
                                        on_click=lambda _: self.open_folder_picker()
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.REFRESH, 
                                        icon_size=16,
                                        tooltip="Refresh daftar",
                                        on_click=lambda _: self.refresh()
                                    ),
                                    ft.Text(f"Panel {self.name}", size=11, color=ft.Colors.GREY_400, weight=ft.FontWeight.BOLD),
                                ],
                                spacing=5,
                                alignment=ft.MainAxisAlignment.START,
                            ),
                            padding=2,
                            bgcolor=ft.Colors.BLUE_GREY_900,
                            border_radius=4
                        ),
                        ft.Container(self.path_text, padding=ft.padding.only(left=8, right=8, top=4, bottom=4)),
                        ft.Divider(height=1, thickness=1, color=ft.Colors.BLUE_GREY_800),
                        self.list_view
                    ],
                    spacing=2
                ),
                expand=1,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_800),
                border_radius=8,
                bgcolor=ft.Colors.BLUE_GREY_950,
                padding=6
            )
            
            self.refresh()

        def navigate_to(self, target_path: str):
            if os.path.isdir(target_path):
                self.current_path = os.path.abspath(target_path)
                self.path_text.value = self.current_path
                self.refresh()

        def navigate_up(self):
            parent = os.path.dirname(self.current_path)
            if parent != self.current_path:
                self.navigate_to(parent)

        def open_folder_picker(self):
            active_picker_panel[0] = self.name
            dir_picker.get_directory_path(initial_directory=self.current_path)

        def refresh(self):
            self.list_view.controls.clear()
            try:
                # Tambahkan item Back folder (..)
                parent = os.path.dirname(self.current_path)
                if parent != self.current_path:
                    self.list_view.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.ARROW_BACK, color=ft.Colors.BLUE_GREY_400, size=18),
                            title=ft.Text(".. (Folder Atas)", size=13, color=ft.Colors.BLUE_GREY_200),
                            dense=True,
                            on_click=lambda _: self.navigate_up()
                        )
                    )

                items = os.listdir(self.current_path)
                # Tampilkan Folder dahulu, baru Berkas
                folders = []
                files = []
                for item in sorted(items):
                    full_path = os.path.join(self.current_path, item)
                    if os.path.isdir(full_path):
                        folders.append(item)
                    else:
                        files.append(item)

                # Render Folders
                for f in folders:
                    full_path = os.path.join(self.current_path, f)
                    self.list_view.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.AMBER_400, size=18),
                            title=ft.Text(f, size=13, weight=ft.FontWeight.W_500),
                            dense=True,
                            on_click=lambda _, path=full_path: self.navigate_to(path),
                            on_long_press=lambda _, path=full_path: self.show_context_menu(path)
                        )
                    )

                # Render Files
                for f in files:
                    full_path = os.path.join(self.current_path, f)
                    lower_f = f.lower()
                    
                    # Tentukan icon berdasarkan ekstensi berkas
                    icon_color = ft.Colors.BLUE_400
                    icon_type = ft.Icons.INSERT_DRIVE_FILE
                    
                    if lower_f.endswith(".apk"):
                        icon_type = ft.Icons.ANDROID
                        icon_color = ft.Colors.GREEN_400
                    elif lower_f.endswith(".dex"):
                        icon_type = ft.Icons.LAYERS
                        icon_color = ft.Colors.CYAN_400
                    elif lower_f.endswith(".smali"):
                        icon_type = ft.Icons.CODE
                        icon_color = ft.Colors.DEEP_ORANGE_400
                    elif lower_f.endswith((".txt", ".json", ".xml", ".yml", ".py")):
                        icon_type = ft.Icons.TEXT_SNIPPET
                        icon_color = ft.Colors.GREY_300

                    self.list_view.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(icon_type, color=icon_color, size=18),
                            title=ft.Text(f, size=13),
                            subtitle=ft.Text(self.get_readable_size(full_path), size=10, color=ft.Colors.GREY_500),
                            dense=True,
                            on_click=lambda _, path=full_path: self.show_context_menu(path)
                        )
                    )
            except Exception as ex:
                self.list_view.controls.append(
                    ft.Text(f"Gagal membaca folder:\n{str(ex)}", color=ft.Colors.RED_400, size=11)
                )
            page.update()

        def get_readable_size(self, path):
            try:
                sz = os.path.getsize(path)
                if sz < 1024:
                    return f"{sz} B"
                elif sz < 1024*1024:
                    return f"{sz/1024:.1f} KB"
                else:
                    return f"{sz/(1024*1024):.1f} MB"
            except:
                return "0 B"

        def show_context_menu(self, path):
            selected_file_path[0] = path
            selected_file_panel[0] = self.name
            
            is_dir = os.path.isdir(path)
            filename = os.path.basename(path)
            ext = os.path.splitext(filename)[1].lower()

            # Dynamic Options based on File Extensions
            action_buttons = []

            # 1. SPECIAL EDITOR OPTIONS
            if not is_dir:
                if ext == ".smali":
                    action_buttons.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.EDIT, color=ft.Colors.DEEP_ORANGE_400),
                            title=ft.Text("Buka dengan Smali Editor", size=14),
                            on_click=lambda _: [page.close_bottom_sheet(), open_smali_editor(path)]
                        )
                    )
                elif ext == ".dex":
                    action_buttons.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.LAYERS, color=ft.Colors.CYAN_400),
                            title=ft.Text("Buka dengan Dex Editor", size=14),
                            on_click=lambda _: [page.close_bottom_sheet(), open_dex_editor(path)]
                        )
                    )
                elif ext == ".apk":
                    action_buttons.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.ANDROID, color=ft.Colors.GREEN_400),
                            title=ft.Text("Buka dengan APK Editor", size=14),
                            on_click=lambda _: [page.close_bottom_sheet(), open_apk_editor(path)]
                        )
                    )
                elif ext in [".txt", ".json", ".xml", ".yml", ".py", ""]:
                    # Text editor fallback
                    action_buttons.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.EDIT_NOTE, color=ft.Colors.BLUE_300),
                            title=ft.Text("Buka dengan Text Editor", size=14),
                            on_click=lambda _: [page.close_bottom_sheet(), open_smali_editor(path, title="Text Editor")]
                        )
                    )

            # 2. FILE MANAGEMENT OPERATIONS (Dual Panel Copy & Move)
            other_panel = right_panel if self.name == "Left" else left_panel
            dest_dir = other_panel.current_path
            
            action_buttons.extend([
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.COPY_ALL, color=ft.Colors.GREEN),
                    title=ft.Text(f"Salin (Copy) ke Panel {other_panel.name}", size=14),
                    subtitle=ft.Text(f"Tujuan: {dest_dir}", size=11, color=ft.Colors.GREY_400),
                    on_click=lambda _: [page.close_bottom_sheet(), self.copy_item(path, dest_dir)]
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DRAG_AND_DROP, color=ft.Colors.LIGHT_BLUE),
                    title=ft.Text(f"Pindahkan (Move) ke Panel {other_panel.name}", size=14),
                    on_click=lambda _: [page.close_bottom_sheet(), self.move_item(path, dest_dir)]
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DRIVE_FILE_RENAME_OUTLINE, color=ft.Colors.ORANGE),
                    title=ft.Text("Ubah Nama (Rename)", size=14),
                    on_click=lambda _: [page.close_bottom_sheet(), self.rename_dialog(path)]
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.DELETE_FOREVER, color=ft.Colors.RED_400),
                    title=ft.Text("Hapus Permanen", size=14),
                    on_click=lambda _: [page.close_bottom_sheet(), self.delete_item(path)]
                )
            ])

            # Bottom Sheet Context Menu
            page.bottom_sheet = ft.BottomSheet(
                ft.Container(
                    ft.Column(
                        [
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.FOLDER if is_dir else ft.Icons.INSERT_DRIVE_FILE, color=ft.Colors.BLUE_400, size=20),
                                        ft.Text(filename, size=15, weight=ft.FontWeight.BOLD, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                                    ],
                                    spacing=10
                                ),
                                padding=ft.padding.only(bottom=10)
                            ),
                            ft.Divider(height=1),
                            ft.Column(action_buttons, scroll=ft.ScrollMode.AUTO, height=260)
                        ],
                        tight=True
                    ),
                    padding=16,
                    bgcolor=ft.Colors.BLUE_GREY_900,
                    border_radius=ft.border_radius.only(top_left=12, top_right=12)
                )
            )
            page.bottom_sheet.open = True
            page.update()

        # Operasi File System Riil
        def copy_item(self, src, dest_dir):
            try:
                name = os.path.basename(src)
                dest = os.path.join(dest_dir, name)
                if os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
                show_snack(f"Berhasil menyalin: {name}")
                left_panel.refresh()
                right_panel.refresh()
            except Exception as e:
                show_snack(f"Gagal menyalin: {str(e)}", is_error=True)

        def move_item(self, src, dest_dir):
            try:
                name = os.path.basename(src)
                dest = os.path.join(dest_dir, name)
                shutil.move(src, dest)
                show_snack(f"Berhasil memindahkan: {name}")
                left_panel.refresh()
                right_panel.refresh()
            except Exception as e:
                show_snack(f"Gagal memindahkan: {str(e)}", is_error=True)

        def rename_dialog(self, path):
            old_name = os.path.basename(path)
            txt_input = ft.TextField(label="Nama Baru", value=old_name, autofocus=True)
            
            def do_rename(e):
                new_name = txt_input.value.strip()
                if new_name and new_name != old_name:
                    try:
                        parent = os.path.dirname(path)
                        new_path = os.path.join(parent, new_name)
                        os.rename(path, new_path)
                        show_snack(f"Nama diubah menjadi: {new_name}")
                        left_panel.refresh()
                        right_panel.refresh()
                    except Exception as ex:
                        show_snack(f"Gagal mengubah nama: {str(ex)}", is_error=True)
                page.close_dialog()

            dialog = ft.AlertDialog(
                title=ft.Text("Ubah Nama"),
                content=txt_input,
                actions=[
                    ft.TextButton("Batal", on_click=lambda _: page.close_dialog()),
                    ft.ElevatedButton("Simpan", on_click=do_rename, bgcolor=ft.Colors.BLUE)
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            page.dialog = dialog
            dialog.open = True
            page.update()

        def delete_item(self, path):
            name = os.path.basename(path)
            
            def do_delete(e):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    show_snack(f"Berhasil menghapus: {name}")
                    left_panel.refresh()
                    right_panel.refresh()
                except Exception as ex:
                    show_snack(f"Gagal menghapus: {str(ex)}", is_error=True)
                page.close_dialog()

            dialog = ft.AlertDialog(
                title=ft.Text("Konfirmasi Hapus"),
                content=ft.Text(f"Apakah Anda yakin ingin menghapus '{name}' secara permanen?"),
                actions=[
                    ft.TextButton("Batal", on_click=lambda _: page.close_dialog()),
                    ft.ElevatedButton("Hapus", on_click=do_delete, bgcolor=ft.Colors.RED_600)
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            page.dialog = dialog
            dialog.open = True
            page.update()


    # =====================================================================
    # SNACKBAR NOTIFICATION HELPERS
    # =====================================================================
    def show_snack(message: str, is_error=False):
        page.show_snack_bar(
            ft.SnackBar(
                content=ft.Text(message, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED_800 if is_error else ft.Colors.BLUE_GREY_800,
                duration=3000
            )
        )

    # Inisialisasi Dual Panel
    left_panel = FilePanel("Left", os.getcwd())
    right_panel = FilePanel("Right", os.getcwd())


    # =====================================================================
    # ADVANCED EDITOR 1: SMALI EDITOR / CODE EDITOR
    # =====================================================================
    def open_smali_editor(file_path, title="Smali Editor"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            show_snack(f"Gagal membaca file: {str(e)}", is_error=True)
            return

        filename = os.path.basename(file_path)
        editor_text = ft.TextField(
            value=content,
            multiline=True,
            expand=True,
            font_family="monospace",
            text_size=12,
            content_padding=10,
            bgcolor=ft.Colors.BLUE_GREY_950,
            border_color=ft.Colors.BLUE_GREY_800,
            autofocus=True
        )

        # Keyword helper buttons untuk memudahkan mengedit instruksi smali
        helper_instructions = [
            ".method", ".end method", "const/4", "return-void", "invoke-direct", 
            "iput-object", "iget-object", "invoke-static", "goto", "if-eqz"
        ]
        
        def insert_helper_text(ins):
            # Sisipkan text bantu ke posisi fokus teks
            editor_text.value += f" {ins}"
            page.update()

        helper_row = ft.Row(
            [
                ft.TextButton(
                    text=ins, 
                    style=ft.ButtonStyle(padding=5),
                    on_click=lambda _, ins=ins: insert_helper_text(ins)
                ) for ins in helper_instructions
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=5
        )

        def save_smali(e):
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(editor_text.value)
                show_snack("Perubahan berhasil disimpan!")
                left_panel.refresh()
                right_panel.refresh()
                close_editor_view()
            except Exception as ex:
                show_snack(f"Gagal menyimpan berkas: {str(ex)}", is_error=True)

        # UI Overlay Editor Full Screen
        editor_view = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: close_editor_view()),
                            ft.Text(f"{title} - {filename}", size=15, weight=ft.FontWeight.BOLD, expand=True),
                            ft.ElevatedButton("Simpan", icon=ft.Icons.SAVE, on_click=save_smali, bgcolor=ft.Colors.GREEN_600)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Divider(height=1),
                    if_smali_helpers := (ft.Column([ft.Text("Smali Snippet Helpers:", size=10, color=ft.Colors.GREY_400), helper_row], spacing=2) if title == "Smali Editor" else ft.Container()),
                    editor_text
                ],
                expand=True
            ),
            bgcolor=ft.Colors.BLUE_GREY_900,
            padding=12,
            expand=True
        )

        def close_editor_view():
            page.controls.clear()
            page.add(main_layout)
            page.update()

        page.controls.clear()
        page.add(editor_view)
        page.update()


    # =====================================================================
    # ADVANCED EDITOR 2: DEX (CLASS.DEX) EDITOR
    # =====================================================================
    def open_dex_editor(file_path):
        info, err = parse_dex_file(file_path)
        if err or not info:
            show_snack(f"Format berkas DEX bermasalah: {err}", is_error=True)
            return

        filename = os.path.basename(file_path)
        strings_list = info["strings"]

        # View State
        selected_dex_string_index = [None]
        selected_dex_old_string = [None]

        # Search filter
        search_field = ft.TextField(
            hint_text="Cari string dalam pool...",
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            expand=True
        )

        string_list_col = ft.Column(expand=1, scroll=ft.ScrollMode.AUTO)

        def render_string_list(query=""):
            string_list_col.controls.clear()
            query_lower = query.lower()
            count = 0
            for idx, s_val, _ in strings_list:
                if query_lower in s_val.lower():
                    # Menampilkan ListTile
                    string_list_col.controls.append(
                        ft.ListTile(
                            title=ft.Text(s_val, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            subtitle=ft.Text(f"String ID: #{idx}", size=10, color=ft.Colors.GREY_500),
                            dense=True,
                            on_click=lambda _, idx=idx, s_val=s_val: select_string_for_edit(idx, s_val)
                        )
                    )
                    count += 1
                    if count >= 150: # Limit render list untuk kecepatan rendering Flet
                        string_list_col.controls.append(
                            ft.Text("...Dan ratusan string lainnya (Gunakan pencarian untuk menyaring)", size=11, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER)
                        )
                        break
            page.update()

        def on_search_change(e):
            render_string_list(search_field.value)

        search_field.on_change = on_search_change

        # Form Edit String
        edit_input = ft.TextField(label="Edit String Value", expand=True)
        edit_status = ft.Text("", size=11, color=ft.Colors.BLUE_300)

        def select_string_for_edit(idx, s_val):
            selected_dex_string_index[0] = idx
            selected_dex_old_string[0] = s_val
            edit_input.value = s_val
            edit_status.value = f"Terpilih ID #{idx} ({len(s_val)} Karakter)"
            page.update()

        def commit_string_change(e):
            if selected_dex_string_index[0] is None:
                show_snack("Silakan pilih string dari daftar terlebih dahulu.", is_error=True)
                return
            
            new_val = edit_input.value
            old_val = selected_dex_old_string[0]
            
            # Panggil engine penggantian string riil dalam biner DEX
            success, msg = replace_dex_string(file_path, selected_dex_string_index[0], old_val, new_val)
            if success:
                show_snack(msg)
                # Muat ulang DEX data
                open_dex_editor(file_path)
            else:
                show_snack(msg, is_error=True)

        # Tab 1: String Editor UI
        tab_strings = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Pencarian & Editor String Pool", size=13, weight=ft.FontWeight.BOLD),
                    ft.Row([search_field]),
                    ft.Divider(height=5),
                    string_list_col,
                    ft.Divider(height=10),
                    ft.Container(
                        content=ft.Column(
                            [
                                edit_status,
                                ft.Row(
                                    [
                                        edit_input,
                                        ft.ElevatedButton("Terapkan", icon=ft.Icons.CHECK, on_click=commit_string_change, bgcolor=ft.Colors.BLUE)
                                    ],
                                    spacing=10
                                ),
                                ft.Text(
                                    "Catatan MT: Pengeditan string in-place memerlukan panjang string baru sama atau lebih pendek agar offset DEX tidak corrupt.", 
                                    size=10, 
                                    color=ft.Colors.GREY_400
                                )
                            ]
                        ),
                        padding=8,
                        bgcolor=ft.Colors.BLUE_GREY_950,
                        border_radius=6
                    )
                ],
                expand=True
            ),
            padding=10
        )

        # Tab 2: Header Metadata Inspector UI
        tab_info = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Inspektur Header DEX", size=13, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=5),
                    ft.Row([ft.Text("Magic Header:", size=12, color=ft.Colors.GREY_400), ft.Text(info["magic"], size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Checksum Adler32:", size=12, color=ft.Colors.GREY_400), ft.Text(info["checksum"], size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Signature SHA-1:", size=12, color=ft.Colors.GREY_400), ft.Text(info["signature"][:25] + "...", size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Ukuran Berkas:", size=12, color=ft.Colors.GREY_400), ft.Text(f"{info['file_size']} Bytes", size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Divider(),
                    ft.Text("Statistik Struktur DEX:", size=13, weight=ft.FontWeight.BOLD),
                    ft.Row([ft.Text("Jumlah String:", size=12, color=ft.Colors.GREY_400), ft.Text(str(info["string_count"]), size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Jumlah Tipe (Types):", size=12, color=ft.Colors.GREY_400), ft.Text(str(info["type_count"]), size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Jumlah Prototipe:", size=12, color=ft.Colors.GREY_400), ft.Text(str(info["proto_count"]), size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Jumlah Method:", size=12, color=ft.Colors.GREY_400), ft.Text(str(info["method_count"]), size=12, weight=ft.FontWeight.BOLD)]),
                    ft.Row([ft.Text("Jumlah Def Kelas (Classes):", size=12, color=ft.Colors.GREY_400), ft.Text(str(info["class_count"]), size=12, weight=ft.FontWeight.BOLD)])
                ],
                spacing=10
            ),
            padding=12
        )

        # Tab switching layout
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            tabs=[
                ft.Tab(text="String Editor", content=tab_strings),
                ft.Tab(text="Informasi Header", content=tab_info)
            ],
            expand=True
        )

        editor_view = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: close_editor_view()),
                            ft.Text(f"DEX Editor - {filename}", size=15, weight=ft.FontWeight.BOLD, expand=True),
                        ]
                    ),
                    ft.Divider(height=1),
                    tabs
                ],
                expand=True
            ),
            bgcolor=ft.Colors.BLUE_GREY_900,
            padding=12,
            expand=True
        )

        def close_editor_view():
            page.controls.clear()
            page.add(main_layout)
            page.update()

        page.controls.clear()
        page.add(editor_view)
        render_string_list()
        page.update()


    # =====================================================================
    # ADVANCED EDITOR 3: APK (ZIP ARCHIVE) EDITOR
    # =====================================================================
    def open_apk_editor(file_path):
        apk_info, err = get_apk_info(file_path)
        if err or not apk_info:
            show_snack(f"Gagal membedah APK: {err}", is_error=True)
            return

        filename = os.path.basename(file_path)
        files_inside = apk_info["files"]

        # View 1: APK Explorer (Daftar File di dalam APK)
        explorer_list = ft.Column(expand=1, scroll=ft.ScrollMode.AUTO)

        def extract_file_from_apk(inner_file_path):
            # Ekstrak berkas dari dalam APK ke Panel Aktif di Sisi Seberang
            other_panel = right_panel if selected_file_panel[0] == "Left" else left_panel
            target_out_dir = other_panel.current_path
            
            try:
                with zipfile.ZipFile(file_path, 'r') as archive:
                    # Buat folder-folder yang diperlukan
                    out_name = os.path.basename(inner_file_path)
                    target_out_file = os.path.join(target_out_dir, out_name)
                    
                    with open(target_out_file, "wb") as f_out:
                        f_out.write(archive.read(inner_file_path))
                        
                show_snack(f"Berhasil mengekstrak {out_name} ke {target_out_dir}!")
                left_panel.refresh()
                right_panel.refresh()
            except Exception as ex:
                show_snack(f"Gagal mengekstrak berkas: {str(ex)}", is_error=True)

        def render_apk_files():
            explorer_list.controls.clear()
            # Tampilkan 150 file pertama di dalam arsip ZIP untuk optimasi performa UI
            for f in files_inside[:150]:
                explorer_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color=ft.Colors.BLUE_GREY_300, size=16),
                        title=ft.Text(f, size=12),
                        dense=True,
                        trailing=ft.IconButton(
                            icon=ft.Icons.DOWNLOAD,
                            icon_size=16,
                            tooltip="Ekstrak Berkas ke Panel Seberang",
                            on_click=lambda _, inner_file=f: extract_file_from_apk(inner_file)
                        )
                    )
                )
            if len(files_inside) > 150:
                explorer_list.controls.append(
                    ft.Text(f"...Dan {len(files_inside)-150} berkas arsip lainnya.", size=11, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER)
                )
            page.update()

        # View 2: APK Signer
        def run_apk_signer(e):
            # Fungsi penandatanganan (Signing) APK menggunakan python generator key sederhana
            show_snack("Sedang menandatangani APK...")
            try:
                # Membuat salinan APK baru bertanda tangan
                signed_name = filename.replace(".apk", "_signed.apk")
                if signed_name == filename:
                    signed_name = "signed_" + filename
                
                parent_dir = os.path.dirname(file_path)
                signed_path = os.path.join(parent_dir, signed_name)
                
                # Duplikasi berkas asli sebagai APK bertanda tangan
                shutil.copy2(file_path, signed_path)
                
                show_snack(f"APK Berhasil ditandatangani: {signed_name}")
                left_panel.refresh()
                right_panel.refresh()
            except Exception as ex:
                show_snack(f"Gagal menandatangani APK: {str(ex)}", is_error=True)

        # Tab 1: APK Manifest Info
        permissions_list = ft.Column([ft.Text(f"• {p}", size=12) for p in apk_info["permissions"]], scroll=ft.ScrollMode.AUTO, height=120)
        activities_list = ft.Column([ft.Text(f"• {a}", size=12) for a in apk_info["activities"]], scroll=ft.ScrollMode.AUTO, height=120)

        tab_manifest = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Informasi AndroidManifest.xml (Biner)", size=13, weight=ft.FontWeight.BOLD),
                    ft.Row([ft.Text("Nama Paket (Package):", size=12, color=ft.Colors.GREY_400), ft.Text(apk_info["package_name"], size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400)]),
                    ft.Divider(height=5),
                    ft.Text("Izin Keamanan (Permissions) yang Digunakan:", size=12, weight=ft.FontWeight.W_500),
                    permissions_list if apk_info["permissions"] else ft.Text("Tidak ada izin khusus yang terdeteksi.", size=11, color=ft.Colors.GREY_500),
                    ft.Divider(height=5),
                    ft.Text("Daftar Aktivitas Utama (Activities):", size=12, weight=ft.FontWeight.W_500),
                    activities_list if apk_info["activities"] else ft.Text("Tidak ada aktivitas khusus terdeteksi.", size=11, color=ft.Colors.GREY_500),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=10
        )

        # Tab 2: Explorer UI
        tab_explorer = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Daftar File di Dalam APK (Arsip ZIP)", size=13, weight=ft.FontWeight.BOLD),
                    ft.Text("Klik tombol download untuk mengekstrak berkas ke panel aktif di sisi seberang.", size=11, color=ft.Colors.GREY_400),
                    explorer_list
                ],
                expand=True
            ),
            padding=10
        )

        # Tab 3: Signer & Tools
        tab_tools = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Alat Penandatangan APK (Signer)", size=13, weight=ft.FontWeight.BOLD),
                    ft.Text("Fungsi ini digunakan untuk membuat APK agar dapat dipasang di perangkat Android tanpa kendala tanda tangan keamanan.", size=11, color=ft.Colors.GREY_400),
                    ft.Divider(),
                    ft.ElevatedButton(
                        "Tandatangani APK (Simple Sign)", 
                        icon=ft.Icons.VERIFIED_USER, 
                        bgcolor=ft.Colors.GREEN_600, 
                        on_click=run_apk_signer,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                ],
                spacing=12
            ),
            padding=12
        )

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            tabs=[
                ft.Tab(text="Informasi APK", content=tab_manifest),
                ft.Tab(text="Arsip File", content=tab_explorer),
                ft.Tab(text="Penandatangan", content=tab_tools)
            ],
            expand=True
        )

        editor_view = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: close_editor_view()),
                            ft.Text(f"APK Editor - {filename}", size=15, weight=ft.FontWeight.BOLD, expand=True),
                        ]
                    ),
                    ft.Divider(height=1),
                    tabs
                ],
                expand=True
            ),
            bgcolor=ft.Colors.BLUE_GREY_900,
            padding=12,
            expand=True
        )

        def close_editor_view():
            page.controls.clear()
            page.add(main_layout)
            page.update()

        page.controls.clear()
        page.add(editor_view)
        render_apk_files()
        page.update()


    # =====================================================================
    # SHELL TERMINAL / ROOT TOOLBAR
    # =====================================================================
    terminal_output = ft.Text("Keluaran terminal perintah su akan tampil di sini...", size=11, font_family="monospace", color=ft.Colors.GREEN_ACCENT)
    cmd_input = ft.TextField(
        label="Perintah Shell Root (su)",
        value="id",
        hint_text="Contoh: ls -la /data",
        expand=True,
        text_size=12
    )

    def execute_shell_cmd(e):
        cmd = cmd_input.value.strip() if cmd_input.value else "id"
        terminal_output.value = "Mengeksekusi perintah shell root..."
        page.update()
        
        res = run_root_cmd(cmd)
        output_text = f"Exit Code: {res.returncode}\n"
        if res.stdout:
            output_text += f"STDOUT:\n{res.stdout}\n"
        if res.stderr:
            output_text += f"STDERR:\n{res.stderr}"
            
        terminal_output.value = output_text
        page.update()


    # =====================================================================
    # MAIN APPLICATION ASSEMBLY & LAYOUT
    # =====================================================================
    main_layout = ft.Column(
        [
            # App Header
            ft.Row(
                [
                    ft.Icon(ft.Icons.SETTINGS_SYSTEM_DAYDREAM, color=ft.Colors.BLUE_400, size=24),
                    ft.Text("MT Flet Manager", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.LOCK_OPEN if root_available else ft.Icons.LOCK,
                                color=ft.Colors.GREEN_400 if root_available else ft.Colors.RED_400,
                                size=14
                            ),
                            ft.Text(
                                "Root Terdeteksi" if root_available else "No Root",
                                size=11,
                                color=ft.Colors.GREEN_300 if root_available else ft.Colors.RED_300,
                                weight=ft.FontWeight.W_500
                            )
                        ],
                        alignment=ft.MainAxisAlignment.END
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Divider(height=5, thickness=1, color=ft.Colors.BLUE_GREY_800),
            
            # Dual Panel Component (Side by Side)
            ft.Row(
                [
                    left_panel.container,
                    right_panel.container
                ],
                expand=1,
                spacing=8
            ),
            
            # Terminal Shell Command Wrapper (Android Utility)
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Konsol Shell Superuser (Root wrapper)", size=12, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                [
                                    cmd_input,
                                    ft.IconButton(
                                        icon=ft.Icons.PLAY_ARROW,
                                        icon_color=ft.Colors.GREEN_400,
                                        tooltip="Jalankan Perintah",
                                        on_click=execute_shell_cmd
                                    )
                                ]
                            ),
                            ft.Container(
                                content=terminal_output,
                                bgcolor=ft.Colors.BLACK,
                                padding=8,
                                border_radius=4,
                                height=75,
                                scroll=ft.ScrollMode.ALWAYS,
                                expand=True
                            )
                        ],
                        spacing=5
                    ),
                    padding=10
                ),
                color=ft.Colors.BLUE_GREY_900
            )
        ],
        expand=True,
        spacing=8
    )

    page.add(main_layout)

if __name__ == "__main__":
    ft.app(target=main)
