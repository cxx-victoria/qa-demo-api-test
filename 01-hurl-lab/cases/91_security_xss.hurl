
# 安全：XSS 字符串。要求原样存储（由前端负责转义），接口不能崩
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "<script>alert(1)</script>", "done": false }
HTTP 201
[Captures]
task_id: jsonpath "$.id"

GET http://127.0.0.1:8000/tasks/{{task_id}}
HTTP 200
[Asserts]
jsonpath "$.title" contains "<script>"
