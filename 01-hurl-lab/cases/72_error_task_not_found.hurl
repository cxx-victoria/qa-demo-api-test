
# 异常：查询不存在的任务，期望 404（这条会失败 = 缺陷 D2）
GET http://127.0.0.1:8000/tasks/does-not-exist-999
HTTP 404
