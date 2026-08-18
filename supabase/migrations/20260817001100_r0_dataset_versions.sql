-- ---------------------------------------------------------------------------
-- R0 execution plane, part 2: dataset_versions
--
-- The first execution-plane migration shipped collection_runs, checkpoints,
-- provider_states, scheduler_locks and artifact_registry but left every run
-- asserting a bare `dataset_version` string with nothing to check it against.
-- That makes a typo indistinguishable from a real version bump, and it leaves
-- R2/R7 unable to answer "what did version 1.0.0 of this dataset actually mean"
-- once the collector's code has moved on.
--
-- dataset_versions is that registry: one row per (dataset_id, dataset_version),
-- declaring the schema, the provider contract and the code SHA that produced it.
-- collection_runs then references it, so a run can only claim a version that has
-- been declared.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS zonepilot_exec.dataset_versions (
  dataset_id        text NOT NULL CHECK (length(dataset_id) BETWEEN 1 AND 128),
  dataset_version   text NOT NULL CHECK (length(dataset_version) BETWEEN 1 AND 128),

  provider          text NOT NULL CHECK (length(provider) BETWEEN 1 AND 128),
  schema_name       text NOT NULL CHECK (length(schema_name) BETWEEN 1 AND 128),
  schema_version    text NOT NULL CHECK (length(schema_version) BETWEEN 1 AND 32),

  -- The evidence grade every record of this version carries. Reusing the
  -- canonical 9-value enum keeps this from drifting from the contract.
  evidence_class    zonepilot_temporal.evidence_class NOT NULL,

  -- Which unit set the features of this version are expressed in. Without this
  -- a consumer cannot safely compare 1.0.0 against 1.1.0.
  feature_unit_set_id char(64)
      REFERENCES zonepilot_temporal.feature_unit_sets (unit_set_id),

  -- Provenance of the code that produced the version.
  public_code_sha   char(40) CHECK (public_code_sha IS NULL OR public_code_sha ~ '^[0-9a-f]{40}$'),
  description       text CHECK (description IS NULL OR length(description) <= 1024),

  -- Lifecycle. A superseded version stays readable forever; it just stops
  -- being a legal target for new runs.
  status            text NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'RETRACTED')),
  declared_at       timestamptz NOT NULL DEFAULT now(),
  superseded_at     timestamptz,

  CONSTRAINT dataset_versions_pkey PRIMARY KEY (dataset_id, dataset_version),
  CONSTRAINT dataset_versions_supersede_is_consistent CHECK (
    (status = 'ACTIVE') = (superseded_at IS NULL)
  )
);

COMMENT ON TABLE zonepilot_exec.dataset_versions IS
  'Declared dataset versions. A run may only claim a version registered here, so a '
  'typo cannot masquerade as a version bump and every stored row has a resolvable contract.';

CREATE INDEX IF NOT EXISTS dataset_versions_active_idx
  ON zonepilot_exec.dataset_versions (dataset_id, declared_at DESC)
  WHERE status = 'ACTIVE';

-- Declare the version the R1 Open-Meteo pilot already writes under, so the
-- foreign key below can be added without orphaning the rows already stored.
INSERT INTO zonepilot_exec.dataset_versions
      (dataset_id, dataset_version, provider, schema_name, schema_version,
       evidence_class, description)
VALUES ('openmeteo-weather-forecast-h3r8-blr-pilot', '1.0.0', 'open-meteo',
        'weather_forecast_hourly', '1.0.0', 'PUBLIC_OFFICIAL',
        'Hourly Open-Meteo forecast for the 94 H3 R8 cells of the R1 Bengaluru pilot, '
        'versioned by provider issue cycle.')
ON CONFLICT (dataset_id, dataset_version) DO NOTHING;

-- Backfill the unit set actually in use, if exactly one is registered.
UPDATE zonepilot_exec.dataset_versions AS dv
   SET feature_unit_set_id = fr.feature_unit_set_id
  FROM (
    SELECT DISTINCT dataset_id, dataset_version, feature_unit_set_id
      FROM zonepilot_temporal.feature_records
  ) AS fr
 WHERE dv.dataset_id = fr.dataset_id
   AND dv.dataset_version = fr.dataset_version
   AND dv.feature_unit_set_id IS NULL;

-- Now that every existing run's version is declared, make the reference real.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conname = 'collection_runs_dataset_version_fkey'
       AND conrelid = 'zonepilot_exec.collection_runs'::regclass
  ) THEN
    ALTER TABLE zonepilot_exec.collection_runs
      ADD CONSTRAINT collection_runs_dataset_version_fkey
      FOREIGN KEY (dataset_id, dataset_version)
      REFERENCES zonepilot_exec.dataset_versions (dataset_id, dataset_version);
  END IF;
END
$$;

-- The collector reads the registry to validate itself; it must not be able to
-- invent a version, so no INSERT/UPDATE here.
GRANT SELECT ON zonepilot_exec.dataset_versions TO zonepilot_r0_collector;

REVOKE ALL ON zonepilot_exec.dataset_versions FROM PUBLIC, anon, authenticated;
