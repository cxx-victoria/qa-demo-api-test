# 正常：登录后创建一个普通任务
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "正常任务", "done": false }
HTTP 201
[Asserts]
jsonpath "$.title" == "正常任务"