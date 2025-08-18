import json

def export_tree_to_json(tree, filename="tree_output.json"):
    tree_summary = {
        "levels": [],
        "selected_thoughts": []
    }

    for level in tree.levels:
        thoughts = [str(thought) for thought in level.get_thoughts()]
        selected = str(level.get_selected_thought())

        tree_summary["levels"].append({
            "thoughts": thoughts,
            "selected_thought": selected
        })
        tree_summary["selected_thoughts"].append(selected)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(tree_summary, f, indent=2, ensure_ascii=False)

    print(f"Tree structure saved to {filename}")

import json

def import_tree_from_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        tree_data = json.load(f)

    levels_raw = tree_data.get("levels", [])
    selected_thoughts = tree_data.get("selected_thoughts", [])

    structured_levels = []

    for idx, level in enumerate(levels_raw):
        thoughts = level.get("thoughts", [])
        selected_thought = level.get("selected_thought", None)

        try:
            selected_index = thoughts.index(selected_thought) if selected_thought in thoughts else -1
        except ValueError:
            selected_index = -1

        structured_levels.append({
            "thoughts": thoughts,
            "selected_thought": selected_thought,
        })

    return {"levels": structured_levels, "selected_thoughts": selected_thoughts}
