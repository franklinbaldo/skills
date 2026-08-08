-- Canonical Agent Skills audit views over the RFC 0006 typed projection.
--
-- Input contract:
--   okf_types."Skill"
--   okf_types."SkillResource"
--   okf_types."SkillRelation"
--   okf_types."SkillEval"
--   okf_types."SkillMention"
--   okf_types."SkillRoutingRun"
--
-- These are observations and review queues, not universal lint rules.

CREATE SCHEMA IF NOT EXISTS audit;

CREATE OR REPLACE VIEW audit.eval_coverage AS
SELECT
    s.name AS skill,
    count(e.case_index) AS eval_count,
    count(e.case_index) FILTER (WHERE e.should_trigger IS TRUE) AS positive_count,
    count(e.case_index) FILTER (WHERE e.should_trigger IS FALSE) AS negative_count,
    count(e.case_index) > 0 AS has_routing_evals
FROM okf_types."Skill" AS s
LEFT JOIN okf_types."SkillEval" AS e
    ON e.skill = s.name
GROUP BY s.name;

CREATE OR REPLACE VIEW audit.skill_relations AS
SELECT
    r.source_skill,
    r.target_skill,
    r.target_kind,
    r.source_line,
    r.resolved,
    coalesce(r.evidence_kind, 'authored_link') AS evidence_kind,
    r.review_reason
FROM okf_types."SkillRelation" AS r
WHERE r.target_kind = 'skill'
ORDER BY r.source_skill, r.target_skill, r.source_line;

CREATE OR REPLACE VIEW audit.mentions_without_edge AS
SELECT
    m.source_skill,
    m.target_skill,
    count(*) AS mention_count,
    min(m.source_line) AS first_source_line
FROM okf_types."SkillMention" AS m
WHERE NOT EXISTS (
    SELECT 1
    FROM okf_types."SkillRelation" AS r
    WHERE r.resolved IS TRUE
      AND r.target_kind = 'skill'
      AND r.source_skill = m.source_skill
      AND r.target_skill = m.target_skill
)
GROUP BY m.source_skill, m.target_skill
ORDER BY mention_count DESC, m.source_skill, m.target_skill;

CREATE OR REPLACE VIEW audit.isolated_skills AS
SELECT s.name AS skill
FROM okf_types."Skill" AS s
WHERE NOT EXISTS (
    SELECT 1
    FROM okf_types."SkillRelation" AS r
    WHERE r.resolved IS TRUE
      AND r.target_kind = 'skill'
      AND (r.source_skill = s.name OR r.target_skill = s.name)
)
ORDER BY s.name;

CREATE OR REPLACE VIEW audit.resource_surface AS
SELECT
    s.name AS skill,
    count(r.source_path) AS resource_count,
    count(r.source_path) FILTER (WHERE r.kind = 'reference') AS reference_count,
    count(r.source_path) FILTER (WHERE r.kind = 'script') AS script_count,
    count(r.source_path) FILTER (WHERE r.kind = 'eval') AS eval_resource_count,
    coalesce(sum(r.size_bytes), 0)::UBIGINT AS total_resource_bytes,
    coalesce(sum(r.line_count), 0)::UBIGINT AS total_resource_lines
FROM okf_types."Skill" AS s
LEFT JOIN okf_types."SkillResource" AS r
    ON r.skill = s.name
GROUP BY s.name;

CREATE OR REPLACE VIEW audit.routing_run_coverage AS
SELECT
    skill,
    count(*) AS planned_runs,
    count(observed_trigger) AS observed_runs,
    count(*) FILTER (WHERE execution_status = 'error') AS failed_runs,
    count(*) FILTER (WHERE execution_status IS NULL) AS pending_runs,
    CASE
        WHEN count(*) = 0 THEN NULL
        ELSE count(observed_trigger)::DOUBLE / count(*)
    END AS completion_rate
FROM okf_types."SkillRoutingRun"
GROUP BY skill
ORDER BY skill;

CREATE OR REPLACE VIEW audit.routing_case_results AS
SELECT
    skill,
    case_index,
    any_value(should_trigger) AS should_trigger,
    count(*) AS planned_runs,
    count(observed_trigger) AS observed_runs,
    count(*) FILTER (WHERE execution_status = 'error') AS failed_runs,
    count(*) FILTER (WHERE execution_status IS NULL) AS pending_runs,
    count(*) FILTER (WHERE observed_trigger IS TRUE) AS trigger_count,
    CASE
        WHEN count(observed_trigger) = 0 THEN NULL
        ELSE count(*) FILTER (WHERE observed_trigger IS TRUE)::DOUBLE / count(observed_trigger)
    END AS trigger_rate,
    CASE
        WHEN count(*) FILTER (WHERE execution_status IS NULL) > 0
          OR count(*) FILTER (WHERE execution_status = 'error') > 0
            THEN NULL
        ELSE count(*) FILTER (WHERE observed_trigger IS TRUE) * 2 >= count(observed_trigger)
    END AS majority_trigger,
    CASE
        WHEN count(*) FILTER (WHERE execution_status IS NULL) > 0
          OR count(*) FILTER (WHERE execution_status = 'error') > 0
            THEN NULL
        WHEN any_value(should_trigger) IS TRUE
             AND count(*) FILTER (WHERE observed_trigger IS TRUE) * 2 >= count(observed_trigger)
            THEN 'true_positive'
        WHEN any_value(should_trigger) IS TRUE THEN 'false_negative'
        WHEN count(*) FILTER (WHERE observed_trigger IS TRUE) * 2 >= count(observed_trigger)
            THEN 'false_positive'
        ELSE 'true_negative'
    END AS outcome
FROM okf_types."SkillRoutingRun"
GROUP BY skill, case_index
ORDER BY skill, case_index;

CREATE OR REPLACE VIEW audit.routing_skill_results AS
SELECT
    skill,
    count(*) AS case_count,
    count(*) FILTER (WHERE outcome IS NOT NULL) AS completed_cases,
    sum(failed_runs)::UBIGINT AS failed_runs,
    sum(pending_runs)::UBIGINT AS pending_runs,
    count(*) FILTER (WHERE outcome = 'true_positive') AS true_positive,
    count(*) FILTER (WHERE outcome = 'true_negative') AS true_negative,
    count(*) FILTER (WHERE outcome = 'false_positive') AS false_positive,
    count(*) FILTER (WHERE outcome = 'false_negative') AS false_negative,
    CASE
        WHEN count(*) FILTER (WHERE outcome IS NOT NULL) = 0 THEN NULL
        ELSE (
            count(*) FILTER (WHERE outcome IN ('true_positive', 'true_negative'))::DOUBLE
            / count(*) FILTER (WHERE outcome IS NOT NULL)
        )
    END AS accuracy
FROM audit.routing_case_results
GROUP BY skill
ORDER BY skill;
