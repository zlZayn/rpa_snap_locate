import ctypes
import platform


def get_system_dpi_scale() -> float:
    system = platform.system()
    if system == "Windows":
        try:
            shcore = ctypes.windll.shcore
            dpi = shcore.GetScaleFactorForDevice(0)
            return dpi / 100.0
        except Exception:
            return 1.0
    elif system == "Darwin":
        return 2.0
    else:
        return 1.0


def phys_to_normalized(
    phys_x: int, phys_y: int, logical_w: int, logical_h: int, dpi_scale: float
) -> tuple[float, float]:
    logical_x = phys_x / dpi_scale
    logical_y = phys_y / dpi_scale
    norm_x = logical_x / logical_w
    norm_y = logical_y / logical_h
    return (norm_x, norm_y)


def normalized_to_phys(
    norm_x: float, norm_y: float, logical_w: int, logical_h: int, dpi_scale: float
) -> tuple[int, int]:
    logical_x = norm_x * logical_w
    logical_y = norm_y * logical_h
    phys_x = int(logical_x * dpi_scale)
    phys_y = int(logical_y * dpi_scale)
    return (phys_x, phys_y)
