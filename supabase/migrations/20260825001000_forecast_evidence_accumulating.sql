-- Let a forecast record say "no prediction yet" instead of inventing one.
--
-- predict_forecast deliberately writes predicted_value = NULL together with a
-- NULL model, dataset and graph version: no forecast has been produced, so
-- there is no model that produced it and no feature snapshot behind it. That is
-- the truthful EVIDENCE_ACCUMULATING state introduced when fabricated forecast
-- values were removed (F-018).
--
-- The table declared those columns NOT NULL, so every such insert failed and
-- the API reported FORECAST_STORE_UNAVAILABLE -- blaming the store for a
-- contract disagreement, while the only way to satisfy the schema was to
-- invent values. A schema that cannot represent "unavailable" pressures the
-- code into fabricating data, which is the opposite of what this system is for.
--
-- NULL here means "not yet produced". A record that HAS a prediction must still
-- carry the lineage that produced it, which the CHECK below enforces.

ALTER TABLE public.forecast_records ALTER COLUMN predicted_value DROP NOT NULL;
ALTER TABLE public.forecast_records ALTER COLUMN model_version DROP NOT NULL;
ALTER TABLE public.forecast_records ALTER COLUMN feature_dataset_version DROP NOT NULL;
ALTER TABLE public.forecast_records ALTER COLUMN graph_version DROP NOT NULL;

-- A prediction without provenance is exactly the defect F-018 removed, so the
-- permissive nullability must not become a way to record an unattributed number.
ALTER TABLE public.forecast_records
    DROP CONSTRAINT IF EXISTS forecast_prediction_requires_lineage;
ALTER TABLE public.forecast_records
    ADD CONSTRAINT forecast_prediction_requires_lineage CHECK (
        predicted_value IS NULL
        OR (
            model_version IS NOT NULL
            AND feature_dataset_version IS NOT NULL
            AND graph_version IS NOT NULL
        )
    );

COMMENT ON COLUMN public.forecast_records.predicted_value IS
    'NULL = no forecast produced yet (EVIDENCE_ACCUMULATING). A non-NULL value requires model, dataset and graph lineage.';
