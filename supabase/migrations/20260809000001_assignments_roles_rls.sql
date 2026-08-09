-- Allow participants to read their own assignments
CREATE POLICY "Participants can read own assignments"
    ON public.assignments
    FOR SELECT
    USING (auth.uid() = participant_id);

-- Allow participants to read their own roles
CREATE POLICY "Participants can read own roles"
    ON public.participant_roles
    FOR SELECT
    USING (auth.uid() = participant_id);
