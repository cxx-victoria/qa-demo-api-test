
# 类型：done 传字符串 "yes"，期望被拒绝（422）
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "类型测试", "done": "yes" }
HTTP 422

