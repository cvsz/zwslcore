from services.engineering.runtime import EngineeringRuntime


def test_parser():
    raw = 'prefix {"changes":[{"path":"services/example.py","content":"x = 1"}]} suffix'
    assert EngineeringRuntime._parse_changes(raw) == [
        {"path": "services/example.py", "content": "x = 1"}
    ]


if __name__ == "__main__":
    test_parser()
