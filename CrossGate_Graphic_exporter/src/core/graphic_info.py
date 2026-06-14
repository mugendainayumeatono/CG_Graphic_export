import os
import struct

class GraphicInfoData:
    def __init__(self):
        self.index = 0
        self.addr = 0
        self.length = 0
        self.offset_x = 0
        self.offset_y = 0
        self.width = 0
        self.height = 0
        self.east = 0
        self.south = 0
        self.blocked = False
        self.as_ground = False
        self.serial = 0
        self.graphic_file = ""
        
        self.is_encrypted = False
        self.pwd_index = 0
        self.pwd_len = 0
        self.pwd = b""

class GraphicInfoManager:
    def __init__(self):
        self._cache = {}
        self._index_cache = {}
        self.encrypt_key = b""
        
    def init_graphics(self, bin_dir):
        if not os.path.exists(bin_dir):
            return
            
        directories = [bin_dir]
        directories.extend([os.path.join(bin_dir, d) for d in os.listdir(bin_dir) if os.path.isdir(os.path.join(bin_dir, d))])
        
        for directory in directories:
            self._analysis_directory(directory)
            
    def _analysis_directory(self, directory):
        files = os.listdir(directory)
        info_files = [f for f in files if f.lower().startswith('graphicinfo') and f.lower().endswith('.bin')]
        
        for info_file in info_files:
            prefix = 'graphicinfo'
            filename_no_ext = os.path.splitext(info_file)[0]
            full_version = filename_no_ext[len(prefix):]
            
            graphic_filename = f"graphic{full_version}.bin"
            
            # Find graphic file case insensitively
            graphic_file_path = None
            for f in files:
                if f.lower() == graphic_filename.lower():
                    graphic_file_path = os.path.join(directory, f)
                    break
                    
            if not graphic_file_path:
                print(f"Cannot find graphic file for {info_file}")
                continue
                
            info_file_path = os.path.join(directory, info_file)
            version = os.path.basename(directory)
            if not full_version:
                version = version.upper()
                
            self._load_graphic_info(version, info_file_path, graphic_file_path)
            
    def _load_graphic_info(self, version, info_file_path, graphic_file_path):
        if version not in self._index_cache:
            self._index_cache[version] = {}
            
        with open(graphic_file_path, 'rb') as gf:
            head = gf.read(3)
            is_encrypted = False
            pwd_index = 0
            pwd_len = 0
            pwd = b""
            
            if len(head) >= 3 and head[0] == 0x52 and head[1] == 0x44: # 'RD'
                is_encrypted = False
            else:
                if len(head) >= 3:
                    is_encrypted = True
                    from_head = (head[0] % 2) == 0
                    pwd_len = head[2]
                    if from_head:
                        pwd_index = 3 + head[1]
                    else:
                        file_size = os.path.getsize(graphic_file_path)
                        pwd_index = file_size - pwd_len - 3 - head[1] + 3
                        
                    gf.seek(pwd_index)
                    pwd = bytearray(gf.read(pwd_len))
                    
                    if self.encrypt_key:
                        for i in range(pwd_len):
                            pwd[i] = pwd[i] ^ self.encrypt_key[i % len(self.encrypt_key)]
                            
        with open(info_file_path, 'rb') as f:
            file_size = os.path.getsize(info_file_path)
            data_length = file_size // 40
            
            for i in range(data_length):
                data = f.read(40)
                if len(data) < 40:
                    break
                
                info = GraphicInfoData()
                info.index = struct.unpack_from('<I', data, 0)[0]
                info.addr = struct.unpack_from('<I', data, 4)[0]
                info.length = struct.unpack_from('<I', data, 8)[0]
                info.offset_x = struct.unpack_from('<i', data, 12)[0]
                info.offset_y = struct.unpack_from('<i', data, 16)[0]
                info.width = struct.unpack_from('<I', data, 20)[0]
                info.height = struct.unpack_from('<I', data, 24)[0]
                info.east = data[28]
                info.south = data[29]
                info.blocked = (data[30] % 2) == 0
                info.as_ground = data[31] == 1
                # 32-35 unknown
                info.serial = struct.unpack_from('<I', data, 36)[0]
                info.graphic_file = graphic_file_path
                info.is_encrypted = is_encrypted
                info.pwd_index = pwd_index
                info.pwd_len = pwd_len
                info.pwd = pwd
                
                self._index_cache[version][info.index] = info
                if info.serial != 0:
                    self._cache[info.serial] = info

    def get_graphic_info(self, serial):
        return self._cache.get(serial)

    def get_all_graphics(self):
        return list(self._cache.values())

graphic_info_manager = GraphicInfoManager()
