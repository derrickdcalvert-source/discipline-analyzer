# Atlas Ingestion Contract (v1.2)

This contract defines the non-negotiable conditions required for Atlas to generate a full Decision Brief.

## Required Inputs
- Two CSV files per run:
  1) Incident File
  2) Consequence File

## Join Rules
- Join key: Incident Number
- No fallback joins permitted
- Join success must be ≥ 95%
- If join success < 95%, ingestion halts

## Instructional Minutes
- Minutes per instructional day: 480
- Weekends excluded
- Inclusive date counting
- Partial days:
  - If explicit instructional minutes exist, use them
  - If not, count as a full instructional day (480 minutes)
  - Never infer partial days

## Consequence Types (case-insensitive)
- ISS
- OSS
- DAEP
- JJAEP
- EXPULSION
- LOCAL_ONLY

## Enforcement
- No partial briefs
- No silent fallbacks
- No inferred data
- If requirements are not met, Atlas halts with an operator-facing error
