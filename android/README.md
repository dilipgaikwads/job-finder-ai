# Android app

Target: Samsung Galaxy S26 Ultra (Android 15+, large screen, S-Pen aware). Min SDK 30.

**Status:** directory layout + screen inventory. No build yet — this scaffold is deliberately code-light so a Kotlin/Android engineer can wire the Gradle build to house conventions (KMP? Version catalog source? CI?) without ripping out placeholders.

## Planned modules

```
android/
  app/
    src/main/java/com/jobfinderai/
      ui/           # Jetpack Compose screens (see below)
      data/         # Repositories, Retrofit clients to /jobs/verify etc.
      domain/       # Kotlin mirrors of backend evidence/profile/job models
      di/           # Hilt modules
    src/main/res/   # themes (light/dark), typography, adaptive layouts
```

## Screens (matches `docs/ARCHITECTURE.md` §main_screens)

1. Dashboard — new matches, high-pay, remote, international, AI, needs-attention, upcoming interviews, learning.
2. My Profile
3. Resume/CV Manager
4. Job Discovery
5. Recommended Jobs
6. Job Verification (surfaces the `VerificationReport` from backend — per-signal, factual, non-defamatory)
7. Job Details
8. Application Center
9. Application Tracker
10. Interview Preparation
11. AI Mock Interview
12. Learning Center
13. Documents
14. Saved Jobs
15. Alerts
16. Agent Activity (transparency: which agent did what, with evidence)
17. Security & Privacy (data controls, autonomy mode)
18. Settings

## S26-Ultra-specific considerations

- Adaptive layout: two-pane on the S26 Ultra's ~6.9" display; navigation rail instead of bottom bar on width ≥ 600dp.
- Dark mode first-class; large-type support.
- BiometricPrompt for viewing/editing PII and for authorizing consequential actions.
- Background sync via WorkManager with battery/network constraints.
- Secure storage via EncryptedSharedPreferences + Keystore.
- Offline-first for saved jobs and profile drafts.

## Verification UI contract

The `Job Verification` screen renders the `VerificationReport` as-is:
- Composite status badge with the 5 states (`VERIFIED`, `PARTIALLY_VERIFIED`, `UNVERIFIED`, `HIGH_RISK`, `CONFLICTING`).
- Per-signal cards with plain factual explanations and links to source evidence.
- No defamatory language — the backend already enforces this.
