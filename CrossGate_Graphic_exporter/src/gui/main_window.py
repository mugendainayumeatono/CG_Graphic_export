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
        
        # Directory Selection
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        self.browse_btn = QPushButton("Browse Base Dir")
        self.browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(QLabel("Base Dir:"))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_btn)
        
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
        
        left_panel.addLayout(dir_layout)
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
        # Let's try to find bin and pal near the current directory
        cwd = os.getcwd()
        # Look in current, parent, and sibling references
        search_dirs = [
            cwd,
            os.path.dirname(cwd),
            os.path.join(os.path.dirname(cwd), "reference", "CGTool")
        ]
        
        found = False
        for d in search_dirs:
            bin_dir = os.path.join(d, "bin")
            if os.path.exists(bin_dir):
                self.load_base_directory(d)
                found = True
                break
                
        if not found:
            QMessageBox.information(self, "Auto Scan", "Could not auto-detect 'bin' directory. Please manually select the base directory containing 'bin' and 'pal' folders.")

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Base Directory")
        if dir_path:
            self.load_base_directory(dir_path)

    def load_base_directory(self, base_dir):
        bin_dir = os.path.join(base_dir, "bin")
        pal_dir = os.path.join(base_dir, "pal")
        
        if not os.path.exists(bin_dir):
            QMessageBox.warning(self, "Error", f"'bin' directory not found in {base_dir}")
            return
            
        self.dir_input.setText(base_dir)
        
        # Load Palettes
        palet_manager._cache.clear()
        if os.path.exists(pal_dir):
            palet_manager.init_palettes(pal_dir)
        
        # Update Palette Combo
        self.pal_combo.clear()
        self.pal_combo.addItem("Default (0)", 0)
        for p_idx in sorted(palet_manager._cache.keys()):
            self.pal_combo.addItem(f"Palette {p_idx}", p_idx)
            
        # Load Graphics Info
        graphic_info_manager._cache.clear()
        graphic_info_manager._index_cache.clear()
        graphic_info_manager.init_graphics(bin_dir)
        
        self.graphics_list = graphic_info_manager.get_all_graphics()
        
        # Update List
        self.list_widget.clear()
        for g in self.graphics_list:
            self.list_widget.addItem(f"Serial: {g.serial} | Index: {g.index}")
            
        QMessageBox.information(self, "Loaded", f"Loaded {len(self.graphics_list)} graphics.")

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
            
        img = graphic_data_manager.get_graphic_image(self.current_graphic, palet_idx)
        if img:
            qim = ImageQt(img)
            pix = QPixmap.fromImage(qim)
            self.preview_label.setPixmap(pix)
        else:
            self.preview_label.setText("Failed to load graphic")

    def export_preview(self):
        if not self.current_graphic:
            return
            
        palet_idx = self.pal_combo.currentData()
        if palet_idx is None:
            palet_idx = 0
            
        img = graphic_data_manager.get_graphic_image(self.current_graphic, palet_idx)
        if img:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Graphic", f"graphic_{self.current_graphic.serial}_{palet_idx}.png", "PNG Files (*.png)")
            if save_path:
                img.save(save_path)
                QMessageBox.information(self, "Exported", f"Successfully exported to {save_path}")

    def export_all(self):
        if not self.graphics_list:
            return
            
        palet_idx = self.pal_combo.currentData()
        if palet_idx is None:
            palet_idx = 0
            
        export_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if export_dir:
            success_count = 0
            total_count = len(self.graphics_list)
            
            progress = QProgressDialog("Exporting Graphics...", "Cancel", 0, total_count, self)
            progress.setWindowTitle("Export Progress")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            for i, g in enumerate(self.graphics_list):
                if progress.wasCanceled():
                    break
                    
                img = graphic_data_manager.get_graphic_image(g, palet_idx)
                if img:
                    save_path = os.path.join(export_dir, f"graphic_{g.serial}_{palet_idx}.png")
                    img.save(save_path)
                    success_count += 1
                    
                progress.setValue(i + 1)
                QApplication.processEvents()
            
            progress.setValue(total_count)
            QMessageBox.information(self, "Export Complete", f"Successfully exported {success_count} images.")
