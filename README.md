# StyleKBLoaderNode — ComfyUI 风格技法知识库节点

把 `knowledge_base/style_technique_knowledge_base.json` 中整理好的风格 / 技法信息直接暴露为 ComfyUI 节点的输出端口，方便在工作流里拼装到 `CLIPTextEncode` 或其它文本节点中。

## 目录结构

```
StyleKBLoaderNode/
├── __init__.py                             # 暴露 NODE_CLASS_MAPPINGS（ComfyUI 的唯一要求）
├── config.py                               # 元信息
├── knowledge_base/
│   └── style_technique_knowledge_base.json # 原始 JSON
├── nodes/
│   └── style_kb_loader.py                  # 4 个节点实现
└── workflows/
    └── style_kb_example.json               # 示例工作流
```

## 输入 JSON 格式

```json
{
  "entries": [
    {
      "style_special_word": "瓷眸凝釉风格",
      "aliases": ["瓷眸凝釉"],
      "prompt_phrase": "瓷眸凝釉风格，无线稿，瓷面高光边，材质模拟……",
      "techniques": [
        {"dimension": "line",           "dimension_zh": "线条技法", "primary": "无线稿",        "secondary": "瓷面高光边"},
        {"dimension": "brush_material", "dimension_zh": "质感/材质", "primary": "材质模拟",      "secondary": "冷瓷瞳釉"},
        {"dimension": "form",           "dimension_zh": "形体技法", "primary": "轻度简化",      "secondary": "巨瞳圆脸瓷偶"},
        {"dimension": "color",          "dimension_zh": "色彩技法", "primary": "自然/真实色调", "secondary": "自然肤亮釉光"}
      ],
      "search_text": "瓷眸凝釉风格 无线稿 瓷面高光边 材质模拟 冷瓷瞳釉 ……"
    }
  ]
}
```

## 节点列表（分类：StyleKB）

### 1. Style KB Loader — 最常用
- **输入**：`kb_file`、`style_name`、`extra_positive`、`extra_location = append|prepend|replace`
- **输出**：`prompt`、`style_name`、`aliases`、`line_primary`、`line_secondary`、`brush_material_primary`、`brush_material_secondary`、`form_primary`、`form_secondary`、`color_primary`、`color_secondary`、`techniques_summary`、`search_text`、`entry_json`
- `prompt` 可直接接到 `CLIPTextEncode.text`

### 2. Style KB Search — 关键词搜索
- 输入：`kb_file`、`keyword`、`top_k`、`separator`、`output_mode = prompt_phrase|style_special_word`
- 输出：`results`、`style_names`、`matched_aliases`

### 3. Style KB Filter by Technique — 按技法筛选
- 输入：`kb_file`、`dimension = any|line|brush_material|form|color`、`keyword`、`top_k`、`separator`、`output_mode`
- 示例：`dimension = line` + `keyword = 硬边` → 返回“线条技法”条目里含有“硬边”的所有风格。

### 4. Style KB Join — 通用文本拼接
- 输入：`text_a`、可选 `text_b/c/d`、`separator`、`skip_empty`
- 输出：拼接后的字符串。

## 安装

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Sinky7777/StyleKBLoaderNod.git
```

重启 ComfyUI 后，`StyleKB` 分类下会出现上面 4 个节点。也可以直接把 `workflows/style_kb_example.json` 拖进 ComfyUI 查看示例连线。

## 更新知识库

把最新版 `style_technique_knowledge_base.json` 覆盖到 `knowledge_base/`，重启 ComfyUI 即可。你也可以在 `knowledge_base/` 放多个 JSON 版本，在节点里通过 `kb_file` 下拉切换。
