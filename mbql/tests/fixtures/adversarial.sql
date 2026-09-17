-- Adversarial fixture for future DuckDB SQL <-> Metabase MBQL differential execution.
-- Keep tiny but semantically separating: NULLs, duplicates, missing joins, negatives,
-- zeros, case differences, Unicode and boundary-ish timestamps.

CREATE TABLE customers (
    id INTEGER,
    name VARCHAR,
    active BOOLEAN
);

INSERT INTO customers VALUES
    (1, 'Alice', TRUE),
    (2, 'alice', FALSE),
    (3, 'Álvaro', TRUE),
    (4, NULL, NULL);

CREATE TABLE orders (
    id INTEGER,
    customer_id INTEGER,
    total DOUBLE,
    quantity INTEGER,
    status VARCHAR,
    created_at TIMESTAMP
);

INSERT INTO orders VALUES
    (1, 1, 100.0, 1, 'paid', TIMESTAMP '1970-01-01 00:00:00'),
    (2, 1, 100.0, 1, 'paid', TIMESTAMP '2026-09-17 12:00:00'),
    (3, 2, 0.0, 0, 'open', TIMESTAMP '2026-09-17 12:00:01'),
    (4, 3, -10.0, -1, 'OPEN', NULL),
    (5, 999, NULL, 2, NULL, TIMESTAMP '2038-01-19 03:14:07'),
    (6, NULL, 50.5, 2, '', TIMESTAMP '2000-02-29 23:59:59'),
    (7, 4, 50.5, 2, '', TIMESTAMP '2000-02-29 23:59:59');
