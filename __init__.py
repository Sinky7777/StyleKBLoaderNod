"""ComfyUI 扩展入口 — 暴露节点映射给 ComfyUI 加载器。"""
from .style_kb_loader import (
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
