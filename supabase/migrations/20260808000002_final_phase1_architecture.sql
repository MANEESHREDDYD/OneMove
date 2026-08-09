-- 20260808000002_final_phase1_architecture.sql
-- Enforce participant identity, expand assignments, and fix probe_observations

-- 1. Enforce participants.id == auth.uid() invariant
ALTER TABLE public.participants ADD CONSTRAINT fk_participant_auth FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;

-- 2. Add study_phase to studies
CREATE TYPE study_phase_type AS ENUM ('DRY_RUN', 'EXPERIMENT_A', 'EXPERIMENT_B');
ALTER TABLE public.studies ADD COLUMN study_phase study_phase_type NOT NULL DEFAULT 'DRY_RUN';

-- 3. Extend assignments with structural fields
ALTER TABLE public.assignments ADD COLUMN zone_cluster TEXT NOT NULL DEFAULT 'UNKNOWN';
ALTER TABLE public.assignments ADD COLUMN platform TEXT NOT NULL DEFAULT 'UNKNOWN';
ALTER TABLE public.assignments ADD COLUMN intent TEXT NOT NULL DEFAULT 'UNKNOWN';
ALTER TABLE public.assignments ADD COLUMN protocol TEXT NOT NULL DEFAULT 'ANCHOR';
ALTER TABLE public.assignments ADD COLUMN scheduled_for TIMESTAMPTZ;
ALTER TABLE public.assignments ADD COLUMN protocol_version TEXT NOT NULL DEFAULT '1.0';
ALTER TABLE public.assignments ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE';

-- 4. Make participant_roles study-scoped
-- We need to drop the old unique constraint and add study_id
ALTER TABLE public.participant_roles DROP CONSTRAINT IF EXISTS participant_roles_participant_id_role_key;
ALTER TABLE public.participant_roles ADD COLUMN study_id UUID REFERENCES public.studies(id) ON DELETE CASCADE;
-- For existing rows, this might be null, but we'll assume a fresh db reset or update them.
ALTER TABLE public.participant_roles ADD CONSTRAINT participant_roles_participant_study_role_key UNIQUE(participant_id, study_id, role);

-- 5. Fix probe_observations references
-- We already have participant_id referencing auth.users in probe_observations, but it should conceptually be referencing participants
ALTER TABLE public.probe_observations DROP CONSTRAINT IF EXISTS probe_observations_participant_id_fkey;
ALTER TABLE public.probe_observations ADD CONSTRAINT fk_probe_participant FOREIGN KEY (participant_id) REFERENCES public.participants(id) ON DELETE CASCADE;

-- Add FKs for study_id and assignment_id
ALTER TABLE public.probe_observations ADD CONSTRAINT fk_probe_study FOREIGN KEY (study_id) REFERENCES public.studies(id) ON DELETE CASCADE;
ALTER TABLE public.probe_observations ADD CONSTRAINT fk_probe_assignment FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;

-- 6. Assignment-Aware RLS for probe_observations
-- Drop old policies
DROP POLICY IF EXISTS "Participant can insert own probe observations" ON public.probe_observations;
DROP POLICY IF EXISTS "Participant can select own probe observations" ON public.probe_observations;

-- New INSERT policy:
-- 1. participant_id = auth.uid()
-- 2. assignment belongs to participant and study
-- 3. structural fields match assignment
CREATE POLICY "Participant can insert own valid probes"
    ON public.probe_observations
    FOR INSERT
    WITH CHECK (
        auth.uid() = participant_id AND
        EXISTS (
            SELECT 1 FROM public.assignments a
            WHERE a.id = probe_observations.assignment_id 
              AND a.participant_id = auth.uid()
              AND a.study_id = probe_observations.study_id
              AND a.status = 'ACTIVE'
              AND a.zone_cluster = probe_observations.zone_cluster
              AND a.platform = probe_observations.platform
              AND a.intent = probe_observations.intent
              AND a.protocol = probe_observations.protocol
        )
    );

-- New SELECT policy for participants (own probes)
CREATE POLICY "Participant can select own probes"
    ON public.probe_observations
    FOR SELECT
    USING (auth.uid() = participant_id);

-- New SELECT policy for Owner QC
CREATE POLICY "Owner QC can read probes for authorized studies"
    ON public.probe_observations
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.participant_roles pr
            WHERE pr.participant_id = auth.uid()
              AND pr.study_id = probe_observations.study_id
              AND pr.role = 'OWNER'
        )
    );

-- 7. Current-State View for Correction Semantics
CREATE VIEW public.probe_observations_current AS
SELECT p.* 
FROM public.probe_observations p
WHERE NOT EXISTS (
    SELECT 1 FROM public.probe_observations c 
    WHERE c.supersedes_id = p.id 
      AND c.record_status = 'ACTIVE'
) AND p.record_status = 'ACTIVE';

