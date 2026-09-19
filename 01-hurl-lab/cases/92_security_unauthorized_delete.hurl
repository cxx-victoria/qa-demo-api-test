
# 安全：未登录就删除别人的任务，期望 401（这条会失败 = 缺陷 D3 越权）
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "别人的任务", "done": false }
HTTP 201
[Captures]
task_id: jsonpath "$.id"

# 关键：不带 Authorization
DELETE http://127.0.0.1:8000/tasks/{{task_id}}
HTTP 401

