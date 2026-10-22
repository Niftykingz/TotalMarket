"""AI provider layer with budget enforcement and rate limiting.

Phase 1 ships only the free deterministic MockProvider. A paid provider cannot be selected:
`get_provider()` refuses anything but "mock" until the owner approves provider, model,
pricing and budget (and the code for it is added and reviewed).

Every call goes through `Budget.charge()` *before* it is made: the estimated cost is checked
against the daily and monthly hard caps, and the call is refused (job suspended) if it would
exceed them. Actual usage is recorded in `api_usage`.
"""
import threading
import time
from datetime import datetime, timezone

from .database import now
from .models import canonical


class BudgetExceeded(RuntimeError):
    pass


class ProviderNotApproved(RuntimeError):
    pass


def tokens(text) -> int:
    return max(1, len(text) // 4)


class Budget:
    def __init__(self, db, daily_inr, monthly_inr):
        self.db, self._lock = db, threading.Lock()
        self.daily, self.monthly = float(daily_inr), float(monthly_inr)
        last = db.one("SELECT daily_inr, monthly_inr FROM budget_changes ORDER BY id DESC LIMIT 1")
        if last:  # owner-approved changes override settings
            self.daily, self.monthly = last["daily_inr"], last["monthly_inr"]

    def spent(self):
        d = datetime.now(timezone.utc)
        day = self.db.one("SELECT COALESCE(SUM(cost_inr),0) s FROM api_usage WHERE substr(created_at,1,10)=?", (d.strftime("%Y-%m-%d"),))["s"]
        month = self.db.one("SELECT COALESCE(SUM(cost_inr),0) s FROM api_usage WHERE substr(created_at,1,7)=?", (d.strftime("%Y-%m"),))["s"]
        return day, month

    def charge(self, est_cost):
        """Raise BudgetExceeded if a call costing `est_cost` would break a cap. Free calls always pass."""
        if est_cost <= 0:
            return
        with self._lock:
            day, month = self.spent()
            if day + est_cost > self.daily + 1e-9 or month + est_cost > self.monthly + 1e-9:
                raise BudgetExceeded(f"budget cap reached (today ₹{day:.2f}/{self.daily:.2f}, month ₹{month:.2f}/{self.monthly:.2f}); "
                                     "jobs suspended until the owner approves an increase")

    def raise_cap(self, owner_key, daily, monthly, note=""):
        from . import permissions
        permissions.require_owner(owner_key, "raise_budget")
        self.db.x("INSERT INTO budget_changes(actor, daily_inr, monthly_inr, note, created_at) VALUES (?,?,?,?,?)",
                  ("owner", float(daily), float(monthly), note, now()))
        self.db.audit("owner", "budget_change", daily=daily, monthly=monthly, note=note)
        self.daily, self.monthly = float(daily), float(monthly)


class RateLimiter:
    def __init__(self, per_minute):
        self.per_minute, self.calls, self._lock = max(1, int(per_minute)), [], threading.Lock()

    def wait(self):
        with self._lock:
            t = time.monotonic()
            self.calls = [c for c in self.calls if t - c < 60]
            if len(self.calls) >= self.per_minute:
                time.sleep(max(0, 60 - (t - self.calls[0])))
            self.calls.append(time.monotonic())


class Provider:
    name, model = "base", "base"
    inr_per_1k_in, inr_per_1k_out = 0.0, 0.0

    def __init__(self, db, budget, limiter):
        self.db, self.budget, self.limiter = db, budget, limiter

    def estimate(self, prompt, max_out=800):
        return tokens(prompt) / 1000 * self.inr_per_1k_in + max_out / 1000 * self.inr_per_1k_out

    def complete(self, agent, system, payload, task_id=None):
        prompt = system + "\n<untrusted_data>\n" + canonical(payload) + "\n</untrusted_data>"
        self.budget.charge(self.estimate(prompt))
        self.limiter.wait()
        out = self._generate(agent, payload)
        pt, ct = tokens(prompt), tokens(canonical(out))
        cost = pt / 1000 * self.inr_per_1k_in + ct / 1000 * self.inr_per_1k_out
        self.db.x("INSERT INTO api_usage(task_id, agent, provider, model, prompt_tokens, completion_tokens, cost_inr, created_at) "
                  "VALUES (?,?,?,?,?,?,?,?)", (task_id, agent, self.name, self.model, pt, ct, round(cost, 6), now()))
        return out

    def _generate(self, agent, payload):
        raise NotImplementedError


class MockProvider(Provider):
    """Free and deterministic: the same input always gives the same output. Used by the demo
    and every test. Agent-specific generators live with each agent (agents/*.py: mock())."""
    name, model = "mock", "mock-deterministic-1"
    handlers = {}

    def _generate(self, agent, payload):
        fn = self.handlers.get(agent)
        if not fn:
            raise RuntimeError(f"mock provider has no generator for {agent}")
        return fn(payload)


class PricedMockProvider(MockProvider):
    """Mock output with a pretend price, for testing budget caps without spending money."""
    name = "mock-priced"

    def __init__(self, db, budget, limiter, inr_in=1.0, inr_out=1.0):
        super().__init__(db, budget, limiter)
        self.inr_per_1k_in, self.inr_per_1k_out = inr_in, inr_out


def get_provider(settings, db):
    budget = Budget(db, settings.budget_daily_inr, settings.budget_monthly_inr)
    limiter = RateLimiter(settings.calls_per_minute)
    if settings.provider == "mock":
        return MockProvider(db, budget, limiter)
    raise ProviderNotApproved(f"provider '{settings.provider}' is not approved. Paid AI calls need the owner's approval "
                              "of provider, model, pricing and budget first.")
