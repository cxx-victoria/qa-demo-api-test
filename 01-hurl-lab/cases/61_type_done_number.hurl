
# 类型：done 传数字 1。Pydantic 通常会把 1 转成 true，所以可能返回 201
# 这条用例的作用是"把实际行为记录下来"，而不是判断对错
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "类型测试2", "done": 1 }
HTTP 201
[Asserts]
jsonpath "$.done" isBoolean
