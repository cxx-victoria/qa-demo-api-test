"""数据库一致性测试：接口返回的"成功"，和数据库里真实的"数据"，是不是同一回事？

为什么要有这一层（面试高频）：
    接口测试只能看到 HTTP 响应。**返回 201 不等于数据真的写对了**，
    返回 204 也不等于数据真的删对了。所以要在「接口行为」和「数据库真实状态」
    之间做**交叉验证**（cross-check），这是测试工程师的必备技能。

典型能抓到的问题：
    · 接口返回成功但库里没有这条记录（写丢失 / 事务没提交）
    · 接口返回失败但库里数据已经变了（脏写）
    · 未授权请求虽然"应该被拒绝"，但数据真的被删了 —— 接口层看不出严重性，数据层能
    · 列表接口返回的条数/顺序与库表不一致（分页、排序、缓存导致）
    · 非法数据（空标题）真的落库了（脏数据）
    · 字段类型在库里的真实形态（D4：done 在库里是 0/1 整数）

前置条件：被测服务必须正在运行。
    在另一个窗口执行（不要关）：
        cd D:\\qa-projects\\00-demo-api
        .\\.venv\\Scripts\\Activate.ps1
        uvicorn app:app --port 8000

用法（项目目录 D:\\qa-projects\\07-db-lab 下）：
    cd D:\\qa-projects\\00-demo-api
    .\\.venv\\Scripts\\Activate.ps1
    pip install pytest
    cd ..\\07-db-lab
    python -m pytest test_db_consistency.py -v

设计要点：
    · 数据库连接使用**只读模式**（mode=ro），测试永远不可能写坏数据
    · 测试自己创建的记录，跑完自动通过接口清理，不污染数据
    · 已知缺陷（D3 越权、空标题落库）用 xfail 标注：缺陷还在 → xfailed，修好 → xpassed
"""
import os
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import requests

# ------------------------------------------------------------------ 配置
API = os.environ.get("DEMO_API", "http://127.0.0.1:8000")
CRED = {"username": "tester", "password": "123456"}
MAX_ROWS = 5000

HERE = Path(__file__).resolve().parent
DB_CANDIDATES = [
    os.environ.get("DEMO_DB"),
    str(HERE.parent / "00-demo-api" / "tasks.db"),
    str(HERE / "tasks.db"),
    r"D:\qa-projects\00-demo-api\tasks.db",
]


# ------------------------------------------------------------------ fixture
@pytest.fixture(scope="session", autouse=True)
def require_service():
    """先确认被测服务活着，否则直接给出人话提示，而不是一堆看不懂的报错。"""
    try:
        resp = requests.get(f"{API}/tasks", timeout=5)
        if resp.status_code != 200:
            raise RuntimeError(f"返回码 {resp.status_code}")
    except Exception as exc:
        raise RuntimeError(
            f"\n被测服务不可用：{API}/tasks\n"
            f"原因：{exc}\n"
            "请先另开一个窗口启动被测服务（并保持运行）：\n"
            "    cd D:\\qa-projects\\00-demo-api\n"
            "    .\\.venv\\Scripts\\Activate.ps1\n"
            "    uvicorn app:app --port 8000\n"
        ) from exc


@pytest.fixture(scope="session")
def db_path():
    """定位 SQLite 数据库文件。"""
    for cand in DB_CANDIDATES:
        if cand and Path(cand).exists():
            return Path(cand)
    raise RuntimeError(
        "找不到 tasks.db。已尝试以下位置：\n  "
        + "\n  ".join(str(c) for c in DB_CANDIDATES)
        + "\n可以用环境变量指定：$env:DEMO_DB = '完整路径\\tasks.db'"
    )


@pytest.fixture()
def db(db_path):
    """只读连接数据库：测试只做校验，不可能写坏数据。"""
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def token():
    resp = requests.post(f"{API}/login", json=CRED, timeout=10)
    resp.raise_for_status()
    return resp.json()["token"]


@pytest.fixture()
def created(token):
    """记录本用例创建的 task_id，跑完自动清理。"""
    ids = []
    yield ids
    h = {"Authorization": f"Bearer {token}"}
    for task_id in ids:
        try:
            requests.delete(f"{API}/tasks/{task_id}", headers=h, timeout=10)
        except Exception:
            pass


# ------------------------------------------------------------------ 工具函数
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def unique_title(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def create(token, title, done=False):
    return requests.post(
        f"{API}/tasks", json={"title": title, "done": done},
        headers=headers(token), timeout=10,
    )


def row_of(db, task_id):
    return db.execute(
        "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()


# ==================================================================
# 一、写操作：接口成功 ≠ 数据落库
# ==================================================================
def test_test_db_is_same_file_service_writes(token, db, db_path, created):
    """前置自检：测试读的数据库文件，必须和服务写的是同一个。

    为什么必须有这条：
        如果 DEMO_DB 指错了文件，后面所有一致性用例都会失败，
        但真正的原因只是"路径配错"，而不是被测系统有缺陷 ——
        这属于典型的"环境问题伪装成缺陷"。
        这条用例用一个探针任务把两者区分开，并直接告诉你排查方向。
    """
    title = unique_title("库同源自检")
    resp = create(token, title)
    assert resp.status_code == 201, f"探针创建失败：{resp.status_code} {resp.text}"
    task_id = resp.json()["id"]
    created.append(task_id)

    assert row_of(db, task_id) is not None, (
        "\n测试读的数据库文件，和服务真正写入的不是同一个！\n"
        f"  接口创建成功（id={task_id}），但记录没有出现在测试读取的库里。\n"
        f"  测试当前读取：{db_path}\n"
        "  排查方法：确认被测服务启动时的工作目录（或 DEMO_DB 环境变量）\n"
        "  与测试的 DEMO_DB 指向的是同一个 tasks.db。\n"
        "  典型写法：$env:DEMO_DB = 'D:\\qa-projects\\00-demo-api\\tasks.db'\n"
    )


def test_create_persists_to_db(token, db, created):
    """创建接口返回 201 后，数据库里必须真的有这条记录，且字段值正确。"""
    title = unique_title("落库校验")
    resp = create(token, title)
    assert resp.status_code == 201, f"创建失败：{resp.status_code} {resp.text}"

    task_id = resp.json()["id"]
    created.append(task_id)

    row = row_of(db, task_id)
    assert row is not None, (
        f"接口返回 201（声称创建成功），但数据库里查不到 id={task_id} —— 写丢失"
    )
    assert row["title"] == title, "数据库里的 title 与提交的不一致"
    assert row["done"] == 0, "新建任务的 done 应为 0"


def test_delete_removes_row_from_db(token, db, created):
    """删除接口返回 204 后，数据库里这条记录必须真的消失。"""
    resp = create(token, unique_title("删除校验"))
    task_id = resp.json()["id"]
    created.append(task_id)
    assert row_of(db, task_id) is not None, "前置条件失败：创建后库里应有数据"

    deleted = requests.delete(f"{API}/tasks/{task_id}", headers=headers(token), timeout=10)
    assert deleted.status_code == 204

    assert row_of(db, task_id) is None, (
        f"接口返回 204（声称删除成功），但数据库里 id={task_id} 还在 —— 假删除"
    )


def test_delete_twice_keeps_db_clean(token, db, created):
    """重复删除同一条：第二次应返回 404，并且库里始终没有这条记录。"""
    resp = create(token, unique_title("重复删除"))
    task_id = resp.json()["id"]
    created.append(task_id)

    first = requests.delete(f"{API}/tasks/{task_id}", headers=headers(token), timeout=10)
    second = requests.delete(f"{API}/tasks/{task_id}", headers=headers(token), timeout=10)

    assert first.status_code == 204
    assert second.status_code == 404, f"重复删除期望 404，实际 {second.status_code}"
    assert row_of(db, task_id) is None


# ==================================================================
# 二、读操作：列表接口与库表必须完全一致
# ==================================================================
def test_api_list_matches_db_rows(token, db):
    """接口返回的列表，必须与数据库里的记录逐条一致（含顺序）。"""
    api_rows = requests.get(f"{API}/tasks", params={"limit": MAX_ROWS}, timeout=10).json()
    db_rows = [
        dict(r) for r in db.execute(
            "SELECT id, title, done FROM tasks ORDER BY rowid LIMIT ?", (MAX_ROWS,)
        )
    ]

    assert len(api_rows) == len(db_rows), (
        f"接口返回 {len(api_rows)} 条，数据库有 {len(db_rows)} 条 —— 数量不一致"
    )
    for index, (api_row, db_row) in enumerate(zip(api_rows, db_rows)):
        assert api_row["id"] == db_row["id"], f"第 {index + 1} 条 id 不一致（顺序或分页有问题）"
        assert api_row["title"] == db_row["title"], f"第 {index + 1} 条 title 不一致"
        assert bool(api_row["done"]) == bool(db_row["done"]), f"第 {index + 1} 条 done 不一致"


def test_list_pagination_is_consistent(token):
    """分页：limit + offset 取出来的切片，必须等于全量结果按同样方式切片。"""
    all_rows = requests.get(f"{API}/tasks", params={"limit": MAX_ROWS}, timeout=10).json()
    page = requests.get(f"{API}/tasks", params={"limit": 2, "offset": 1}, timeout=10).json()

    assert page == all_rows[1:3], "分页结果与全量结果的对应切片不一致 —— 分页或排序有 bug"


# ==================================================================
# 三、数据层看缺陷 D3：未授权删除的"真实严重性"
# ==================================================================
@pytest.mark.xfail(
    reason="已知缺陷 D3：删除接口未校验 Authorization，未授权也能删（接口层证据）",
    strict=False,
)
def test_unauthorized_delete_should_be_rejected(token, created):
    """【缺陷 D3 · 接口层】不带 token 删除应当被拒绝（401）。"""
    resp = create(token, unique_title("越权-接口层"))
    task_id = resp.json()["id"]
    created.append(task_id)

    no_auth = requests.delete(f"{API}/tasks/{task_id}", timeout=10)
    assert no_auth.status_code == 401, (
        f"未授权删除期望 401，实际 {no_auth.status_code} "
        "（D3：删除接口完全没校验 Authorization）"
    )


@pytest.mark.xfail(
    reason="已知缺陷 D3：未授权删除不只是返回码错，数据真的被删了（数据层证据）",
    strict=False,
)
def test_unauthorized_delete_must_not_touch_data(token, db, created):
    """【缺陷 D3 · 数据层】这条才是把严重度钉死的证据。

    接口层看到的是"返回码不对"（204 而应该是 401），
    数据层看到的是"别人的数据真的没了" —— 两层证据叠加，
    才能把缺陷从"错误码不规范"升级为"高危越权 + 数据被破坏"。
    """
    resp = create(token, unique_title("越权-数据层"))
    task_id = resp.json()["id"]
    created.append(task_id)
    assert row_of(db, task_id) is not None

    requests.delete(f"{API}/tasks/{task_id}", timeout=10)  # 故意不带 token

    row = row_of(db, task_id)
    assert row is not None, (
        f"【高危 · 数据层证据】未授权请求删除 id={task_id} 后，"
        "数据库里的记录真的消失了 —— 越权不只是返回码问题，而是造成了数据破坏"
    )


# ==================================================================
# 四、边界与脏数据在数据库中的真实形态
# ==================================================================
def test_title_100_chars_is_persisted(token, db, created):
    """边界内（100 字符）应当正常落库。"""
    title = "a" * 100
    resp = create(token, title)
    assert resp.status_code == 201
    created.append(resp.json()["id"])
    assert row_of(db, resp.json()["id"])["title"] == title


def test_title_101_chars_is_not_persisted(token, db):
    """边界外（101 字符）：实现返回 422，那就不能在库里留下记录。

    这条同时验证了"拒绝"是不是真的拒绝 —— 有的实现会先写库再报错。
    """
    resp = create(token, "a" * 101)
    assert resp.status_code == 422, f"期望 422，实际 {resp.status_code}"

    leaked = db.execute("SELECT id FROM tasks WHERE title = ?", ("a" * 101,)).fetchone()
    assert leaked is None, "接口返回 422（拒绝），但数据仍然写进了库 —— 拒绝不彻底"


@pytest.mark.xfail(
    reason="已知问题：空标题/纯空格未被校验，会作为脏数据落库",
    strict=False,
)
def test_empty_title_should_not_be_persisted(token, created):
    """空标题与纯空格不应落库（属于脏数据）。"""
    for bad in ("", "   "):
        resp = create(token, bad)
        if resp.status_code == 201:
            created.append(resp.json()["id"])
            raise AssertionError(f"空值标题 {bad!r} 被接受并落库了（返回 201）")
        assert resp.status_code == 422, f"标题 {bad!r} 期望 422，实际 {resp.status_code}"


def test_done_field_type_in_db(token, db, created):
    """【缺陷 D4 · 数据层】库里 done 的真实类型是 0/1 整数，不是 boolean。"""
    resp = create(token, unique_title("类型校验"), done=True)
    task_id = resp.json()["id"]
    created.append(task_id)

    raw = db.execute(
        "SELECT done, typeof(done) AS t FROM tasks WHERE id = ?", (task_id,)
    ).fetchone()
    assert raw["t"] == "integer", f"库里 done 的类型是 {raw['t']}"
    assert raw["done"] in (0, 1)
    assert isinstance(resp.json()["done"], int), (
        "接口返回的 done 是 int，与接口契约声明的 boolean 不一致（缺陷 D4）"
    )


# ==================================================================
# 五、全表数据完整性
# ==================================================================
def test_all_ids_are_valid_uuid_hex(token, db, created):
    """全表扫描：id 必须非空、唯一、32 位十六进制（uuid4().hex）。

    先自己造一条探针数据，保证表非空 —— 否则在空库上这条用例会误报
    （前面的用例跑完会清理掉自己创建的数据）。
    """
    resp = create(token, unique_title("全表扫描探针"))
    assert resp.status_code == 201
    created.append(resp.json()["id"])

    rows = db.execute("SELECT id FROM tasks").fetchall()
    assert rows, "表里一条数据都没有（探针也没写进去）—— 数据库同源性可能有问题"
    ids = [r["id"] for r in rows]
    for task_id in ids:
        assert task_id, "存在空 id"
        assert len(task_id) == 32, f"id 长度不是 32：{task_id!r}"
        assert all(ch in "0123456789abcdef" for ch in task_id), f"id 含非十六进制字符：{task_id!r}"
    assert len(ids) == len(set(ids)), "存在重复 id（主键约束被绕过）"


def test_all_titles_are_non_null(token, db, created):
    """全表扫描：title 不应为 NULL（NOT NULL 约束是否真的生效）。"""
    resp = create(token, unique_title("NOT NULL 探针"))
    assert resp.status_code == 201
    created.append(resp.json()["id"])

    nulls = db.execute("SELECT COUNT(*) AS n FROM tasks WHERE title IS NULL").fetchone()["n"]
    assert nulls == 0, f"有 {nulls} 条记录的 title 是 NULL"


# ==================================================================
# 六、并发写入（SQLite 单写锁的真实表现）
# ==================================================================
def test_concurrent_creates_all_persisted(token, db, created):
    """并发创建 8 条：全部应成功落库，且 id 不重复。

    这也是性能报告里"SQLite 单写锁导致部分请求 500"那个说法的数据层验证。
    """
    def one(index):
        resp = create(token, unique_title(f"并发{index}"))
        return resp.status_code, (resp.json().get("id") if resp.status_code == 201 else None)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(one, range(8)))

    ok = [task_id for code, task_id in results if code == 201]
    created.extend(ok)

    assert len(ok) == 8, (
        f"并发 8 条只成功 {len(ok)} 条，返回码分布={[c for c, _ in results]}"
        "（可能是 SQLite 写锁竞争导致）"
    )
    assert len(set(ok)) == 8, "并发创建出现了重复 id"

    missing = [task_id for task_id in ok if row_of(db, task_id) is None]
    assert not missing, f"接口返回成功但未落库的 id：{missing}"
