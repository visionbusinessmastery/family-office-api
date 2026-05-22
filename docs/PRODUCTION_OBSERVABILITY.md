# WHITE ROCK Production Observability

## Runtime monitoring

- `/health` returns aggregated platform status.
- `/health/db`, `/health/cache`, `/health/openai`, `/health/stripe` are ready for UptimeRobot or Render checks.
- `/system/admin/diagnostics` exposes dependency status, feature flags and Ethan cost summaries for security admins.
- `/system/admin/system-state` exposes the current hybrid source map for security admins without executing business logic.
- `/system/admin/mismatch-report` returns a passive safe-mode mismatch report scaffold. It does not auto-compare or correct production data.

## Hybrid consistency audit

WHITE ROCK currently runs in a safe hybrid state:

- Score: `/intelligence/global-command-center` is the dashboard view while `/intelligence/user-intelligence` and recalculation endpoints remain active.
- Opportunities: command center, category opportunities and deal-flow generation intentionally coexist.
- Gamification: `/gamification/`, `/product/context` and command center keep overlapping state for resilience.
- Portfolio and finance: backend domain services return raw and domain totals while the frontend still keeps legacy consolidated calculations.

The mismatch report is intentionally passive. It preserves all sources, performs no automatic correction and requires manual review before any remediation.

## Sentry

Set:

- `SENTRY_DSN`
- `APP_ENV=production`
- `SENTRY_TRACES_SAMPLE_RATE=0.05`

Payloads are scrubbed for common sensitive keys before being sent.

## PostHog

Set:

- `POSTHOG_API_KEY`
- `POSTHOG_HOST`

Tracking is consent-aware and only dispatches when the user accepted analytics.

## Feature flags

Table: `feature_flags`

Initial flags:

- `opportunity_real_estate_v2`
- `opportunity_business_v2`
- `opportunity_investments_v2`
- `legacy_international`
- `ethan_dynasty`
- `referrals_v2`
- `weekly_reports_v2`

Feature flags complement entitlements. They do not replace subscription rules.

## Load testing

Install Locust locally or in a disposable environment:

```bash
pip install locust
locust -f tests/load/locustfile.py --host https://family-office-api-n4sv.onrender.com
```

Suggested founder launch target: 50 concurrent users, 10 minute run, zero 5xx on health/auth/read endpoints.

## Stripe readiness

Run before enabling live mode:

```bash
python scripts/stripe_production_check.py
```
