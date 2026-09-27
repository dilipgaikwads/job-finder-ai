package com.jobfinderai.ui

import com.jobfinderai.domain.SignalOutcome
import com.jobfinderai.domain.VerificationReport
import com.jobfinderai.domain.VerificationStatus

/**
 * Placeholder — real screen will be @Composable once the Gradle build is set up.
 * Kept as a pure Kotlin function so the verification-status → user-facing-text mapping
 * (which is the enforcement-relevant part) can be unit-tested today.
 */
object JobVerificationScreen {
    fun badgeText(status: VerificationStatus): String = when (status) {
        VerificationStatus.VERIFIED -> "✓ Verified"
        VerificationStatus.PARTIALLY_VERIFIED -> "⚠ Partially verified"
        VerificationStatus.UNVERIFIED -> "? Unverified"
        VerificationStatus.CONFLICTING -> "⚠ Conflicting sources"
        VerificationStatus.HIGH_RISK -> "⚠ High risk"
    }

    fun signalIcon(outcome: SignalOutcome): String = when (outcome) {
        SignalOutcome.PASS -> "✓"
        SignalOutcome.WARN -> "!"
        SignalOutcome.FAIL -> "×"
        SignalOutcome.INCONCLUSIVE -> "?"
    }

    /** Render-order rules: fails first, then warnings, then passes, then inconclusive. */
    fun orderedSignals(report: VerificationReport) =
        report.signals.sortedBy {
            when (it.outcome) {
                SignalOutcome.FAIL -> 0
                SignalOutcome.WARN -> 1
                SignalOutcome.PASS -> 2
                SignalOutcome.INCONCLUSIVE -> 3
            }
        }
}
