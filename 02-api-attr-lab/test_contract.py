"""把 Schemathesis 接进 pytest，这样就能和手工用例一起跑、一起出报告。"""
import schemathesis

# 从 URL 读取契约
schema = schemathesis.openapi.from_url("http://127.0.0.1:8000/openapi.json")


@schema.parametrize()
def test_api(case):
    """pytest 会为每个自动生成的用例调用一次这个函数。"""
    case.call_and_validate()