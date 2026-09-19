# 正常：带分页参数查列表
GET http://127.0.0.1:8000/tasks?limit=10&offset=0
HTTP 200
[Asserts]
jsonpath "$" isCollection