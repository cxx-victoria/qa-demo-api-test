
# 边界：中文标题（检查编码与长度按字符还是字节计算）
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "这是一条中文标题的测试任务", "done": false }
HTTP 201
[Captures]
task_id: jsonpath "$.id"

GET http://127.0.0.1:8000/tasks/{{task_id}}
HTTP 200
[Asserts]
jsonpath "$.title" == "这是一条中文标题的测试任务"
