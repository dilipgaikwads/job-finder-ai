"""User professional profile — never invented, only user-supplied or user-confirmed."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class Skill(BaseModel):
    name: str
    years: float | None = None
    last_used: date | None = None
    source: Literal["user_supplied", "extracted_from_resume", "inferred_from_project"]


class WorkExperience(BaseModel):
    company: str
    title: str
    start: date
    end: date | None = None  # None = current
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str
    field: str | None = None
    start: date | None = None
    end: date | None = None


class Certification(BaseModel):
    name: str
    issuer: str
    issued: date | None = None
    expires: date | None = None
    credential_url: HttpUrl | None = None


class Project(BaseModel):
    name: str
    description: str
    url: HttpUrl | None = None
    technologies: list[str] = Field(default_factory=list)
    role: str | None = None


class WorkAuthorization(BaseModel):
    country: str  # ISO 3166-1 alpha-2
    status: Literal["citizen", "permanent_resident", "work_visa", "needs_sponsorship", "other"]
    notes: str | None = None


class Preferences(BaseModel):
    remote_only: bool = False
    hybrid_ok: bool = True
    onsite_ok: bool = False
    preferred_locations: list[str] = Field(default_factory=list)
    open_to_relocation: bool = False
    open_to_international: bool = False
    min_base_salary_usd: float | None = None
    target_base_salary_usd: float | None = None
    role_interests: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class Profile(BaseModel):
    user_id: str
    full_name: str | None = None
    email: EmailStr | None = None
    headline: str | None = None
    summary: str | None = None
    skills: list[Skill] = Field(default_factory=list)
    experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    work_authorization: list[WorkAuthorization] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)
    github_url: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None
    portfolio_url: HttpUrl | None = None

    def total_years_experience(self) -> float:
        # Deterministic aggregate — not "inferred market fact", just arithmetic over user-supplied data.
        from datetime import date as _d
        total_days = 0
        for e in self.experience:
            end = e.end or _d.today()
            total_days += max(0, (end - e.start).days)
        return round(total_days / 365.25, 1)
