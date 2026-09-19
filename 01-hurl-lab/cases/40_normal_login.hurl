# 正常：正确的账号密码登录，返回 token
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Asserts]
jsonpath "$.token" isString
jsonpath "$.username" == "tester"