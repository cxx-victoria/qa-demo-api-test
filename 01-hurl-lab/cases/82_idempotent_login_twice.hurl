
# 幂等：连续登录两次，应该都能成功（登录不是幂等操作，但这里是查"重复登录会不会出问题"）
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token1: jsonpath "$.token"

POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Asserts]
jsonpath "$.token" isString
