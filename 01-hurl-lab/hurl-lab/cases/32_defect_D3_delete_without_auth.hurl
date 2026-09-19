# 【缺陷复现 D3】越权 / 缺少鉴权
#
# 现象：删除接口没有校验 Authorization，任何人不登录就能删掉别人的数据。
#       这是安全测试里最典型的"越权"问题。
#
# 预期结果：这条用例 FAIL（期望 401 未授权，实际 204 删除成功）。

# 先正常登录并创建一条任务（为了有东西可删）
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "这条数据会被未登录的人删掉", "done": false }
HTTP 201
[Captures]
task_id: jsonpath "$.id"

# 关键一步：不带 Authorization 直接删除
DELETE http://127.0.0.1:8000/tasks/{{task_id}}
HTTP 401
