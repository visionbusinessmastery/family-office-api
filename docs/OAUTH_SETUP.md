# WHITE ROCK OAuth Setup

## Callback URLs

Backend callbacks:

- Google: `https://family-office-api-n4sv.onrender.com/auth/oauth/google/callback`
- Apple: `https://family-office-api-n4sv.onrender.com/auth/oauth/apple/callback`

Local callbacks:

- Google: `http://localhost:8000/auth/oauth/google/callback`
- Apple: `http://localhost:8000/auth/oauth/apple/callback`

## Google Cloud

1. Create an OAuth client in Google Cloud Console.
2. Application type: Web application.
3. Add authorized redirect URI:
   - production callback above
   - local callback if needed
4. Scopes used by WHITE ROCK:
   - `openid`
   - `email`
   - `profile`
5. Set Render env vars:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`

## Apple

1. Enable Sign in with Apple in Apple Developer.
2. Create Services ID for the web client.
3. Add redirect URL:
   - production callback above
4. Create a private key for Sign in with Apple.
5. Set Render env vars:
   - `APPLE_CLIENT_ID`
   - `APPLE_TEAM_ID`
   - `APPLE_KEY_ID`
   - `APPLE_PRIVATE_KEY`
   - optional `APPLE_CLIENT_SECRET` if you prefer to pre-generate it.

`APPLE_PRIVATE_KEY` can be stored with escaped newlines.

## Required platform URLs

- `FRONTEND_URL=https://vision-business.com`
- `BACKEND_URL=https://family-office-api-n4sv.onrender.com`

## Feature flags

OAuth providers can be disabled without redeploy:

- `oauth_google_enabled`
- `oauth_apple_enabled`
- `oauth_microsoft_enabled`
- `oauth_linkedin_enabled`

Microsoft and LinkedIn are intentionally prepared but disabled.

## Account linking

If a user already exists with the OAuth email, WHITE ROCK links the provider to
the existing user. It does not create a duplicate user, so billing, portfolio,
Ethan memory, gamification and workspaces stay attached to the same account.

## Privacy

Only provider identity metadata is stored by default:

- provider
- provider user id
- provider email
- avatar

Provider access and refresh tokens are optional columns but are not stored by
the current login flow.
