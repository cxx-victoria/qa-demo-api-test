# 【冒烟测试】最基础的检查：服务活着吗？接口通吗？
# 这条用例的目的不是找 bug，而是确认"环境没问题，可以开始测了"

GET http://127.0.0.1:8000/tasks
HTTP 200
[Asserts]
jsonpath "$" isCollection
