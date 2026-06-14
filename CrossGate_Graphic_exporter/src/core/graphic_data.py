import os
import struct
import numpy as np
from PIL import Image

from core.palet import palet_manager

class GraphicDataManager:
    def __init__(self):
        pass

    def get_graphic_image(self, info_data, palet_index=0):
        if not info_data.graphic_file or not os.path.exists(info_data.graphic_file):
            return None

        with open(info_data.graphic_file, 'rb') as f:
            if info_data.is_encrypted:
                f.seek(info_data.addr + 3)
                position = info_data.addr + 3
                
                if position + info_data.length < info_data.pwd_index:
                    content = f.read(info_data.length)
                elif position < info_data.pwd_index and position + info_data.length > info_data.pwd_index:
                    pre_len = int(info_data.pwd_index - position + 3) # Why +3? Because pwd_index logic in C#
                    pre_content = f.read(pre_len)
                    next_len = int(info_data.length - pre_len)
                    f.seek(info_data.pwd_index + info_data.pwd_len)
                    next_content = f.read(next_len)
                    content = pre_content + next_content
                else:
                    f.seek(position + info_data.pwd_len)
                    content = f.read(info_data.length)
                    
                content = bytearray(content)
                pwd_index_match = 0
                if len(content) >= 2:
                    for i in range(info_data.pwd_len):
                        if (content[0] ^ info_data.pwd[i]) == 0x52:
                            nxt = i + 1
                            if i == info_data.pwd_len - 1: nxt = 0
                            if (content[1] ^ info_data.pwd[nxt]) == 0x44:
                                pwd_index_match = i
                                break
                                
                for i in range(len(content)):
                    content[i] ^= info_data.pwd[pwd_index_match]
                    pwd_index_match += 1
                    if pwd_index_match >= info_data.pwd_len:
                        pwd_index_match = 0
            else:
                f.seek(info_data.addr)
                content = f.read(info_data.length)

        if len(content) < 16:
            return None
            
        # Parse head
        rd = content[0:2]
        version = content[2]
        unknown = content[3]
        width = struct.unpack_from('<I', content, 4)[0]
        height = struct.unpack_from('<I', content, 8)[0]
        data_len = struct.unpack_from('<I', content, 12)[0]
        
        inner_palet_len = 0
        head_len = 16
        if version > 1:
            head_len = 20
            if len(content) >= 20:
                inner_palet_len = struct.unpack_from('<I', content, 16)[0]

        content_len = data_len - head_len
        pixel_len = info_data.width * info_data.height
        
        compressd = (version % 2) != 0
        
        data_bytes = content[head_len:]
        
        # Decompress
        color_indices = []
        idx = 0
        
        if not compressd:
            color_indices = list(data_bytes[:pixel_len])
            idx = pixel_len
        else:
            color_indices = []
            while idx < len(data_bytes) and len(color_indices) < pixel_len:
                head = data_bytes[idx]
                idx += 1
                
                if head < 0x10:
                    repeat = head
                    for _ in range(repeat):
                        if idx < len(data_bytes):
                            color_indices.append(data_bytes[idx])
                            idx += 1
                elif head < 0x20:
                    if idx < len(data_bytes):
                        repeat = (head % 0x10) * 0x100 + data_bytes[idx]
                        idx += 1
                        for _ in range(repeat):
                            if idx < len(data_bytes):
                                color_indices.append(data_bytes[idx])
                                idx += 1
                elif head < 0x80:
                    if idx + 1 < len(data_bytes):
                        repeat = (head % 0x20) * 0x10000 + data_bytes[idx] * 0x100 + data_bytes[idx+1]
                        idx += 2
                        for _ in range(repeat):
                            if idx < len(data_bytes):
                                color_indices.append(data_bytes[idx])
                                idx += 1
                elif head < 0x90:
                    repeat = head % 0x80
                    if idx < len(data_bytes):
                        color_val = data_bytes[idx]
                        idx += 1
                        color_indices.extend([color_val] * repeat)
                elif head < 0xa0:
                    if idx + 1 < len(data_bytes):
                        color_val = data_bytes[idx]
                        repeat = (head % 0x90) * 0x100 + data_bytes[idx+1]
                        idx += 2
                        color_indices.extend([color_val] * repeat)
                elif head < 0xc0:
                    if idx + 2 < len(data_bytes):
                        color_val = data_bytes[idx]
                        repeat = (head % 0xa0) * 0x10000 + data_bytes[idx+1] * 0x100 + data_bytes[idx+2]
                        idx += 3
                        color_indices.extend([color_val] * repeat)
                elif head < 0xd0:
                    repeat = head % 0xc0
                    color_indices.extend([0] * repeat)
                elif head < 0xe0:
                    if idx < len(data_bytes):
                        repeat = (head % 0xd0) * 0x100 + data_bytes[idx]
                        idx += 1
                        color_indices.extend([0] * repeat)
                else: # <= 0xff
                    if idx + 1 < len(data_bytes):
                        repeat = (head % 0xe0) * 0x10000 + data_bytes[idx] * 0x100 + data_bytes[idx+1]
                        idx += 2
                        color_indices.extend([0] * repeat)
                        
        color_indices = color_indices[:pixel_len]
        if len(color_indices) < pixel_len:
            color_indices.extend([0] * (pixel_len - len(color_indices)))
            
        # Parse inner palette if exists
        inner_palet = None
        if inner_palet_len > 0:
            pal_bytes = data_bytes[idx:idx+inner_palet_len]
            if len(pal_bytes) >= inner_palet_len:
                inner_palet = []
                color_len = inner_palet_len // 3
                for i in range(color_len):
                    b = pal_bytes[i*3]
                    g = pal_bytes[i*3+1]
                    r = pal_bytes[i*3+2]
                    alpha = 0 if i == 0 else 255
                    inner_palet.append((r, g, b, alpha))
                inner_palet.append((0, 0, 0, 0)) # clear at end

        palet = inner_palet
        if not palet:
            palet = palet_manager.get_palet(palet_index)
        if not palet:
            palet = palet_manager.get_palet(0)

        if not palet:
            # Fallback to empty image
            return Image.new("RGBA", (info_data.width, info_data.height), (0,0,0,0))
            
        # Map indices to pixels
        # Create numpy array for fast mapping
        palet_arr = np.array(palet, dtype=np.uint8)
        idx_arr = np.array(color_indices, dtype=np.int32)
        
        # Ensure indices are within palette bounds
        idx_arr = np.clip(idx_arr, 0, len(palet_arr) - 1)
        
        pixels = palet_arr[idx_arr]
        pixels = pixels.reshape((info_data.height, info_data.width, 4))
        
        # Image is typically bottom-up? Wait, the spec says bottom-up. But my reading might be top-down. Let's not flip it yet, or flip it? 
        # C# loaded directly into texture without flip but used negative Y offset. I will leave it as is, or flip it.
        # Let's try normal and see. Usually we don't need to flip manually if we use Image.fromarray.
        img = Image.fromarray(pixels, 'RGBA')
        
        return img

graphic_data_manager = GraphicDataManager()
