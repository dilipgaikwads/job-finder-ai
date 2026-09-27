package com.jobfinderai.domain

/**
 * Kotlin mirrors of the backend evidence/verification models.
 * Kept intentionally small until the Gradle build is wired; use kotlinx.serialization then.
 */

enum class VerificationStatus { VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, CONFLICTING, HIGH_RISK }

enum class SignalOutcome { PASS, WARN, FAIL, INCONCLUSIVE }

data class VerificationSignal(
    val name: String,
    val outcome: SignalOutcome,
    val weight: Double,
    val explanation: String,
    val evidenceIds: List<String>,
)

data class VerificationReport(
    val jobId: String,
    val signals: List<VerificationSignal>,
    val compositeStatus: VerificationStatus,
    val summary: String,
    val riskFlags: List<String>,
)
