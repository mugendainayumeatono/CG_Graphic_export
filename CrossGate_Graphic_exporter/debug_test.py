import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from core.graphic_info import graphic_info_manager
from core.graphic_data import graphic_data_manager
from core.palet import palet_manager

def test():
    cwd = os.getcwd()
    search_dirs = [
        cwd,
        os.path.dirname(cwd),
        os.path.join(os.path.dirname(cwd), "reference", "CGTool")
    ]
    
    bin_dir = None
    pal_dir = None
    for d in search_dirs:
        bd = os.path.join(d, "bin")
        if os.path.exists(bd):
            bin_dir = bd
            pal_dir = os.path.join(d, "pal")
            break

    if not bin_dir:
        print("Could not find bin directory")
        return

    print(f"Loading from {bin_dir} and {pal_dir}")
    if os.path.exists(pal_dir):
        palet_manager.init_palettes(pal_dir)
    print(f"Loaded {len(palet_manager._cache)} palettes")

    graphic_info_manager.init_graphics(bin_dir)
    graphics = graphic_info_manager.get_all_graphics()
    print(f"Loaded {len(graphics)} graphics")

    if not graphics:
        return

    # Test first 5 graphics
    for g in graphics[:5]:
        img = graphic_data_manager.get_graphic_image(g, 0)
        if img:
            extrema = img.getextrema()
            alpha_extrema = extrema[3] if len(extrema) == 4 else None
            print(f"Graphic {g.serial}: size={img.width}x{img.height}, alpha_extrema={alpha_extrema}")
        else:
            print(f"Graphic {g.serial}: Failed to load image")

if __name__ == "__main__":
    test()
