"""ComfyUI 风格技法知识库节点 — 加载 knowledge_base/*.json。"""
import json
import os
from typing import Dict, List, Optional


_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
_KB_DIR = os.path.join(_EXT_DIR, "knowledge_base")


def _kb_files() -> List[str]:
    if not os.path.isdir(_KB_DIR):
        return []
    return sorted(name for name in os.listdir(_KB_DIR) if name.lower().endswith(".json"))


def _load_entries(filename: str) -> List[Dict]:
    path = os.path.join(_KB_DIR, filename)
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
# 节点 1：Style KB Loader — 按风格下拉加载
# ---------------------------------------------------------------------------

class StyleKBLoader:
    @classmethod
    def INPUT_TYPES(cls):
        files = _kb_files() or ["<knowledge_base 为空>"]
        try:
            if files and not files[0].startswith("<"):
                entries = _load_entries(files[0])
            else:
                entries = []
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
        "STRING",
        "STRING",
        "STRING",
        "STRING", "STRING",
        "STRING", "STRING",
        "STRING", "STRING",
        "STRING", "STRING",
        "STRING",
        "STRING",
        "STRING",
    )
    RETURN_NAMES = (
        "prompt",
        "style_name",
        "aliases",
        "line_primary", "line_secondary",
        "brush_material_primary", "brush_material_secondary",
        "form_primary", "form_secondary",
        "color_primary", "color_secondary",
        "techniques_summary",
        "search_text",
        "entry_json",
    )
    FUNCTION = "load_entry"
    CATEGORY = "StyleKB"

    def load_entry(self, kb_file, style_name, extra_positive="", extra_location="append"):
        empty = ("",) * 14
        try:
            if kb_file.startswith("<"):
                return empty
            entries = _load_entries(kb_file)
            entry = _entry_by_style_name(entries, style_name)
            if entry is None and entries:
                entry = entries[0]
            if not entry:
                return empty

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

            summary_parts = []
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
                    summary_parts.append(f"[{dim_label}] {p} / {s}".strip())

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
                " | ".join(summary_parts),
                entry.get("search_text", "") or "",
                json.dumps(entry, ensure_ascii=False, indent=2),
            )
        except Exception as exc:
            return (f"[加载错误] {exc}",) + ("",) * 13


# ---------------------------------------------------------------------------
# 节点 2：Style KB Search — 关键词搜索
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
                "separator": ("STRING", {"default": "\\n"}),
                "output_mode": (["prompt_phrase", "style_special_word"],),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("results", "style_names", "matched_aliases")
    FUNCTION = "search"
    CATEGORY = "StyleKB"

    def search(self, kb_file, keyword, top_k=5, separator="\\n", output_mode="prompt_phrase"):
        empty = ("", "", "")
        try:
            if kb_file.startswith("<"):
                return empty
            entries = _load_entries(kb_file)
            kw = (keyword or "").strip().lower()
            scored = []
            for e in entries:
                haystack = " ".join([
                    e.get("style_special_word", "") or "",
                    " ".join(e.get("aliases", []) or []),
                    e.get("search_text", "") or "",
                    e.get("prompt_phrase", "") or "",
                ]).lower()
                if kw and kw in haystack:
                    scored.append((haystack.count(kw), e))
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
# 节点 3：Style KB Filter by Technique — 按技法维度筛选
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
                "separator": ("STRING", {"default": "\\n"}),
                "output_mode": (["prompt_phrase", "style_special_word"],),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("results", "style_names")
    FUNCTION = "filter_tech"
    CATEGORY = "StyleKB"

    def filter_tech(self, kb_file, dimension, keyword, top_k=5, separator="\\n", output_mode="prompt_phrase"):
        empty = ("", "")
        try:
            if kb_file.startswith("<"):
                return empty
            entries = _load_entries(kb_file)
            kw = (keyword or "").strip().lower()
            matches = []
            for e in entries:
                techs = e.get("techniques", []) or []
                haystack = []
                for t in techs:
                    if dimension == "any" or t.get("dimension") == dimension:
                        haystack.append(t.get("primary", "") or "")
                        haystack.append(t.get("secondary", "") or "")
                        haystack.append(t.get("dimension_zh", "") or "")
                joined = " ".join(haystack).lower()
                if kw in joined:
                    matches.append((joined.count(kw), e))
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
# 节点 4：Style KB Join — 通用文本拼接
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


# ---------------------------------------------------------------------------
# 自测：python -m <this_file> 即可快速验证
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    it = StyleKBLoader.INPUT_TYPES()
    print("kb_file:", it["required"]["kb_file"][0])
    print("风格数:", len(it["required"]["style_name"][0]))
    print("前 3 个:", it["required"]["style_name"][0][:3])
    kb_file = it["required"]["kb_file"][0][0]
    style = it["required"]["style_name"][0][0]
    out = StyleKBLoader().load_entry(kb_file, style, extra_positive="1girl", extra_location="prepend")
    for n, v in zip(StyleKBLoader.RETURN_NAMES, out):
        print(f"  {n:<28}: {str(v)[:80]}")
    r = StyleKBSearch().search(kb_file, "低饱和", top_k=3, output_mode="style_special_word")
    print("[search 低饱和]:", r[1])
    r = StyleKBFilterByTechnique().filter_tech(kb_file, "line", "硬边", top_k=5, output_mode="style_special_word")
    print("[filter line/硬边]:", r[1])
    r = StyleKBJoin().join_text("1girl", "blue eyes", "", "smile", separator=", ", skip_empty="true")
    print("[join]:", r[0])
