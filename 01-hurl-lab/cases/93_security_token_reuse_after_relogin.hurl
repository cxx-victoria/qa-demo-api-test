
# 安全：用"重新登录前的旧 token"访问，检查 token 是否还会被接受
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
old_token: jsonpath "$.token"

POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
new_token: jsonpath "$.token"

# 本系统允许多 token 并存（无失效机制），所以下面期望仍是 201
# 这条用例是把"实际安全策略"记录下来，写进报告
POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{old_token}}
Content-Type: application/json
{ "title": "旧 token 仍可用", "done": false }
HTTP 201
