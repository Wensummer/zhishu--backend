"""演示用调价/故障公告(原样移植 lib/demo/announcements.ts)。

Phase 后期由运营后台 / 监控取数替换。
"""
from app.schemas.announcement import Announcement

ANNOUNCEMENTS: list[Announcement] = [
    Announcement(
        id="a-1", kind="priceChange",
        title="DeepSeek-V3 输出价下调 12%",
        body="自 2026-06-15 起生效,提前 7 天公示。老客户合同锁价不受影响。",
        model_id="deepseek-v3", published_at="2026-06-08",
    ),
    Announcement(
        id="a-2", kind="incident",
        title="DeepSeek-R1 短时延迟升高",
        body="06-06 14:20 ~ 15:05 TTFT 升高约 300ms,已扩容恢复,期间无请求失败。",
        model_id="deepseek-r1", published_at="2026-06-06", resolved_at="2026-06-06",
    ),
    Announcement(
        id="a-3", kind="shelf",
        title="新增上架 Kimi-128K 超长上下文",
        body="适配长文档 / RAG 场景,已纳入横评与选型引擎。",
        model_id="moonshot-128k", published_at="2026-06-01",
    ),
    Announcement(
        id="a-4", kind="maintenance",
        title="文心一言-4.0 例行维护",
        body="05-30 02:00 ~ 02:30 滚动维护,采用灰度切换,服务不中断。",
        model_id="ernie-4", published_at="2026-05-30", resolved_at="2026-05-30",
    ),
]
