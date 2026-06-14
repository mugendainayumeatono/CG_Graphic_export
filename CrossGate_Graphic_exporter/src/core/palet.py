import os
import struct

HEAD_PLATE_RGB = [
    (0, 0, 0, 0),       # 0x000000 (Transparent)
    (128, 0, 0, 255),   # 0x000080
    (0, 128, 0, 255),   # 0x008000
    (128, 128, 0, 255), # 0x008080
    (128, 0, 128, 255), # 0x800080
    (0, 0, 128, 255),   # 0x800000
    (0, 128, 128, 255), # 0x808000
    (192, 192, 192, 255), # 0xc0c0c0
    (192, 220, 192, 255), # 0xc0dcc0
    (166, 202, 240, 255), # 0xf0caa6
    (222, 0, 0, 255),   # 0x0000de
    (255, 95, 0, 255),  # 0x005fff
    (255, 255, 160, 255), # 0xa0ffff
    (0, 95, 210, 255),  # 0xd25f00
    (80, 210, 255, 255), # 0xffd250
    (40, 225, 40, 255), # 0x28e128
]

FOOT_PLATE_RGB = [
    (245, 195, 150, 255), # 0x96c3f5
    (30, 160, 95, 255),   # 0x5fa01e
    (195, 125, 70, 255),  # 0x467dc3
    (155, 85, 30, 255),   # 0x1e559b
    (70, 65, 55, 255),    # 0x374146
    (40, 35, 30, 255),    # 0x1e2328
    (255, 251, 240, 255), # 0xf0fbff
    (58, 110, 165, 255),  # 0xa56e3a
    (128, 128, 128, 255), # 0x808080
    (255, 0, 0, 255),     # 0x0000ff
    (0, 255, 0, 255),     # 0x00ff00
    (255, 255, 0, 255),   # 0x00ffff
    (0, 0, 255, 255),     # 0xff0000
    (255, 128, 255, 255), # 0xff80ff
    (0, 255, 255, 255),   # 0xffff00
    (255, 255, 255, 255), # 0xffffff
]

class Palet:
    def __init__(self):
        self._cache = {}

    def init_palettes(self, pal_dir):
        errors = []
        success_count = 0
        if not os.path.exists(pal_dir):
            errors.append(f"调色板目录不存在: {pal_dir}")
            return success_count, errors
        
        for filename in os.listdir(pal_dir):
            if filename.lower().startswith("palet_") and filename.lower().endswith(".cgp"):
                try:
                    parts = filename.lower().split('_')
                    index_str = parts[1].split('.')[0]
                    try:
                        index = int(index_str)
                    except ValueError:
                        index = index_str
                    
                    filepath = os.path.join(pal_dir, filename)
                    pal_data = self._load_palet(filepath)
                    if pal_data:
                        self._cache[index] = pal_data
                        success_count += 1
                except Exception as e:
                    errors.append(f"加载调色板 {filename} 失败: {str(e)}")
                    
        return success_count, errors
                    
    def get_palet(self, index):
        if index in self._cache:
            return self._cache[index]
        return None
        
    def _load_palet(self, filepath):
        colors = []
        colors.extend(HEAD_PLATE_RGB)
        
        with open(filepath, 'rb') as f:
            for _ in range(224):
                data = f.read(3)
                if not data or len(data) < 3:
                    raise ValueError(f"调色板数据长度不足")
                # B, G, R
                b, g, r = struct.unpack('BBB', data)
                colors.append((r, g, b, 255))
            
        colors.extend(FOOT_PLATE_RGB)
        
        # Add clear color at the very end just in case
        colors.append((0, 0, 0, 0))
        return colors

# Global palette instance
palet_manager = Palet()
