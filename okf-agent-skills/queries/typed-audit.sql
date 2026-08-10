-- Canonical Agent Skills audit views over the static OKF/DuckDB projection.
-- Production learning comes from real-use postmortems and GitHub feedback issues.
-- Static routing evals remain regression memory; they are not expanded into synthetic runs.

CREATE SCHEMA IF NOT EXISTS audit;

CREATE OR REPLACE VIEW audit.eval_coverage AS
SELECT
    s.name AS skill,
    count(e.case_index) AS eval_count,
    count(e.case_index) FILTER (WHERE e.should_trigger IS TRUE) AS positive_count,
    count(e.case_index) FILTER (WHERE e.should_trigger IS FALSE) AS negative_count,
    count(e.case_index) > 0 AS has_routing_evals
FROM okf_types."Skill" AS s
LEFT JOIN okf_types."SkillEval" AS e ON e.skill = s.name
GROUP BY s.name
ORDER BY s.name;

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
LEFT JOIN okf_types."SkillResource" AS r ON r.skill = s.name
GROUP BY s.name
ORDER BY s.name;
