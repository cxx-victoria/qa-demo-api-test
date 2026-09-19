# 正常：创建后删除，再查应该 404（不过查不存在的 id 本身有缺陷，见 D2）
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "待删除", "done": false }
HTTP 201
[Captures]
task_id: jsonpath "$.id"

DELETE http://127.0.0.1:8000/tasks/{{task_id}}
Authorization: Bearer {{token}}
HTTP 204