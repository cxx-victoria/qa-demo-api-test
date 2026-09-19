# 【缺陷复现 D1】契约不一致
#
# 现象：接口文档（OpenAPI）里 title 是普通字符串，没有长度限制；
#       但实现悄悄规定"超过 100 字符就返回 422"。
# 这条用例按"文档写的行为"来断言：应该创建成功（201）。
#
# 预期结果：这条用例 FAIL —— 失败就说明发现了缺陷。

POST http://127.0.0.1:8000/login
Content-Type: application/json
{ "username": "tester", "password": "123456" }
HTTP 200
[Captures]
token: jsonpath "$.token"

POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{
  "title": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "done": false
}
HTTP 201
