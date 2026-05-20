# WHITE ROCK Security Runbook

## Production readiness

- Set `SECRET_KEY` to a strong random value and rotate it during controlled maintenance windows.
- Configure `STRIPE_WEBHOOK_SECRET` before enabling `STRIPE_MODE=production`.
- Restrict `/security/admin/summary` with `SECURITY_ADMIN_EMAILS` and optionally `SECURITY_ADMIN_IPS`.
- Keep `MAX_REQUEST_BODY_BYTES` low unless a specific upload workflow requires more.
- Never expose server secrets through `NEXT_PUBLIC_*` variables.

## PostgreSQL backup strategy

- Enable Render managed PostgreSQL backups.
- Keep a weekly manual snapshot before Stripe live changes, schema changes, or major releases.
- Test restore into a staging database at least once before public launch.
- Store incident notes with: deploy SHA, migration time, impacted tables, rollback decision, and recovery owner.

## Incident recovery

1. Freeze deploys and collect request IDs from API errors.
2. Check `/security/admin/summary` for suspicious auth, Stripe, Ethan, and rate-limit events.
3. If Stripe is involved, verify webhook events in Stripe dashboard and compare with `subscription_events`.
4. If data access is involved, export `security_audit_logs` and `privacy_audit_logs`.
5. Restore from snapshot only after confirming the latest good backup and notifying impacted users if required.

## Email security checklist

- Configure SPF for the sending domain.
- Configure DKIM in Resend.
- Configure DMARC with reporting before moving to enforcement.
- Keep verification/deletion links short-lived and single-purpose.
