# 【异常用例】用错误的密码登录，应该被拒绝
# 这种"负向用例"和正常用例一样重要：系统该拒绝的时候，必须拒绝

POST http://127.0.0.1:8000/login
Content-Type: application/json
{
  "username": "tester",
  "password": "wrong-password"
}
HTTP 401
