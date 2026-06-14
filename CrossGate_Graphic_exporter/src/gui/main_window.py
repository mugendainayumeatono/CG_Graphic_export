import os
from PIL.ImageQt import ImageQt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QListWidget, QLabel, QComboBox, 
                               QFileDialog, QMessageBox, QLineEdit, QProgressDialog, QApplication)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

from core.palet import palet_manager
from core.graphic_info import graphic_info_manager
from core.graphic_data import graphic_data_manager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CrossGate Graphic Exporter")
        self.resize(1000, 700)
        
        self.current_graphic = None
        self.graphics_list = []
        
        self.setup_ui()
        self.auto_scan_dirs()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Left Panel - Controls & List
        left_panel = QVBoxLayout()
        
        # Bin Directory Selection
        bin_dir_layout = QHBoxLayout()
        self.bin_dir_input = QLineEdit()
        self.bin_dir_input.setReadOnly(True)
        self.browse_bin_btn = QPushButton("Browse")
        self.browse_bin_btn.clicked.connect(self.browse_bin_directory)
        bin_dir_layout.addWidget(QLabel("Bin Dir:"))
        bin_dir_layout.addWidget(self.bin_dir_input)
        bin_dir_layout.addWidget(self.browse_bin_btn)
        
        # Pal Directory Selection
        pal_dir_layout = QHBoxLayout()
        self.pal_dir_input = QLineEdit()
        self.pal_dir_input.setReadOnly(True)
        self.browse_pal_btn = QPushButton("Browse")
        self.browse_pal_btn.clicked.connect(self.browse_pal_directory)
        pal_dir_layout.addWidget(QLabel("Pal Dir:"))
        pal_dir_layout.addWidget(self.pal_dir_input)
        pal_dir_layout.addWidget(self.browse_pal_btn)
        
        # Palette Selection
        pal_layout = QHBoxLayout()
        self.pal_combo = QComboBox()
        self.pal_combo.currentIndexChanged.connect(self.update_preview)
        pal_layout.addWidget(QLabel("Palette:"))
        pal_layout.addWidget(self.pal_combo)
        
        # Graphics List
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.on_graphic_selected)
        
        # Action Buttons
        self.export_btn = QPushButton("Export Preview")
        self.export_btn.clicked.connect(self.export_preview)
        self.export_all_btn = QPushButton("Export All")
        self.export_all_btn.clicked.connect(self.export_all)
        
        left_panel.addLayout(bin_dir_layout)
        left_panel.addLayout(pal_dir_layout)
        left_panel.addLayout(pal_layout)
        left_panel.addWidget(QLabel("Graphics List:"))
        left_panel.addWidget(self.list_widget)
        left_panel.addWidget(self.export_btn)
        left_panel.addWidget(self.export_all_btn)
        
        # Right Panel - Preview
        right_panel = QVBoxLayout()
        self.preview_label = QLabel("Preview Area")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #333; color: white;")
        
        right_panel.addWidget(self.preview_label)
        
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 3)

    def auto_scan_dirs(self):
        cwd = os.getcwd()
        search_dirs = [
            cwd,
            os.path.dirname(cwd)
        ]
        
        found_bin = None
        found_pal = None
        for d in search_dirs:
            b_dir = os.path.join(d, "bin")
            p_dir = os.path.join(d, "pal")
            if os.path.exists(b_dir) and not found_bin:
                found_bin = b_dir
            if os.path.exists(p_dir) and not found_pal:
                found_pal = p_dir
                
        if found_bin:
            self.load_bin_directory(found_bin)
        if found_pal:
            self.load_pal_directory(found_pal)

    def browse_bin_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Bin Directory")
        if dir_path:
            self.load_bin_directory(dir_path)

    def browse_pal_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Pal Directory")
        if dir_path:
            self.load_pal_directory(dir_path)

    def load_bin_directory(self, bin_dir):
        if not os.path.exists(bin_dir):
            QMessageBox.warning(self, "Error", f"Directory not found: {bin_dir}")
            return
            
        self.bin_dir_input.setText(bin_dir)
        
        # Load Graphics Info
        graphic_info_manager._cache.clear()
        graphic_info_manager._index_cache.clear()
        gi_success, gi_errs = graphic_info_manager.init_graphics(bin_dir)
        
        self.graphics_list = graphic_info_manager.get_all_graphics()
        
        # Update List
        self.list_widget.clear()
        for g in self.graphics_list:
            self.list_widget.addItem(f"Serial: {g.serial} | Index: {g.index}")
            
        if gi_errs:
            err_msg = "\n".join(gi_errs[:10])
            if len(gi_errs) > 10:
                err_msg += f"\n... 以及其他 {len(gi_errs)-10} 个错误"
            QMessageBox.warning(self, "加载时发生部分错误", f"成功加载 {gi_success} 个图档索引。\n\n发生了以下错误：\n{err_msg}")
        else:
            QMessageBox.information(self, "Loaded", f"Successfully loaded {len(self.graphics_list)} graphics.")

    def load_pal_directory(self, pal_dir):
        if not os.path.exists(pal_dir):
            QMessageBox.warning(self, "Error", f"Directory not found: {pal_dir}")
            return
            
        self.pal_dir_input.setText(pal_dir)
        
        # Load Palettes
        palet_manager._cache.clear()
        palet_success, palet_errs = palet_manager.init_palettes(pal_dir)
        
        # Update Palette Combo
        self.pal_combo.clear()
        self.pal_combo.addItem("Default (0)", 0)
        
        def sort_key(k):
            if isinstance(k, int): return (0, k)
            return (1, str(k))
            
        for p_idx in sorted(palet_manager._cache.keys(), key=sort_key):
            self.pal_combo.addItem(f"Palette {p_idx}", p_idx)
            
        if palet_errs:
            err_msg = "\n".join(palet_errs[:10])
            if len(palet_errs) > 10:
                err_msg += f"\n... 以及其他 {len(palet_errs)-10} 个错误"
            QMessageBox.warning(self, "加载调色板时发生部分错误", f"成功加载 {palet_success} 个调色板。\n\n发生了以下错误：\n{err_msg}")

    def on_graphic_selected(self, index):
        if 0 <= index < len(self.graphics_list):
            self.current_graphic = self.graphics_list[index]
            self.update_preview()

    def update_preview(self):
        if not self.current_graphic:
            return
            
        palet_idx = self.pal_combo.currentData()
        if palet_idx is None:
            palet_idx = 0
            
        try:
            img = graphic_data_manager.get_graphic_image(self.current_graphic, palet_idx)
            if img:
                data = img.tobytes("raw", "RGBA")
                qim = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
                pix = QPixmap.fromImage(qim.copy())
                self.preview_label.setPixmap(pix)
            else:
                self.preview_label.setText("Failed to load graphic")
        except Exception as e:
            self.preview_label.setText(f"加载失败: {str(e)}")

    def export_preview(self):
        if not self.current_graphic:
            return
            
        palet_idx = self.pal_combo.currentData()
        if palet_idx is None:
            palet_idx = 0
            
        try:
            img = graphic_data_manager.get_graphic_image(self.current_graphic, palet_idx)
            if img:
                save_path, _ = QFileDialog.getSaveFileName(self, "Save Graphic", f"graphic_{self.current_graphic.serial}_{palet_idx}.png", "PNG Files (*.png)")
                if save_path:
                    img.save(save_path)
                    QMessageBox.information(self, "Exported", f"Successfully exported to {save_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"渲染并导出该图像时出错:\n{str(e)}")

    def export_all(self):
        if not self.graphics_list:
            return
            
        palet_idx = self.pal_combo.currentData()
        if palet_idx is None:
            palet_idx = 0
            
        export_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if export_dir:
            success_count = 0
            fail_count = 0
            total_count = len(self.graphics_list)
            
            progress = QProgressDialog("Exporting Graphics...", "Cancel", 0, total_count, self)
            progress.setWindowTitle("Export Progress")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            for i, g in enumerate(self.graphics_list):
                if progress.wasCanceled():
                    break
                    
                try:
                    img = graphic_data_manager.get_graphic_image(g, palet_idx)
                    if img:
                        save_path = os.path.join(export_dir, f"graphic_{g.serial}_{palet_idx}.png")
                        img.save(save_path)
                        success_count += 1
                except Exception:
                    fail_count += 1
                    pass
                    
                progress.setValue(i + 1)
                QApplication.processEvents()
            
            progress.setValue(total_count)
            msg = f"Successfully exported {success_count} images."
            if fail_count > 0:
                msg += f"\n\nFailed to export {fail_count} images due to errors."
                QMessageBox.warning(self, "Export Complete with Errors", msg)
            else:
                QMessageBox.information(self, "Export Complete", msg)
