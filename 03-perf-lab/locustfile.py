from locust import HttpUser, task, between


class ApiUser(HttpUser):
    """模拟一个真实用户：先登录，然后反复浏览/创建任务。"""

    wait_time = between(1, 3)      # 每个动作之间随机等 1~3 秒（模拟人的思考时间）
    token = None

    def on_start(self):
        """每个虚拟用户第一次启动时执行一次：登录拿 token。"""
        resp = self.client.post(
            "/login",
            json={"username": "tester", "password": "123456"},
            name="/login",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("token")

    @task(5)                        # 数字是权重：5 表示这个动作被执行的频率最高
    def list_tasks(self):
        """查列表（读操作，最频繁）。"""
        self.client.get("/tasks", name="/tasks 列表")

    @task(2)
    def query_missing(self):
        """查一个不存在的 id（顺便压测异常路径）。"""
        self.client.get("/tasks/not-exist-id", name="/tasks/{id} 不存在")

    @task(1)
    def create_task(self):
        """创建任务（写操作）。"""
        self.client.post(
            "/tasks",
            json={"title": "压测任务", "done": False},
            headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
            name="/tasks 创建",
        )