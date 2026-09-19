
# 类型：多传一个文档里没有的字段，看服务是忽略还是报错
# 期望：忽略（201），并把实际行为记录下来
POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{ "title": "多余字段测试", "done": false, "hacker": "我是多余的" }
HTTP 201
