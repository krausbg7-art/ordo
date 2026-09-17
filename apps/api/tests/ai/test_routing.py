from ordo_api.ai.routing import load_routing


def test_default_routing_config_has_expected_task_types():
    table = load_routing("config/ai_routing.yaml")

    for task_type in ["extract_tasks_short", "extract_tasks_long", "vision_ocr", "draft_reply", "summary"]:
        route = table.resolve(task_type)
        assert route.provider
        assert route.fallback

    assert table.resolve("extract_tasks_short").provider == "qwen"
    assert table.resolve("extract_tasks_long").provider == "kimi"
    assert table.resolve("vision_ocr").provider == "qwen_vl"
