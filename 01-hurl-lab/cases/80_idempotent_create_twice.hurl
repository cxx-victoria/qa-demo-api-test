
# 幂等：同一个标题连续创建两次，应该生成两条不同的记录（说明没有幂等控制）
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "重复创建测试", "done": false }
HTTP 201
[Captures]
id1: jsonpath "$.id"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "重复创建测试", "done": false }
HTTP 201
[Asserts]
jsonpath "$.id" != "{{id1}}"
