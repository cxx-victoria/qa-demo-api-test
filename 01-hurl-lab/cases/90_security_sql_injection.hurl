
# 安全：SQL 注入字符串。正确行为是"当普通文本存进去"，列表接口仍然正常
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "' OR 1=1 --", "done": false }
HTTP 201

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "x'); DROP TABLE tasks;--", "done": false }
HTTP 201

# 关键验证：如果表被注入删掉了，下面这行就会失败
GET http://127.0.0.1:8000/tasks
HTTP 200
[Asserts]
jsonpath "$" isCollection
