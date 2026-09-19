# 【业务流测试】模拟一个真实用户：登录 → 创建任务 → 查回来验证
# 这里用到 hurl 的核心能力：把上一个请求的返回值，传给下一个请求

# ---------- 第 1 步：登录，拿到 token ----------
POST http://127.0.0.1:8000/login
Content-Type: application/json
{
  "username": "tester",
  "password": "123456"
}
HTTP 200
[Asserts]
jsonpath "$.token" isString
jsonpath "$.username" == "tester"
[Captures]
token: jsonpath "$.token"

# ---------- 第 2 步：用 token 创建任务 ----------
POST http://127.0.0.1:8000/tasks
Authorization: Bearer {{token}}
Content-Type: application/json
{
  "title": "我的第一条自动化用例",
  "done": false
}
HTTP 201
[Asserts]
jsonpath "$.id" isString
jsonpath "$.title" == "我的第一条自动化用例"
[Captures]
task_id: jsonpath "$.id"

# ---------- 第 3 步：按 id 查回来，确认真的存进去了 ----------
GET http://127.0.0.1:8000/tasks/{{task_id}}
HTTP 200
[Asserts]
jsonpath "$.id" == "{{task_id}}"
jsonpath "$.title" == "我的第一条自动化用例"

# ---------- 第 4 步：删除，并确认删除成功 ----------
DELETE http://127.0.0.1:8000/tasks/{{task_id}}
Authorization: Bearer {{token}}
HTTP 204
