# 【缺陷复现 D4】返回类型不符合契约
#
# 现象：接口契约声明 done 是布尔值（true/false），
#       实际返回的却是 0 / 1（整数）。
#       前端如果用严格类型判断（如 done === true）就会出错。
#       这类问题靠"看值"发现不了，必须断言"类型"。
#
# 预期结果：这条用例 FAIL（期望布尔，实际整数）。

POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "检查返回类型", "done": false }
HTTP 201
[Asserts]
jsonpath "$.done" isBoolean
