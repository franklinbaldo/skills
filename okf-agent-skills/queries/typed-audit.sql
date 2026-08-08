-- Canonical Agent Skills audit views over the OKF/DuckDB projection.
-- Behavioral observations arrive as imported SkillRoutingObservation concepts;
-- planned and pending runs are derived relationally from SkillEval × repetitions.

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
LEFT JOIN okf_types."SkillResource" AS r ON r.skill = s.name
GROUP BY s.name;

CREATE OR REPLACE VIEW audit.routing_observations AS
SELECT
    json_extract_string(frontmatter_json, '$.observation_id') AS observation_id,
    json_extract_string(frontmatter_json, '$.skill') AS skill,
    try_cast(json_extract_string(frontmatter_json, '$.case_index') AS INTEGER) AS case_index,
    try_cast(json_extract_string(frontmatter_json, '$.repetition') AS INTEGER) AS repetition,
    try_cast(json_extract_string(frontmatter_json, '$.should_trigger') AS BOOLEAN) AS should_trigger,
    json_extract_string(frontmatter_json, '$.query_sha256') AS query_sha256,
    try_cast(json_extract_string(frontmatter_json, '$.observed_trigger') AS BOOLEAN) AS observed_trigger,
    json_extract_string(frontmatter_json, '$.runner') AS runner,
    json_extract_string(frontmatter_json, '$.model') AS model,
    json_extract_string(frontmatter_json, '$.error') AS error,
    path AS source_path
FROM okf.concepts
WHERE concept_type = 'SkillRoutingObservation';

CREATE OR REPLACE VIEW audit.routing_observation_mismatches AS
WITH config AS (
    SELECT routing_repetitions
    FROM okf_types."AgentSkillsProjection"
    LIMIT 1
)
SELECT o.*
FROM audit.routing_observations AS o
LEFT JOIN okf_types."SkillEval" AS e
    ON e.skill = o.skill AND e.case_index = o.case_index
CROSS JOIN config
WHERE e.skill IS NULL
   OR o.should_trigger IS DISTINCT FROM e.should_trigger
   OR o.query_sha256 IS DISTINCT FROM e.query_sha256
   OR o.repetition < 1
   OR o.repetition > config.routing_repetitions
ORDER BY o.skill, o.case_index, o.repetition;

CREATE OR REPLACE VIEW audit.routing_runs AS
WITH config AS (
    SELECT routing_repetitions
    FROM okf_types."AgentSkillsProjection"
    LIMIT 1
), planned AS (
    SELECT
        e.skill,
        e.case_index,
        repetitions.repetition,
        e.should_trigger,
        e.query_sha256
    FROM okf_types."SkillEval" AS e
    CROSS JOIN config
    CROSS JOIN range(1, config.routing_repetitions + 1) AS repetitions(repetition)
)
SELECT
    p.skill,
    p.case_index,
    p.repetition,
    p.should_trigger,
    p.query_sha256,
    o.observation_id,
    o.observed_trigger,
    o.runner,
    o.model,
    o.error
FROM planned AS p
LEFT JOIN audit.routing_observations AS o
    ON o.skill = p.skill
   AND o.case_index = p.case_index
   AND o.repetition = p.repetition
ORDER BY p.skill, p.case_index, p.repetition;

CREATE OR REPLACE VIEW audit.routing_run_coverage AS
SELECT
    skill,
    count(*) AS planned_runs,
    count(observed_trigger) AS observed_runs,
    count(*) FILTER (WHERE error IS NOT NULL) AS failed_runs,
    count(*) FILTER (WHERE observation_id IS NULL) AS pending_runs,
    count(observation_id)::DOUBLE / count(*) AS attempted_rate,
    count(observed_trigger)::DOUBLE / count(*) AS completion_rate
FROM audit.routing_runs
GROUP BY skill
ORDER BY skill;

CREATE OR REPLACE VIEW audit.routing_case_results AS
SELECT
    skill,
    case_index,
    any_value(should_trigger) AS should_trigger,
    count(*) AS planned_runs,
    count(observed_trigger) AS observed_runs,
    count(*) FILTER (WHERE error IS NOT NULL) AS failed_runs,
    count(*) FILTER (WHERE observation_id IS NULL) AS pending_runs,
    count(*) FILTER (WHERE observed_trigger IS TRUE) AS trigger_count,
    CASE
        WHEN count(observed_trigger) = 0 THEN NULL
        ELSE count(*) FILTER (WHERE observed_trigger IS TRUE)::DOUBLE / count(observed_trigger)
    END AS trigger_rate,
    CASE
        WHEN count(*) FILTER (WHERE observation_id IS NULL OR error IS NOT NULL) > 0 THEN NULL
        ELSE count(*) FILTER (WHERE observed_trigger IS TRUE) * 2 >= count(observed_trigger)
    END AS majority_trigger,
    CASE
        WHEN count(*) FILTER (WHERE observation_id IS NULL OR error IS NOT NULL) > 0 THEN NULL
        WHEN any_value(should_trigger) IS TRUE
             AND count(*) FILTER (WHERE observed_trigger IS TRUE) * 2 >= count(observed_trigger)
            THEN 'true_positive'
        WHEN any_value(should_trigger) IS TRUE THEN 'false_negative'
        WHEN count(*) FILTER (WHERE observed_trigger IS TRUE) * 2 >= count(observed_trigger)
            THEN 'false_positive'
        ELSE 'true_negative'
    END AS outcome
FROM audit.routing_runs
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
        ELSE count(*) FILTER (WHERE outcome IN ('true_positive', 'true_negative'))::DOUBLE
             / count(*) FILTER (WHERE outcome IS NOT NULL)
    END AS accuracy
FROM audit.routing_case_results
GROUP BY skill
ORDER BY skill;
