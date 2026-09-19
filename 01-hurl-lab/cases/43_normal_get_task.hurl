# 正常：先创建再按 id 查回来
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "按 id 查询", "done": false }
HTTP 201
[Captures]
task_id: jsonpath "$.id"

GET http://127.0.0.1:8000/tasks/{{task_id}}
HTTP 200
[Asserts]
jsonpath "$.id" == "{{task_id}}"