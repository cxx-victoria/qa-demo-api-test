
# 边界：emoji 和特殊符号，要求能正常存储不乱码
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "测试 emoji 🚀🎉 和符号 <>&\"'", "done": false }
HTTP 201
[Captures]
task_id: jsonpath "$.id"

GET http://127.0.0.1:8000/tasks/{{task_id}}
HTTP 200
[Asserts]
jsonpath "$.title" contains "🚀"
