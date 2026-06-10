import json
import os
from typing import Dict, List, Optional


def _kb_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge_base")


def _kb_files() -> List[str]:
    folder = _kb_dir()
    if not os.path.isdir(folder):
        return []
    return sorted(name for name in os.listdir(folder) if name.lower().endswith(".json"))


def _load_entries(filename: str) -> List[Dict]:
    path = os.path.join(_kb_dir(), filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("entries", []) or [])


def _entry_by_style_name(entries: List[Dict], style_name: str) -> Optional[Dict]:
    for e in entries:
        if e.get("style_special_word") == style_name:
            return e
    return None


def _tech_by_dim(techniques: List[Dict], dimension: str) -> Dict:
    for t in techniques or []:
        if t.get("dimension") == dimension:
            return t
    return {}


def _join(values, sep=", ") -> str:
    return sep.join(v for v in (values or []) if v)


def _names_from_entries(entries: List[Dict]) -> List[str]:
    placeholder = ["<knowledge_base 为空>"]
    return [e.get("style_special_word") for e in entries if e.get("style_special_word")] or placeholder


# ---------------------------------------------------------------------------
# 节点 1：按风格下拉加载
# ---------------------------------------------------------------------------

class StyleKBLoader:
    @classmethod
    def INPUT_TYPES(cls):
        files = _kb_files() or ["<knowledge_base 为空>"]
        try:
            entries = _load_entries(files[0]) if files and not files[0].startswith("<") else []
        except Exception:
            entries = []
        style_names = _names_from_entries(entries)
        return {
            "required": {
                "kb_file": (files,),
                "style_name": (style_names,),
            },
            "optional": {
                "extra_positive": ("STRING", {"default": "", "multiline": True}),
                "extra_location": (["append", "prepend", "replace"],),
            },
        }

    RETURN_TYPES = (
        "STRING",  # 0 prompt_phrase (可直接喂 CLIP)
        "STRING",  # 1 style_special_word
        "STRING",  # 2 aliases  (以逗号连接)
        "STRING",  # 3 line_primary
        "STRING",  # 4 line_secondary
        "STRING",  # 5 brush_material_primary
        "STRING",  # 6 brush_material_secondary
        "STRING",  # 7 form_primary
        "STRING",  # 8 form_secondary
        "STRING",  # 9 color_primary
        "STRING",  # 10 color_secondary
        "STRING",  # 11 techniques_flat (  human-readable summary )
        "STRING",  # 12 search_text
        "STRING",  # 13 entry_json
    )
    RETURN_NAMES = (
        "prompt",
        "style_name",
        "aliases",
        "line_primary",
        "line_secondary",
        "brush_material_primary",
        "brush_material_secondary",
        "form_primary",
        "form_secondary",
        "color_primary",
        "color_secondary",
        "techniques_summary",
        "search_text",
        "entry_json",
    )
    FUNCTION = "load_entry"
    CATEGORY = "StyleKB"

    def load_entry(self, kb_file, style_name, extra_positive="", extra_location="append"):
        missing = ("",) * 14
        try:
            if kb_file.startswith("<"):
                return missing
            entries = _load_entries(kb_file)
            entry = _entry_by_style_name(entries, style_name)
            if entry is None and entries:
                entry = entries[0]
            if not entry:
                return missing

            techniques = entry.get("techniques", []) or []
            line = _tech_by_dim(techniques, "line")
            brush = _tech_by_dim(techniques, "brush_material")
            form = _tech_by_dim(techniques, "form")
            color = _tech_by_dim(techniques, "color")

            main = entry.get("prompt_phrase", "") or ""
            if extra_positive:
                if extra_location == "prepend":
                    main = f"{extra_positive}, {main}" if main else extra_positive
                elif extra_location == "replace":
                    main = extra_positive
                else:  # append
                    main = f"{main}, {extra_positive}" if main else extra_positive

            flat = []
            for dim_key, dim_label in [
                ("line", "线条技法"),
                ("brush_material", "质感/材质"),
                ("form", "形体技法"),
                ("color", "色彩技法"),
            ]:
                t = _tech_by_dim(techniques, dim_key)
                p = t.get("primary", "")
                s = t.get("secondary", "")
                if p or s:
                    flat.append(f"[{dim_label}] {p} / {s}".strip())

            return (
                main,
                entry.get("style_special_word", "") or "",
                _join(entry.get("aliases", []) or []),
                line.get("primary", "") or "",
                line.get("secondary", "") or "",
                brush.get("primary", "") or "",
                brush.get("secondary", "") or "",
                form.get("primary", "") or "",
                form.get("secondary", "") or "",
                color.get("primary", "") or "",
                color.get("secondary", "") or "",
                " | ".join(flat),
                entry.get("search_text", "") or "",
                json.dumps(entry, ensure_ascii=False, indent=2),
            )
        except Exception as exc:
            return (f"[加载错误] {exc}",) + ("",) * 13


# ---------------------------------------------------------------------------
# 节点 2：关键词搜索，返回 Top-K 的 prompt/style_name 字符串
# ---------------------------------------------------------------------------

class StyleKBSearch:
    @classmethod
    def INPUT_TYPES(cls):
        files = _kb_files() or ["<knowledge_base 为空>"]
        return {
            "required": {
                "kb_file": (files,),
                "keyword": ("STRING", {"default": "", "multiline": False}),
                "top_k": ("INT", {"default": 5, "min": 1, "max": 50, "step": 1}),
                "separator": ("STRING", {"default": "\n"}),
                "output_mode": (["prompt_phrase", "style_special_word"],),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("results", "style_names", "matched_aliases")
    FUNCTION = "search"
    CATEGORY = "StyleKB"

    def search(self, kb_file, keyword, top_k=5, separator="\n", output_mode="prompt_phrase"):
        empty = ("", "", "")
        try:
            if kb_file.startswith("<"):
                return empty
            entries = _load_entries(kb_file)
            keyword = (keyword or "").strip().lower()
            scored = []
            for e in entries:
                haystack = " ".join(
                    [
                        e.get("style_special_word", "") or "",
                        " ".join(e.get("aliases", []) or []),
                        e.get("search_text", "") or "",
                        e.get("prompt_phrase", "") or "",
                    ]
                ).lower()
                if keyword and keyword in haystack:
                    scored.append((haystack.count(keyword), e))
                elif not keyword:
                    scored.append((1, e))
            scored.sort(key=lambda x: x[0], reverse=True)
            selected = [e for _, e in scored[:top_k]]

            if output_mode == "prompt_phrase":
                items = [e.get("prompt_phrase", "") for e in selected]
            else:
                items = [e.get("style_special_word", "") for e in selected]

            names = [e.get("style_special_word", "") for e in selected]
            aliases = [_join(e.get("aliases", []) or []) for e in selected]

            sep = separator.replace("\\n", "\n").replace("\\t", "\t")
            return (sep.join(items), sep.join(names), sep.join(aliases))
        except Exception as exc:
            return (f"[搜索错误] {exc}", "", "")


# ---------------------------------------------------------------------------
# 节点 3：按技法维度（线条/材质/形体/色彩）的 primary/secondary 值筛选
# ---------------------------------------------------------------------------

class StyleKBFilterByTechnique:
    @classmethod
    def INPUT_TYPES(cls):
        files = _kb_files() or ["<knowledge_base 为空>"]
        dims = ["any", "line", "brush_material", "form", "color"]
        return {
            "required": {
                "kb_file": (files,),
                "dimension": (dims, {"default": "any"}),
                "keyword": ("STRING", {"default": "", "multiline": False}),
                "top_k": ("INT", {"default": 5, "min": 1, "max": 50, "step": 1}),
                "separator": ("STRING", {"default": "\n"}),
                "output_mode": (["prompt_phrase", "style_special_word"],),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("results", "style_names")
    FUNCTION = "filter_tech"
    CATEGORY = "StyleKB"

    def filter_tech(self, kb_file, dimension, keyword, top_k=5, separator="\n", output_mode="prompt_phrase"):
        empty = ("", "")
        try:
            if kb_file.startswith("<"):
                return empty
            entries = _load_entries(kb_file)
            kw = (keyword or "").strip().lower()
            matches = []
            for e in entries:
                techs = e.get("techniques", []) or []
                haystacks = []
                for t in techs:
                    if dimension == "any" or t.get("dimension") == dimension:
                        haystacks.append(t.get("primary", "") or "")
                        haystacks.append(t.get("secondary", "") or "")
                        haystacks.append(t.get("dimension_zh", "") or "")
                haystack = " ".join(haystacks).lower()
                if kw in haystack:
                    matches.append((haystack.count(kw), e))
            matches.sort(key=lambda x: x[0], reverse=True)
            selected = [e for _, e in matches[:top_k]]
            if output_mode == "prompt_phrase":
                items = [e.get("prompt_phrase", "") for e in selected]
            else:
                items = [e.get("style_special_word", "") for e in selected]
            names = [e.get("style_special_word", "") for e in selected]
            sep = separator.replace("\\n", "\n").replace("\\t", "\t")
            return (sep.join(items), sep.join(names))
        except Exception as exc:
            return (f"[筛选错误] {exc}", "")


# ---------------------------------------------------------------------------
# 节点 4：把多条字符串用分隔符拼接（通用工具节点，用来拼装 prompt）
# ---------------------------------------------------------------------------

class StyleKBJoin:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_a": ("STRING", {"default": "", "multiline": True}),
            },
            "optional": {
                "text_b": ("STRING", {"default": "", "multiline": True}),
                "text_c": ("STRING", {"default": "", "multiline": True}),
                "text_d": ("STRING", {"default": "", "multiline": True}),
                "separator": ("STRING", {"default": ", "}),
                "skip_empty": (["true", "false"],),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "join_text"
    CATEGORY = "StyleKB"

    def join_text(self, text_a, text_b="", text_c="", text_d="", separator=", ", skip_empty="true"):
        items = [text_a, text_b, text_c, text_d]
        if skip_empty == "true":
            items = [t for t in items if t and t.strip()]
        sep = separator.replace("\\n", "\n").replace("\\t", "\t")
        return (sep.join(items),)


NODE_CLASS_MAPPINGS = {
    "StyleKBLoader": StyleKBLoader,
    "StyleKBSearch": StyleKBSearch,
    "StyleKBFilterByTechnique": StyleKBFilterByTechnique,
    "StyleKBJoin": StyleKBJoin,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StyleKBLoader": "Style KB Loader",
    "StyleKBSearch": "Style KB Search",
    "StyleKBFilterByTechnique": "Style KB Filter by Technique",
    "StyleKBJoin": "Style KB Join",
}
