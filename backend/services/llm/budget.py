"""
LLM Token 预算控制模块

管理用户的 Token 使用量，支持每日/每月限额。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.services.llm.models import get_model_info


@dataclass
class BudgetLimit:
    """预算限制配置"""
    daily_tokens: int = 100000  # 每日限额
    monthly_tokens: int = 1000000  # 每月限额
    daily_cost: float = 10.0  # 每日费用上限（美元）
    monthly_cost: float = 100.0  # 每月费用上限（美元）


@dataclass
class UsageRecord:
    """使用记录"""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    provider: str
    model: str


@dataclass
class BudgetStatus:
    """预算状态"""
    daily_used_tokens: int = 0
    daily_used_cost: float = 0.0
    monthly_used_tokens: int = 0
    monthly_used_cost: float = 0.0
    daily_limit: int = 100000
    monthly_limit: int = 1000000
    daily_cost_limit: float = 10.0
    monthly_cost_limit: float = 100.0

    @property
    def daily_remaining_tokens(self) -> int:
        return max(0, self.daily_limit - self.daily_used_tokens)

    @property
    def monthly_remaining_tokens(self) -> int:
        return max(0, self.monthly_limit - self.monthly_used_tokens)

    @property
    def daily_remaining_cost(self) -> float:
        return max(0.0, self.daily_cost_limit - self.daily_used_cost)

    @property
    def monthly_remaining_cost(self) -> float:
        return max(0.0, self.monthly_cost_limit - self.monthly_used_cost)

    @property
    def is_daily_exceeded(self) -> bool:
        return self.daily_used_tokens >= self.daily_limit

    @property
    def is_monthly_exceeded(self) -> bool:
        return self.monthly_used_tokens >= self.monthly_limit

    @property
    def is_cost_exceeded(self) -> bool:
        return self.daily_used_cost >= self.daily_cost_limit


class TokenBudget:
    """
    Token 预算管理器

    追踪用户 Token 使用量，检查预算限制。
    """

    def __init__(
        self,
        user_id: int,
        daily_limit: int = 100000,
        monthly_limit: int = 1000000,
        daily_cost_limit: float = 10.0,
        monthly_cost_limit: float = 100.0
    ):
        self.user_id = user_id
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.daily_cost_limit = daily_cost_limit
        self.monthly_cost_limit = monthly_cost_limit

        # 内存中的使用记录（生产环境应持久化到数据库）
        self._records: list[UsageRecord] = []
        self._daily_used_tokens = 0
        self._daily_used_cost = 0.0
        self._monthly_used_tokens = 0
        self._monthly_used_cost = 0.0
        self._last_daily_reset: datetime | None = None
        self._last_monthly_reset: datetime | None = None

    def _check_and_reset_daily(self) -> None:
        """检查并重置每日计数"""
        now = datetime.utcnow()
        today = now.date()

        if self._last_daily_reset is None:
            self._last_daily_reset = now
            return

        last_date = self._last_daily_reset.date()
        if today > last_date:
            # 新的一天，重置每日计数
            self._daily_used_tokens = 0
            self._daily_used_cost = 0.0
            self._last_daily_reset = now

    def _check_and_reset_monthly(self) -> None:
        """检查并重置每月计数"""
        now = datetime.utcnow()
        this_month = (now.year, now.month)

        if self._last_monthly_reset is None:
            self._last_monthly_reset = now
            return

        last_month = (self._last_monthly_reset.year, self._last_monthly_reset.month)
        if this_month > last_month:
            # 新的一月，重置每月计数
            self._monthly_used_tokens = 0
            self._monthly_used_cost = 0.0
            self._last_monthly_reset = now

    def get_status(self) -> BudgetStatus:
        """获取当前预算状态"""
        self._check_and_reset_daily()
        self._check_and_reset_monthly()

        return BudgetStatus(
            daily_used_tokens=self._daily_used_tokens,
            daily_used_cost=self._daily_used_cost,
            monthly_used_tokens=self._monthly_used_tokens,
            monthly_used_cost=self._monthly_used_cost,
            daily_limit=self.daily_limit,
            monthly_limit=self.monthly_limit,
            daily_cost_limit=self.daily_cost_limit,
            monthly_cost_limit=self.monthly_cost_limit,
        )

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str
    ) -> float:
        """
        估算请求成本

        Args:
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            model: 模型名称

        Returns:
            估算成本（美元）
        """
        model_info = get_model_info(model)

        input_cost = (input_tokens / 1_000_000) * (model_info.input_price or 0)
        output_cost = (output_tokens / 1_000_000) * (model_info.output_price or 0)

        return input_cost + output_cost

    def check_budget(
        self,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        model: str
    ) -> tuple[bool, str]:
        """
        检查预算是否足够

        Args:
            estimated_input_tokens: 估算输入 token
            estimated_output_tokens: 估算输出 token
            model: 模型名称

        Returns:
            (是否允许, 原因)
        """
        self._check_and_reset_daily()
        self._check_and_reset_monthly()

        estimated_total = estimated_input_tokens + estimated_output_tokens
        estimated_cost = self.estimate_cost(
            estimated_input_tokens,
            estimated_output_tokens,
            model
        )

        # 检查每日限额
        if self._daily_used_tokens + estimated_total > self.daily_limit:
            remaining = self.daily_limit - self._daily_used_tokens
            return False, f"每日 Token 限额已超出。当前剩余: {remaining}"

        # 检查每月限额
        if self._monthly_used_tokens + estimated_total > self.monthly_limit:
            remaining = self.monthly_limit - self._monthly_used_tokens
            return False, f"每月 Token 限额已超出。当前剩余: {remaining}"

        # 检查每日费用限额
        if self._daily_used_cost + estimated_cost > self.daily_cost_limit:
            remaining = self.daily_cost_limit - self._daily_used_cost
            return False, f"每日费用限额已超出。当前剩余: ${remaining:.2f}"

        # 检查每月费用限额
        if self._monthly_used_cost + estimated_cost > self.monthly_cost_limit:
            remaining = self.monthly_cost_limit - self._monthly_used_cost
            return False, f"每月费用限额已超出。当前剩余: ${remaining:.2f}"

        return True, "OK"

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        provider: str,
        model: str,
        timestamp: datetime | None = None
    ) -> UsageRecord:
        """
        记录实际使用量

        Args:
            input_tokens: 实际输入 token
            output_tokens: 实际输出 token
            provider: Provider 名称
            model: 模型名称
            timestamp: 时间戳（可选，默认当前时间）

        Returns:
            使用记录
        """
        self._check_and_reset_daily()
        self._check_and_reset_monthly()

        if timestamp is None:
            timestamp = datetime.utcnow()

        total_tokens = input_tokens + output_tokens
        cost = self.estimate_cost(input_tokens, output_tokens, model)

        # 创建使用记录
        record = UsageRecord(
            timestamp=timestamp,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            provider=provider,
            model=model
        )

        # 更新计数
        self._records.append(record)
        self._daily_used_tokens += total_tokens
        self._daily_used_cost += cost
        self._monthly_used_tokens += total_tokens
        self._monthly_used_cost += cost

        return record

    def get_usage_history(
        self,
        days: int = 7,
        provider: str | None = None
    ) -> list[UsageRecord]:
        """
        获取使用历史

        Args:
            days: 查询天数
            provider: 可选，按 Provider 过滤

        Returns:
            使用记录列表
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        records = [
            r for r in self._records
            if r.timestamp >= cutoff
        ]

        if provider:
            records = [r for r in records if r.provider == provider]

        return records

    def get_usage_by_day(self, days: int = 7) -> dict[str, dict]:
        """
        按日期统计使用量

        Args:
            days: 查询天数

        Returns:
            {date: {tokens, cost, requests}}
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        result: dict[str, dict] = {}

        for record in self._records:
            if record.timestamp < cutoff:
                continue

            date_str = record.timestamp.strftime("%Y-%m-%d")
            if date_str not in result:
                result[date_str] = {
                    "tokens": 0,
                    "cost": 0.0,
                    "requests": 0
                }

            result[date_str]["tokens"] += record.total_tokens
            result[date_str]["cost"] += record.cost
            result[date_str]["requests"] += 1

        return result


# 全局预算管理器（生产环境应使用数据库存储）
_budget_cache: dict[int, TokenBudget] = {}


def get_user_budget(user_id: int) -> TokenBudget:
    """
    获取用户预算管理器

    Args:
        user_id: 用户 ID

    Returns:
        TokenBudget 实例
    """
    if user_id not in _budget_cache:
        _budget_cache[user_id] = TokenBudget(user_id=user_id)
    return _budget_cache[user_id]


def clear_user_budget(user_id: int) -> None:
    """清除用户预算缓存（用于测试或重置）"""
    if user_id in _budget_cache:
        del _budget_cache[user_id]
