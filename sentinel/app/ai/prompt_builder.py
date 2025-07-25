import json
from pathlib import Path
from typing import Any, Dict

TEMPLATES_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "prompt_templates.json"


def build_prompt(file_metadata: Dict[str, Any], extracted_content: Any) -> str:
    """Construct the final prompt string for the LLM."""
    with TEMPLATES_PATH.open("r", encoding="utf-8") as fh:
        tmpl = json.load(fh)

    system_prompt = tmpl["system_prompt"]
    few_shot = tmpl.get("few_shot_examples", [])

    # Build few-shot examples section
    example_blocks = []
    for ex in few_shot:
        meta_json = json.dumps(ex["metadata"], ensure_ascii=False)
        content_json = json.dumps(ex["content"], ensure_ascii=False)
        output_json = json.dumps(ex["output"], ensure_ascii=False)
        example_blocks.append(
            f"### Example\nMetadata: {meta_json}\nContent: {content_json}\nAssistant: {output_json}"
        )

    few_shot_block = "\n\n".join(example_blocks)

    user_meta = json.dumps(file_metadata, ensure_ascii=False)
    user_content = json.dumps(extracted_content, ensure_ascii=False) if not isinstance(extracted_content, str) else extracted_content

    user_block = f"### User File\nMetadata: {user_meta}\nContent: {user_content}\nAssistant:"

    return f"{system_prompt}\n\n{few_shot_block}\n\n{user_block}" 